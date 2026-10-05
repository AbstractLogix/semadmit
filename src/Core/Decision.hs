{-# LANGUAGE OverloadedStrings #-}

module Core.Decision
  ( Outcome (..)
  , DecisionState (..)
  , SubjectDeclaration (..)
  , SubjectArtifact (..)
  , SubjectBinding (..)
  , EvidenceDeclaration (..)
  , EvidenceArtifact (..)
  , EvidenceBinding (..)
  , Bindings
  , DecisionContext (..)
  , ComponentDeclaration (..)
  , ComponentPayload (..)
  , ComponentBinding (..)
  , Diagnostic (..)
  , DecisionError (..)
  , reduceObligations
  , validateComponents
  , normalizeDiagnostics
  , buildBindings
  , buildDecision
  ) where

import Core.Identity (PackIdentity, artifactDigest, decisionDigest)
import Core.Version (protocolVersion)
import Data.Aeson (Value (..), object, (.=))
import Data.List (sortOn)
import Data.Map.Strict (Map)
import Data.Map.Strict qualified as Map
import Data.Set qualified as Set
import Data.Text (Text)
import Data.Text qualified as Text

data Outcome = Pass | Fail | Missing deriving (Eq, Ord, Show)
data DecisionState = Admissible | Inadmissible | Indeterminate deriving (Eq, Show)
data SubjectDeclaration = SubjectDeclaration
  { subjectDeclarationRole :: Text
  , subjectDeclarationKind :: Text
  , subjectDeclarationSchema :: Text
  }
  deriving (Eq, Show)

data SubjectArtifact = SubjectArtifact
  { subjectArtifactRole :: Text
  , subjectArtifactKind :: Text
  , subjectArtifactSchema :: Text
  , subjectArtifactValue :: Value
  }
  deriving (Eq, Show)

data SubjectBinding = SubjectBinding
  { subjectBindingRole :: Text
  , subjectBindingKind :: Text
  , subjectBindingSchema :: Text
  , subjectBindingDigest :: Text
  }
  deriving (Eq, Show)

data EvidenceDeclaration = EvidenceDeclaration
  { evidenceDeclarationKind :: Text
  , evidenceDeclarationSchema :: Text
  }
  deriving (Eq, Show)

data EvidenceArtifact = EvidenceArtifact
  { evidenceArtifactId :: Text
  , evidenceArtifactKind :: Text
  , evidenceArtifactSchema :: Text
  , evidenceArtifactValue :: Value
  }
  deriving (Eq, Show)

data EvidenceBinding = EvidenceBinding
  { evidenceBindingId :: Text
  , evidenceBindingKind :: Text
  , evidenceBindingSchema :: Text
  , evidenceBindingDigest :: Text
  }
  deriving (Eq, Show)

data Bindings = Bindings
  { boundSubjects :: [SubjectBinding]
  , boundComponents :: [ComponentBinding]
  , boundEvidence :: [EvidenceBinding]
  }

data DecisionContext = DecisionContext
  { decisionProtocol :: Text
  , decisionPack :: Text
  , decisionOperation :: Text
  , decisionRequestDigest :: Text
  , decisionPolicyDigest :: Text
  }
  deriving (Eq, Show)

data ComponentDeclaration = ComponentDeclaration
  { declaredSubjectRole :: Text
  , declaredComponentName :: Text
  , declaredComponentKind :: Text
  , declaredComponentSchema :: Text
  , minimumComponents :: Int
  , maximumComponents :: Int
  }
  deriving (Eq, Show)

data ComponentPayload = ComponentPayload
  { payloadSubjectRole :: Text
  , payloadComponentName :: Text
  , payloadComponentKind :: Text
  , payloadComponentSchema :: Text
  , payloadValue :: Value
  }
  deriving (Eq, Show)

data ComponentBinding = ComponentBinding
  { bindingSubjectRole :: Text
  , bindingComponentName :: Text
  , bindingComponentKind :: Text
  , bindingComponentSchema :: Text
  , bindingDigest :: Text
  }
  deriving (Eq, Show)

data Diagnostic = Diagnostic
  { diagnosticObligationId :: Text
  , diagnosticPointer :: Text
  , diagnosticCode :: Text
  }
  deriving (Eq, Ord, Show)

data DecisionError
  = InvalidObligationSet
  | InvalidComponentDeclaration
  | InvalidComponentOutput
  | InvalidDiagnosticOutput
  | InvalidSubjectBindings
  | InvalidEvidenceBindings
  | InvalidDecisionContext
  | InvalidDecisionOutput
  deriving (Eq, Show)

reduceObligations :: [Text] -> [(Text, Outcome)] -> Either DecisionError (DecisionState, [(Text, Outcome)])
reduceObligations declared results
  | null declared = Left InvalidObligationSet
  | any Text.null declared = Left InvalidObligationSet
  | Set.size declaredSet /= length declared = Left InvalidObligationSet
  | Set.size resultSet /= length results = Left InvalidObligationSet
  | resultSet /= declaredSet = Left InvalidObligationSet
  | otherwise = Right (state, sortOn fst results)
  where
    declaredSet = Set.fromList declared
    resultSet = Set.fromList (map fst results)
    outcomes = map snd results
    state
      | Fail `elem` outcomes = Inadmissible
      | Missing `elem` outcomes = Indeterminate
      | otherwise = Admissible

validateComponents
  :: PackIdentity
  -> [ComponentDeclaration]
  -> [ComponentPayload]
  -> Either DecisionError [ComponentBinding]
validateComponents identities declarations payloads
  | not (validDeclarations declarations) = Left InvalidComponentDeclaration
  | any (not . matchesDeclaration) payloads = Left InvalidComponentOutput
  | any outsideCardinality declarations = Left InvalidComponentOutput
  | otherwise = sortOn bindingKey <$> traverse bind payloads
  where
    declarationsByKey = Map.fromList [(declarationKey declaration, declaration) | declaration <- declarations]
    payloadCounts = Map.fromListWith (+) [(payloadKey payload, 1 :: Int) | payload <- payloads]

    validDeclarations items =
      all validDeclaration items
        && Set.size (Set.fromList (map declarationKey items)) == length items

    validDeclaration declaration =
      not (Text.null (declaredSubjectRole declaration))
        && not (Text.null (declaredComponentName declaration))
        && not (Text.null (declaredComponentKind declaration))
        && not (Text.null (declaredComponentSchema declaration))
        && minimumComponents declaration >= 0
        && maximumComponents declaration >= minimumComponents declaration
        && identityDeclared (declaredComponentKind declaration) (declaredComponentSchema declaration)

    identityDeclared kind schema = case artifactDigest identities kind schema Null of
      Right _ -> True
      Left _ -> False

    matchesDeclaration payload = case Map.lookup (payloadKey payload) declarationsByKey of
      Just declaration ->
        payloadComponentKind payload == declaredComponentKind declaration
          && payloadComponentSchema payload == declaredComponentSchema declaration
      Nothing -> False

    outsideCardinality declaration =
      let count = Map.findWithDefault 0 (declarationKey declaration) payloadCounts
       in count < minimumComponents declaration || count > maximumComponents declaration

    bind payload = case artifactDigest identities (payloadComponentKind payload) (payloadComponentSchema payload) (payloadValue payload) of
      Left _ -> Left InvalidComponentOutput
      Right digest ->
        Right
          ComponentBinding
            { bindingSubjectRole = payloadSubjectRole payload
            , bindingComponentName = payloadComponentName payload
            , bindingComponentKind = payloadComponentKind payload
            , bindingComponentSchema = payloadComponentSchema payload
            , bindingDigest = digest
            }

    declarationKey declaration = (declaredSubjectRole declaration, declaredComponentName declaration)
    payloadKey payload = (payloadSubjectRole payload, payloadComponentName payload)
    bindingKey binding = (bindingSubjectRole binding, bindingComponentName binding)

normalizeDiagnostics
  :: [Text]
  -> Map Text [Text]
  -> [Diagnostic]
  -> Either DecisionError [Diagnostic]
normalizeDiagnostics declaredObligations allowedPointers diagnostics
  | null declaredObligations || any Text.null declaredObligations || Set.size declaredSet /= length declaredObligations = Left InvalidObligationSet
  | not (validDeclarations allowedPointers) = Left InvalidDiagnosticOutput
  | any (not . isDeclared) diagnostics = Left InvalidDiagnosticOutput
  | otherwise = Right (Set.toAscList (Set.fromList diagnostics))
  where
    declaredSet = Set.fromList declaredObligations
    isDeclared diagnostic =
      Set.member (diagnosticObligationId diagnostic) declaredSet
        && validPointer (diagnosticPointer diagnostic)
        && case Map.lookup (diagnosticCode diagnostic) allowedPointers of
          Just pointers -> any (\template -> matchesPointerTemplate template (diagnosticPointer diagnostic)) pointers
          Nothing -> False
    validPointer pointer =
      Text.null pointer
        || (Text.isPrefixOf "/" pointer && validPointerEscapes (Text.unpack pointer))

    validDeclarations declarations = all validDeclaration (Map.toList declarations)
    validDeclaration (code, pointers) =
      not (Text.null code)
        && not (null pointers)
        && Set.size (Set.fromList pointers) == length pointers
        && all validPointerTemplate pointers

    validPointerTemplate pointer =
      validPointer pointer
        && all validTemplateSegment (Text.splitOn "/" pointer)

    validTemplateSegment segment
      | not (Text.any (\character -> character == '{' || character == '}') segment) = True
      | otherwise = segment `elem` ["{left,right}", "{role}", "{field}", "{canonical-index}"]

    matchesPointerTemplate template pointer =
      let templateSegments = Text.splitOn "/" template
          pointerSegments = Text.splitOn "/" pointer
       in length templateSegments == length pointerSegments
            && and (zipWith matchesSegment templateSegments pointerSegments)

    matchesSegment "{left,right}" segment = segment == "left" || segment == "right"
    matchesSegment "{role}" segment = segment == "left" || segment == "right"
    matchesSegment "{field}" segment =
      segment `elem` ["quantity_id", "unit_id", "method_id", "reference_frame_id", "context_population_id"]
    matchesSegment "{canonical-index}" segment = canonicalNaturalText segment
    matchesSegment expected segment = expected == segment

    canonicalNaturalText "0" = True
    canonicalNaturalText value = case Text.uncons value of
      Just (first, rest) -> first >= '1' && first <= '9' && Text.all isAsciiDigit rest
      Nothing -> False

    isAsciiDigit character = character >= '0' && character <= '9'

    validPointerEscapes [] = True
    validPointerEscapes ('~' : '0' : rest) = validPointerEscapes rest
    validPointerEscapes ('~' : '1' : rest) = validPointerEscapes rest
    validPointerEscapes ('~' : _) = False
    validPointerEscapes (_ : rest) = validPointerEscapes rest

buildBindings
  :: PackIdentity
  -> [SubjectDeclaration]
  -> [SubjectArtifact]
  -> [ComponentDeclaration]
  -> [ComponentPayload]
  -> Maybe EvidenceDeclaration
  -> [EvidenceArtifact]
  -> Either DecisionError Bindings
buildBindings identities subjectDeclarations subjectArtifacts componentDeclarations componentPayloads evidenceDeclaration evidenceArtifacts
  | not (validSubjectDeclarations subjectDeclarations) = Left InvalidSubjectBindings
  | not (validSubjectArtifacts subjectDeclarations subjectArtifacts) = Left InvalidSubjectBindings
  | not (validEvidence evidenceDeclaration evidenceArtifacts) = Left InvalidEvidenceBindings
  | otherwise = do
      subjectBindings <- traverse bindSubject (sortOn subjectArtifactRole subjectArtifacts)
      componentBindings <- validateComponents identities componentDeclarations componentPayloads
      evidenceBindings <- traverse bindEvidence (sortOn evidenceArtifactId evidenceArtifacts)
      Right (Bindings subjectBindings componentBindings evidenceBindings)
  where
    validSubjectDeclarations declarations =
      not (null declarations)
        && all validSubjectDeclaration declarations
        && Set.size (Set.fromList (map subjectDeclarationRole declarations)) == length declarations

    validSubjectDeclaration declaration =
      not (Text.null (subjectDeclarationRole declaration))
        && not (Text.null (subjectDeclarationKind declaration))
        && not (Text.null (subjectDeclarationSchema declaration))
        && identityDeclared (subjectDeclarationKind declaration) (subjectDeclarationSchema declaration)

    validSubjectArtifacts declarations artifacts =
      length artifacts == length declarations
        && Set.size (Set.fromList (map subjectArtifactRole artifacts)) == length artifacts
        && all matchesDeclaration artifacts
      where
        declarationsByRole = Map.fromList [(subjectDeclarationRole item, item) | item <- declarations]
        matchesDeclaration artifact = case Map.lookup (subjectArtifactRole artifact) declarationsByRole of
          Just declaration ->
            subjectArtifactKind artifact == subjectDeclarationKind declaration
              && subjectArtifactSchema artifact == subjectDeclarationSchema declaration
          Nothing -> False

    validEvidence Nothing artifacts = null artifacts
    validEvidence (Just declaration) artifacts =
      not (Text.null (evidenceDeclarationKind declaration))
        && not (Text.null (evidenceDeclarationSchema declaration))
        && identityDeclared (evidenceDeclarationKind declaration) (evidenceDeclarationSchema declaration)
        && all matchesDeclaration artifacts
        && all (not . Text.null . evidenceArtifactId) artifacts
        && Set.size (Set.fromList (map evidenceArtifactId artifacts)) == length artifacts
      where
        matchesDeclaration artifact =
          evidenceArtifactKind artifact == evidenceDeclarationKind declaration
            && evidenceArtifactSchema artifact == evidenceDeclarationSchema declaration

    identityDeclared kind schema = case artifactDigest identities kind schema Null of
      Right _ -> True
      Left _ -> False

    bindSubject artifact = do
      digest <- either (const (Left InvalidSubjectBindings)) Right
        (artifactDigest identities (subjectArtifactKind artifact) (subjectArtifactSchema artifact) (subjectArtifactValue artifact))
      Right
        SubjectBinding
          { subjectBindingRole = subjectArtifactRole artifact
          , subjectBindingKind = subjectArtifactKind artifact
          , subjectBindingSchema = subjectArtifactSchema artifact
          , subjectBindingDigest = digest
          }

    bindEvidence artifact = do
      digest <- either (const (Left InvalidEvidenceBindings)) Right
        (artifactDigest identities (evidenceArtifactKind artifact) (evidenceArtifactSchema artifact) (evidenceArtifactValue artifact))
      Right
        EvidenceBinding
          { evidenceBindingId = evidenceArtifactId artifact
          , evidenceBindingKind = evidenceArtifactKind artifact
          , evidenceBindingSchema = evidenceArtifactSchema artifact
          , evidenceBindingDigest = digest
          }

buildDecision
  :: DecisionContext
  -> [Text]
  -> [Outcome]
  -> [(Text, Outcome)]
  -> Map Text [Text]
  -> [Diagnostic]
  -> Bindings
  -> Either DecisionError Value
buildDecision context declaredObligations allowedOutcomes results allowedPointers diagnostics bindings
  | not (validContext context) = Left InvalidDecisionContext
  | null allowedOutcomes || Set.size (Set.fromList allowedOutcomes) /= length allowedOutcomes = Left InvalidObligationSet
  | any ((`notElem` allowedOutcomes) . snd) results = Left InvalidObligationSet
  | otherwise = do
      (state, orderedOutcomes) <- reduceObligations declaredObligations results
      orderedDiagnostics <- normalizeDiagnostics declaredObligations allowedPointers diagnostics
      let payload = decisionPayload state orderedOutcomes orderedDiagnostics
      case decisionDigest payload of
        Left _ -> Left InvalidDecisionOutput
        Right digest -> Right (object ["kind" .= ("decision" :: Text), "payload" .= payload, "decision_digest" .= digest])
  where
    validContext candidate =
      decisionProtocol candidate == protocolVersion
        && not (Text.null (decisionPack candidate))
        && not (Text.null (decisionOperation candidate))
        && validDigest (decisionRequestDigest candidate)
        && validDigest (decisionPolicyDigest candidate)

    validDigest value = case Text.stripPrefix "sha256:" value of
      Just hexadecimal -> Text.length hexadecimal == 64 && Text.all isLowerHex hexadecimal
      Nothing -> False
    isLowerHex character = (character >= '0' && character <= '9') || (character >= 'a' && character <= 'f')

    decisionPayload state orderedOutcomes orderedDiagnostics =
      object
        [ "protocol" .= decisionProtocol context
        , "pack" .= decisionPack context
        , "operation" .= decisionOperation context
        , "request_digest" .= decisionRequestDigest context
        , "policy_digest" .= decisionPolicyDigest context
        , "state" .= stateText state
        , "bindings" .= bindingsValue bindings
        , "obligations" .= map obligationValue orderedOutcomes
        , "diagnostics" .= map diagnosticValue orderedDiagnostics
        ]

    bindingsValue value =
      object
        [ "subjects" .= map subjectBindingValue (boundSubjects value)
        , "components" .= map componentBindingValue (boundComponents value)
        , "evidence" .= map evidenceBindingValue (boundEvidence value)
        ]

    subjectBindingValue binding = object
      [ "role" .= subjectBindingRole binding
      , "kind" .= subjectBindingKind binding
      , "schema" .= subjectBindingSchema binding
      , "digest" .= subjectBindingDigest binding
      ]

    componentBindingValue binding = object
      [ "subject_role" .= bindingSubjectRole binding
      , "name" .= bindingComponentName binding
      , "kind" .= bindingComponentKind binding
      , "schema" .= bindingComponentSchema binding
      , "digest" .= bindingDigest binding
      ]

    evidenceBindingValue binding = object
      [ "id" .= evidenceBindingId binding
      , "kind" .= evidenceBindingKind binding
      , "schema" .= evidenceBindingSchema binding
      , "digest" .= evidenceBindingDigest binding
      ]

    obligationValue (identifier, outcome) = object ["id" .= identifier, "outcome" .= outcomeText outcome]
    diagnosticValue item = object
      [ "obligation_id" .= diagnosticObligationId item
      , "pointer" .= diagnosticPointer item
      , "code" .= diagnosticCode item
      ]

    stateText Admissible = "admissible" :: Text
    stateText Inadmissible = "inadmissible"
    stateText Indeterminate = "indeterminate"
    outcomeText Pass = "pass" :: Text
    outcomeText Fail = "fail"
    outcomeText Missing = "missing"
