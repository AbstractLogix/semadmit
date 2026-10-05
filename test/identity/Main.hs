{-# LANGUAGE OverloadedStrings #-}

import Control.Monad (forM_, unless)
import Core.Decision (DecisionError (..), DecisionState (..), Outcome (..), SubjectDeclaration (..), reduceObligations)
import Core.Identity (IdentityError (..), PackIdentity, artifactDigest, canonicalBytes, decisionDigest)
import Core.Pack (NormalizedPackRequest (..), OperationDescriptor (..), Pack (..), PackBehavior (..), PackDescriptor (..), PackResult (..), mkPackRegistry, packIdentityFor)
import Core.Protocol (protocolVersion)
import Data.Aeson (FromJSON (..), Value (..), eitherDecode, toJSON, withObject, (.:), (.:?))
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString.Lazy qualified as Lazy
import Data.Map.Strict qualified as Map
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Text.Encoding qualified as TextEncoding

data Fixture = Fixture [Vector]

data Vector = Vector
  { vectorId :: Text
  , vectorValue :: Value
  , vectorBytes :: Text
  , vectorDigest :: Text
  }

data RfcFixture = RfcFixture [RfcVector]

data RfcVector = RfcVector
  { rfcId :: Text
  , rfcInput :: Maybe Text
  , rfcBytes :: Maybe Text
  }

identityFor :: [(Text, Text)] -> PackIdentity
identityFor declarations = case mkPackRegistry [testPack] of
  Left err -> error (show err)
  Right registry -> case packIdentityFor identifier "test" registry of
    Just identities -> identities
    Nothing -> error "test operation identity scope missing"
  where
    identifier = case declarations of
      ((_, schema) : _) -> case Text.splitOn "/" schema of
        namespace : version : _ -> namespace <> "/" <> version
        _ -> "test/0.1"
      [] -> "test/0.1"
    subjectSchema = identifier <> "/subject"
    artifactDeclarations =
      [("policy", identifier <> "/policy"), ("subject", subjectSchema)]
        <> [pair | pair <- declarations, pair `notElem` [("policy", identifier <> "/policy"), ("subject", subjectSchema)]]
    testPack =
      Pack
        PackDescriptor
          { packId = identifier
          , packProtocolVersions = [protocolVersion]
          , packOperations = Map.singleton "test"
              OperationDescriptor
                { operationArtifactDeclarations = artifactDeclarations
                , operationSubjectDeclarations = [SubjectDeclaration "item" "subject" subjectSchema]
                , operationComponentDeclarations = []
                , operationEvidenceDeclaration = Nothing
                , operationObligations = ["test"]
                , operationAllowedOutcomes = [Pass]
                , operationDiagnosticPointers = Map.empty
                }
          }
        (PackBehavior
          (\_ policy subjects evidence -> Right (NormalizedPackRequest policy subjects evidence Nothing))
          Right
          (const (const (const (PackResult [] [("test", Pass)] [])))))

instance FromJSON Fixture where
  parseJSON = withObject "Fixture" $ \fields -> Fixture <$> fields .: "vectors"

instance FromJSON Vector where
  parseJSON = withObject "Vector" $ \fields ->
    Vector <$> fields .: "id" <*> fields .: "value" <*> fields .: "canonical_utf8" <*> fields .: "sha256"

instance FromJSON RfcFixture where
  parseJSON = withObject "RfcFixture" $ \fields -> RfcFixture <$> fields .: "cases"

instance FromJSON RfcVector where
  parseJSON = withObject "RfcVector" $ \fields ->
    RfcVector <$> fields .: "id" <*> fields .:? "input_json_utf8" <*> fields .:? "expected_canonical_utf8"

field :: Text -> Value -> Maybe Value
field name (Object fields) = KeyMap.lookup (Key.fromText name) fields
field _ _ = Nothing

checkVector :: Vector -> IO ()
checkVector vector = do
  let expected = Lazy.fromStrict (TextEncoding.encodeUtf8 (vectorBytes vector))
  unless (canonicalBytes (vectorValue vector) == Right expected) $
    error ("canonical byte mismatch: " <> Text.unpack (vectorId vector))
  case (field "kind" (vectorValue vector), field "schema" (vectorValue vector), field "payload" (vectorValue vector)) of
    (Just (String kind), Just (String schema), Just payload) ->
      unless (artifactDigest (identityFor [(kind, schema)]) kind schema payload == Right (vectorDigest vector)) $
        error ("artifact digest mismatch: " <> Text.unpack (vectorId vector))
    _ | vectorId vector == "measurement-admissible-decision" ->
      unless (decisionDigest (vectorValue vector) == Right (vectorDigest vector)) $
        error ("decision digest mismatch: " <> Text.unpack (vectorId vector))
    _ -> pure ()

main :: IO ()
main = do
  let emptyPackIdentity = identityFor []
  unless
    (artifactDigest emptyPackIdentity "request" "semantic-oracle/0.1/request" Null /= Left (UndeclaredArtifact "request" "semantic-oracle/0.1/request")) $
    error "common request identity was not available"
  unless
    (artifactDigest emptyPackIdentity "component" "unregistered/0.1/component" Null == Left (UndeclaredArtifact "component" "unregistered/0.1/component")) $
    error "undeclared artifact identity was accepted"
  let declared = ["a", "b"]
  forM_
    [ ([("b", Pass), ("a", Pass)], Admissible)
    , ([("b", Missing), ("a", Pass)], Indeterminate)
    , ([("b", Missing), ("a", Fail)], Inadmissible)
    ] $ \(items, expected) ->
      unless (fmap fst (reduceObligations declared items) == Right expected) $
        error "obligation state reduction mismatch"
  unless (reduceObligations declared [("a", Pass)] == Left InvalidObligationSet) $
    error "omitted obligation was accepted"
  unless (reduceObligations declared [("a", Pass), ("a", Pass)] == Left InvalidObligationSet) $
    error "duplicate obligation was accepted"
  unless (canonicalBytes (toJSON (9007199254740992 :: Integer)) == Left InvalidNumber) $
    error "unsafe JSON integer was accepted"
  unless (canonicalBytes (toJSON (0.5 :: Double)) == Left InvalidNumber) $
    error "fractional JSON number was accepted"
  let nested = iterate (\value -> toJSON [value]) Null !! 65
  unless (canonicalBytes nested == Left TooDeep) $
    error "excessive JSON depth was accepted"
  source <- Lazy.readFile "conformance/fixtures/m0-identity-vectors.json"
  case eitherDecode source of
    Left message -> error message
    Right (Fixture vectors) -> do
      forM_ vectors checkVector
      putStrLn ("verified " <> show (length vectors) <> " M0 identity vectors")
  published <- Lazy.readFile "conformance/fixtures/rfc8785-vectors.json"
  case eitherDecode published of
    Left message -> error message
    Right (RfcFixture cases) ->
      case filter (\item -> rfcId item == "section-3-2-3-property-order-and-utf8") cases of
        [item] -> case (rfcInput item, rfcBytes item) of
          (Just input, Just expected) -> case eitherDecode (Lazy.fromStrict (TextEncoding.encodeUtf8 input)) of
            Left message -> error message
            Right value ->
              unless (canonicalBytes value == Right (Lazy.fromStrict (TextEncoding.encodeUtf8 expected))) $
                error "published RFC 8785 property-order mismatch"
          _ -> error "published RFC 8785 property-order bytes missing"
        _ -> error "published RFC 8785 property-order fixture missing"
