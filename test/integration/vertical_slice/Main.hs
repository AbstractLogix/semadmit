{-# LANGUAGE OverloadedStrings #-}

module Main (main) where

import Control.Exception (bracket, finally)
import Control.Monad (forM_, unless)
import Core.CLI (runCLI)
import Core.Decision
  ( ComponentDeclaration (..)
  , ComponentPayload (..)
  , Diagnostic (..)
  , EvidenceDeclaration (..)
  , Outcome (..)
  , SubjectDeclaration (..)
  )
import Core.Evaluator (evaluateRequest)
import Core.Identity (PackIdentity, artifactDigest, canonicalBytes)
import Core.Pack
  ( NormalizedPackRequest (..)
  , OperationDescriptor (..)
  , Pack (..)
  , PackBehavior (..)
  , PackDescriptor (..)
  , PackInputError (..)
  , PackRegistry
  , PackResult (..)
  , mkPackRegistry
  , packIdentityFor
  )
import Core.Protocol (InputError (..), errorEnvelope, maxRequestBytes, protocolVersion)
import Data.Aeson
  ( Value (..)
  , eitherDecodeStrict'
  , object
  , (.=)
  )
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString qualified as ByteString
import Data.ByteString.Lazy qualified as LazyByteString
import Data.Map.Strict qualified as Map
import Data.Set qualified as Set
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Vector qualified as Vector
import System.Directory (removeFile)
import System.Exit (ExitCode (..))
import System.IO
  ( Handle
  , SeekMode (AbsoluteSeek)
  , hClose
  , hFileSize
  , hFlush
  , hSeek
  , openBinaryTempFile
  )

main :: IO ()
main = do
  registry <- case mkPackRegistry [fixturePack] of
    Left err -> fail ("vertical-slice pack was rejected: " <> show err)
    Right value -> pure value
  source <- ByteString.readFile "test/integration/vertical_slice/vectors.json"
  case eitherDecodeStrict' source of
    Left message -> fail ("vertical-slice vectors are invalid JSON: " <> message)
    Right (Object root) -> case (KeyMap.lookup "format" root, KeyMap.lookup "implementations" root, KeyMap.lookup "scope" root, KeyMap.lookup "excludes" root, KeyMap.lookup "cases" root) of
      (Just (String "semadmit-core-parity-cases/0.1"), Just (Array implementations), Just (Array scope), Just (Array excludes), Just (Array cases)) -> do
        unless (implementations == Vector.fromList [String "python", String "haskell"]) $
          fail "Core parity corpus must name both implementations"
        unless
          ( scope
              == Vector.fromList
                [ String "Core request normalization"
                , String "generic subject, evidence, and component bindings"
                , String "obligation reduction"
                , String "decision payload and digest"
                ]
          ) $
          fail "Core parity corpus scope changed without a test update"
        unless (excludes == Vector.fromList [String "semadmit/claim/0.1", String "isoprax/0.1 domain semantics"]) $
          fail "Core parity corpus scope must exclude unshared pack semantics"
        unless (Vector.length cases == 2) $ fail "Core parity corpus must contain both decisions"
        let vectors = Vector.toList cases
        unless (map (field "id") vectors == [Just (String "admissible"), Just (String "inadmissible")]) $
          fail "Core parity corpus cases must retain their stable identities"
        forM_ vectors (checkVector registry)
        checkCLI registry vectors
      _ -> fail "Core parity corpus metadata or cases are missing"
    Right _ -> fail "vertical-slice root must be an object"

checkVector :: PackRegistry -> Value -> IO ()
checkVector registry vector = case (field "id" vector, field "request" vector, field "expected" vector) of
  (Just (String identifier), Just request, Just expected) -> case canonicalBytes request of
    Left err -> fail ("could not encode vertical-slice request: " <> show err)
    Right bytes -> do
      actual <- evaluateRequest registry (LazyByteString.toStrict bytes)
      unless (actual == expected) $
        fail ("Haskell vertical-slice result differs for " <> Text.unpack identifier)
  _ -> fail "malformed vertical-slice vector"

checkCLI :: PackRegistry -> [Value] -> IO ()
checkCLI registry vectors = do
  passVector <- requireVector "admissible" vectors
  failVector <- requireVector "inadmissible" vectors
  passRequest <- requireField "request" passVector
  failRequest <- requireField "request" failVector
  passExpectedValue <- requireField "expected" passVector
  failExpectedValue <- requireField "expected" failVector
  passInput <- canonicalSource passRequest
  failInput <- canonicalSource failRequest
  passOutput <- canonicalLine passExpectedValue
  failOutput <- canonicalLine failExpectedValue
  missingRequest <- makeMissingRequest registry passRequest
  missingInput <- canonicalSource missingRequest
  missingValue <- evaluateRequest registry missingInput
  missingOutput <- canonicalLine missingValue
  invalidJsonOutput <- canonicalLine (errorEnvelope (InputError "input.invalid_json" ""))
  limitOutput <- canonicalLine (errorEnvelope (InputError "limit.exceeded" ""))
  internalOutput <- canonicalLine (errorEnvelope (InputError "internal.failure" ""))

  assertCLI "single admissible" registry [] passInput ExitSuccess passOutput ""
  assertCLI "single inadmissible" registry [] failInput (ExitFailure 1) failOutput ""
  assertCLI "single indeterminate" registry [] missingInput (ExitFailure 2) missingOutput ""
  assertCLI "single invalid JSON" registry [] "{" (ExitFailure 3) invalidJsonOutput ""
  let paddingLength = maxRequestBytes - ByteString.length passInput
      maxLengthLine = passInput <> ByteString.replicate paddingLength 32 <> "\n"
  assertCLI "single request limit excludes final LF" registry [] maxLengthLine ExitSuccess passOutput ""
  assertCLI
    "single oversized input"
    registry
    []
    (ByteString.replicate (maxRequestBytes + 1) 32)
    (ExitFailure 3)
    limitOutput
    ""
  assertCLI
    "invalid CLI arguments"
    registry
    ["--unknown"]
    passInput
    (ExitFailure 3)
    ""
    "usage: semantic-oracle [--jsonl]\n"

  let lineLocalInput = passInput <> "\r\n\n" <> failInput <> "\n{"
      lineLocalOutput = passOutput <> invalidJsonOutput <> failOutput <> invalidJsonOutput
  assertCLI "JSONL line-local errors and final line" registry ["--jsonl"] lineLocalInput (ExitFailure 3) lineLocalOutput ""
  assertCLI "empty JSONL input" registry ["--jsonl"] "" ExitSuccess "" ""

  let oversizedLine = ByteString.replicate (maxRequestBytes + 1) 32
      oversizedInput = oversizedLine <> "\n" <> passInput
      oversizedOutput = limitOutput <> passOutput
  assertCLI "JSONL oversized-line recovery" registry ["--jsonl"] oversizedInput (ExitFailure 3) oversizedOutput ""

  crashingRegistry <- makeCrashingRegistry
  let internalInput = passInput <> "\n" <> passInput <> "\n"
  assertCLI "JSONL internal failure stops stream" crashingRegistry ["--jsonl"] internalInput (ExitFailure 4) internalOutput ""

requireVector :: Text -> [Value] -> IO Value
requireVector identifier vectors = case filter ((== Just (String identifier)) . field "id") vectors of
  [vector] -> pure vector
  _ -> fail ("missing vertical-slice vector: " <> Text.unpack identifier)

requireField :: Text -> Value -> IO Value
requireField name value = maybe (fail ("missing vertical-slice field: " <> Text.unpack name)) pure (field name value)

canonicalSource :: Value -> IO ByteString.ByteString
canonicalSource value = case canonicalBytes value of
  Left err -> fail ("could not encode CLI test input: " <> show err)
  Right bytes -> pure (LazyByteString.toStrict bytes)

canonicalLine :: Value -> IO ByteString.ByteString
canonicalLine value = (<> "\n") <$> canonicalSource value

makeMissingRequest :: PackRegistry -> Value -> IO Value
makeMissingRequest registry (Object fields) = do
  identities <- maybe (fail "fixture identity is missing") pure (packIdentityFor "fixture/0.1" "check" registry)
  let policy = object ["mode" .= ("missing" :: Text)]
  policyDigest <- case artifactDigest identities "policy" "fixture/0.1/policy" policy of
    Left err -> fail ("could not compute CLI test policy identity: " <> show err)
    Right digest -> pure digest
  pure
    ( Object
        ( KeyMap.insert "policy" policy
            (KeyMap.insert "policy_digest" (String policyDigest) fields)
        )
    )
makeMissingRequest _ _ = fail "admissible fixture request must be an object"

makeCrashingRegistry :: IO PackRegistry
makeCrashingRegistry = case mkPackRegistry [fixturePack {packBehavior = PackBehavior normalize decode crashEvaluate}] of
  Left err -> fail ("crashing fixture pack was rejected: " <> show err)
  Right registry -> pure registry

crashEvaluate :: Text -> PackIdentity -> NormalizedPackRequest -> PackResult
crashEvaluate _ _ _ = error "fixture internal failure"

assertCLI :: String -> PackRegistry -> [String] -> ByteString.ByteString -> ExitCode -> ByteString.ByteString -> ByteString.ByteString -> IO ()
assertCLI label registry arguments input expectedCode expectedOutput expectedError = do
  (actualCode, actualOutput, actualError) <- captureCLI registry arguments input
  unless (actualCode == expectedCode) $
    fail (label <> " returned " <> show actualCode <> ", expected " <> show expectedCode)
  unless (actualOutput == expectedOutput) $
    fail (label <> " wrote unexpected stdout: " <> show actualOutput)
  unless (actualError == expectedError) $
    fail (label <> " wrote unexpected stderr: " <> show actualError)

captureCLI :: PackRegistry -> [String] -> ByteString.ByteString -> IO (ExitCode, ByteString.ByteString, ByteString.ByteString)
captureCLI registry arguments source =
  withTemporaryHandle "semadmit-cli-input" $ \input ->
    withTemporaryHandle "semadmit-cli-output" $ \output ->
      withTemporaryHandle "semadmit-cli-error" $ \errors -> do
        ByteString.hPut input source
        hSeek input AbsoluteSeek 0
        status <- runCLI registry arguments input output errors
        outputBytes <- readTemporaryHandle output
        errorBytes <- readTemporaryHandle errors
        pure (status, outputBytes, errorBytes)

withTemporaryHandle :: String -> (Handle -> IO result) -> IO result
withTemporaryHandle template action =
  bracket
    (openBinaryTempFile "." template)
    (\(path, handle) -> hClose handle `finally` removeFile path)
    (action . snd)

readTemporaryHandle :: Handle -> IO ByteString.ByteString
readTemporaryHandle handle = do
  hFlush handle
  size <- hFileSize handle
  hSeek handle AbsoluteSeek 0
  ByteString.hGet handle (fromIntegral size)

fixturePack :: Pack
fixturePack =
  Pack
    ( PackDescriptor
        { packId = "fixture/0.1"
        , packProtocolVersions = [protocolVersion]
        , packOperations = Map.singleton "check" fixtureOperation
        }
    )
    (PackBehavior normalize decode evaluate)

fixtureOperation :: OperationDescriptor
fixtureOperation =
  OperationDescriptor
    { operationArtifactDeclarations =
        [ ("policy", "fixture/0.1/policy")
        , ("subject", "fixture/0.1/subject")
        , ("component", "fixture/0.1/component")
        , ("assertion", "fixture/0.1/assertion")
        ]
    , operationSubjectDeclarations = [SubjectDeclaration "item" "subject" "fixture/0.1/subject"]
    , operationComponentDeclarations =
        [ComponentDeclaration "item" "name" "component" "fixture/0.1/component" 1 1]
    , operationEvidenceDeclaration = Just (EvidenceDeclaration "assertion" "fixture/0.1/assertion")
    , operationObligations = ["present"]
    , operationAllowedOutcomes = [Pass, Fail, Missing]
    , operationDiagnosticPointers = Map.singleton "domain.mismatch" ["/subjects/item/name"]
    }

normalize :: Text -> Value -> Value -> [Value] -> Either PackInputError NormalizedPackRequest
normalize _ policy subjects evidence = do
  validatePolicy policy
  validateSubjects subjects
  validateEvidence 0 Set.empty evidence
  Right (NormalizedPackRequest policy subjects evidence Nothing)

validatePolicy :: Value -> Either PackInputError ()
validatePolicy (Object fields) = case KeyMap.lookup "mode" fields of
  Just (String mode)
    | KeyMap.size fields == 1 && mode `elem` ["pass", "fail", "missing"] -> Right ()
  _ -> Left (PackInputError "policy.unsupported" "/policy")
validatePolicy _ = Left (PackInputError "policy.unsupported" "/policy")

validateSubjects :: Value -> Either PackInputError ()
validateSubjects (Object fields) = case KeyMap.lookup "item" fields of
  Just (Object item)
    | KeyMap.size fields == 1
    , KeyMap.size item == 1
    , Just (String _) <- KeyMap.lookup "name" item -> Right ()
  _ -> Left (PackInputError "input.invalid_type" "/subjects")
validateSubjects _ = Left (PackInputError "input.invalid_type" "/subjects")

validateEvidence :: Int -> Set.Set Text -> [Value] -> Either PackInputError ()
validateEvidence _ _ [] = Right ()
validateEvidence index seen (item : rest) = case item of
  Object fields -> case (KeyMap.lookup "id" fields, KeyMap.lookup "present" fields) of
    (Just (String identifier), Just (Bool _))
      | KeyMap.size fields == 2 ->
          if Set.member identifier seen
            then Left (PackInputError "evidence.duplicate_id" ("/evidence/" <> Text.pack (show index) <> "/id"))
            else validateEvidence (index + 1) (Set.insert identifier seen) rest
    _ -> invalidEvidence
  _ -> invalidEvidence
  where
    invalidEvidence = Left (PackInputError "input.invalid_type" ("/evidence/" <> Text.pack (show index)))

decode :: NormalizedPackRequest -> Either () NormalizedPackRequest
decode = Right

evaluate :: Text -> PackIdentity -> NormalizedPackRequest -> PackResult
evaluate _ _ request =
  PackResult
    [ ComponentPayload
        "item"
        "name"
        "component"
        "fixture/0.1/component"
        (object ["name" .= subjectName])
    ]
    [("present", outcome)]
    diagnostics
  where
    subject = field "item" (normalizedSubjects request)
    subjectName = maybe Null String (subject >>= textField "name")
    outcome = case textField "mode" (normalizedPolicy request) of
      Just "fail" -> Fail
      Just "missing" -> Missing
      _ -> Pass
    diagnostics = case outcome of
      Fail -> [Diagnostic "present" "/subjects/item/name" "domain.mismatch"]
      _ -> []

field :: Text -> Value -> Maybe Value
field name (Object fields) = KeyMap.lookup (Key.fromText name) fields
field _ _ = Nothing

textField :: Text -> Value -> Maybe Text
textField name value = case field name value of
  Just (String text) -> Just text
  _ -> Nothing
