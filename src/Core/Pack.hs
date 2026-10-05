{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE ExistentialQuantification #-}

module Core.Pack
  ( Pack (..)
  , PackDescriptor (..)
  , OperationDescriptor (..)
  , PackBehavior (..)
  , NormalizedPackRequest (..)
  , PackInputError (..)
  , PackResult (..)
  , PackRegistry
  , PackRegistryError (..)
  , packIdentityFor
  , lookupOperation
  , lookupPack
  , mkPackRegistry
  , validPackId
  ) where

import Core.Version (protocolVersion)
import Core.Decision
  ( ComponentDeclaration (..)
  , ComponentPayload
  , Diagnostic
  , EvidenceDeclaration (..)
  , Outcome
  , SubjectDeclaration (..)
  )
import Core.Identity (PackIdentity)
import Core.Identity.Internal (newPackIdentity)
import Data.Aeson (Value)
import Data.List (nub)
import Data.Map.Strict (Map)
import Data.Map.Strict qualified as Map
import Data.Set qualified as Set
import Data.Text (Text)
import Data.Text qualified as Text

data PackDescriptor = PackDescriptor
  { packId :: Text
  , packProtocolVersions :: [Text]
  , packOperations :: Map Text OperationDescriptor
  }
  deriving (Eq, Show)

data OperationDescriptor = OperationDescriptor
  { operationArtifactDeclarations :: [(Text, Text)]
  , operationSubjectDeclarations :: [SubjectDeclaration]
  , operationComponentDeclarations :: [ComponentDeclaration]
  , operationEvidenceDeclaration :: Maybe EvidenceDeclaration
  , operationObligations :: [Text]
  , operationAllowedOutcomes :: [Outcome]
  , operationDiagnosticPointers :: Map Text [Text]
  }
  deriving (Eq, Show)

-- | Trusted, statically linked Haskell pack behavior. Validation receives the
-- source projections and must return their normalized JSON form. Core sorts
-- normalized evidence before the behavior decodes it into the pack's typed
-- input. That same typed input is passed to the evaluator.
data Pack = Pack
  { packDescriptor :: PackDescriptor
  , packBehavior :: PackBehavior
  }

data NormalizedPackRequest = NormalizedPackRequest
  { normalizedPolicy :: Value
  , normalizedSubjects :: Value
  , normalizedEvidence :: [Value]
  -- Optional pack-specific projection used only for subject artifact bindings.
  -- The common request digest and decoder always use normalizedSubjects.
  , normalizedSubjectIdentityProjection :: Maybe Value
  }
  deriving (Eq, Show)

data PackInputError = PackInputError
  { packInputErrorCode :: Text
  , packInputErrorPointer :: Text
  }
  deriving (Eq, Show)

data PackResult = PackResult
  { packResultComponents :: [ComponentPayload]
  , packResultObligations :: [(Text, Outcome)]
  , packResultDiagnostics :: [Diagnostic]
  }
  deriving (Eq, Show)

-- | Pack behavior is validation, decoding from Core's immutable normalized
-- snapshot, then evaluation over the pack-specific typed input. A decode
-- failure is a pack defect and must be reported as internal.failure by Core.
data PackBehavior = forall input. PackBehavior
  (Text -> Value -> Value -> [Value] -> Either PackInputError NormalizedPackRequest)
  (NormalizedPackRequest -> Either () input)
  (Text -> PackIdentity -> input -> PackResult)

newtype PackRegistry = PackRegistry (Map Text Pack)

data PackRegistryError
  = InvalidPackDescriptor Text
  | DuplicatePackId Text
  deriving (Eq, Show)

mkPackRegistry :: [Pack] -> Either PackRegistryError PackRegistry
mkPackRegistry = fmap PackRegistry . foldl insert (Right Map.empty)
  where
    insert result pack = do
      packs <- result
      let descriptor = packDescriptor pack
          identifier = packId descriptor
      if not (validDescriptor descriptor)
        then Left (InvalidPackDescriptor identifier)
        else
          if Map.member identifier packs
            then Left (DuplicatePackId identifier)
            else Right (Map.insert identifier pack packs)

lookupPack :: Text -> PackRegistry -> Maybe Pack
lookupPack identifier (PackRegistry packs) = Map.lookup identifier packs

-- | Resolve the selected operation's declared artifact identities from a
-- registered pack descriptor. The returned service also permits Core's
-- common request identity pair.
packIdentityFor :: Text -> Text -> PackRegistry -> Maybe PackIdentity
packIdentityFor identifier operation (PackRegistry packs) = do
  pack <- Map.lookup identifier packs
  descriptor <- lookupOperation operation pack
  pure (newPackIdentity (operationArtifactDeclarations descriptor))

lookupOperation :: Text -> Pack -> Maybe OperationDescriptor
lookupOperation operation pack = Map.lookup operation (packOperations (packDescriptor pack))

validPackId :: Text -> Bool
validPackId identifier = case Text.splitOn "/" identifier of
  [namespace, version] -> validNamespace namespace && validVersion version
  _ -> False

validDescriptor :: PackDescriptor -> Bool
validDescriptor descriptor =
  validPackId (packId descriptor)
    && not (null versions)
    && all (== protocolVersion) versions
    && unique versions
    && not (Map.null operations)
    && all (not . Text.null) (Map.keys operations)
    && all validOperation (Map.elems operations)
  where
    versions = packProtocolVersions descriptor
    operations = packOperations descriptor

    validOperation operation =
      validArtifactDeclarations (operationArtifactDeclarations operation)
        && exactlyOnePolicyArtifact (operationArtifactDeclarations operation)
        && validSubjects operation
        && validComponents operation
        && validEvidence operation
        && validObligations operation
        && validOutcomes operation
        && validDiagnosticDeclarations (operationDiagnosticPointers operation)

    validArtifactDeclarations artifacts = unique artifacts && all validArtifact artifacts

    validArtifact (kind, schema) =
      not (Text.null kind)
        && (packId descriptor <> "/") `Text.isPrefixOf` schema
        && Text.length schema > Text.length (packId descriptor) + 1

    exactlyOnePolicyArtifact artifacts = length (filter ((== "policy") . fst) artifacts) == 1

    validSubjects operation =
      not (null subjects)
        && all validSubject subjects
        && unique (map subjectDeclarationRole subjects)
      where
        subjects = operationSubjectDeclarations operation
        artifacts = Set.fromList (operationArtifactDeclarations operation)
        validSubject subject =
          not (Text.null (subjectDeclarationRole subject))
            && (subjectDeclarationKind subject, subjectDeclarationSchema subject) `Set.member` artifacts

    validComponents operation =
      all validComponent components
        && unique (map componentKey components)
      where
        subjects = Set.fromList (map subjectDeclarationRole (operationSubjectDeclarations operation))
        components = operationComponentDeclarations operation
        componentKey component = (declaredSubjectRole component, declaredComponentName component)
        artifacts = Set.fromList (operationArtifactDeclarations operation)
        validComponent component =
          Set.member (declaredSubjectRole component) subjects
            && not (Text.null (declaredComponentName component))
            && (declaredComponentKind component, declaredComponentSchema component) `Set.member` artifacts
            && minimumComponents component >= 0
            && maximumComponents component >= minimumComponents component

    validEvidence operation = case operationEvidenceDeclaration operation of
      Nothing -> True
      Just evidence -> (evidenceDeclarationKind evidence, evidenceDeclarationSchema evidence) `Set.member` artifacts
      where
        artifacts = Set.fromList (operationArtifactDeclarations operation)

    validObligations operation =
      not (null obligations) && all (not . Text.null) obligations && unique obligations
      where
        obligations = operationObligations operation

    validOutcomes operation =
      not (null outcomes) && unique outcomes
      where
        outcomes = operationAllowedOutcomes operation

    validDiagnosticDeclarations declarations = all validDiagnostic (Map.toList declarations)
      where
        validDiagnostic (code, pointers) =
          not (Text.null code)
            && not (null pointers)
            && unique pointers
            && all validPointer pointers

    validPointer pointer =
      Text.null pointer
        || (Text.isPrefixOf "/" pointer
              && validPointerEscapes (Text.unpack pointer)
              && all validTemplateSegment (Text.splitOn "/" pointer))

    validTemplateSegment segment
      | not (Text.any (\character -> character == '{' || character == '}') segment) = True
      | otherwise = segment `elem` ["{left,right}", "{role}", "{field}", "{canonical-index}"]

    validPointerEscapes [] = True
    validPointerEscapes ('~' : '0' : rest) = validPointerEscapes rest
    validPointerEscapes ('~' : '1' : rest) = validPointerEscapes rest
    validPointerEscapes ('~' : _) = False
    validPointerEscapes (_ : rest) = validPointerEscapes rest

validNamespace :: Text -> Bool
validNamespace namespace = case Text.uncons namespace of
  Nothing -> False
  Just (first, rest) ->
    Text.length namespace <= 63
      && asciiLower first
      && Text.all validNamespaceTail rest

validNamespaceTail :: Char -> Bool
validNamespaceTail character = asciiLower character || asciiDigit character || character == '-'

validVersion :: Text -> Bool
validVersion version = case Text.splitOn "." version of
  [major, minor] -> canonicalNatural major && canonicalNatural minor
  _ -> False

canonicalNatural :: Text -> Bool
canonicalNatural "0" = True
canonicalNatural digits = case Text.uncons digits of
  Just (first, rest) -> first >= '1' && first <= '9' && Text.all asciiDigit rest
  Nothing -> False

asciiLower :: Char -> Bool
asciiLower character = character >= 'a' && character <= 'z'

asciiDigit :: Char -> Bool
asciiDigit character = character >= '0' && character <= '9'

unique :: Eq item => [item] -> Bool
unique items = length items == length (nub items)
