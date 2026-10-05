{-# LANGUAGE OverloadedStrings #-}

module Core.Protocol
  ( CommonRequest (..)
  , InputError (..)
  , parseJsonBytes
  , errorEnvelope
  , protocolVersion
  , maxRequestBytes
  , maxEvidenceItems
  , validateCommon
  ) where

import Core.Pack (OperationDescriptor, Pack (..), PackDescriptor (..), PackRegistry, lookupOperation, lookupPack)
import Core.Version (protocolVersion)
import Data.Aeson (Value (..), eitherDecodeStrict', object, (.=))
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString (ByteString)
import Data.ByteString qualified as ByteString
import Data.List (sortOn)
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Text.Encoding qualified as TextEncoding
import Data.Vector qualified as Vector
import Data.Word (Word8)
import Numeric (readHex)

maxRequestBytes, maxContainerDepth, maxEvidenceItems :: Int
maxRequestBytes = 10 * 1024 * 1024
maxContainerDepth = 64
maxEvidenceItems = 256

data InputError = InputError
  { inputErrorCode :: Text
  , inputErrorPointer :: Text
  }
  deriving (Eq, Read, Show)

errorEnvelope :: InputError -> Value
errorEnvelope (InputError code pointer) =
  object ["kind" .= ("error" :: Text), "code" .= code, "pointer" .= pointer]

data CommonRequest = CommonRequest
  { commonPack :: Pack
  , commonOperation :: Text
  , commonOperationDescriptor :: OperationDescriptor
  , commonPolicyDigest :: Text
  , commonPolicy :: Value
  , commonSubjects :: Value
  , commonEvidence :: [Value]
  }

parseJsonBytes :: ByteString -> Either InputError Value
parseJsonBytes source
  | ByteString.length source > maxRequestBytes = problem "limit.exceeded" ""
  | otherwise = case TextEncoding.decodeUtf8' source of
      Left _ -> problem "input.invalid_utf8" ""
      Right decoded
        | Text.isPrefixOf "\xfeff" decoded -> problem "input.invalid_json" ""
        | otherwise -> do
            (value, next) <- parseValue source "" 0 0
            if skipWhitespace source next == ByteString.length source
              then Right value
              else problem "input.invalid_json" ""

parseValue :: ByteString -> Text -> Int -> Int -> Either InputError (Value, Int)
parseValue source pointer depth offset =
  let start = skipWhitespace source offset
   in if start >= ByteString.length source
        then problem "input.invalid_json" ""
        else case byteAt source start of
          0x7b ->
            if depth >= maxContainerDepth
              then problem "limit.exceeded" pointer
              else parseObject source pointer (depth + 1) (start + 1)
          0x5b ->
            if depth >= maxContainerDepth
              then problem "limit.exceeded" pointer
              else parseArray source pointer (depth + 1) (start + 1)
          0x22 -> do
            (value, next) <- parseString source start
            pure (String value, next)
          0x74 -> parseLiteral source start "true" (Bool True)
          0x66 -> parseLiteral source start "false" (Bool False)
          0x6e -> parseLiteral source start "null" Null
          byte | byte == 0x2d || isDigit byte -> parseNumber source pointer start
          _ -> problem "input.invalid_json" ""

parseObject :: ByteString -> Text -> Int -> Int -> Either InputError (Value, Int)
parseObject source pointer childDepth offset =
  let first = skipWhitespace source offset
   in if first < ByteString.length source && byteAt source first == 0x7d
        then Right (Object KeyMap.empty, first + 1)
        else go KeyMap.empty first
  where
    go fields current
      | current >= ByteString.length source = problem "input.invalid_json" ""
      | byteAt source current /= 0x22 = problem "input.invalid_json" ""
      | otherwise = do
          (name, afterName) <- parseString source current
          let memberPointer = pointer <> "/" <> escapePointer name
              key = Key.fromText name
          if KeyMap.member key fields
            then problem "input.duplicate_key" memberPointer
            else pure ()
          let afterColon = skipWhitespace source afterName
          if afterColon >= ByteString.length source || byteAt source afterColon /= 0x3a
            then problem "input.invalid_json" ""
            else pure ()
          (member, afterMember) <- parseValue source memberPointer childDepth (afterColon + 1)
          let updated = KeyMap.insert key member fields
              next = skipWhitespace source afterMember
          if next >= ByteString.length source
            then problem "input.invalid_json" ""
            else case byteAt source next of
              0x7d -> Right (Object updated, next + 1)
              0x2c -> go updated (skipWhitespace source (next + 1))
              _ -> problem "input.invalid_json" ""

parseArray :: ByteString -> Text -> Int -> Int -> Either InputError (Value, Int)
parseArray source pointer childDepth offset =
  let first = skipWhitespace source offset
   in if first < ByteString.length source && byteAt source first == 0x5d
        then Right (Array Vector.empty, first + 1)
        else go [] 0 first
  where
    go reversed index current
      | current >= ByteString.length source = problem "input.invalid_json" ""
      | pointer == "/evidence" && index >= maxEvidenceItems =
          problem "limit.exceeded" (pointer <> "/" <> Text.pack (show index))
      | otherwise = do
          (member, afterMember) <- parseValue source (pointer <> "/" <> Text.pack (show index)) childDepth current
          let next = skipWhitespace source afterMember
          if next >= ByteString.length source
            then problem "input.invalid_json" ""
            else case byteAt source next of
              0x5d -> Right (Array (Vector.fromList (reverse (member : reversed))), next + 1)
              0x2c -> go (member : reversed) (index + 1) (skipWhitespace source (next + 1))
              _ -> problem "input.invalid_json" ""

parseString :: ByteString -> Int -> Either InputError (Text, Int)
parseString source offset
  | offset >= ByteString.length source || byteAt source offset /= 0x22 =
      problem "input.invalid_json" ""
  | otherwise = scan (offset + 1)
  where
    scan current
      | current >= ByteString.length source = problem "input.invalid_json" ""
      | otherwise = case byteAt source current of
          0x22 -> decodeToken (current + 1)
          0x5c -> scanEscape (current + 1)
          byte | byte < 0x20 -> problem "input.invalid_json" ""
          _ -> scan (current + 1)

    scanEscape escapeOffset
      | escapeOffset >= ByteString.length source = problem "input.invalid_json" ""
      | otherwise = case byteAt source escapeOffset of
          0x22 -> scan (escapeOffset + 1)
          0x5c -> scan (escapeOffset + 1)
          0x2f -> scan (escapeOffset + 1)
          0x62 -> scan (escapeOffset + 1)
          0x66 -> scan (escapeOffset + 1)
          0x6e -> scan (escapeOffset + 1)
          0x72 -> scan (escapeOffset + 1)
          0x74 -> scan (escapeOffset + 1)
          0x75 -> scanUnicode (escapeOffset + 1)
          _ -> problem "input.invalid_json" ""

    scanUnicode digitsOffset = case hexQuad source digitsOffset of
      Nothing -> problem "input.invalid_json" ""
      Just (codepoint, afterDigits)
        | codepoint >= 0xdc00 && codepoint <= 0xdfff -> problem "input.invalid_unicode" ""
        | codepoint >= 0xd800 && codepoint <= 0xdbff ->
            if afterDigits + 2 > ByteString.length source
              || byteAt source afterDigits /= 0x5c
              || byteAt source (afterDigits + 1) /= 0x75
              then problem "input.invalid_unicode" ""
              else case hexQuad source (afterDigits + 2) of
                Nothing -> problem "input.invalid_json" ""
                Just (low, afterLow)
                  | low >= 0xdc00 && low <= 0xdfff -> scan afterLow
                  | otherwise -> problem "input.invalid_unicode" ""
        | otherwise -> scan afterDigits

    decodeToken end =
      let token = ByteString.take (end - offset) (ByteString.drop offset source)
       in case eitherDecodeStrict' token of
            Left _ -> problem "input.invalid_json" ""
            Right value -> Right (value, end)

parseNumber :: ByteString -> Text -> Int -> Either InputError (Value, Int)
parseNumber source pointer offset =
  let end = scanNumber source offset
      token = ByteString.take (end - offset) (ByteString.drop offset source)
      text = TextEncoding.decodeUtf8 token
   in if not (validJsonNumber token) || not (validNumberBoundary source end)
        then problem "input.invalid_json" ""
        else
          if Text.any (`elem` (".eE" :: String)) text || text == "-0" || not (safeInteger text)
            then problem "input.number_profile" pointer
            else Right (Number (read (Text.unpack text)), end)

parseLiteral :: ByteString -> Int -> ByteString -> Value -> Either InputError (Value, Int)
parseLiteral source offset literal value
  | literal `ByteString.isPrefixOf` ByteString.drop offset source = Right (value, offset + ByteString.length literal)
  | otherwise = problem "input.invalid_json" ""

validateCommon :: PackRegistry -> Value -> Either InputError CommonRequest
validateCommon registry value = case value of
  Object fields -> do
    rejectUnknownFields fields
    protocol <- textField fields "protocol"
    if protocol /= protocolVersion
      then problem "protocol.unsupported_version" "/protocol"
      else pure ()
    identifier <- textField fields "pack"
    pack <- case lookupPack identifier registry of
      Nothing -> problem "protocol.unsupported_pack" "/pack"
      Just registered -> Right registered
    operation <- textField fields "operation"
    let descriptor = packDescriptor pack
    if protocol `notElem` packProtocolVersions descriptor
      then problem "protocol.unsupported_version" "/protocol"
      else pure ()
    operationDescriptor <- case lookupOperation operation pack of
      Nothing -> problem "protocol.unsupported_operation" "/operation"
      Just selected -> Right selected
    policyDigest <- textField fields "policy_digest"
    if validDigest policyDigest
      then pure ()
      else problem "input.invalid_value" "/policy_digest"
    policy <- objectField fields "policy"
    subjects <- objectField fields "subjects"
    evidence <- arrayField fields "evidence"
    if length evidence > maxEvidenceItems
      then problem "limit.exceeded" ("/evidence/" <> Text.pack (show maxEvidenceItems))
      else pure ()
    pure
      CommonRequest
        { commonPack = pack
        , commonOperation = operation
        , commonOperationDescriptor = operationDescriptor
        , commonPolicyDigest = policyDigest
        , commonPolicy = Object policy
        , commonSubjects = Object subjects
        , commonEvidence = evidence
        }
  _ -> problem "input.invalid_type" ""

rejectUnknownFields :: KeyMap.KeyMap Value -> Either InputError ()
rejectUnknownFields fields = case sortOn Text.unpack extras of
  [] -> Right ()
  field : _ -> problem "input.unknown_field" ("/" <> escapePointer field)
  where
    known = ["protocol", "pack", "operation", "policy_digest", "policy", "subjects", "evidence"]
    extras = filter (`notElem` known) (map Key.toText (KeyMap.keys fields))

textField :: KeyMap.KeyMap Value -> Text -> Either InputError Text
textField fields name = case KeyMap.lookup (Key.fromText name) fields of
  Nothing -> problem "input.missing_field" ("/" <> name)
  Just (String value) -> Right value
  Just _ -> problem "input.invalid_type" ("/" <> name)

objectField :: KeyMap.KeyMap Value -> Text -> Either InputError (KeyMap.KeyMap Value)
objectField fields name = case KeyMap.lookup (Key.fromText name) fields of
  Nothing -> problem "input.missing_field" ("/" <> name)
  Just (Object value) -> Right value
  Just _ -> problem "input.invalid_type" ("/" <> name)

arrayField :: KeyMap.KeyMap Value -> Text -> Either InputError [Value]
arrayField fields name = case KeyMap.lookup (Key.fromText name) fields of
  Nothing -> problem "input.missing_field" ("/" <> name)
  Just (Array values) -> Right (Vector.toList values)
  Just _ -> problem "input.invalid_type" ("/" <> name)

validDigest :: Text -> Bool
validDigest digest = case Text.stripPrefix "sha256:" digest of
  Just hex -> Text.length hex == 64 && Text.all validHex hex
  Nothing -> False

validHex :: Char -> Bool
validHex character = (character >= '0' && character <= '9') || (character >= 'a' && character <= 'f')

escapePointer :: Text -> Text
escapePointer = Text.replace "/" "~1" . Text.replace "~" "~0"

skipWhitespace :: ByteString -> Int -> Int
skipWhitespace source = go
  where
    go index
      | index < ByteString.length source && byteAt source index `elem` [0x20, 0x09, 0x0a, 0x0d] = go (index + 1)
      | otherwise = index

scanNumber :: ByteString -> Int -> Int
scanNumber source = go
  where
    go index
      | index < ByteString.length source && isNumberByte (byteAt source index) = go (index + 1)
      | otherwise = index

isNumberByte :: Word8 -> Bool
isNumberByte byte = isDigit byte || byte `elem` [0x2d, 0x2b, 0x2e, 0x65, 0x45]

isDigit :: Word8 -> Bool
isDigit byte = byte >= 0x30 && byte <= 0x39

validJsonNumber :: ByteString -> Bool
validJsonNumber token = validInteger && validFraction && validExponent && exponentEnd == size
  where
    size = ByteString.length token
    start = if size > 0 && byteAt token 0 == 0x2d then 1 else 0
    (integerEnd, validInteger) = parseInteger start
    (fractionEnd, validFraction) = parseFraction integerEnd
    (exponentEnd, validExponent) = parseExponent fractionEnd
    parseInteger index
      | index >= size = (index, False)
      | byteAt token index == 0x30 =
          let next = index + 1
           in (next, next >= size || not (isDigit (byteAt token next)))
      | byteAt token index >= 0x31 && byteAt token index <= 0x39 =
          (consumeDigits (index + 1), True)
      | otherwise = (index, False)
    parseFraction index
      | index < size && byteAt token index == 0x2e =
          let first = index + 1
              next = consumeDigits first
           in (next, next > first)
      | otherwise = (index, True)
    parseExponent index
      | index < size && byteAt token index `elem` [0x65, 0x45] =
          let afterE = index + 1
              first = if afterE < size && byteAt token afterE `elem` [0x2b, 0x2d] then afterE + 1 else afterE
              next = consumeDigits first
           in (next, next > first)
      | otherwise = (index, True)
    consumeDigits index
      | index < size && isDigit (byteAt token index) = consumeDigits (index + 1)
      | otherwise = index

safeInteger :: Text -> Bool
safeInteger value =
  let digits = Text.unpack (Text.dropWhile (== '-') value)
   in length digits < 16 || (length digits == 16 && digits <= "9007199254740991")

validNumberBoundary :: ByteString -> Int -> Bool
validNumberBoundary source offset =
  offset >= ByteString.length source
    || byteAt source offset `elem` [0x20, 0x09, 0x0a, 0x0d, 0x2c, 0x5d, 0x7d]

hexQuad :: ByteString -> Int -> Maybe (Int, Int)
hexQuad source offset
  | offset + 4 > ByteString.length source = Nothing
  | otherwise = do
      let digits = ByteString.take 4 (ByteString.drop offset source)
      value <- case readHex (map (toEnum . fromIntegral) (ByteString.unpack digits)) of
        [(number, "")] -> Just number
        _ -> Nothing
      pure (value, offset + 4)

byteAt :: ByteString -> Int -> Word8
byteAt = ByteString.index

problem :: Text -> Text -> Either InputError value
problem code pointer = Left (InputError code pointer)
