{-# LANGUAGE OverloadedStrings #-}

module Core.Identity.Internal
  ( PackIdentity (..)
  , newPackIdentity
  ) where

import Data.Set qualified as Set
import Data.Text (Text)

newtype PackIdentity = PackIdentity (Set.Set (Text, Text))
  deriving (Eq, Show)

newPackIdentity :: [(Text, Text)] -> PackIdentity
newPackIdentity declared =
  PackIdentity (Set.insert requestIdentity (Set.fromList declared))
  where
    requestIdentity = ("request", "semantic-oracle/0.1/request")
