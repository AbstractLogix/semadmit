module Main (main, runApplication) where

import Core.CLI (runCLI)
import Core.Pack (mkPackRegistry)
import Pack.Isoprax.PoolPredictions (isopraxPack)
import System.Environment (getArgs)
import System.Exit (ExitCode, exitWith)
import System.IO (Handle, stderr, stdin, stdout)

main :: IO ()
main = do
  arguments <- getArgs
  runApplication arguments stdin stdout stderr >>= exitWith

runApplication :: [String] -> Handle -> Handle -> Handle -> IO ExitCode
runApplication arguments input output errors = do
  registry <- case mkPackRegistry [isopraxPack] of
    Left problem -> fail ("first-party pack registry is invalid: " <> show problem)
    Right value -> pure value
  runCLI registry arguments input output errors
