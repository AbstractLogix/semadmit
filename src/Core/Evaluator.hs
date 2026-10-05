{-# LANGUAGE OverloadedStrings #-}

module Core.Evaluator
  ( evaluateRequest
  ) where

import Control.Exception qualified as Exception
import Core.Decision
  ( DecisionContext (..)
  , EvidenceArtifact (..)
  , EvidenceDeclaration (..)
  , SubjectArtifact (..)
  , SubjectDeclaration (..)
  , buildBindings
  , buildDecision
  )
import Core.Identity (PackIdentity, artifactDigest, canonicalBytes)
import Core.Pack
  ( NormalizedPackRequest (..)
  , OperationDescriptor (..)
  , PackBehavior (..)
  , Pack (..)
  , PackInputError (..)
  , PackDescriptor (..)
  , PackRegistry
  , PackResult (..)
  , packIdentityFor
  )
import Core.Protocol
  ( CommonRequest (..)
  , InputError (..)
  , errorEnvelope
  , maxEvidenceItems
  , maxRequestBytes
  , parseJsonBytes
  , protocolVersion
  , validateCommon
  )
import Data.Aeson (Value (..), object, (.=))
import Data.Aeson.Key qualified as Key
import Data.Aeson.KeyMap qualified as KeyMap
import Data.ByteString (ByteString)
import Data.ByteString.Lazy qualified as LazyByteString
import Data.List (sortOn)
import Data.Set qualified as Set
import Data.Text (Text)
import Data.Text qualified as Text

-- | Parse, validate, and evaluate one request from its original bytes. Pack failures and
-- invalid pack outputs share the single public internal.failure envelope.
evaluateRequest :: PackRegistry -> ByteString -> IO Value
evaluateRequest registry source = do
  outcome <- trySynchronous $ do
    result <- Exception.evaluate (evaluateRequestPure registry source)
    case canonicalBytes result of
      Left _ -> pure internalFailure
      Right bytes -> do
        _ <- Exception.evaluate (LazyByteString.length bytes)
        pure result
  pure (either (const internalFailure) id outcome)

evaluateRequestPure :: PackRegistry -> ByteString -> Value
evaluateRequestPure registry source = case parseJsonBytes source of
  Left problem -> errorEnvelope problem
  Right request -> case validateCommon registry request of
    Left problem -> errorEnvelope problem
    Right common -> evaluateCommon registry common

evaluateCommon :: PackRegistry -> CommonRequest -> Value
evaluateCommon registry common = case packBehavior selected of
  PackBehavior validate decode evaluateTyped -> case
      validate operation (commonPolicy common) (commonSubjects common) (commonEvidence common)
    of
      Left problem
        | validPackInputError problem -> errorEnvelope (InputError (packInputErrorCode problem) (packInputErrorPointer problem))
        | otherwise -> internalFailure
      Right normalized
        | not (validNormalized normalized) -> internalFailure
        | otherwise -> evaluateNormalized registry common normalized decode evaluateTyped
  where
    selected = commonPack common
    operation = commonOperation common

evaluateNormalized
  :: PackRegistry
  -> CommonRequest
  -> NormalizedPackRequest
  -> (NormalizedPackRequest -> Either () input)
  -> (Text -> PackIdentity -> input -> PackResult)
  -> Value
evaluateNormalized registry common normalized decode evaluateTyped = case
    (policySchema descriptor, packIdentityFor identifier operation registry)
  of
    (Just schema, Just identities) -> case artifactDigest identities "policy" schema policy of
      Left _ -> internalFailure
      Right actualPolicyDigest
        | actualPolicyDigest /= commonPolicyDigest common ->
            errorEnvelope (InputError "identity.digest_mismatch" "/policy_digest")
        | otherwise -> buildDecisionResult identities actualPolicyDigest
    _ -> internalFailure
  where
    selected = commonPack common
    descriptor = commonOperationDescriptor common
    identifier = packId (packDescriptor selected)
    operation = commonOperation common
    policy = normalizedPolicy normalized
    subjects = normalizedSubjects normalized
    subjectIdentityProjection = maybe subjects id (normalizedSubjectIdentityProjection normalized)
    evidence = sortOn evidenceId (normalizedEvidence normalized)
    orderedRequest = normalized {normalizedEvidence = evidence}

    buildDecisionResult identities actualPolicyDigest =
      let requestPayload =
            object
              [ "protocol" .= protocolVersion
              , "pack" .= identifier
              , "operation" .= operation
              , "policy_digest" .= actualPolicyDigest
              , "policy" .= policy
              , "subjects" .= subjects
              , "evidence" .= evidence
              ]
       in case artifactDigest identities "request" "semantic-oracle/0.1/request" requestPayload of
            Left _ -> internalFailure
            Right requestDigest -> buildResult identities actualPolicyDigest requestDigest

    buildResult identities actualPolicyDigest requestDigest = case decode orderedRequest of
      Left _ -> internalFailure
      Right input ->
        case (subjectArtifacts descriptor subjectIdentityProjection, evidenceArtifacts (operationEvidenceDeclaration descriptor) evidence) of
          (Right subjectsForBindings, Right evidenceForBindings) ->
            let PackResult components outcomes diagnostics = evaluateTyped operation identities input
             in case buildBindings
                  identities
                  (operationSubjectDeclarations descriptor)
                  subjectsForBindings
                  (operationComponentDeclarations descriptor)
                  components
                  (operationEvidenceDeclaration descriptor)
                  evidenceForBindings of
                  Left _ -> internalFailure
                  Right bindings ->
                    case buildDecision
                      (DecisionContext protocolVersion identifier operation requestDigest actualPolicyDigest)
                      (operationObligations descriptor)
                      (operationAllowedOutcomes descriptor)
                      outcomes
                      (operationDiagnosticPointers descriptor)
                      diagnostics
                      bindings of
                      Left _ -> internalFailure
                      Right result -> result
          _ -> internalFailure

policySchema :: OperationDescriptor -> Maybe Text
policySchema descriptor = case filter ((== "policy") . fst) (operationArtifactDeclarations descriptor) of
  [("policy", schema)] -> Just schema
  _ -> Nothing

subjectArtifacts :: OperationDescriptor -> Value -> Either () [SubjectArtifact]
subjectArtifacts descriptor (Object fields)
  | actualRoles /= declaredRoles = Left ()
  | otherwise = traverse makeArtifact (operationSubjectDeclarations descriptor)
  where
    actualRoles = Set.fromList (map (Key.toText . fst) (KeyMap.toList fields))
    declaredRoles = Set.fromList (map subjectDeclarationRole (operationSubjectDeclarations descriptor))
    makeArtifact declaration = case KeyMap.lookup (Key.fromText (subjectDeclarationRole declaration)) fields of
      Nothing -> Left ()
      Just value ->
        Right
          SubjectArtifact
            { subjectArtifactRole = subjectDeclarationRole declaration
            , subjectArtifactKind = subjectDeclarationKind declaration
            , subjectArtifactSchema = subjectDeclarationSchema declaration
            , subjectArtifactValue = value
            }
subjectArtifacts _ _ = Left ()

evidenceArtifacts :: Maybe EvidenceDeclaration -> [Value] -> Either () [EvidenceArtifact]
evidenceArtifacts Nothing [] = Right []
evidenceArtifacts Nothing _ = Left ()
evidenceArtifacts (Just declaration) values = traverse makeArtifact values
  where
    makeArtifact value = case value of
      Object fields -> case KeyMap.lookup "id" fields of
        Just (String identifier) ->
          Right
            EvidenceArtifact
              { evidenceArtifactId = identifier
              , evidenceArtifactKind = evidenceDeclarationKind declaration
              , evidenceArtifactSchema = evidenceDeclarationSchema declaration
              , evidenceArtifactValue = value
              }
        _ -> Left ()
      _ -> Left ()

validNormalized :: NormalizedPackRequest -> Bool
validNormalized normalized = validRequestSnapshot && validSubjectProjection
  where
    evidence = normalizedEvidence normalized
    validRequestSnapshot = case (normalizedPolicy normalized, normalizedSubjects normalized) of
      (Object _, Object _) ->
        case (traverse evidenceId evidence, canonicalBytes normalizedPayload) of
          (Just identifiers, Right bytes) ->
            length evidence <= maxEvidenceItems
              && all (not . Text.null) identifiers
              && Set.size (Set.fromList identifiers) == length identifiers
              && LazyByteString.length bytes <= fromIntegral maxRequestBytes
          _ -> False
      _ -> False
    validSubjectProjection = case normalizedSubjectIdentityProjection normalized of
      Nothing -> True
      Just projection@(Object _) -> case canonicalBytes projection of
        Right bytes -> LazyByteString.length bytes <= fromIntegral maxRequestBytes
        Left _ -> False
      Just _ -> False
    normalizedPayload =
      object
        [ "policy" .= normalizedPolicy normalized
        , "subjects" .= normalizedSubjects normalized
        , "evidence" .= evidence
        ]

evidenceId :: Value -> Maybe Text
evidenceId (Object fields) = case KeyMap.lookup "id" fields of
  Just (String identifier) -> Just identifier
  Just _ -> Nothing
  Nothing -> Nothing
evidenceId _ = Nothing

validPackInputError :: PackInputError -> Bool
validPackInputError (PackInputError code pointer) =
  Set.member code allowedCodes
    && validPointer pointer
    && (Text.null pointer || Set.member (pointerRoot pointer) allowedRoots)
  where
    allowedCodes = Set.fromList
      [ "input.invalid_utf8"
      , "input.invalid_json"
      , "input.duplicate_key"
      , "input.invalid_unicode"
      , "input.number_profile"
      , "input.missing_field"
      , "input.unknown_field"
      , "input.invalid_type"
      , "input.invalid_value"
      , "policy.unsupported"
      , "identity.digest_mismatch"
      , "evidence.duplicate_id"
      , "evidence.duplicate_role"
      , "limit.exceeded"
      ]
    allowedRoots = Set.fromList ["policy", "subjects", "evidence"]

pointerRoot :: Text -> Text
pointerRoot pointer = Text.replace "~0" "~" (Text.replace "~1" "/" firstSegment)
  where
    firstSegment = case Text.splitOn "/" (Text.drop 1 pointer) of
      [] -> ""
      first : _ -> first

validPointer :: Text -> Bool
validPointer pointer = Text.null pointer ||
  (Text.isPrefixOf "/" pointer && validPointerEscapes (Text.unpack pointer))
  where
    validPointerEscapes [] = True
    validPointerEscapes ('~' : '0' : rest) = validPointerEscapes rest
    validPointerEscapes ('~' : '1' : rest) = validPointerEscapes rest
    validPointerEscapes ('~' : _) = False
    validPointerEscapes (_ : rest) = validPointerEscapes rest

internalFailure :: Value
internalFailure = errorEnvelope (InputError "internal.failure" "")

trySynchronous :: IO result -> IO (Either Exception.SomeException result)
trySynchronous = Exception.tryJust synchronousOnly
  where
    synchronousOnly exception =
      case Exception.fromException exception :: Maybe Exception.SomeAsyncException of
        Just _ -> Nothing
        Nothing -> Just exception
