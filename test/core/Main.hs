{-# LANGUAGE OverloadedStrings #-}

import Core.Pack (NormalizedPackRequest (..), OperationDescriptor (..), Pack (..), PackBehavior (..), PackDescriptor (..), PackInputError (..), PackRegistry, PackRegistryError (..), PackResult (..), lookupOperation, lookupPack, mkPackRegistry)
import Core.Pack (packIdentityFor)
import Core.Evaluator (evaluateRequest)
import Core.Identity (IdentityError (..), PackIdentity, artifactDigest, canonicalBytes, decisionDigest)
import Core.Decision
  ( ComponentBinding (..)
  , ComponentDeclaration (..)
  , ComponentPayload (..)
  , DecisionContext (..)
  , DecisionError (..)
  , Diagnostic (..)
  , EvidenceArtifact (..)
  , EvidenceDeclaration (..)
  , Outcome (..)
  , SubjectArtifact (..)
  , SubjectDeclaration (..)
  , buildBindings
  , buildDecision
  , normalizeDiagnostics
  , validateComponents
  )
import Core.Protocol (CommonRequest (..), InputError (..), errorEnvelope, parseJsonBytes, protocolVersion, validateCommon)
import Data.Aeson (Value (..), eitherDecodeStrict', object, (.=))
import Data.Aeson qualified as Aeson
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString qualified as ByteString
import Data.ByteString.Char8 qualified as ByteStringChar8
import Data.ByteString.Lazy qualified as LazyByteString
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Text.Encoding qualified as TextEncoding
import Data.Map.Strict qualified as Map
import Data.Vector qualified as Vector
import Numeric (readHex)

check :: String -> Bool -> IO ()
check label condition = if condition then pure () else fail label

registryRejected :: PackRegistryError -> Either PackRegistryError PackRegistry -> Bool
registryRejected expected result = case result of
  Left actual -> actual == expected
  Right _ -> False

pack :: Text -> Pack
pack identifier = packWithRuntime identifier normalize run
  where
    normalize _ policy subjects evidence =
      Right (NormalizedPackRequest policy subjects evidence Nothing)
    run _ _ passing =
      PackResult
        [ComponentPayload "item" "spec" "component" (identifier <> "/component") Null]
        [("z", if passing then Pass else Fail), ("a", Pass)]
        []

packWithRuntime
  :: Text
  -> (Text -> Value -> Value -> [Value] -> Either PackInputError NormalizedPackRequest)
  -> (Text -> PackIdentity -> Bool -> PackResult)
  -> Pack
packWithRuntime identifier normalize run =
  Pack
    ( PackDescriptor
        { packId = identifier
        , packProtocolVersions = [protocolVersion]
        , packOperations = Map.singleton "check" (operation identifier)
        }
    )
    (PackBehavior normalize decodePassing run)

decodePassing :: NormalizedPackRequest -> Either () Bool
decodePassing normalized = case normalizedSubjects normalized of
  Object fields -> case KeyMap.lookup "item" fields of
    Just (Object item) -> case KeyMap.lookup "pass" item of
      Just (Bool passing) -> Right passing
      _ -> Left ()
    _ -> Left ()
  _ -> Left ()

normalizeRequest :: Text -> Value -> Value -> [Value] -> Either PackInputError NormalizedPackRequest
normalizeRequest _ policy subjects evidence =
  Right (NormalizedPackRequest policy subjects evidence Nothing)

packWithDescriptor :: PackDescriptor -> Pack
packWithDescriptor descriptor = (pack (packId descriptor)) {packDescriptor = descriptor}

registered :: Text -> PackRegistry
registered identifier = case mkPackRegistry [pack identifier] of
  Right registry -> registry
  Left err -> error (show err)

operation :: Text -> OperationDescriptor
operation identifier =
  OperationDescriptor
    { operationArtifactDeclarations =
        [ ("policy", identifier <> "/policy")
        , ("component", identifier <> "/component")
        , ("subject", identifier <> "/subject")
        , ("evidence", identifier <> "/evidence")
        ]
    , operationSubjectDeclarations = [SubjectDeclaration "item" "subject" (identifier <> "/subject")]
    , operationComponentDeclarations = [ComponentDeclaration "item" "spec" "component" (identifier <> "/component") 1 1]
    , operationEvidenceDeclaration = Just (EvidenceDeclaration "evidence" (identifier <> "/evidence"))
    , operationObligations = ["z", "a"]
    , operationAllowedOutcomes = [Pass, Fail, Missing]
    , operationDiagnosticPointers = Map.singleton "domain.mismatch" ["/subjects/item"]
    }

main :: IO ()
main = do
  case mkPackRegistry [pack "example/0.1"] of
    Left _ -> fail "valid pack descriptor was rejected"
    Right registry -> do
      check "exact pack ID lookup failed"
        (fmap packDescriptor (lookupPack "example/0.1" registry) == Just (packDescriptor (pack "example/0.1")))
      check "registry lookup accepted an unregistered version"
        (case lookupPack "example/0.2" registry of Nothing -> True; _ -> False)
  case packIdentityFor "example/0.1" "check" (registered "example/0.1") of
    Nothing -> fail "declared operation identity scope was not available"
    Just identities -> do
      check "declared pack artifact identity was rejected" (case artifactDigest identities "policy" "example/0.1/policy" Null of Right _ -> True; _ -> False)
      check "undeclared pack artifact identity was accepted" (artifactDigest identities "unknown" "example/0.1/unknown" Null == Left (UndeclaredArtifact "unknown" "example/0.1/unknown"))
  check "registered operation descriptor was not selected"
    (lookupOperation "check" (pack "example/0.1") == Just (operation "example/0.1"))
  check "undeclared operation identity scope was available" (case packIdentityFor "example/0.1" "other" (registered "example/0.1") of Nothing -> True; _ -> False)
  case packIdentityFor "example/0.1" "check" (registered "example/0.1") of
    Nothing -> fail "declared component identity scope was not available"
    Just identities -> do
      let selected = operation "example/0.1"
      declaration <- case operationComponentDeclarations selected of
        [item] -> pure item
        _ -> fail "test operation component descriptor changed"
      subjectDeclaration <- case operationSubjectDeclarations selected of
        [item] -> pure item
        _ -> fail "test operation subject descriptor changed"
      let payload = ComponentPayload "item" "spec" "component" "example/0.1/component" (object ["value" .= (1 :: Int)])
      case validateComponents identities [declaration] [payload] of
        Right [binding] -> check "component binding changed its declared identity fields"
          (bindingSubjectRole binding == "item" && bindingComponentName binding == "spec"
            && bindingComponentKind binding == "component" && bindingComponentSchema binding == "example/0.1/component")
        _ -> fail "valid component output was rejected"
      check "missing required component was accepted" (validateComponents identities [declaration] [] == Left InvalidComponentOutput)
      check "undeclared component output was accepted" (validateComponents identities [] [payload] == Left InvalidComponentOutput)
      check "invalid component cardinality was accepted"
        (validateComponents identities [declaration {minimumComponents = 2, maximumComponents = 1}] [] == Left InvalidComponentDeclaration)
      check "undeclared optional component schema was accepted"
        (validateComponents identities [declaration {declaredComponentSchema = "foreign/0.1/component", minimumComponents = 0}] [] == Left InvalidComponentDeclaration)
      let subjectArtifact = SubjectArtifact "item" "subject" "example/0.1/subject" (object [])
          evidenceDeclaration = operationEvidenceDeclaration selected
          evidenceArtifact = EvidenceArtifact "ev-1" "evidence" "example/0.1/evidence" Null
          context = DecisionContext protocolVersion "example/0.1" "check" ("sha256:" <> Text.replicate 64 "0") ("sha256:" <> Text.replicate 64 "1")
          outcomes = [("z", Pass), ("a", Pass)]
          diagnostics = [Diagnostic "z" "/subjects/item" "domain.mismatch", Diagnostic "z" "/subjects/item" "domain.mismatch"]
          allowedPointers = operationDiagnosticPointers selected
      case buildBindings identities (operationSubjectDeclarations selected) [subjectArtifact] (operationComponentDeclarations selected) [payload] evidenceDeclaration [evidenceArtifact] of
        Left _ -> fail "valid subject, component, and evidence bindings were rejected"
        Right bindings -> do
          check "duplicate evidence ID was accepted"
            (case buildBindings identities [subjectDeclaration] [subjectArtifact] [declaration] [payload] evidenceDeclaration [evidenceArtifact, evidenceArtifact] of Left InvalidEvidenceBindings -> True; _ -> False)
          case buildDecision context (operationObligations selected) (operationAllowedOutcomes selected) outcomes allowedPointers diagnostics bindings of
            Left _ -> fail "valid decision payload was rejected"
            Right result -> case result of
              Object envelope -> do
                check "decision envelope kind was invalid" (KeyMap.lookup "kind" envelope == Just (String "decision"))
                case (KeyMap.lookup "payload" envelope, KeyMap.lookup "decision_digest" envelope) of
                  (Just decisionPayload, Just (String digest)) -> do
                    check "decision digest did not match its payload" (decisionDigest decisionPayload == Right digest)
                    check "decision state was not derived" (field "state" decisionPayload == Just (String "admissible"))
                    check "decision obligation order was not canonical"
                      (case field "obligations" decisionPayload of Just (Array items) -> map (field "id") (Vector.toList items) == [Just (String "a"), Just (String "z")]; _ -> False)
                    check "duplicate decision diagnostics were not removed"
                      (case field "diagnostics" decisionPayload of Just (Array items) -> Vector.length items == 1; _ -> False)
                    check "generic binding records were not emitted"
                      (case field "bindings" decisionPayload of
                        Just (Object bindingFields) -> all hasOne ["subjects", "components", "evidence"]
                          where
                            hasOne name = case KeyMap.lookup name bindingFields of Just (Array items) -> Vector.length items == 1; _ -> False
                        _ -> False)
                  _ -> fail "decision payload or digest was missing"
              _ -> fail "decision result was not an object"
          check "incomplete decision obligations were accepted"
            (case buildDecision context (operationObligations selected) (operationAllowedOutcomes selected) [("z", Pass)] allowedPointers [] bindings of Left InvalidObligationSet -> True; _ -> False)
  let diagnostic = Diagnostic "compare" "/subjects/item" "domain.mismatch"
  check "valid diagnostic was rejected"
    (normalizeDiagnostics ["compare"] (Map.singleton "domain.mismatch" ["/subjects/item"]) [diagnostic] == Right [diagnostic])
  check "duplicate diagnostics were not removed"
    (normalizeDiagnostics ["compare"] (Map.singleton "domain.mismatch" ["/subjects/item"]) [diagnostic, diagnostic] == Right [diagnostic])
  check "undeclared diagnostic pointer was accepted"
    (normalizeDiagnostics ["compare"] (Map.singleton "domain.mismatch" ["/subjects/other"]) [diagnostic] == Left InvalidDiagnosticOutput)
  check "invalid diagnostic pointer escape was accepted"
    (normalizeDiagnostics ["compare"] (Map.singleton "domain.mismatch" ["/subjects/bad~2"]) [Diagnostic "compare" "/subjects/bad~2" "domain.mismatch"] == Left InvalidDiagnosticOutput)
  check "empty diagnostic code declaration was accepted"
    (normalizeDiagnostics ["compare"] (Map.singleton "" ["/subjects/item"]) [] == Left InvalidDiagnosticOutput)
  check "empty obligation declaration was accepted"
    (normalizeDiagnostics [""] (Map.singleton "domain.mismatch" ["/subjects/item"]) [] == Left InvalidObligationSet)
  let unknownTemplate = Map.singleton "definition.unknown" ["/subjects/{left,right}/definition/thresholds/{canonical-index}/value"]
      canonicalThresholdDiagnostic = Diagnostic "compare" "/subjects/right/definition/thresholds/0/value" "definition.unknown"
  check "canonical-index diagnostic template was rejected"
    (normalizeDiagnostics ["compare"] unknownTemplate [canonicalThresholdDiagnostic] == Right [canonicalThresholdDiagnostic])
  check "noncanonical diagnostic index matched a pointer template"
    (normalizeDiagnostics ["compare"] unknownTemplate [canonicalThresholdDiagnostic {diagnosticPointer = "/subjects/right/definition/thresholds/01/value"}] == Left InvalidDiagnosticOutput)
  check "unknown diagnostic template placeholder was accepted"
    (normalizeDiagnostics ["compare"] (Map.singleton "unknown" ["/subjects/{unknown}"]) [] == Left InvalidDiagnosticOutput)
  check "duplicate pack ID was accepted"
    (registryRejected (DuplicatePackId "example/0.1") (mkPackRegistry [pack "example/0.1", pack "example/0.1"]))
  mapM_
    (\identifier ->
        check
          ("invalid pack ID was accepted: " <> Text.unpack identifier)
          (case mkPackRegistry [pack identifier] of Left (InvalidPackDescriptor _) -> True; _ -> False)
    )
    ["Example/0.1", "example/00.1", "example/0.01", "example/0.1/extra", "example/١.0"]
  check "unsupported protocol version was accepted"
    (registryRejected (InvalidPackDescriptor "example/0.1") (mkPackRegistry [packWithDescriptor (PackDescriptor "example/0.1" ["semantic-oracle/0.2"] (Map.singleton "check" (operation "example/0.1")))]))
  check "empty operation name was accepted"
    (registryRejected (InvalidPackDescriptor "example/0.1") (mkPackRegistry [packWithDescriptor (PackDescriptor "example/0.1" [protocolVersion] (Map.singleton "" (operation "example/0.1")))]))
  let invalidComponentOperation = (operation "example/0.1")
        { operationComponentDeclarations = [ComponentDeclaration "item" "spec" "component" "foreign/0.1/component" 0 1] }
  check "operation component schema outside its identity scope was accepted"
    (registryRejected (InvalidPackDescriptor "example/0.1") (mkPackRegistry [packWithDescriptor (PackDescriptor "example/0.1" [protocolVersion] (Map.singleton "check" invalidComponentOperation))]))
  checkParse "duplicate key pointer" "input.duplicate_key" "/x" "{\"x\":1,\"x\":2}"
  checkParse "invalid unicode" "input.invalid_unicode" "" "{\"x\":\"\\ud800\"}"
  checkParse "invalid JSON syntax" "input.invalid_json" "" "01"
  checkParse "array trailing comma" "input.invalid_json" "" "[1,]"
  checkParse "object trailing comma" "input.invalid_json" "" "{\"x\":1,}"
  checkParse "number profile" "input.number_profile" "/n" "{\"n\":1e2}"
  checkParse "negative zero" "input.number_profile" "" "-0"
  checkParse "safe integer upper bound" "input.number_profile" "" "9007199254740992"
  checkParse "byte order mark" "input.invalid_json" "" (TextEncoding.encodeUtf8 "\xfeff{}")
  checkParse "request byte limit" "limit.exceeded" "" (ByteString.replicate (10 * 1024 * 1024 + 1) 0x20)
  case parseJsonBytes "{\"x\":\"\\ud83d\\ude00\",\"n\":9007199254740991}" of
    Right (Object fields) -> check "valid scalar pair or safe integer rejected"
      (KeyMap.lookup "x" fields == Just (String "😀") && KeyMap.lookup "n" fields == Just (Aeson.Number 9007199254740991))
    _ -> fail "valid Unicode scalar pair and safe integer were rejected"
  case parseJsonBytes (ByteString.pack [0xff]) of
    Left err -> check "invalid UTF-8 code" (err == InputError "input.invalid_utf8" "")
    Right _ -> fail "invalid UTF-8 was accepted"
  checkParse "RFC 6901 duplicate pointer" "input.duplicate_key" "/a~1b/~0" "{\"a/b\":{\"~\":1,\"~\":2}}"
  let tooManyEvidence = "{\"evidence\":[" <> ByteStringChar8.intercalate "," (replicate 257 "0") <> "]}"
  checkParse "evidence limit pointer" "limit.exceeded" "/evidence/256" tooManyEvidence
  let deepJson = ByteString.concat (replicate 65 "[" <> ["0"] <> replicate 65 "]")
  case parseJsonBytes deepJson of
    Left err -> check "depth limit code and pointer" (err == InputError "limit.exceeded" (Text.replicate 64 "/0"))
    Right _ -> fail "excessive nesting was accepted"
  case mkPackRegistry [pack "example/0.1"] of
    Left _ -> fail "valid registry descriptor was rejected"
    Right registry -> do
      case validateCommon registry commonRequest of
        Right request -> check "common request selected wrong pack or operation"
          (packDescriptor (commonPack request) == packDescriptor (pack "example/0.1") && commonOperation request == "check"
            && commonOperationDescriptor request == operation "example/0.1")
        Left _ -> fail "valid common request was rejected"
      case validateCommon registry (commonRequestWithPack "example/0.2") of
        Left err -> check "unknown pack error" (err == InputError "protocol.unsupported_pack" "/pack")
        Right _ -> fail "unregistered pack was accepted"
      case validateCommon registry commonRequestWithUnknowns of
        Left err -> check "unknown field ordering and pointer escaping" (err == InputError "input.unknown_field" "/a~1b")
        Right _ -> fail "unknown common fields were accepted"
  checkEvaluator
  checkProtocolFixtures

checkEvaluator :: IO ()
checkEvaluator = do
  let identifier = "example/0.1"
      operationName = "check"
      policy = object []
      evidence =
        [ object ["id" .= ("z" :: Text), "value" .= (1 :: Int)]
        , object ["id" .= ("a" :: Text), "value" .= (2 :: Int)]
        ]
  registry <- case mkPackRegistry [pack identifier] of
    Left err -> fail ("evaluator fixture pack was rejected: " <> show err)
    Right value -> pure value
  identities <- case packIdentityFor identifier operationName registry of
    Nothing -> fail "evaluator fixture identity scope was unavailable"
    Just value -> pure value
  policyDigest <- case artifactDigest identities "policy" (identifier <> "/policy") policy of
    Left err -> fail ("evaluator fixture policy could not be identified: " <> show err)
    Right value -> pure value
  let request passing suppliedDigest items =
        object
          [ "protocol" .= protocolVersion
          , "pack" .= identifier
          , "operation" .= operationName
          , "policy_digest" .= suppliedDigest
          , "policy" .= policy
          , "subjects" .= object ["item" .= object ["pass" .= passing]]
          , "evidence" .= items
          ]
  admissible <- evaluateValue registry (request True policyDigest evidence)
  inadmissible <- evaluateValue registry (request False policyDigest evidence)
  reordered <- evaluateValue registry (request True policyDigest (reverse evidence))
  check "Haskell evaluator did not produce a decision envelope"
    (field "kind" admissible == Just (String "decision"))
  check "passing registered operation was not admissible" (decisionState admissible == Just "admissible")
  check "failing registered operation was not inadmissible" (decisionState inadmissible == Just "inadmissible")
  check "normalized evidence order changed the decision" (admissible == reordered)
  mismatch <- evaluateValue registry (request True ("sha256:" <> Text.replicate 64 "0") evidence)
  check "policy digest mismatch was not a protocol error"
    (field "code" mismatch == Just (String "identity.digest_mismatch"))
  let invalidOutputPack = packWithRuntime identifier normalizeRequest
        (\_ _ _ -> PackResult [] [] [])
  invalidOutputRegistry <- case mkPackRegistry [invalidOutputPack] of
    Left err -> fail ("invalid-output fixture pack descriptor was rejected: " <> show err)
    Right value -> pure value
  invalidOutput <- evaluateValue invalidOutputRegistry (request True policyDigest evidence)
  check "invalid pack output did not fail closed"
    (invalidOutput == errorEnvelope (InputError "internal.failure" ""))
  let invalidErrorPack = packWithRuntime identifier
        (\_ _ _ _ -> Left (PackInputError "input.invalid_value" "/outside"))
        (\_ _ _ -> PackResult [] [] [])
  invalidErrorRegistry <- case mkPackRegistry [invalidErrorPack] of
    Left err -> fail ("invalid-error fixture pack descriptor was rejected: " <> show err)
    Right value -> pure value
  invalidError <- evaluateValue invalidErrorRegistry (request True policyDigest evidence)
  check "pack error pointer outside pack inputs was not hidden"
    (invalidError == errorEnvelope (InputError "internal.failure" ""))
  let validErrorPack = packWithRuntime identifier
        (\_ _ _ _ -> Left (PackInputError "input.invalid_value" "/subjects/item/pass"))
        (\_ _ _ -> PackResult [] [] [])
  validErrorRegistry <- case mkPackRegistry [validErrorPack] of
    Left err -> fail ("valid-error fixture pack descriptor was rejected: " <> show err)
    Right value -> pure value
  validError <- evaluateValue validErrorRegistry (request True policyDigest evidence)
  check "declared pack input error was not preserved"
    (validError == errorEnvelope (InputError "input.invalid_value" "/subjects/item/pass"))
  let exceptionPack = packWithRuntime identifier normalizeRequest
        (\_ _ _ -> error "private pack exception")
  exceptionRegistry <- case mkPackRegistry [exceptionPack] of
    Left err -> fail ("exception fixture pack descriptor was rejected: " <> show err)
    Right value -> pure value
  exceptionResult <- evaluateValue exceptionRegistry (request True policyDigest evidence)
  check "synchronous pack exception was not converted to internal.failure"
    (exceptionResult == errorEnvelope (InputError "internal.failure" ""))

decisionState :: Value -> Maybe Text
decisionState result = case field "payload" result >>= field "state" of
  Just (String state) -> Just state
  _ -> Nothing

evaluateValue :: PackRegistry -> Value -> IO Value
evaluateValue registry value = case canonicalBytes value of
  Left err -> fail ("evaluator fixture request could not be encoded: " <> show err)
  Right bytes -> evaluateRequest registry (LazyByteString.toStrict bytes)

checkParse :: String -> Text -> Text -> ByteString.ByteString -> IO ()
checkParse label code pointer source = case parseJsonBytes source of
  Left err -> check label (err == InputError code pointer)
  Right _ -> fail (label <> " was accepted")

commonRequest :: Value
commonRequest = object
  [ "protocol" .= protocolVersion
  , "pack" .= ("example/0.1" :: Text)
  , "operation" .= ("check" :: Text)
  , "policy_digest" .= ("sha256:" <> Text.replicate 64 "0")
  , "policy" .= object []
  , "subjects" .= object ["item" .= object []]
  , "evidence" .= ([] :: [Value])
  ]

commonRequestWithPack :: Text -> Value
commonRequestWithPack identifier = case commonRequest of
  Object fields -> Object (KeyMap.insert "pack" (String identifier) fields)
  other -> other

commonRequestWithUnknowns :: Value
commonRequestWithUnknowns = case commonRequest of
  Object fields -> Object
    (KeyMap.insert "z" (Aeson.Number 1)
      (KeyMap.insert "a/b" (Aeson.Number 1) fields))
  other -> other

checkProtocolFixtures :: IO ()
checkProtocolFixtures = do
  bytes <- ByteString.readFile "conformance/fixtures/protocol-cases.json"
  case eitherDecodeStrict' bytes of
    Left message -> fail message
    Right (Object root) -> case KeyMap.lookup "cases" root of
      Just (Array cases) -> mapM_ checkFixture (Vector.toList cases)
      _ -> fail "protocol fixture cases are missing"
    Right _ -> fail "protocol fixture root is not an object"
  where
    checkFixture fixture = case (field "id" fixture, field "input" fixture, field "expected" fixture) of
      (Just (String identifier), Just input, Just expected) -> case (field "kind" input, field "error" expected) of
        (Just (String "raw-json-utf8"), Just errorValue) ->
          case field "text" input of
            Just (String jsonText) -> compareExpected identifier (TextEncoding.encodeUtf8 jsonText) errorValue
            _ -> fail "raw JSON fixture text is missing"
        (Just (String "raw-bytes-hex"), Just errorValue) ->
          case field "hex" input of
            Just (String hex) -> case decodeHex hex of
              Just raw -> compareExpected identifier raw errorValue
              Nothing -> fail "raw byte fixture contains invalid hex"
            _ -> fail "raw byte fixture hex is missing"
        _ -> pure ()
      _ -> fail "malformed protocol fixture"

    compareExpected identifier source expected = case (field "code" expected, field "pointer" expected) of
      (Just (String code), Just (String pointer)) -> case parseJsonBytes source of
        Left actual ->
          check
            ("protocol fixture " <> Text.unpack identifier)
            (inputErrorCode actual == code && inputErrorPointer actual == pointer)
        Right _ -> fail ("protocol fixture was accepted: " <> Text.unpack identifier)
      _ -> fail "protocol fixture error is incomplete"

field :: Text -> Value -> Maybe Value
field name (Object fields) = KeyMap.lookup (Key.fromText name) fields
field _ _ = Nothing

decodeHex :: Text -> Maybe ByteString.ByteString
decodeHex input
  | odd (Text.length input) = Nothing
  | otherwise = ByteString.pack <$> pairs (Text.unpack input)
  where
    pairs [] = Just []
    pairs (first : second : rest) = do
      high <- hexDigit first
      low <- hexDigit second
      ((fromIntegral (high * 16 + low)) :) <$> pairs rest
    pairs _ = Nothing
    hexDigit character = case readHex [character] of
      [(value, "")] -> Just (value :: Int)
      _ -> Nothing
