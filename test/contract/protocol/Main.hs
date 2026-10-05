{-# LANGUAGE OverloadedStrings #-}

import Core.Decision
  ( DecisionContext (..)
  , Outcome (..)
  , SubjectDeclaration (..)
  , SubjectArtifact (..)
  , buildBindings
  , buildDecision
  )
import Core.Identity (decisionDigest)
import Core.Pack
  ( NormalizedPackRequest (..)
  , OperationDescriptor (..)
  , Pack (..)
  , PackBehavior (..)
  , PackDescriptor (..)
  , PackResult (..)
  , PackRegistry
  , mkPackRegistry
  , packIdentityFor
  )
import Core.Protocol
  ( CommonRequest (..)
  , InputError (..)
  , errorEnvelope
  , protocolVersion
  , validateCommon
  )
import Data.Aeson (Value (..), object, (.=))
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.List (sort)
import Data.Map.Strict qualified as Map
import Data.Text (Text)
import Data.Text qualified as Text

main :: IO ()
main = do
  registry <- case mkPackRegistry [fixturePack] of
    Left err -> fail ("valid test pack was rejected: " <> show err)
    Right value -> pure value
  request <- case validateCommon registry (commonRequest "fixture/0.1" "check") of
    Left err -> fail ("valid common request was rejected: " <> show err)
    Right value -> pure value
  check "request dispatch selected the wrong registered operation"
    (packDescriptor (commonPack request) == packDescriptor fixturePack && commonOperation request == "check"
      && commonOperationDescriptor request == fixtureOperation)
  expectError registry (commonRequest "unknown/0.1" "check")
    (InputError "protocol.unsupported_pack" "/pack")
  expectError registry (commonRequest "fixture/0.1" "other")
    (InputError "protocol.unsupported_operation" "/operation")
  checkDecision registry

checkDecision :: PackRegistry -> IO ()
checkDecision registry = do
  identities <- case packIdentityFor "fixture/0.1" "check" registry of
    Nothing -> fail "registered identity scope was unavailable"
    Just value -> pure value
  bindings <- case buildBindings identities (operationSubjectDeclarations fixtureOperation)
      [SubjectArtifact "item" "subject" "fixture/0.1/subject" (object [])]
      [] [] Nothing [] of
    Left err -> fail ("valid generic bindings were rejected: " <> show err)
    Right value -> pure value
  result <- case buildDecision context ["check"] [Pass, Fail, Missing] [("check", Pass)] Map.empty [] bindings of
    Left err -> fail ("valid generic decision was rejected: " <> show err)
    Right value -> pure value
  case (objectKeys result, field "payload" result, field "decision_digest" result) of
    ( ["decision_digest", "kind", "payload"]
      , Just payload
      , Just (String digest)
      ) -> do
        check "decision envelope kind was invalid" (field "kind" result == Just (String "decision"))
        check "decision payload fields were not closed"
          (objectKeys payload == ["bindings", "diagnostics", "obligations", "operation", "pack", "policy_digest", "protocol", "request_digest", "state"])
        check "decision binding groups were not closed or complete"
          (case field "bindings" payload of
            Just value -> objectKeys value == ["components", "evidence", "subjects"]
              && all (== Just (Array mempty)) [field "components" value, field "evidence" value]
              && case field "subjects" value of Just (Array subjects) -> length subjects == 1; _ -> False
            _ -> False)
        check "decision outcome or state was invalid"
          (field "state" payload == Just (String "admissible")
            && case field "obligations" payload of Just (Array items) -> length items == 1; _ -> False)
        check "decision digest was not bound to the exact payload" (decisionDigest payload == Right digest)
    _ -> fail "decision result envelope did not have the exact field set"

expectError :: PackRegistry -> Value -> InputError -> IO ()
expectError registry value expected = case validateCommon registry value of
  Left actual -> do
    check "protocol error did not match the expected code and pointer" (actual == expected)
    check "protocol error envelope fields were not exact"
      (objectKeys (errorEnvelope actual) == ["code", "kind", "pointer"])
    check "protocol error envelope values were invalid"
      (field "kind" (errorEnvelope actual) == Just (String "error")
        && field "code" (errorEnvelope actual) == Just (String (inputErrorCode actual))
        && field "pointer" (errorEnvelope actual) == Just (String (inputErrorPointer actual)))
  Right _ -> fail "invalid common request was accepted"

check :: String -> Bool -> IO ()
check label condition = if condition then pure () else fail label

commonRequest :: Text -> Text -> Value
commonRequest packIdentifier operationName =
  object
    [ "protocol" .= protocolVersion
    , "pack" .= packIdentifier
    , "operation" .= operationName
    , "policy_digest" .= ("sha256:" <> Text.replicate 64 "0")
    , "policy" .= object []
    , "subjects" .= object ["item" .= object []]
    , "evidence" .= ([] :: [Value])
    ]

fixturePack :: Pack
fixturePack =
  Pack
    PackDescriptor
      { packId = "fixture/0.1"
      , packProtocolVersions = [protocolVersion]
      , packOperations = Map.singleton "check" fixtureOperation
      }
    (PackBehavior
      (\_ policy subjects evidence -> Right (NormalizedPackRequest policy subjects evidence Nothing))
      Right
      (const (const (const (PackResult [] [("check", Pass)] [])))))

fixtureOperation :: OperationDescriptor
fixtureOperation =
  OperationDescriptor
    { operationArtifactDeclarations =
        [("policy", "fixture/0.1/policy"), ("subject", "fixture/0.1/subject")]
    , operationSubjectDeclarations = [SubjectDeclaration "item" "subject" "fixture/0.1/subject"]
    , operationComponentDeclarations = []
    , operationEvidenceDeclaration = Nothing
    , operationObligations = ["check"]
    , operationAllowedOutcomes = [Pass, Fail, Missing]
    , operationDiagnosticPointers = Map.empty
    }

context :: DecisionContext
context =
  DecisionContext
    protocolVersion
    "fixture/0.1"
    "check"
    ("sha256:" <> Text.replicate 64 "1")
    ("sha256:" <> Text.replicate 64 "0")

field :: Text -> Value -> Maybe Value
field name (Object fields) = KeyMap.lookup (Key.fromText name) fields
field _ _ = Nothing

objectKeys :: Value -> [Text]
objectKeys (Object fields) = sort (map Key.toText (KeyMap.keys fields))
objectKeys _ = []
