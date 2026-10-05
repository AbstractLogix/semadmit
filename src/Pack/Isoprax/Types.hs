{-# LANGUAGE OverloadedStrings #-}

module Pack.Isoprax.Types
  ( Decimal
  , decimalText
  , decimalValue
  , IsopraxSubjects (..)
  , IsopraxSubject (..)
  , OutcomeDefinition (..)
  , ObservationProcess (..)
  , DefinitionWindow (..)
  , Threshold (..)
  , ThresholdValue (..)
  , PredictionSample
  , predictionScores
  , predictionOutcomes
  , DefinitionSemanticKey (..)
  , ThresholdSemanticKey (..)
  , SemanticThresholdValue (..)
  , asciiTrim
  , asciiLowerTrim
  , parseCanonicalDecimal
  , normalizeIsopraxSubjects
  , normalizeIsopraxSubjectProjections
  , decodeIsopraxSubjects
  , normalizedDefinition
  , normalizedSubject
  , definitionSemanticKey
  , componentPayloads
  )
where

import Core.Decision (ComponentPayload (..))
import Core.Identity (IdentityError (..), PackIdentity, artifactDigest, canonicalBytes)
import Core.Pack (PackInputError (..))
import Data.Aeson (Value (..), object, (.=))
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.Int (Int64)
import Data.Map.Strict (Map)
import Data.Map.Strict qualified as Map
import Data.Ratio ((%))
import Data.Scientific (toBoundedInteger)
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Vector qualified as Vector
import Data.List (sortOn)

data Decimal = Decimal
  { decimalText :: Text
  , decimalValue :: Rational
  }
  deriving (Show)

instance Eq Decimal where
  left == right = decimalValue left == decimalValue right

instance Ord Decimal where
  compare left right = compare (decimalValue left) (decimalValue right)

data ThresholdValue
  = UnknownThresholdValue
  | TextThresholdValue Text
  | DecimalThresholdValue Decimal
  deriving (Eq, Show)

data ObservationProcess = ObservationProcess
  { observationProcessKind :: Text
  , observationProcessParameters :: Map Text Text
  , observationProcessRaw :: Text
  }
  deriving (Eq, Show)

data DefinitionWindow = DefinitionWindow
  { definitionWindowDuration :: Maybe Decimal
  , definitionWindowUnit :: Text
  , definitionWindowAnchor :: Text
  , definitionWindowRaw :: Text
  }
  deriving (Eq, Show)

data Threshold = Threshold
  { thresholdMetric :: Text
  , thresholdOperator :: Text
  , thresholdValue :: ThresholdValue
  , thresholdSustain :: Maybe Decimal
  , thresholdSustainUnit :: Text
  , thresholdRaw :: Text
  }
  deriving (Eq, Show)

data OutcomeDefinition = OutcomeDefinition
  { definitionId :: Text
  , definitionEvent :: Text
  , definitionObservationProcess :: ObservationProcess
  , definitionWindow :: DefinitionWindow
  , definitionThresholds :: [Threshold]
  , definitionDescription :: Maybe Text
  }
  deriving (Eq, Show)

data PredictionSample = PredictionSample
  { predictionScores :: [Decimal]
  , predictionOutcomes :: [Int]
  }
  deriving (Eq, Show)

data IsopraxSubject = IsopraxSubject
  { isopraxDefinition :: OutcomeDefinition
  , isopraxSample :: Maybe PredictionSample
  }
  deriving (Eq, Show)

data IsopraxSubjects = IsopraxSubjects
  { leftSubject :: IsopraxSubject
  , rightSubject :: IsopraxSubject
  }
  deriving (Eq, Show)

data SemanticThresholdValue
  = SemanticUnknown
  | SemanticText Text
  | SemanticDecimal Rational
  deriving (Eq, Ord, Show)

data ThresholdSemanticKey = ThresholdSemanticKey
  { semanticThresholdMetric :: Text
  , semanticThresholdOperator :: Text
  , semanticThresholdValue :: SemanticThresholdValue
  , semanticThresholdSustain :: Maybe Rational
  , semanticThresholdSustainUnit :: Text
  }
  deriving (Eq, Ord, Show)

data DefinitionSemanticKey = DefinitionSemanticKey
  { semanticEvent :: Text
  , semanticProcessKind :: Text
  , semanticProcessParameters :: [(Text, Text)]
  , semanticProcessRaw :: Text
  , semanticWindowDuration :: Maybe Rational
  , semanticWindowUnit :: Text
  , semanticWindowAnchor :: Text
  , semanticThresholds :: [ThresholdSemanticKey]
  }
  deriving (Eq, Ord, Show)

safeInteger :: Integer
safeInteger = 9007199254740991

asciiTrim :: Text -> Text
asciiTrim = Text.dropAround isAsciiSpace
  where
    isAsciiSpace character = (character >= '\t' && character <= '\r') || character == ' '

asciiLowerTrim :: Text -> Text
asciiLowerTrim = Text.map lower . asciiTrim
  where
    lower character
      | character >= 'A' && character <= 'Z' = toEnum (fromEnum character + 32)
      | otherwise = character

parseCanonicalDecimal :: Text -> Either () Decimal
parseCanonicalDecimal source
  | Text.null source || Text.length source > 30 = Left ()
  | otherwise = do
      let (negative, unsigned) = case Text.uncons source of
            Just ('-', rest) -> (True, rest)
            _ -> (False, source)
      if unsigned == "0" && negative then Left () else pure ()
      let pieces = Text.splitOn "." unsigned
      (whole, fraction) <- case pieces of
        [integer] -> Right (integer, "")
        [integer, fractional] -> Right (integer, fractional)
        _ -> Left ()
      if not (validIntegerPart whole) || not (validFraction fraction) || Text.length whole > 16
        then Left ()
        else do
          let wholeNumber = read (Text.unpack whole) :: Integer
              fractionNumber = if Text.null fraction then 0 else read (Text.unpack fraction) :: Integer
              scale = Text.length fraction
              denominator = 10 ^ scale
              magnitude = wholeNumber * denominator + fractionNumber
              signed = if negative then negate magnitude else magnitude
              exact = signed % denominator
          if abs exact > fromInteger safeInteger
            then Left ()
            else Right (Decimal source exact)
  where
    validIntegerPart "0" = True
    validIntegerPart value = case Text.uncons value of
      Just (first, rest) -> first >= '1' && first <= '9' && Text.all isDigit rest
      Nothing -> False
    validFraction value
      | Text.null value = True
      | Text.length value > 12 = False
      | otherwise = isNonZero (Text.last value) && Text.all isDigit value
    isDigit character = character >= '0' && character <= '9'
    isNonZero character = character >= '1' && character <= '9'

type Input = Either PackInputError

invalidType :: Text -> Input value
invalidType = Left . PackInputError "input.invalid_type"

invalidValue :: Text -> Input value
invalidValue = Left . PackInputError "input.invalid_value"

escapePointer :: Text -> Text
escapePointer = Text.concatMap escape
  where
    escape '~' = "~0"
    escape '/' = "~1"
    escape character = Text.singleton character

childPointer :: Text -> Text -> Text
childPointer path name = path <> "/" <> escapePointer name

asObject :: Text -> Value -> Input (KeyMap.KeyMap Value)
asObject _ (Object fields) = Right fields
asObject path _ = invalidType path

closedObject :: Text -> [Text] -> [Text] -> Value -> Input (KeyMap.KeyMap Value)
closedObject path required optional value = do
  fields <- asObject path value
  let allowed = required <> optional
      unknown =
        sortOn Key.toText
          [ key
          | key <- KeyMap.keys fields
          , Key.toText key `notElem` allowed
          ]
  case unknown of
    key : _ -> Left (PackInputError "input.unknown_field" (childPointer path (Key.toText key)))
    [] -> mapM_ (requirePresent path fields) required >> Right fields
  where
    requirePresent parent fields name =
      if KeyMap.member (Key.fromText name) fields
        then Right ()
        else Left (PackInputError "input.missing_field" (childPointer parent name))

fieldValue :: Text -> KeyMap.KeyMap Value -> Text -> Input Value
fieldValue path fields name =
  maybe (Left (PackInputError "input.missing_field" (childPointer path name))) Right (KeyMap.lookup (Key.fromText name) fields)

requiredText :: Text -> KeyMap.KeyMap Value -> Text -> Bool -> Input Text
requiredText path fields name nonEmpty = do
  value <- fieldValue path fields name
  case value of
    String text
      | not nonEmpty || not (Text.null (asciiTrim text)) -> Right text
      | otherwise -> invalidValue (childPointer path name)
    _ -> invalidType (childPointer path name)

optionalText :: Text -> KeyMap.KeyMap Value -> Text -> Text -> Input Text
optionalText path fields name defaultValue = case KeyMap.lookup (Key.fromText name) fields of
  Nothing -> Right defaultValue
  Just Null -> Right defaultValue
  Just (String text) -> Right text
  _ -> invalidType (childPointer path name)

optionalDescription :: Text -> KeyMap.KeyMap Value -> Input (Maybe Text)
optionalDescription path fields = case KeyMap.lookup "description" fields of
  Nothing -> Right Nothing
  Just Null -> Right Nothing
  Just (String value) -> Right (Just value)
  _ -> invalidType (childPointer path "description")

optionalDecimal :: Text -> KeyMap.KeyMap Value -> Text -> Bool -> Input (Maybe Decimal)
optionalDecimal path fields name nonNegative = case KeyMap.lookup (Key.fromText name) fields of
  Nothing -> Right Nothing
  Just Null -> Right Nothing
  Just (String source) -> case parseCanonicalDecimal source of
    Right decimal
      | not nonNegative || decimalValue decimal >= 0 -> Right (Just decimal)
    _ -> invalidValue (childPointer path name)
  _ -> invalidType (childPointer path name)

parseSubjects :: Value -> Input IsopraxSubjects
parseSubjects value = do
  fields <- closedObject "/subjects" ["left", "right"] [] value
  left <- fieldValue "/subjects" fields "left" >>= parseSubject "/subjects/left"
  right <- fieldValue "/subjects" fields "right" >>= parseSubject "/subjects/right"
  Right (IsopraxSubjects left right)

parseSubject :: Text -> Value -> Input IsopraxSubject
parseSubject path value = do
  fields <- closedObject path ["definition", "sample"] [] value
  definitionValue <- fieldValue path fields "definition"
  sampleValue <- fieldValue path fields "sample"
  definition <- parseDefinition (childPointer path "definition") definitionValue
  sample <- parseSample (childPointer path "sample") sampleValue
  Right (IsopraxSubject definition sample)

parseDefinition :: Text -> Value -> Input OutcomeDefinition
parseDefinition path value = do
  fields <- closedObject path ["id", "event", "observation_process", "window"] ["thresholds", "description"] value
  identifier <- requiredText path fields "id" True
  event <- requiredText path fields "event" True
  processValue <- fieldValue path fields "observation_process"
  windowValue <- fieldValue path fields "window"
  process <- parseProcess (childPointer path "observation_process") processValue
  window <- parseWindow (childPointer path "window") windowValue
  thresholdValues <- case KeyMap.lookup "thresholds" fields of
    Nothing -> Right []
    Just (Array items) -> mapM (uncurry (parseThreshold (childPointer path "thresholds"))) (zip [0 :: Int ..] (Vector.toList items))
    _ -> invalidType (childPointer path "thresholds")
  _ <- sortThresholds (childPointer path "thresholds") thresholdValues
  let thresholds = thresholdValues
  description <- optionalDescription path fields
  Right (OutcomeDefinition identifier event process window thresholds description)

parseProcess :: Text -> Value -> Input ObservationProcess
parseProcess path value = do
  fields <- closedObject path ["kind"] ["parameters", "raw"] value
  kind <- requiredText path fields "kind" True
  parameters <- case KeyMap.lookup "parameters" fields of
    Nothing -> Right Map.empty
    Just (Object values) -> Map.fromList <$> mapM parseParameter (sortOn (Key.toText . fst) (KeyMap.toList values))
    _ -> invalidType (childPointer path "parameters")
  raw <- optionalText path fields "raw" ""
  Right (ObservationProcess kind parameters raw)
  where
    parseParameter (key, String text) = Right (Key.toText key, text)
    parseParameter (key, _) = invalidType (childPointer (childPointer path "parameters") (Key.toText key))

parseWindow :: Text -> Value -> Input DefinitionWindow
parseWindow path value = do
  fields <- closedObject path ["unit", "anchor"] ["duration", "raw"] value
  duration <- optionalDecimal path fields "duration" True
  unit <- requiredText path fields "unit" True
  anchor <- requiredText path fields "anchor" True
  raw <- optionalText path fields "raw" ""
  Right (DefinitionWindow duration unit anchor raw)

parseThreshold :: Text -> Int -> Value -> Input Threshold
parseThreshold parent index value = do
  let path = childPointer parent (Text.pack (show index))
  fields <- closedObject path ["metric", "operator"] ["value", "sustain", "sustain_unit", "raw"] value
  metric <- requiredText path fields "metric" True
  operator <- requiredText path fields "operator" True
  thresholdValue' <- parseThresholdValue path fields
  sustain <- optionalDecimal path fields "sustain" True
  sustainUnit <- optionalText path fields "sustain_unit" ""
  raw <- optionalText path fields "raw" ""
  Right (Threshold metric operator thresholdValue' sustain sustainUnit raw)

parseThresholdValue :: Text -> KeyMap.KeyMap Value -> Input ThresholdValue
parseThresholdValue path fields = case KeyMap.lookup "value" fields of
  Nothing -> Right UnknownThresholdValue
  Just Null -> Right UnknownThresholdValue
  Just value@(Object _) -> do
    valueFields <- closedObject (childPointer path "value") ["type", "value"] [] value
    kind <- requiredText (childPointer path "value") valueFields "type" True
    raw <- requiredText (childPointer path "value") valueFields "value" False
    case kind of
      "text" -> Right (TextThresholdValue raw)
      "decimal" -> case parseCanonicalDecimal raw of
        Right decimal -> Right (DecimalThresholdValue decimal)
        Left () -> invalidValue (childPointer (childPointer path "value") "value")
      _ -> invalidValue (childPointer (childPointer path "value") "type")
  Just _ -> invalidType (childPointer path "value")

parseSample :: Text -> Value -> Input (Maybe PredictionSample)
parseSample _ Null = Right Nothing
parseSample path value = do
  fields <- closedObject path ["scores", "outcomes"] [] value
  scoreValues <- fieldValue path fields "scores"
  outcomeValues <- fieldValue path fields "outcomes"
  scoreItems <- case scoreValues of
    Array items -> Right items
    _ -> invalidType (childPointer path "scores")
  if Vector.length scoreItems > 100000
    then Left (PackInputError "limit.exceeded" (childPointer (childPointer path "scores") "100000"))
    else Right ()
  outcomeItems <- case outcomeValues of
    Array items -> Right items
    _ -> invalidType (childPointer path "outcomes")
  if Vector.length outcomeItems > 100000
    then Left (PackInputError "limit.exceeded" (childPointer (childPointer path "outcomes") "100000"))
    else Right ()
  if Vector.length scoreItems /= Vector.length outcomeItems
    then invalidValue (childPointer path "outcomes")
    else do
      scores <- mapM parseScore (zip [0 :: Int ..] (Vector.toList scoreItems))
      outcomes <- mapM parseOutcome (zip [0 :: Int ..] (Vector.toList outcomeItems))
      Right (Just (PredictionSample scores outcomes))
  where
    parseScore (index, String source) = case parseCanonicalDecimal source of
      Right decimal
        | decimalValue decimal >= 0 && decimalValue decimal <= 1 -> Right decimal
      _ -> invalidValue (childPointer (childPointer path "scores") (Text.pack (show index)))
    parseScore (index, _) = invalidType (childPointer (childPointer path "scores") (Text.pack (show index)))
    parseOutcome (index, Number number) = case toBoundedInteger number :: Maybe Int64 of
      Just outcome | outcome == 0 || outcome == 1 -> Right (fromIntegral outcome)
      _ -> invalidValue (childPointer (childPointer path "outcomes") (Text.pack (show index)))
    parseOutcome (index, _) = invalidType (childPointer (childPointer path "outcomes") (Text.pack (show index)))

sortThresholds :: Text -> [Threshold] -> Input [Threshold]
sortThresholds path thresholds = do
  keyed <- mapM withIdentityBytes thresholds
  Right (map fst (sortOn snd keyed))
  where
    withIdentityBytes threshold = case canonicalBytes (normalizedThreshold threshold) of
      Left _ -> invalidValue path
      Right bytes -> Right (threshold, (thresholdSemanticKey threshold, bytes))

thresholdSemanticKey :: Threshold -> ThresholdSemanticKey
thresholdSemanticKey threshold =
  ThresholdSemanticKey
    { semanticThresholdMetric = asciiLowerTrim (thresholdMetric threshold)
    , semanticThresholdOperator = asciiTrim (thresholdOperator threshold)
    , semanticThresholdValue = case thresholdValue threshold of
        UnknownThresholdValue -> SemanticUnknown
        TextThresholdValue value -> SemanticText value
        DecimalThresholdValue decimal -> SemanticDecimal (decimalValue decimal)
    , semanticThresholdSustain = decimalValue <$> thresholdSustain threshold
    , semanticThresholdSustainUnit = asciiLowerTrim (thresholdSustainUnit threshold)
    }

normalizedThreshold :: Threshold -> Value
normalizedThreshold threshold =
  object
    [ "metric" .= thresholdMetric threshold
    , "operator" .= thresholdOperator threshold
    , "value" .= normalizedThresholdValue (thresholdValue threshold)
    , "sustain" .= (normalizedDecimal <$> thresholdSustain threshold)
    , "sustain_unit" .= thresholdSustainUnit threshold
    , "raw" .= thresholdRaw threshold
    ]

normalizedThresholdValue :: ThresholdValue -> Value
normalizedThresholdValue thresholdValue' = case thresholdValue' of
  UnknownThresholdValue -> Null
  TextThresholdValue value -> object ["type" .= ("text" :: Text), "value" .= value]
  DecimalThresholdValue decimal -> object ["type" .= ("decimal" :: Text), "value" .= decimalText decimal]

normalizedDefinition :: OutcomeDefinition -> Value
normalizedDefinition definition =
  object
    [ "id" .= definitionId definition
    , "event" .= definitionEvent definition
    , "observation_process" .= processValue
    , "window" .= windowValue
    , "thresholds" .= map normalizedThreshold (definitionThresholds definition)
    , "description" .= maybe Null String (definitionDescription definition)
    ]
  where
    process = definitionObservationProcess definition
    processValue =
      object
        [ "kind" .= observationProcessKind process
        , "parameters" .= textMapValue (observationProcessParameters process)
        , "raw" .= observationProcessRaw process
        ]
    window = definitionWindow definition
    windowValue =
      object
        [ "duration" .= (normalizedDecimal <$> definitionWindowDuration window)
        , "unit" .= definitionWindowUnit window
        , "anchor" .= definitionWindowAnchor window
        , "raw" .= definitionWindowRaw window
        ]

normalizedSubject :: IsopraxSubject -> Value
normalizedSubject subject =
  object
    [ "definition" .= normalizedDefinition (isopraxDefinition subject)
    , "sample" .= maybe Null normalizedSample (isopraxSample subject)
    ]

normalizedSample :: PredictionSample -> Value
normalizedSample sample =
  object
    [ "scores" .= map decimalText (predictionScores sample)
    , "outcomes" .= predictionOutcomes sample
    ]

normalizedDecimal :: Decimal -> Text
normalizedDecimal = decimalText

textMapValue :: Map Text Text -> Value
textMapValue = Object . KeyMap.fromList . map toPair . Map.toList
  where
    toPair (key, value) = (Key.fromText key, String value)

normalizedIsopraxSubjects :: IsopraxSubjects -> Value
normalizedIsopraxSubjects subjects =
  object
    [ "left" .= normalizedSubject (leftSubject subjects)
    , "right" .= normalizedSubject (rightSubject subjects)
    ]

normalizeIsopraxSubjects :: Value -> Either PackInputError Value
normalizeIsopraxSubjects value = fst <$> normalizeIsopraxSubjectProjections value

normalizeIsopraxSubjectProjections :: Value -> Either PackInputError (Value, Value)
normalizeIsopraxSubjectProjections value = do
  subjects <- parseSubjects value
  identitySubjects <- case normalizedIsopraxIdentitySubjects subjects of
    Left _ -> Left (PackInputError "input.invalid_value" "/subjects")
    Right result -> Right result
  Right (normalizedIsopraxSubjects subjects, identitySubjects)

normalizedIsopraxIdentitySubjects :: IsopraxSubjects -> Either IdentityError Value
normalizedIsopraxIdentitySubjects subjects = do
  left <- normalizedIdentitySubject (leftSubject subjects)
  right <- normalizedIdentitySubject (rightSubject subjects)
  Right (object ["left" .= left, "right" .= right])

normalizedIdentitySubject :: IsopraxSubject -> Either IdentityError Value
normalizedIdentitySubject subject = do
  definition <- normalizedIdentityDefinition (isopraxDefinition subject)
  Right
    ( object
        [ "definition" .= definition
        , "sample" .= maybe Null normalizedSample (isopraxSample subject)
        ]
    )

normalizedIdentityDefinition :: OutcomeDefinition -> Either IdentityError Value
normalizedIdentityDefinition definition = do
  thresholds <- case sortThresholds "/subjects/definition/thresholds" (definitionThresholds definition) of
    Left _ -> Left InvalidNumber
    Right result -> Right result
  Right (normalizedDefinition (definition {definitionThresholds = thresholds}))

decodeIsopraxSubjects :: Value -> Either () IsopraxSubjects
decodeIsopraxSubjects value = case parseSubjects value of
  Left _ -> Left ()
  Right subjects
    | normalizedIsopraxSubjects subjects == value -> Right subjects
    | otherwise -> Left ()

definitionSemanticKey :: OutcomeDefinition -> DefinitionSemanticKey
definitionSemanticKey definition =
  DefinitionSemanticKey
    { semanticEvent = asciiLowerTrim (definitionEvent definition)
    , semanticProcessKind = asciiLowerTrim (observationProcessKind process)
    , semanticProcessParameters = Map.toAscList (observationProcessParameters process)
    , semanticProcessRaw = asciiLowerTrim (observationProcessRaw process)
    , semanticWindowDuration = decimalValue <$> definitionWindowDuration window
    , semanticWindowUnit = asciiLowerTrim (definitionWindowUnit window)
    , semanticWindowAnchor = asciiLowerTrim (definitionWindowAnchor window)
    , semanticThresholds = sortOn id (map thresholdSemanticKey (definitionThresholds definition))
    }
  where
    process = definitionObservationProcess definition
    window = definitionWindow definition

componentPayloads :: PackIdentity -> IsopraxSubjects -> Either IdentityError [ComponentPayload]
componentPayloads identities subjects =
  concat <$> mapM bindSubject [("left", leftSubject subjects), ("right", rightSubject subjects)]
  where
    bindSubject (role, subject) = do
      definition <- normalizedIdentityDefinition (isopraxDefinition subject)
      definitionDigest <- artifactDigest identities "definition" definitionSchema definition
      let definitionComponent = ComponentPayload role "definition" "definition" definitionSchema definition
      case isopraxSample subject of
        Nothing -> Right [definitionComponent]
        Just sample -> do
          let sampleValue =
                object
                  [ "definition_digest" .= definitionDigest
                  , "scores" .= map decimalText (predictionScores sample)
                  , "outcomes" .= predictionOutcomes sample
                  ]
          _ <- artifactDigest identities "sample" sampleSchema sampleValue
          Right (definitionComponent : [ComponentPayload role "sample" "sample" sampleSchema sampleValue])
    definitionSchema = "isoprax/0.1/definition"
    sampleSchema = "isoprax/0.1/sample"
