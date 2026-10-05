{-# LANGUAGE OverloadedStrings #-}

module Pack.Isoprax.Calibration
  ( DecimalTarget (..)
  , LegacyConversion (..)
  , LegacyConversionError (..)
  , CalibrationPolicy
  , CalibrationPolicyError (..)
  , CalibrationFailure (..)
  , CalibrationResult (..)
  , convertLegacyBinary64
  , mkCalibrationPolicy
  , calibrateSample
  )
where

import Data.Aeson (toJSON)
import Data.Aeson.RFC8785 (encodeCanonical)
import Data.ByteString.Lazy qualified as LazyByteString
import Data.Map.Strict qualified as Map
import Data.Ratio ((%))
import Data.Set qualified as Set
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Text.Encoding qualified as TextEncoding
import Pack.Isoprax.Types
  ( Decimal
  , decimalValue
  , predictionOutcomes
  , predictionScores
  , PredictionSample
  , parseCanonicalDecimal
  )

data DecimalTarget
  = NonNegativeTarget
  | UnitIntervalTarget
  | SignedTarget
  deriving (Eq, Show)

data LegacyConversion = LegacyConversion
  { legacyJcsNumber :: Text
  , legacyExpandedDecimal :: Text
  , legacyDecimal :: Decimal
  }
  deriving (Eq, Show)

data LegacyConversionError
  = LegacyNonFinite
  | LegacyEncodingFailure
  | LegacyDecimalProfileFailure
  | LegacyFieldRangeFailure
  deriving (Eq, Show)

data CalibrationPolicy = CalibrationPolicy
  { calibrationMinimumEvents :: Int
  , calibrationBinCount :: Int
  , calibrationMaximumECE :: Decimal
  }
  deriving (Eq, Show)

data CalibrationPolicyError
  = MinimumEventsOutOfRange
  | BinCountOutOfRange
  | MaximumECEOutOfRange
  deriving (Eq, Show)

data CalibrationFailure
  = CalibrationMinimumEvents
  | CalibrationOutcomeClassMissing
  | CalibrationZeroScoreVariance
  | CalibrationECEExceeded
  deriving (Eq, Ord, Show)

data CalibrationResult = CalibrationResult
  { calibrationExactECE :: Maybe Rational
  , calibrationFailures :: [CalibrationFailure]
  }
  deriving (Eq, Show)

convertLegacyBinary64 :: DecimalTarget -> Double -> Either LegacyConversionError LegacyConversion
convertLegacyBinary64 target source
  | isNaN source || isInfinite source = Left LegacyNonFinite
  | otherwise = do
      jcs <- case TextEncoding.decodeUtf8' (LazyByteString.toStrict (encodeCanonical (toJSON source))) of
        Left _ -> Left LegacyEncodingFailure
        Right text -> Right text
      expanded <- expandExponent jcs
      decimal <- case parseCanonicalDecimal expanded of
        Left () -> Left LegacyDecimalProfileFailure
        Right value -> Right value
      if allowedTarget target (decimalValue decimal)
        then Right (LegacyConversion jcs expanded decimal)
        else Left LegacyFieldRangeFailure

allowedTarget :: DecimalTarget -> Rational -> Bool
allowedTarget target value = case target of
  NonNegativeTarget -> value >= 0
  UnitIntervalTarget -> value >= 0 && value <= 1
  SignedTarget -> True

expandExponent :: Text -> Either LegacyConversionError Text
expandExponent source = case Text.break (\character -> character == 'e' || character == 'E') source of
  (mantissa, rest)
    | Text.null rest -> Right source
    | otherwise -> do
        powerOfTen <- parseExponent (Text.drop 1 rest)
        renderPlain mantissa powerOfTen

parseExponent :: Text -> Either LegacyConversionError Int
parseExponent source =
  let (sign, digits) = case Text.uncons source of
        Just ('+', rest) -> (1, rest)
        Just ('-', rest) -> (-1, rest)
        _ -> (1, source)
   in if Text.null digits || Text.length digits > 4 || not (Text.all isDigit digits)
        then Left LegacyEncodingFailure
        else Right (sign * Text.foldl' (\value character -> value * 10 + fromEnum character - fromEnum '0') 0 digits)
  where
    isDigit character = character >= '0' && character <= '9'

renderPlain :: Text -> Int -> Either LegacyConversionError Text
renderPlain source powerOfTen = do
  let (negative, unsigned) = case Text.uncons source of
        Just ('-', rest) -> (True, rest)
        _ -> (False, source)
      pieces = Text.splitOn "." unsigned
  (whole, fraction) <- case pieces of
    [integer] -> Right (integer, "")
    [integer, decimal] -> Right (integer, decimal)
    _ -> Left LegacyEncodingFailure
  if Text.null whole || not (Text.all isDigit whole) || not (Text.all isDigit fraction)
    then Left LegacyEncodingFailure
    else do
      let digits = whole <> fraction
          decimalPosition = Text.length whole + powerOfTen
          signLength = if negative then 1 else 0
          expandedLength
            | decimalPosition <= 0 = signLength + 2 + negate decimalPosition + Text.length digits
            | decimalPosition >= Text.length digits = signLength + decimalPosition
            | otherwise = signLength + Text.length digits + 1
      if expandedLength > 30
        then Left LegacyDecimalProfileFailure
        else
          let body
                | decimalPosition <= 0 = "0." <> Text.replicate (negate decimalPosition) "0" <> digits
                | decimalPosition >= Text.length digits = digits <> Text.replicate (decimalPosition - Text.length digits) "0"
                | otherwise = Text.take decimalPosition digits <> "." <> Text.drop decimalPosition digits
           in Right ((if negative then "-" else "") <> body)
  where
    isDigit character = character >= '0' && character <= '9'

mkCalibrationPolicy :: Int -> Int -> Decimal -> Either CalibrationPolicyError CalibrationPolicy
mkCalibrationPolicy minimumEvents bins maximumECE
  | minimumEvents < 1 || minimumEvents > 100000 = Left MinimumEventsOutOfRange
  | bins < 1 || bins > 1000 = Left BinCountOutOfRange
  | decimalValue maximumECE < 0 || decimalValue maximumECE > 1 = Left MaximumECEOutOfRange
  | otherwise = Right (CalibrationPolicy minimumEvents bins maximumECE)

calibrateSample :: CalibrationPolicy -> PredictionSample -> CalibrationResult
calibrateSample policy sample
  | eventCount == 0 = CalibrationResult Nothing [CalibrationMinimumEvents]
  | otherwise = CalibrationResult (Just ece) failures
  where
    scores = predictionScores sample
    outcomes = predictionOutcomes sample
    eventCount = length scores
    outcomeClasses = Set.fromList outcomes
    distinctScores = Set.fromList scores
    ece = exactECE (calibrationBinCount policy) scores outcomes
    failures =
      [CalibrationMinimumEvents | eventCount < calibrationMinimumEvents policy]
        <> [CalibrationOutcomeClassMissing | Set.size outcomeClasses < 2]
        <> [CalibrationZeroScoreVariance | Set.size distinctScores < 2]
        <> [CalibrationECEExceeded | ece > decimalValue (calibrationMaximumECE policy)]

exactECE :: Int -> [Decimal] -> [Int] -> Rational
exactECE bins scores outcomes = sum (map weightedError (Map.elems grouped))
  where
    totalEvents = length scores
    grouped =
      Map.fromListWith (++)
        [ (binIndex score, [(decimalValue score, fromIntegral outcome :: Rational)])
        | (score, outcome) <- zip scores outcomes
        ]
    binIndex :: Decimal -> Int
    binIndex score = fromInteger (min (toInteger bins - 1) (floor (decimalValue score * fromIntegral bins)))
    weightedError values =
      let count = length values
          meanScore = sum (map fst values) / fromIntegral count
          meanOutcome = sum (map snd values) / fromIntegral count
       in (toInteger count % toInteger totalEvents) * abs (meanScore - meanOutcome)
