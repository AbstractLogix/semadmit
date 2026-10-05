{-# LANGUAGE OverloadedStrings #-}

module Main (main) where

import Control.Monad (forM_, unless)
import Core.Decision
  ( ComponentDeclaration (..)
  , ComponentPayload (..)
  , Outcome (Pass)
  , SubjectDeclaration (..)
  )
import Core.Identity (PackIdentity, artifactDigest)
import Core.Pack
  ( NormalizedPackRequest (..)
  , OperationDescriptor (..)
  , Pack (..)
  , PackBehavior (..)
  , PackDescriptor (..)
  , PackInputError (..)
  , PackResult (..)
  , mkPackRegistry
  , packIdentityFor
  )
import Core.Protocol (protocolVersion)
import Data.Aeson (Value (..), eitherDecodeStrict', object, (.=))
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString qualified as ByteString
import Data.Map.Strict qualified as Map
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Vector qualified as Vector
import Pack.Isoprax.Types
  ( IsopraxSubject (..)
  , IsopraxSubjects (..)
  , componentPayloads
  , decodeIsopraxSubjects
  , definitionSemanticKey
  , normalizeIsopraxSubjects
  , parseCanonicalDecimal
  )

main :: IO ()
main = do
  registry <- case mkPackRegistry [testPack] of
    Left errorValue -> fail ("Isoprax identity test pack was rejected: " <> show errorValue)
    Right value -> pure value
  identities <- maybe (fail "Isoprax identity test service is missing") pure (packIdentityFor "isoprax/0.1" "pool_predictions" registry)
  source <- ByteString.readFile "conformance/fixtures/isoprax-cases.json"
  root <- case eitherDecodeStrict' source of
    Left message -> fail ("Isoprax fixture JSON is invalid: " <> message)
    Right value -> pure value
  cases <- case field "cases" root of
    Just (Array values) -> pure (Vector.toList values)
    _ -> fail "Isoprax fixtures have no cases array"
  forM_ cases (checkCase identities)
  checkDecimalProfile
  checkValidationEdges

checkCase :: PackIdentity -> Value -> IO ()
checkCase identities value = do
  identifier <- requiredText "id" value
  request <- requiredField "request" value
  subjects <- requiredField "subjects" request
  expected <- requiredField "expected" value
  case field "error" expected of
    Just errorValue | pointerStartsWithSubjects errorValue -> checkInputError identifier subjects errorValue
    _ -> do
      normalized <- case normalizeIsopraxSubjects subjects of
        Left errorValue -> fail ("unexpected Isoprax input error for " <> Text.unpack identifier <> ": " <> show errorValue)
        Right result -> pure result
      typed <- case decodeIsopraxSubjects normalized of
        Left () -> fail ("normalized Isoprax subjects did not decode for " <> Text.unpack identifier)
        Right result -> pure result
      if field "component_digests" expected == Nothing
        then pure ()
        else checkComponentDigests identities identifier expected typed
      checkSemanticCase identifier typed

checkInputError :: Text -> Value -> Value -> IO ()
checkInputError identifier subjects expectedError = case normalizeIsopraxSubjects subjects of
  Right _ -> fail ("expected Isoprax input error for " <> Text.unpack identifier)
  Left actual -> do
    expectedCode <- requiredText "code" expectedError
    expectedPointer <- requiredText "pointer" expectedError
    unless (packInputErrorCode actual == expectedCode && packInputErrorPointer actual == expectedPointer) $
      fail ("Isoprax input error differs for " <> Text.unpack identifier <> ": " <> show actual)

checkComponentDigests :: PackIdentity -> Text -> Value -> IsopraxSubjects -> IO ()
checkComponentDigests identities identifier expected subjects = do
  expectedValue <- requiredField "component_digests" expected
  expectedDigests <- objectTextMap expectedValue
  components <- case componentPayloads identities subjects of
    Left errorValue -> fail ("could not build Isoprax component payloads: " <> show errorValue)
    Right result -> pure result
  actualDigests <- Map.fromList <$> mapM digestComponent components
  unless (actualDigests == expectedDigests) $
    fail ("Isoprax component digests differ for " <> Text.unpack identifier)
  where
    digestComponent component = do
      digest <- case artifactDigest identities (payloadComponentKind component) (payloadComponentSchema component) (payloadValue component) of
        Left errorValue -> fail ("could not hash Isoprax component: " <> show errorValue)
        Right result -> pure result
      pure (payloadSubjectRole component <> "/" <> payloadComponentName component, digest)

checkSemanticCase :: Text -> IsopraxSubjects -> IO ()
checkSemanticCase identifier subjects = case identifier of
  "admissible-different-definition-ids" ->
    unless (definitionSemanticKey (isopraxDefinition (leftSubject subjects)) == definitionSemanticKey (isopraxDefinition (rightSubject subjects))) $
      fail "different definition IDs changed the Isoprax semantic key"
  "inadmissible-event-mismatch" ->
    unless (definitionSemanticKey (isopraxDefinition (leftSubject subjects)) /= definitionSemanticKey (isopraxDefinition (rightSubject subjects))) $
      fail "a changed event did not change the Isoprax semantic key"
  _ -> pure ()

checkDecimalProfile :: IO ()
checkDecimalProfile = do
  unless (parseCanonicalDecimal "9007199254740991" /= Left ()) $
    fail "the largest safe Isoprax decimal was rejected"
  forM_ ["-0", "1.0", "1e-1", "9007199254740992", "0.0000000000001"] $ \value ->
    unless (parseCanonicalDecimal value == Left ()) $
      fail ("a noncanonical or out-of-range decimal was accepted: " <> Text.unpack value)

checkValidationEdges :: IO ()
checkValidationEdges = do
  let base = validSubjects
      withThreshold thresholdValue = setPath ["left", "definition", "thresholds"] (Array (Vector.singleton thresholdValue)) base
      withSample sampleValue = setPath ["left", "sample"] sampleValue base
      threshold = object ["metric" .= ("metric" :: Text), "operator" .= ("=" :: Text)]
      sample = object ["scores" .= (["0.5"] :: [Text]), "outcomes" .= ([0] :: [Int])]
  assertAccepted "minimal defaulted subjects" base
  expectInputError "root type" "input.invalid_type" "/subjects" Null
  expectInputError "unknown role" "input.unknown_field" "/subjects/unexpected" (addField [] "unexpected" Null base)
  expectInputError "escaped unknown role" "input.unknown_field" "/subjects/unexpected~1role" (addField [] "unexpected/role" Null base)
  expectInputError "missing role" "input.missing_field" "/subjects/right" (removePath ["right"] base)
  expectInputError "subject type" "input.invalid_type" "/subjects/left" (setPath ["left"] Null base)
  expectInputError "unknown subject field" "input.unknown_field" "/subjects/left/extra" (addField ["left"] "extra" Null base)
  expectInputError "missing sample" "input.missing_field" "/subjects/left/sample" (removePath ["left", "sample"] base)
  expectInputError "definition type" "input.invalid_type" "/subjects/left/definition" (setPath ["left", "definition"] Null base)
  expectInputError "unknown definition field" "input.unknown_field" "/subjects/left/definition/extra" (addField ["left", "definition"] "extra" Null base)
  expectInputError "missing event" "input.missing_field" "/subjects/left/definition/event" (removePath ["left", "definition", "event"] base)
  expectInputError "id type" "input.invalid_type" "/subjects/left/definition/id" (setPath ["left", "definition", "id"] (Number 1) base)
  expectInputError "blank id" "input.invalid_value" "/subjects/left/definition/id" (setPath ["left", "definition", "id"] (String " \t") base)
  expectInputError "process type" "input.invalid_type" "/subjects/left/definition/observation_process" (setPath ["left", "definition", "observation_process"] Null base)
  expectInputError "missing process kind" "input.missing_field" "/subjects/left/definition/observation_process/kind" (removePath ["left", "definition", "observation_process", "kind"] base)
  expectInputError "blank process kind" "input.invalid_value" "/subjects/left/definition/observation_process/kind" (setPath ["left", "definition", "observation_process", "kind"] (String " ") base)
  expectInputError "unknown process field" "input.unknown_field" "/subjects/left/definition/observation_process/extra" (addField ["left", "definition", "observation_process"] "extra" Null base)
  expectInputError "parameters type" "input.invalid_type" "/subjects/left/definition/observation_process/parameters" (setPath ["left", "definition", "observation_process", "parameters"] (String "bad") base)
  expectInputError "parameter value type" "input.invalid_type" "/subjects/left/definition/observation_process/parameters/p" (setPath ["left", "definition", "observation_process", "parameters"] (object ["p" .= (1 :: Int)]) base)
  expectInputError "process raw type" "input.invalid_type" "/subjects/left/definition/observation_process/raw" (setPath ["left", "definition", "observation_process", "raw"] (Number 1) base)
  expectInputError "window type" "input.invalid_type" "/subjects/left/definition/window" (setPath ["left", "definition", "window"] Null base)
  expectInputError "window decimal profile" "input.invalid_value" "/subjects/left/definition/window/duration" (setPath ["left", "definition", "window", "duration"] (String "-1") base)
  expectInputError "window decimal type" "input.invalid_type" "/subjects/left/definition/window/duration" (setPath ["left", "definition", "window", "duration"] (Number 1) base)
  expectInputError "window unit blank" "input.invalid_value" "/subjects/left/definition/window/unit" (setPath ["left", "definition", "window", "unit"] (String " ") base)
  expectInputError "window anchor type" "input.invalid_type" "/subjects/left/definition/window/anchor" (setPath ["left", "definition", "window", "anchor"] Null base)
  expectInputError "window raw type" "input.invalid_type" "/subjects/left/definition/window/raw" (setPath ["left", "definition", "window", "raw"] (Bool True) base)
  expectInputError "thresholds type" "input.invalid_type" "/subjects/left/definition/thresholds" (setPath ["left", "definition", "thresholds"] Null base)
  expectInputError "threshold type" "input.invalid_type" "/subjects/left/definition/thresholds/0" (withThreshold (String "bad"))
  expectInputError "unknown threshold field" "input.unknown_field" "/subjects/left/definition/thresholds/0/extra" (withThreshold (addField [] "extra" Null threshold))
  expectInputError "threshold metric blank" "input.invalid_value" "/subjects/left/definition/thresholds/0/metric" (withThreshold (setField "metric" (String " ") threshold))
  expectInputError "threshold operator type" "input.invalid_type" "/subjects/left/definition/thresholds/0/operator" (withThreshold (setField "operator" Null threshold))
  expectInputError "threshold value type" "input.invalid_type" "/subjects/left/definition/thresholds/0/value" (withThreshold (setField "value" (Number 1) threshold))
  expectInputError "threshold value schema" "input.missing_field" "/subjects/left/definition/thresholds/0/value/value" (withThreshold (setField "value" (object ["type" .= ("text" :: Text)]) threshold))
  expectInputError "threshold value kind" "input.invalid_value" "/subjects/left/definition/thresholds/0/value/type" (withThreshold (setField "value" (object ["type" .= ("other" :: Text), "value" .= ("x" :: Text)]) threshold))
  expectInputError "threshold decimal profile" "input.invalid_value" "/subjects/left/definition/thresholds/0/value/value" (withThreshold (setField "value" (object ["type" .= ("decimal" :: Text), "value" .= ("1.0" :: Text)]) threshold))
  expectInputError "threshold sustain negative" "input.invalid_value" "/subjects/left/definition/thresholds/0/sustain" (withThreshold (setField "sustain" (String "-1") threshold))
  expectInputError "threshold sustain type" "input.invalid_type" "/subjects/left/definition/thresholds/0/sustain" (withThreshold (setField "sustain" (Bool True) threshold))
  expectInputError "threshold sustain unit type" "input.invalid_type" "/subjects/left/definition/thresholds/0/sustain_unit" (withThreshold (setField "sustain_unit" (Number 1) threshold))
  expectInputError "threshold raw type" "input.invalid_type" "/subjects/left/definition/thresholds/0/raw" (withThreshold (setField "raw" (Number 1) threshold))
  expectInputError "description type" "input.invalid_type" "/subjects/left/definition/description" (setPath ["left", "definition", "description"] (Number 1) base)
  expectInputError "sample type" "input.invalid_type" "/subjects/left/sample" (withSample (Bool True))
  expectInputError "unknown sample field" "input.unknown_field" "/subjects/left/sample/extra" (withSample (addField [] "extra" Null sample))
  expectInputError "missing outcomes" "input.missing_field" "/subjects/left/sample/outcomes" (withSample (removeField "outcomes" sample))
  expectInputError "scores type" "input.invalid_type" "/subjects/left/sample/scores" (withSample (setField "scores" Null sample))
  expectInputError "outcomes type" "input.invalid_type" "/subjects/left/sample/outcomes" (withSample (setField "outcomes" Null sample))
  expectInputError "score type" "input.invalid_type" "/subjects/left/sample/scores/0" (withSample (setField "scores" (Array (Vector.singleton (Number 1))) sample))
  expectInputError "outcome range" "input.invalid_value" "/subjects/left/sample/outcomes/0" (withSample (setField "outcomes" (asArray [2]) sample))
  expectInputError "sample lengths" "input.invalid_value" "/subjects/left/sample/outcomes" (withSample (setField "outcomes" (asArray []) sample))
  let largeSample = object ["scores" .= replicate 100001 ("0" :: Text), "outcomes" .= replicate 100001 (0 :: Int)]
  expectInputError "sample size" "limit.exceeded" "/subjects/left/sample/scores/100000" (withSample largeSample)

assertAccepted :: Text -> Value -> IO ()
assertAccepted label value = case normalizeIsopraxSubjects value of
  Right _ -> pure ()
  Left errorValue -> fail (Text.unpack label <> " was rejected: " <> show errorValue)

expectInputError :: Text -> Text -> Text -> Value -> IO ()
expectInputError label expectedCode expectedPointer value = case normalizeIsopraxSubjects value of
  Left actual
    | packInputErrorCode actual == expectedCode && packInputErrorPointer actual == expectedPointer -> pure ()
    | otherwise -> fail (Text.unpack label <> " returned a different error: " <> show actual)
  Right _ -> fail (Text.unpack label <> " was accepted")

validSubjects :: Value
validSubjects = object ["left" .= subject, "right" .= subject]
  where
    subject = object ["definition" .= definition, "sample" .= Null]
    definition =
      object
        [ "id" .= ("definition" :: Text)
        , "event" .= ("event" :: Text)
        , "observation_process" .= object ["kind" .= ("process" :: Text)]
        , "window" .= object ["unit" .= ("day" :: Text), "anchor" .= ("start" :: Text)]
        ]

setPath :: [Text] -> Value -> Value -> Value
setPath [] replacement _ = replacement
setPath (name : rest) replacement (Object fields) =
  let key = Key.fromText name
      child = maybe Null id (KeyMap.lookup key fields)
   in Object (KeyMap.insert key (setPath rest replacement child) fields)
setPath _ _ value = value

removePath :: [Text] -> Value -> Value
removePath [name] (Object fields) = Object (KeyMap.delete (Key.fromText name) fields)
removePath (name : rest) (Object fields) =
  let key = Key.fromText name
      child = maybe Null id (KeyMap.lookup key fields)
   in Object (KeyMap.insert key (removePath rest child) fields)
removePath _ value = value

addField :: [Text] -> Text -> Value -> Value -> Value
addField path name member = modifyPath path (setField name member)

modifyPath :: [Text] -> (Value -> Value) -> Value -> Value
modifyPath [] update value = update value
modifyPath (name : rest) update (Object fields) =
  let key = Key.fromText name
      child = maybe Null id (KeyMap.lookup key fields)
   in Object (KeyMap.insert key (modifyPath rest update child) fields)
modifyPath _ _ value = value

setField :: Text -> Value -> Value -> Value
setField name member (Object fields) = Object (KeyMap.insert (Key.fromText name) member fields)
setField _ _ value = value

removeField :: Text -> Value -> Value
removeField name (Object fields) = Object (KeyMap.delete (Key.fromText name) fields)
removeField _ value = value

asArray :: [Int] -> Value
asArray = Array . Vector.fromList . map (Number . fromIntegral)

pointerStartsWithSubjects :: Value -> Bool
pointerStartsWithSubjects errorValue = case field "pointer" errorValue of
  Just (String pointer) -> "/subjects" `Text.isPrefixOf` pointer
  _ -> False

objectTextMap :: Value -> IO (Map.Map Text Text)
objectTextMap (Object fields) = Map.fromList <$> mapM readPair (KeyMap.toList fields)
  where
    readPair (key, String value) = pure (Key.toText key, value)
    readPair _ = fail "fixture component digest map contains a non-string"
objectTextMap _ = fail "fixture component digests are not an object"

requiredField :: Text -> Value -> IO Value
requiredField name value = maybe (fail ("missing Isoprax test field: " <> Text.unpack name)) pure (field name value)

requiredText :: Text -> Value -> IO Text
requiredText name value = do
  found <- requiredField name value
  case found of
    String text -> pure text
    _ -> fail ("Isoprax test field is not text: " <> Text.unpack name)

field :: Text -> Value -> Maybe Value
field name (Object fields) = KeyMap.lookup (Key.fromText name) fields
field _ _ = Nothing

testPack :: Pack
testPack =
  Pack
    ( PackDescriptor
        "isoprax/0.1"
        [protocolVersion]
        ( Map.singleton
            "pool_predictions"
            ( OperationDescriptor
                [ ("policy", "isoprax/0.1/policy")
                , ("subject", "isoprax/0.1/subject")
                , ("definition", "isoprax/0.1/definition")
                , ("sample", "isoprax/0.1/sample")
                ]
                [SubjectDeclaration "left" "subject" "isoprax/0.1/subject", SubjectDeclaration "right" "subject" "isoprax/0.1/subject"]
                [ ComponentDeclaration "left" "definition" "definition" "isoprax/0.1/definition" 1 1
                , ComponentDeclaration "left" "sample" "sample" "isoprax/0.1/sample" 0 1
                , ComponentDeclaration "right" "definition" "definition" "isoprax/0.1/definition" 1 1
                , ComponentDeclaration "right" "sample" "sample" "isoprax/0.1/sample" 0 1
                ]
                Nothing
                ["test"]
                [Pass]
                Map.empty
            )
        )
    )
    (PackBehavior normalizeTest decodeTest evaluateTest)

normalizeTest :: Text -> Value -> Value -> [Value] -> Either PackInputError NormalizedPackRequest
normalizeTest _ policy subjects evidence = Right (NormalizedPackRequest policy subjects evidence Nothing)

decodeTest :: NormalizedPackRequest -> Either () NormalizedPackRequest
decodeTest = Right

evaluateTest :: Text -> PackIdentity -> NormalizedPackRequest -> PackResult
evaluateTest _ _ _ = PackResult [] [("test", Pass)] []
