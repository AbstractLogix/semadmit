{-# LANGUAGE OverloadedStrings #-}

module Pack.Isoprax.PoolPredictions (isopraxPack) where

import Core.Decision
  ( ComponentDeclaration (..)
  , Diagnostic (..)
  , Outcome (..)
  , SubjectDeclaration (..)
  )
import Core.Identity (PackIdentity)
import Core.Pack
  ( NormalizedPackRequest (..)
  , OperationDescriptor (..)
  , Pack (..)
  , PackBehavior (..)
  , PackDescriptor (..)
  , PackInputError (..)
  , PackResult (..)
  )
import Core.Protocol (protocolVersion)
import Data.Aeson (Result (..), Value (..), fromJSON)
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.List (sortOn)
import Data.Map.Strict (Map)
import Data.Map.Strict qualified as Map
import Data.Set qualified as Set
import Data.Text (Text)
import Data.Text qualified as Text
import Pack.Isoprax.Calibration
  ( CalibrationFailure (..)
  , CalibrationPolicy
  , CalibrationResult (..)
  , calibrateSample
  , mkCalibrationPolicy
  )
import Pack.Isoprax.Types
  ( DefinitionSemanticKey (..)
  , DefinitionWindow (..)
  , IsopraxSubject (..)
  , IsopraxSubjects (..)
  , OutcomeDefinition (..)
  , PredictionSample
  , SemanticThresholdValue (..)
  , Threshold (..)
  , ThresholdSemanticKey (..)
  , ThresholdValue (..)
  , componentPayloads
  , decimalValue
  , decodeIsopraxSubjects
  , definitionSemanticKey
  , normalizeIsopraxSubjectProjections
  , parseCanonicalDecimal
  )

data PoolInput = PoolInput
  { poolPolicy :: CalibrationPolicy
  , poolSubjects :: IsopraxSubjects
  }

isopraxPack :: Pack
isopraxPack = Pack descriptor (PackBehavior normalize decode evaluate)
  where
    descriptor =
      PackDescriptor
        "isoprax/0.1"
        [protocolVersion]
        (Map.singleton "pool_predictions" operation)
    operation =
      OperationDescriptor
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
        ["definition.compatibility", "calibration.left", "calibration.right"]
        [Pass, Fail, Missing]
        diagnosticPointerTemplates

diagnosticPointerTemplates :: Map Text [Text]
diagnosticPointerTemplates =
  Map.fromList
    [ ("definition.event_mismatch", ["/subjects/right/definition/event"])
    , ("definition.observation_process_mismatch", ["/subjects/right/definition/observation_process"])
    , ("definition.window_mismatch", ["/subjects/right/definition/window"])
    , ("definition.thresholds_mismatch", ["/subjects/right/definition/thresholds"])
    , ( "definition.unknown"
      , [ "/subjects/{left,right}/definition/window/duration"
        , "/subjects/{left,right}/definition/thresholds/{canonical-index}/value"
        ]
      )
    , ("calibration.sample_missing", ["/subjects/{left,right}/sample"])
    , ("calibration.min_events", ["/subjects/{left,right}/sample"])
    , ("calibration.outcome_class_missing", ["/subjects/{left,right}/sample"])
    , ("calibration.zero_score_variance", ["/subjects/{left,right}/sample"])
    , ("calibration.ece_exceeded", ["/subjects/{left,right}/sample"])
    ]

normalize :: Text -> Value -> Value -> [Value] -> Either PackInputError NormalizedPackRequest
normalize _ policy subjects evidence = do
  _ <- parsePolicy policy
  (normalizedSubjects, subjectIdentityProjection) <- normalizeIsopraxSubjectProjections subjects
  case evidence of
    [] -> Right (NormalizedPackRequest policy normalizedSubjects [] (Just subjectIdentityProjection))
    _ -> Left (PackInputError "input.invalid_value" "/evidence/0")

decode :: NormalizedPackRequest -> Either () PoolInput
decode request = do
  policy <- either (const (Left ())) Right (parsePolicy (normalizedPolicy request))
  subjects <- decodeIsopraxSubjects (normalizedSubjects request)
  if null (normalizedEvidence request)
    then Right (PoolInput policy subjects)
    else Left ()

parsePolicy :: Value -> Either PackInputError CalibrationPolicy
parsePolicy value = do
  fields <- closedPolicyObject value
  minimumEvents <- policyInteger fields "min_events"
  bins <- policyInteger fields "n_bins"
  maximumECEText <- policyText fields "max_ece"
  maximumECE <- case parseCanonicalDecimal maximumECEText of
    Left () -> invalidValue "/policy/max_ece"
    Right decimal
      | decimalValue decimal >= 0 && decimalValue decimal <= 1 -> Right decimal
      | otherwise -> invalidValue "/policy/max_ece"
  comparison <- policyText fields "definition_comparison"
  numericProfile <- policyText fields "numeric_profile"
  if comparison /= "normalized-key/0.1"
    then Left (PackInputError "policy.unsupported" "/policy/definition_comparison")
    else if numericProfile /= "decimal-rational-12/0.1"
      then Left (PackInputError "policy.unsupported" "/policy/numeric_profile")
      else case mkCalibrationPolicy minimumEvents bins maximumECE of
        Left _ -> invalidValue "/policy"
        Right policy -> Right policy

closedPolicyObject :: Value -> Either PackInputError (KeyMap.KeyMap Value)
closedPolicyObject (Object fields) = do
  let required = ["min_events", "n_bins", "max_ece", "definition_comparison", "numeric_profile"]
      unknown = sortOn Key.toText [key | key <- KeyMap.keys fields, Key.toText key `notElem` required]
  case unknown of
    key : _ -> Left (PackInputError "input.unknown_field" (pointer "/policy" (Key.toText key)))
    [] -> mapM_ require required >> Right fields
  where
    require name =
      if KeyMap.member (Key.fromText name) fields
        then Right ()
        else Left (PackInputError "input.missing_field" (pointer "/policy" name))
closedPolicyObject _ = invalidType "/policy"

policyInteger :: KeyMap.KeyMap Value -> Text -> Either PackInputError Int
policyInteger fields name = case KeyMap.lookup (Key.fromText name) fields of
  Just (Number value) -> case fromJSON (Number value) of
    Success number
      | withinRange name number -> Right number
      | otherwise -> invalidValue (pointer "/policy" name)
    Error _ -> invalidValue (pointer "/policy" name)
  Just _ -> invalidType (pointer "/policy" name)
  Nothing -> Left (PackInputError "input.missing_field" (pointer "/policy" name))
  where
    withinRange "min_events" number = number >= 1 && number <= 100000
    withinRange "n_bins" number = number >= 1 && number <= 1000
    withinRange _ _ = False

policyText :: KeyMap.KeyMap Value -> Text -> Either PackInputError Text
policyText fields name = case KeyMap.lookup (Key.fromText name) fields of
  Just (String text) -> Right text
  Just _ -> invalidType (pointer "/policy" name)
  Nothing -> Left (PackInputError "input.missing_field" (pointer "/policy" name))

invalidType :: Text -> Either PackInputError value
invalidType = Left . PackInputError "input.invalid_type"

invalidValue :: Text -> Either PackInputError value
invalidValue = Left . PackInputError "input.invalid_value"

pointer :: Text -> Text -> Text
pointer base fieldName = base <> "/" <> Text.replace "/" "~1" (Text.replace "~" "~0" fieldName)

evaluate :: Text -> PackIdentity -> PoolInput -> PackResult
evaluate _ identities input = PackResult components obligations diagnostics
  where
    subjects = poolSubjects input
    (compatibility, compatibilityDiagnostics) = compareDefinitions (isopraxDefinition (leftSubject subjects)) (isopraxDefinition (rightSubject subjects))
    (leftOutcome, leftDiagnostics) = calibrationOutcome "left" (poolPolicy input) (isopraxSample (leftSubject subjects))
    (rightOutcome, rightDiagnostics) = calibrationOutcome "right" (poolPolicy input) (isopraxSample (rightSubject subjects))
    obligations =
      [ ("definition.compatibility", compatibility)
      , ("calibration.left", leftOutcome)
      , ("calibration.right", rightOutcome)
      ]
    diagnostics = compatibilityDiagnostics <> leftDiagnostics <> rightDiagnostics
    components = either (const []) id (componentPayloads identities subjects)

compareDefinitions :: OutcomeDefinition -> OutcomeDefinition -> (Outcome, [Diagnostic])
compareDefinitions left right = (outcome, mismatchDiagnostics <> unknownDiagnostics)
  where
    leftKey = definitionSemanticKey left
    rightKey = definitionSemanticKey right
    mismatchDiagnostics =
      [ Diagnostic "definition.compatibility" "/subjects/right/definition/event" "definition.event_mismatch"
      | semanticEvent leftKey /= semanticEvent rightKey
      ]
        <> [ Diagnostic "definition.compatibility" "/subjects/right/definition/observation_process" "definition.observation_process_mismatch"
           | (semanticProcessKind leftKey, semanticProcessParameters leftKey, semanticProcessRaw leftKey)
               /= (semanticProcessKind rightKey, semanticProcessParameters rightKey, semanticProcessRaw rightKey)
           ]
        <> [ Diagnostic "definition.compatibility" "/subjects/right/definition/window" "definition.window_mismatch"
           | semanticWindowUnit leftKey /= semanticWindowUnit rightKey
               || semanticWindowAnchor leftKey /= semanticWindowAnchor rightKey
               || knownDurationMismatch (semanticWindowDuration leftKey) (semanticWindowDuration rightKey)
           ]
        <> [ Diagnostic "definition.compatibility" "/subjects/right/definition/thresholds" "definition.thresholds_mismatch"
           | knownThresholdMismatch (semanticThresholds leftKey) (semanticThresholds rightKey)
           ]
    unknownDiagnostics = unknownDefinitionDiagnostics "left" left <> unknownDefinitionDiagnostics "right" right
    outcome
      | not (null mismatchDiagnostics) = Fail
      | not (null unknownDiagnostics) = Missing
      | otherwise = Pass

knownDurationMismatch :: Maybe Rational -> Maybe Rational -> Bool
knownDurationMismatch (Just left) (Just right) = left /= right
knownDurationMismatch _ _ = False

unknownDefinitionDiagnostics :: Text -> OutcomeDefinition -> [Diagnostic]
unknownDefinitionDiagnostics role definition = durationUnknown <> thresholdUnknown
  where
    base = "/subjects/" <> role <> "/definition"
    durationUnknown = case definitionWindowDuration (definitionWindow definition) of
      Nothing -> [Diagnostic "definition.compatibility" (base <> "/window/duration") "definition.unknown"]
      Just _ -> []
    thresholdUnknown =
      [ Diagnostic "definition.compatibility" (base <> "/thresholds/" <> Text.pack (show index) <> "/value") "definition.unknown"
      | (index, threshold) <- zip [0 :: Int ..] (definitionThresholds definition)
      , thresholdValue threshold == UnknownThresholdValue
      ]

type ThresholdBase = (Text, Text, Maybe Rational, Text)

knownThresholdMismatch :: [ThresholdSemanticKey] -> [ThresholdSemanticKey] -> Bool
knownThresholdMismatch left right = any mismatch (Set.toList allBases)
  where
    leftGroups = groupThresholds left
    rightGroups = groupThresholds right
    allBases = Set.union (Map.keysSet leftGroups) (Map.keysSet rightGroups)
    mismatch base =
      let leftValues = Map.findWithDefault [] base leftGroups
          rightValues = Map.findWithDefault [] base rightGroups
          leftKnown = valueCounts leftValues
          rightKnown = valueCounts rightValues
          allKnownValues = Set.union (Map.keysSet leftKnown) (Map.keysSet rightKnown)
          leftUnknown = length (filter (== SemanticUnknown) leftValues)
          rightUnknown = length (filter (== SemanticUnknown) rightValues)
          requiredLeft = sum [max 0 (count rightKnown value - count leftKnown value) | value <- Set.toList allKnownValues]
          requiredRight = sum [max 0 (count leftKnown value - count rightKnown value) | value <- Set.toList allKnownValues]
       in length leftValues /= length rightValues || requiredLeft > leftUnknown || requiredRight > rightUnknown
    count counts value = Map.findWithDefault 0 value counts

groupThresholds :: [ThresholdSemanticKey] -> Map ThresholdBase [SemanticThresholdValue]
groupThresholds = Map.fromListWith (<>) . map toGroup
  where
    toGroup threshold =
      ( ( semanticThresholdMetric threshold
        , semanticThresholdOperator threshold
        , semanticThresholdSustain threshold
        , semanticThresholdSustainUnit threshold
        )
      , [semanticThresholdValue threshold]
      )

valueCounts :: [SemanticThresholdValue] -> Map SemanticThresholdValue Int
valueCounts = Map.fromListWith (+) . map (\value -> (value, 1)) . filter (/= SemanticUnknown)

calibrationOutcome :: Text -> CalibrationPolicy -> Maybe PredictionSample -> (Outcome, [Diagnostic])
calibrationOutcome role _ Nothing =
  (Missing, [Diagnostic obligation pointerValue "calibration.sample_missing"])
  where
    obligation = "calibration." <> role
    pointerValue = "/subjects/" <> role <> "/sample"
calibrationOutcome role policy (Just sample) =
  (outcome, map diagnostic (calibrationFailures result))
  where
    obligation = "calibration." <> role
    pointerValue = "/subjects/" <> role <> "/sample"
    result = calibrateSample policy sample
    outcome = if null (calibrationFailures result) then Pass else Fail
    diagnostic failure = Diagnostic obligation pointerValue (failureCode failure)

failureCode :: CalibrationFailure -> Text
failureCode failure = case failure of
  CalibrationMinimumEvents -> "calibration.min_events"
  CalibrationOutcomeClassMissing -> "calibration.outcome_class_missing"
  CalibrationZeroScoreVariance -> "calibration.zero_score_variance"
  CalibrationECEExceeded -> "calibration.ece_exceeded"
