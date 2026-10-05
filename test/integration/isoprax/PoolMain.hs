{-# LANGUAGE OverloadedStrings #-}

module IsopraxPoolTest (main) where

import Control.Exception (bracket, finally)
import Control.Monad (forM_, unless)
import Core.Evaluator (evaluateRequest)
import Core.Identity (canonicalBytes)
import Core.Pack (PackRegistry, mkPackRegistry)
import Data.Aeson (Value (..), eitherDecodeStrict', object, (.=))
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString qualified as ByteString
import Data.ByteString.Lazy qualified as LazyByteString
import Data.List (sortOn)
import Data.Text qualified as Text
import Data.Vector qualified as Vector
import Main qualified as Application
import System.Directory (removeFile)
import System.Exit (ExitCode (..))
import System.IO (Handle, SeekMode (AbsoluteSeek), hClose, hFileSize, hFlush, hSeek, openBinaryTempFile)
import Pack.Isoprax.PoolPredictions (isopraxPack)

main :: IO ()
main = do
  registry <- case mkPackRegistry [isopraxPack] of
    Left errorValue -> fail ("Isoprax pack descriptor was rejected: " <> show errorValue)
    Right value -> pure value
  source <- ByteString.readFile "conformance/fixtures/isoprax-cases.json"
  root <- case eitherDecodeStrict' source of
    Left message -> fail ("Isoprax request fixtures are invalid JSON: " <> message)
    Right value -> pure value
  cases <- case field "cases" root of
    Just (Array values) -> pure (Vector.toList values)
    _ -> fail "Isoprax fixture cases are missing"
  forM_ cases (checkCase registry)
  assertThresholdPermutation registry cases

assertThresholdPermutation :: PackRegistry -> [Value] -> IO ()
assertThresholdPermutation registry cases = do
  fixture <- case [value | value <- cases, field "id" value == Just (String "admissible-threshold-multiset-permutation")] of
    [value] -> pure value
    _ -> fail "the threshold multiset permutation fixture is missing or duplicated"
  request <- requiredField "request" fixture
  permuted <- updateObjectPath ["subjects", "left", "definition", "thresholds"] reverseArray request
  originalResult <- evaluateRequestValue registry request
  permutedResult <- evaluateRequestValue registry permuted
  unless (originalResult == permutedResult) $
    fail "threshold array permutation changed the Isoprax request or decision digest"

evaluateRequestValue :: PackRegistry -> Value -> IO Value
evaluateRequestValue registry request = do
  requestBytes <- case canonicalBytes request of
    Left errorValue -> fail ("could not encode threshold permutation request: " <> show errorValue)
    Right bytes -> pure (LazyByteString.toStrict bytes)
  evaluateRequest registry requestBytes

updateObjectPath :: [Text.Text] -> (Value -> IO Value) -> Value -> IO Value
updateObjectPath [] update value = update value
updateObjectPath (name : rest) update (Object fields) = do
  let key = Key.fromText name
  current <- maybe (fail ("missing Isoprax request field: " <> Text.unpack name)) pure (KeyMap.lookup key fields)
  replacement <- updateObjectPath rest update current
  pure (Object (KeyMap.insert key replacement fields))
updateObjectPath (name : _) _ _ = fail ("non-object in Isoprax request path: " <> Text.unpack name)

reverseArray :: Value -> IO Value
reverseArray (Array values)
  | Vector.length values > 1 = pure (Array (Vector.reverse values))
reverseArray _ = fail "threshold permutation fixture needs at least two thresholds"

checkCase :: PackRegistry -> Value -> IO ()
checkCase registry vector = do
  identifier <- requiredText "id" vector
  request <- requiredField "request" vector
  expected <- requiredField "expected" vector
  requestBytes <- case canonicalBytes request of
    Left errorValue -> fail ("could not encode Isoprax request " <> Text.unpack identifier <> ": " <> show errorValue)
    Right bytes -> pure (LazyByteString.toStrict bytes)
  actual <- evaluateRequest registry requestBytes
  normative <- case field "error" expected of
    Just expectedError -> pure expectedError
    Nothing -> fullExpectedDecision request expected
  if actual == normative
    then assertApplicationCase identifier requestBytes normative
    else fail ("Isoprax decision differs from the normative fixture: " <> Text.unpack identifier <> "\nactual: " <> show actual <> "\nexpected: " <> show normative)

assertApplicationCase :: Text.Text -> ByteString.ByteString -> Value -> IO ()
assertApplicationCase identifier requestBytes expected = do
  expectedBytes <- case canonicalBytes expected of
    Left errorValue -> fail ("could not encode expected CLI output for " <> Text.unpack identifier <> ": " <> show errorValue)
    Right bytes -> pure (LazyByteString.toStrict bytes <> "\n")
  expectedStatus <- expectedApplicationStatus expected
  (actualStatus, actualBytes, actualErrors) <- captureApplication [] requestBytes
  unless (actualStatus == expectedStatus) $
    fail ("first-party CLI returned " <> show actualStatus <> " for " <> Text.unpack identifier <> "; expected " <> show expectedStatus)
  unless (actualBytes == expectedBytes) $
    fail ("first-party CLI wrote unexpected output for " <> Text.unpack identifier <> ": " <> show actualBytes)
  unless (ByteString.null actualErrors) $
    fail ("first-party CLI wrote unexpected errors for " <> Text.unpack identifier <> ": " <> show actualErrors)

expectedApplicationStatus :: Value -> IO ExitCode
expectedApplicationStatus result = case field "kind" result of
  Just (String "error") -> pure (ExitFailure 3)
  Just (String "decision") -> case field "payload" result >>= field "state" of
    Just (String "admissible") -> pure ExitSuccess
    Just (String "inadmissible") -> pure (ExitFailure 1)
    Just (String "indeterminate") -> pure (ExitFailure 2)
    _ -> fail "first-party CLI fixture has an invalid decision state"
  _ -> fail "first-party CLI fixture has an invalid result kind"

captureApplication :: [String] -> ByteString.ByteString -> IO (ExitCode, ByteString.ByteString, ByteString.ByteString)
captureApplication arguments source =
  withTemporaryHandle "semadmit-isoprax-input" $ \input ->
    withTemporaryHandle "semadmit-isoprax-output" $ \output ->
      withTemporaryHandle "semadmit-isoprax-errors" $ \errors -> do
        ByteString.hPut input source
        hSeek input AbsoluteSeek 0
        status <- Application.runApplication arguments input output errors
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

fullExpectedDecision :: Value -> Value -> IO Value
fullExpectedDecision request sidecar = do
  protocol <- requiredField "protocol" request
  pack <- requiredField "pack" request
  operation <- requiredField "operation" request
  state <- requiredField "state" sidecar
  requestDigest <- requiredField "request_digest" sidecar
  policyDigest <- requiredField "policy_digest" sidecar
  decisionDigest <- requiredField "decision_digest" sidecar
  obligations <- requiredField "obligations" sidecar
  diagnostics <- requiredField "diagnostics" sidecar
  subjects <- requiredDigestMap "subject_digests" sidecar
  components <- requiredDigestMap "component_digests" sidecar
  evidence <- requiredDigestMap "evidence_digests" sidecar
  if null evidence
    then pure ()
    else fail "Isoprax pool fixture unexpectedly contains evidence bindings"
  let subjectBindings =
        [ object ["role" .= role, "kind" .= ("subject" :: Text.Text), "schema" .= ("isoprax/0.1/subject" :: Text.Text), "digest" .= digest]
        | (role, digest) <- subjects
        ]
  componentBindings <- traverse makeComponentBinding components
  pure $ object
    [ "kind" .= ("decision" :: Text.Text)
    , "payload" .= object
        [ "protocol" .= protocol
        , "pack" .= pack
        , "operation" .= operation
        , "request_digest" .= requestDigest
        , "policy_digest" .= policyDigest
        , "state" .= state
        , "bindings" .= object
            [ "subjects" .= subjectBindings
            , "components" .= componentBindings
            , "evidence" .= ([] :: [Value])
            ]
        , "obligations" .= obligations
        , "diagnostics" .= diagnostics
        ]
    , "decision_digest" .= decisionDigest
    ]

requiredDigestMap :: Text.Text -> Value -> IO [(Text.Text, Value)]
requiredDigestMap name value = do
  digestObject <- requiredField name value
  case digestObject of
    Object fields -> pure
      [ (Key.toText key, digest)
      | (key, digest) <- sortOn (Key.toText . fst) (KeyMap.toList fields)
      ]
    _ -> fail ("Isoprax fixture field is not an object: " <> Text.unpack name)

makeComponentBinding :: (Text.Text, Value) -> IO Value
makeComponentBinding (identity, digest) = case Text.splitOn "/" identity of
  [role, name] -> pure $ object
    [ "subject_role" .= role
    , "name" .= name
    , "kind" .= name
    , "schema" .= ("isoprax/0.1/" <> name)
    , "digest" .= digest
    ]
  _ -> fail ("Isoprax fixture component key is invalid: " <> Text.unpack identity)

requiredField :: Text.Text -> Value -> IO Value
requiredField name value = maybe (fail ("missing Isoprax fixture field: " <> Text.unpack name)) pure (field name value)

requiredText :: Text.Text -> Value -> IO Text.Text
requiredText name value = do
  found <- requiredField name value
  case found of
    String text -> pure text
    _ -> fail ("Isoprax fixture field is not text: " <> Text.unpack name)

field :: Text.Text -> Value -> Maybe Value
field name (Object fields) = KeyMap.lookup (Key.fromText name) fields
field _ _ = Nothing
