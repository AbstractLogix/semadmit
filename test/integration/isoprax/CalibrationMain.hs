{-# LANGUAGE OverloadedStrings #-}

module Main (main) where

import Control.Monad (forM_, unless)
import Data.Aeson (Result (..), Value (..), eitherDecodeStrict', fromJSON)
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString qualified as ByteString
import Data.Map.Strict qualified as Map
import Data.Ratio ((%))
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Vector qualified as Vector
import GHC.Float (castWord64ToDouble)
import Numeric (readHex)
import Pack.Isoprax.Calibration
  ( CalibrationPolicy
  , CalibrationPolicyError (..)
  , CalibrationResult (..)
  , DecimalTarget (..)
  , LegacyConversion (..)
  , LegacyConversionError (..)
  , calibrateSample
  , convertLegacyBinary64
  , mkCalibrationPolicy
  )
import Pack.Isoprax.Types
  ( Decimal
  , IsopraxSubject (..)
  , IsopraxSubjects (..)
  , decodeIsopraxSubjects
  , normalizeIsopraxSubjects
  , parseCanonicalDecimal
  )
import Data.Word (Word64)

main :: IO ()
main = do
  requests <- loadCases "conformance/fixtures/isoprax-cases.json"
  calculations <- loadCases "conformance/fixtures/isoprax-calculations.json"
  let calculationById = Map.fromList [(identifier, value) | value <- calculations, Just identifier <- [textField "id" value]]
  forM_ requests (checkRequest calculationById)
  adapter <- loadCases "conformance/fixtures/isoprax-legacy-number-adapter.json"
  forM_ adapter checkLegacyNumber
  checkPolicyBounds

loadCases :: FilePath -> IO [Value]
loadCases path = do
  source <- ByteString.readFile path
  root <- case eitherDecodeStrict' source of
    Left message -> fail (path <> " is invalid JSON: " <> message)
    Right value -> pure value
  case field "cases" root of
    Just (Array values) -> pure (Vector.toList values)
    _ -> fail (path <> " has no cases array")

checkRequest :: Map.Map Text Value -> Value -> IO ()
checkRequest calculationById requestCase = case field "expected" requestCase of
  Just expected | field "error" expected /= Nothing -> pure ()
  Just expected -> do
    identifier <- requiredText "id" requestCase
    request <- requiredField "request" requestCase
    subjectsValue <- requiredField "subjects" request
    policyValue <- requiredField "policy" request
    normalized <- case normalizeIsopraxSubjects subjectsValue of
      Left errorValue -> fail ("unexpected subject error in " <> Text.unpack identifier <> ": " <> show errorValue)
      Right value -> pure value
    subjects <- case decodeIsopraxSubjects normalized of
      Left () -> fail ("normalized subjects did not decode in " <> Text.unpack identifier)
      Right value -> pure value
    policy <- decodePolicy policyValue
    let calculation = Map.lookup identifier calculationById
    checkRole "left" (leftSubject subjects) policy expected calculation
    checkRole "right" (rightSubject subjects) policy expected calculation
  _ -> fail "Isoprax request fixture has no expected value"

decodePolicy :: Value -> IO CalibrationPolicy
decodePolicy value = do
  minimumEvents <- intField "min_events" value
  bins <- intField "n_bins" value
  maximumText <- requiredText "max_ece" value
  maximumECE <- parseDecimal maximumText
  case mkCalibrationPolicy minimumEvents bins maximumECE of
    Left errorValue -> fail ("fixture policy was rejected: " <> show errorValue)
    Right policy -> pure policy

checkRole :: Text -> IsopraxSubject -> CalibrationPolicy -> Value -> Maybe Value -> IO ()
checkRole role subject policy expected calculation = do
  expectedOutcome <- obligationOutcome ("calibration." <> role) expected
  actualResult <- case isopraxSample subject of
    Nothing -> do
      unless (expectedOutcome == "missing") $ fail ("missing sample did not produce missing calibration for " <> Text.unpack role)
      pure Nothing
    Just sample -> do
      let result = calibrateSample policy sample
          outcome = if null (calibrationFailures result) then "pass" else "fail"
      unless (outcome == expectedOutcome) $
        fail ("calibration outcome differs for " <> Text.unpack role <> ": " <> show result)
      pure (Just result)
  case calculation of
    Nothing -> pure ()
    Just calculationValue -> do
      expectedECE <- parseExpectedECE role calculationValue
      let actualECE = calibrationExactECE =<< actualResult
      unless (actualECE == expectedECE) $
        fail ("exact ECE differs for " <> Text.unpack role <> ": " <> show actualECE <> " /= " <> show expectedECE)

checkLegacyNumber :: Value -> IO ()
checkLegacyNumber value = do
  identifier <- requiredText "id" value
  bitsText <- requiredText "ieee754_hex" value
  targetText <- requiredText "target_field" value
  profile <- requiredText "expected_profile" value
  bits <- maybe (fail ("invalid IEEE-754 fixture bits in " <> Text.unpack identifier)) pure (parseWord64 bitsText)
  let target = if targetText == "score" then UnitIntervalTarget else SignedTarget
      converted = convertLegacyBinary64 target (castWord64ToDouble bits)
  case (profile, converted) of
    ("accepted", Right result) -> do
      expectedJcs <- requiredText "expected_jcs_number" value
      expectedDecimal <- requiredText "expected_expanded_decimal" value
      unless (legacyJcsNumber result == expectedJcs && legacyExpandedDecimal result == expectedDecimal) $
        fail ("legacy number mapping differs for " <> Text.unpack identifier <> ": " <> show result)
    ("rejected", Left _) -> pure ()
    _ -> fail ("legacy number profile result differs for " <> Text.unpack identifier <> ": " <> show converted)

checkPolicyBounds :: IO ()
checkPolicyBounds = do
  half <- parseDecimal "0.5"
  over <- parseDecimal "1.1"
  negative <- parseDecimal "-0.25"
  unless (mkCalibrationPolicy 0 1 half == Left MinimumEventsOutOfRange) $ fail "minimum event lower bound was not enforced"
  unless (mkCalibrationPolicy 100001 1 half == Left MinimumEventsOutOfRange) $ fail "minimum event upper bound was not enforced"
  unless (mkCalibrationPolicy 1 0 half == Left BinCountOutOfRange) $ fail "bin lower bound was not enforced"
  unless (mkCalibrationPolicy 1 1001 half == Left BinCountOutOfRange) $ fail "bin upper bound was not enforced"
  unless (mkCalibrationPolicy 1 1 over == Left MaximumECEOutOfRange) $ fail "ECE upper bound was not enforced"
  unless (mkCalibrationPolicy 1 1 negative == Left MaximumECEOutOfRange) $ fail "ECE lower bound was not enforced"
  unless (convertLegacyBinary64 NonNegativeTarget (-0.25) == Left LegacyFieldRangeFailure) $
    fail "negative nonnegative-target value was accepted"

parseExpectedECE :: Text -> Value -> IO (Maybe Rational)
parseExpectedECE role calculation = case field "ece" calculation >>= field role of
  Nothing -> pure Nothing
  Just value -> do
    numeratorText <- requiredText "numerator" value
    denominatorText <- requiredText "denominator" value
    numerator <- parseInteger numeratorText
    denominator <- parseInteger denominatorText
    if denominator <= 0 then fail "ECE fixture denominator is not positive" else pure (Just (numerator % denominator))

obligationOutcome :: Text -> Value -> IO Text
obligationOutcome obligation expected = case field "obligations" expected of
  Just (Array values) -> case [outcome | value <- Vector.toList values, textField "id" value == Just obligation, Just outcome <- [textField "outcome" value]] of
    [outcome] -> pure outcome
    _ -> fail ("fixture obligation is missing: " <> Text.unpack obligation)
  _ -> fail "fixture obligations are not an array"

parseDecimal :: Text -> IO Decimal
parseDecimal value = case parseCanonicalDecimal value of
  Left () -> fail ("invalid canonical fixture decimal: " <> Text.unpack value)
  Right decimal -> pure decimal

parseInteger :: Text -> IO Integer
parseInteger value = maybe (fail ("invalid fixture integer: " <> Text.unpack value)) pure (readMaybeInteger value)

readMaybeInteger :: Text -> Maybe Integer
readMaybeInteger source = case reads (Text.unpack source) of
  [(value, "")] -> Just value
  _ -> Nothing

intField :: Text -> Value -> IO Int
intField name value = do
  found <- requiredField name value
  case fromJSON found of
    Success integer -> pure integer
    Error _ -> fail ("fixture field is not an integer: " <> Text.unpack name)

requiredField :: Text -> Value -> IO Value
requiredField name value = maybe (fail ("missing fixture field: " <> Text.unpack name)) pure (field name value)

requiredText :: Text -> Value -> IO Text
requiredText name value = do
  found <- requiredField name value
  case found of
    String text -> pure text
    _ -> fail ("fixture field is not text: " <> Text.unpack name)

textField :: Text -> Value -> Maybe Text
textField name value = case field name value of
  Just (String text) -> Just text
  _ -> Nothing

field :: Text -> Value -> Maybe Value
field name (Object fields) = KeyMap.lookup (Key.fromText name) fields
field _ _ = Nothing

parseWord64 :: Text -> Maybe Word64
parseWord64 source = case readHex (Text.unpack source) of
  [(value, "")] -> Just value
  _ -> Nothing
