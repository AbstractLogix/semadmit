{-# LANGUAGE OverloadedStrings #-}

module Core.CLI
  ( runCLI
  )
where

import Core.Evaluator (evaluateRequest)
import Core.Identity (canonicalBytes)
import Core.Pack (PackRegistry)
import Core.Protocol (InputError (..), errorEnvelope, maxRequestBytes)
import Data.Aeson (Value (..))
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString (ByteString)
import Data.ByteString qualified as ByteString
import Data.ByteString.Lazy qualified as LazyByteString
import System.Exit (ExitCode (..))
import System.IO (Handle, hFlush, hPutStrLn, hSetBinaryMode)

inputChunkBytes :: Int
inputChunkBytes = 32 * 1024

data LineBuffer = LineBuffer
  { bufferedBytes :: !Int
  , bufferedChunks :: [ByteString]
  , discardingLine :: !Bool
  }

emptyLine :: LineBuffer
emptyLine = LineBuffer 0 [] False

runCLI :: PackRegistry -> [String] -> Handle -> Handle -> Handle -> IO ExitCode
runCLI registry arguments input output errors = do
  hSetBinaryMode input True
  hSetBinaryMode output True
  case arguments of
    [] -> runSingle registry input output
    ["--jsonl"] -> runJsonl registry input output
    _ -> do
      hPutStrLn errors "usage: semantic-oracle [--jsonl]"
      hFlush errors
      pure (ExitFailure 3)

runSingle :: PackRegistry -> Handle -> Handle -> IO ExitCode
runSingle registry input output = do
  source <- readBounded input 0 []
  case source of
    Left () -> writeLimitError output
    Right bytes -> case singleRequestBytes bytes of
      Left () -> writeLimitError output
      Right request -> do
        result <- evaluateRequest registry request
        (status, _) <- writeResult output result
        pure (exitCode status)

writeLimitError :: Handle -> IO ExitCode
writeLimitError output = do
  (status, _) <- writeResult output limitExceeded
  pure (exitCode status)

readBounded :: Handle -> Int -> [ByteString] -> IO (Either () ByteString)
readBounded input total chunks
  | total > maxRequestBytes + 1 = pure (Left ())
  | otherwise = do
      let remaining = maxRequestBytes + 2 - total
      chunk <- ByteString.hGetSome input (min inputChunkBytes remaining)
      if ByteString.null chunk
        then pure (Right (ByteString.concat (reverse chunks)))
        else
          let nextTotal = total + ByteString.length chunk
           in if nextTotal > maxRequestBytes + 1
                then pure (Left ())
                else readBounded input nextTotal (chunk : chunks)

singleRequestBytes :: ByteString -> Either () ByteString
singleRequestBytes source
  | ByteString.length source <= maxRequestBytes = Right source
  | ByteString.length source == maxRequestBytes + 1
      && ByteString.last source == 10 = Right (ByteString.init source)
  | otherwise = Left ()

runJsonl :: PackRegistry -> Handle -> Handle -> IO ExitCode
runJsonl registry input output = do
  worstStatus <- readLines emptyLine 0
  pure (exitCode worstStatus)
  where
    readLines line worstStatus = do
      chunk <- ByteString.hGetSome input inputChunkBytes
      if ByteString.null chunk
        then
          if discardingLine line || bufferedBytes line > 0
            then do
              (status, _) <- finishLine registry output line
              pure (max worstStatus status)
            else pure worstStatus
        else consumeChunk chunk line worstStatus

    consumeChunk chunk line worstStatus = case ByteString.elemIndex 10 chunk of
      Nothing -> readLines (appendSegment chunk line) worstStatus
      Just newlineOffset -> do
        let segment = ByteString.take newlineOffset chunk
            remaining = ByteString.drop (newlineOffset + 1) chunk
            completedLine = appendSegment segment line
        (status, continue) <- finishLine registry output completedLine
        let nextWorstStatus = max worstStatus status
        if not continue
          then pure nextWorstStatus
          else
            if ByteString.null remaining
              then readLines emptyLine nextWorstStatus
              else consumeChunk remaining emptyLine nextWorstStatus

appendSegment :: ByteString -> LineBuffer -> LineBuffer
appendSegment segment line
  | discardingLine line = line
  | nextBytes > maxRequestBytes = LineBuffer 0 [] True
  | ByteString.null segment = line
  | otherwise = LineBuffer nextBytes (segment : bufferedChunks line) False
  where
    nextBytes = bufferedBytes line + ByteString.length segment

finishLine :: PackRegistry -> Handle -> LineBuffer -> IO (Int, Bool)
finishLine _ output line
  | discardingLine line = writeResult output limitExceeded
finishLine registry output line = do
  let source = ByteString.concat (reverse (bufferedChunks line))
  result <- evaluateRequest registry source
  writeResult output result

writeResult :: Handle -> Value -> IO (Int, Bool)
writeResult output candidate = do
  let (result, status, continue) = classifyResult candidate
  case canonicalBytes result of
    Right bytes -> do
      writeBytes output bytes
      pure (status, continue)
    Left _ -> writeInternalFailure output

writeInternalFailure :: Handle -> IO (Int, Bool)
writeInternalFailure output = case canonicalBytes internalFailure of
  Right bytes -> do
    writeBytes output bytes
    pure (4, False)
  Left _ -> pure (4, False)

writeBytes :: Handle -> LazyByteString.ByteString -> IO ()
writeBytes output bytes = do
  LazyByteString.hPut output bytes
  ByteString.hPut output "\n"
  hFlush output

classifyResult :: Value -> (Value, Int, Bool)
classifyResult (Object fields) = case KeyMap.lookup "kind" fields of
  Just (String "error") -> case KeyMap.lookup "code" fields of
    Just (String "internal.failure") -> internalResult
    Just (String _) -> (Object fields, 3, True)
    _ -> internalResult
  Just (String "decision") -> case KeyMap.lookup "payload" fields of
    Just (Object payload) -> case KeyMap.lookup "state" payload of
      Just (String "admissible") -> (Object fields, 0, True)
      Just (String "inadmissible") -> (Object fields, 1, True)
      Just (String "indeterminate") -> (Object fields, 2, True)
      _ -> internalResult
    _ -> internalResult
  _ -> internalResult
classifyResult _ = internalResult

internalResult :: (Value, Int, Bool)
internalResult = (internalFailure, 4, False)

internalFailure :: Value
internalFailure = errorEnvelope (InputError "internal.failure" "")

limitExceeded :: Value
limitExceeded = errorEnvelope (InputError "limit.exceeded" "")

exitCode :: Int -> ExitCode
exitCode 0 = ExitSuccess
exitCode status = ExitFailure status
