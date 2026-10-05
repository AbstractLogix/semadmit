{-# LANGUAGE OverloadedStrings #-}

module Core.Identity
  ( IdentityError (..)
  , PackIdentity
  , canonicalBytes
  , artifactDigest
  , decisionDigest
  ) where

import Crypto.Hash.SHA256 qualified as SHA256
import Core.Identity.Internal (PackIdentity (..))
import Data.Aeson (Value (..), object, (.=))
import Data.Aeson.Key (toText)
import Data.Aeson.KeyMap qualified as KeyMap
import Data.Aeson.RFC8785 (encodeCanonical)
import Data.ByteString qualified as BS
import Data.ByteString.Lazy qualified as LBS
import Data.Char (ord)
import Data.Int (Int64)
import Data.Scientific (toBoundedInteger)
import Data.Set qualified as Set
import Data.Text (Text)
import Data.Text qualified as Text
import Data.Vector qualified as Vector
import Data.Word (Word8)
import Numeric (showHex)

data IdentityError
  = InvalidUnicode
  | InvalidNumber
  | TooDeep
  | UndeclaredArtifact Text Text
  deriving (Eq, Show)

safeInteger :: Int64
safeInteger = 9007199254740991

validText :: Text -> Bool
validText = Text.all (\char -> let codepoint = ord char in codepoint < 0xD800 || codepoint > 0xDFFF)

validate :: Int -> Value -> Either IdentityError ()
validate depth value = case value of
  Null -> Right ()
  Bool _ -> Right ()
  String text -> if validText text then Right () else Left InvalidUnicode
  Number number -> case toBoundedInteger number :: Maybe Int64 of
    Just integer | integer >= negate safeInteger && integer <= safeInteger -> Right ()
    _ -> Left InvalidNumber
  Array values
    | depth >= 64 -> Left TooDeep
    | otherwise -> mapM_ (validate (depth + 1)) (Vector.toList values)
  Object fields
    | depth >= 64 -> Left TooDeep
    | otherwise -> mapM_ validateField (KeyMap.toList fields)
    where
      validateField (key, member)
        | not (validText (toText key)) = Left InvalidUnicode
        | otherwise = validate (depth + 1) member

canonicalBytes :: Value -> Either IdentityError LBS.ByteString
canonicalBytes value = do
  validate 0 value
  pure (encodeCanonical value)

hexByte :: Word8 -> String
hexByte byte = case showHex byte "" of
  [digit] -> ['0', digit]
  digits -> digits

digest :: LBS.ByteString -> Text
digest bytes = "sha256:" <> Text.pack (concatMap hexByte (BS.unpack (SHA256.hash (LBS.toStrict bytes))))

artifactDigest :: PackIdentity -> Text -> Text -> Value -> Either IdentityError Text
artifactDigest (PackIdentity declared) kind schema payload
  | Set.member (kind, schema) declared =
      digest <$> canonicalBytes (object ["kind" .= kind, "schema" .= schema, "payload" .= payload])
  | otherwise = Left (UndeclaredArtifact kind schema)

decisionDigest :: Value -> Either IdentityError Text
decisionDigest payload = digest <$> canonicalBytes payload
