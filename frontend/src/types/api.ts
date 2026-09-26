/**
 * TypeScript mirrors of the backend contracts (backend/app/schemas).
 * Keep in sync with /openapi.json. A change here is a contract change: tell the team.
 */

export type ComplaintStatus =
  | 'CREATED'
  | 'UNDERSTANDING'
  | 'NEEDS_INFO'
  | 'UNDERSTOOD'
  | 'CLASSIFYING'
  | 'CLASSIFIED'
  | 'NEEDS_REVIEW'
  | 'DRAFTING'
  | 'DRAFTED'
  | 'FILED'
  | 'FILING_FAILED'
  | 'MONITORING'
  | 'WARNING'
  | 'BREACHED'
  | 'ESCALATED'
  | 'RESOLVED'
  | 'CLOSED'

/** ACKNOWLEDGED is not RESOLVED: it does not stop the SLA or escalation by default. */
export type AuthorityStatus = 'NONE' | 'RECEIVED' | 'ACKNOWLEDGED' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED'

export type SLAStage = 'NOT_STARTED' | 'ON_TRACK' | 'APPROACHING' | 'BREACHED' | 'STOPPED'

export type EscalationState = 'NONE' | 'ESCALATED' | 'ACKNOWLEDGED' | 'CLOSED'

export type InputChannel = 'text' | 'voice'

export type ActorType = 'agent' | 'citizen' | 'authority' | 'system'

export interface HealthResponse {
  status: 'ok' | 'degraded'
  service: string
  version: string
  environment: string
  database: 'ok' | 'unavailable'
  configuration: Record<string, unknown>
  knowledge_base?: Record<string, unknown> | null
}

export interface ComplaintCreateRequest {
  citizen_input: string
  language?: string | null
  channel?: InputChannel
}

export interface ComplaintSummary {
  id: string
  tracking_id: string | null
  issue: string | null
  status: ComplaintStatus
  authority_status: AuthorityStatus
  escalation_state: EscalationState
  created_at: string
  updated_at: string
}

export interface Complaint extends ComplaintSummary {
  citizen_input: string
  input_channel: InputChannel
  language: string | null
  location: string | null
  duration: string | null
  category: string | null
  department_id: string | null
  jurisdiction_id: string | null
  drafted_complaint: Record<string, unknown> | null
  sla_start: string | null
  sla_deadline: string | null
}

export interface ComplaintListResponse {
  items: ComplaintSummary[]
  total: number
}

export interface SLAState {
  policy_id: string
  started_at: string
  warning_at: string
  deadline_at: string
  stage: SLAStage
  stopped_at: string | null
  stop_reason: string | null
}

export interface Escalation {
  id: number
  level: number
  policy_id: string
  target_authority_id: string
  state: EscalationState
  reason: string
  mock_reference: string | null
  created_at: string
  updated_at: string
}

export interface ComplaintStatusResponse {
  id: string
  tracking_id: string | null
  status: ComplaintStatus
  authority_status: AuthorityStatus
  sla: SLAState | null
  escalation_state: EscalationState
  escalations: Escalation[]
  updated_at: string
}

export interface AuditEvent {
  id: number
  complaint_id: string | null
  event_type: string
  actor_type: ActorType
  actor_name: string
  summary: string
  payload: Record<string, unknown>
  evidence: Record<string, unknown>[]
  occurred_at: string
  sim_time: string | null
}

export interface AuditEventListResponse {
  items: AuditEvent[]
  total: number
}

export interface ErrorDetail {
  field: string | null
  message: string
}

/** Every backend error has this shape. */
export interface ErrorResponse {
  error: {
    code: string
    message: string
    details: ErrorDetail[]
    request_id: string | null
  }
}

// ---------------------------------------------------------------- Citizen intake (Phase 2)
// Mirrors backend/app/schemas/intake.py

export type IntakeField = 'issue' | 'location' | 'duration'
export type FieldRequirement = 'REQUIRED_TO_CONTINUE' | 'OPTIONAL' | 'UNKNOWN'
export type FactSource = 'citizen_statement' | 'citizen_correction'
/** How a fact was found: offline pattern rule, offline language lexicon, optional AI, or the citizen's own correction. */
export type FactMethod = 'rule' | 'lexicon' | 'ai' | 'citizen'
export type FactQuality = 'clear' | 'vague' | 'partial'
export type IntakeStatus = 'COMPLETED' | 'NEEDS_INFO' | 'NEEDS_LANGUAGE' | 'FAILED'
export type ConfirmationStatus = 'NOT_READY' | 'PENDING' | 'CONFIRMED'
export type SupportLevel = 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'FALLBACK' | 'UNAVAILABLE'
export type ProcessingMode = 'OFFLINE_RULE' | 'OFFLINE_LOCAL_MODEL' | 'OPTIONAL_AI' | 'MIXED'
/** Intake only ever reaches UNDERSTOOD, and only after the citizen confirms. */
export type IntakeComplaintStatus = 'CREATED' | 'UNDERSTANDING' | 'NEEDS_INFO' | 'UNDERSTOOD'

export interface ExtractedFact {
  value: string
  /** The citizen's exact words: the evidence for this fact. */
  source_span: string
  source: FactSource
  statement_index: number
  confidence: number | null
  method?: FactMethod | null
  quality?: FactQuality
}

export interface ExtractedEntity extends ExtractedFact {
  type: string
}

export interface ExtractedGrievance {
  issue: ExtractedFact | null
  location: ExtractedFact | null
  duration: ExtractedFact | null
  entities: ExtractedEntity[]
}

export interface MissingField {
  field: IntakeField
  requirement: FieldRequirement
  reason: string
}

export interface ClarificationQuestion {
  /** Phase 2 asks about intake fields; Phase 3 reuses this for 'locality' and 'category'. */
  field: IntakeField | 'locality' | 'category'
  text: string
  language: string
}

export interface ProviderTraceStep {
  stage: string
  provider: string
  outcome: string
  detail: string | null
}

export interface LanguageDetection {
  language: string
  confidence: number | null
  method: 'declared' | 'script' | 'heuristic' | 'provider' | 'default'
  transliterated: boolean
  script: string | null
  supported: boolean
}

export interface IntakeResult {
  complaint_id: string
  input_channel: InputChannel
  status: IntakeComplaintStatus
  intake_status: IntakeStatus
  original_text: string
  transcript: { text: string; provider: string; language: string | null; confidence: number | null } | null
  language: LanguageDetection
  language_source?: string
  original_language: string
  processing_language: string
  translation: {
    status: 'NOT_REQUIRED' | 'TRANSLATED' | 'FAILED' | 'UNAVAILABLE'
    source_language: string
    target_language: string
    translated_text: string | null
    provider: string | null
    error: string | null
  }
  translated_text: string | null
  extracted: ExtractedGrievance
  rejected_facts: { field: string; value: string; claimed_evidence: string | null; reason: string }[]
  missing_information: MissingField[]
  missing_fields: string[]
  clarification_questions: ClarificationQuestion[]
  extraction: {
    status: 'COMPLETED' | 'FAILED' | 'NOT_RUN'
    method: 'offline_rules' | 'ai_provider' | 'mixed' | 'rule_based_fallback' | 'none'
    provider: string | null
    fallback_reason: string | null
    error: string | null
  }
  confidence: number | null
  processing_mode?: ProcessingMode | null
  provider_trace?: ProviderTraceStep[]
  safety_flags?: string[]
  category_required_fields?: string[]
  citizen_confirmation_status: ConfirmationStatus
  evidence: { field: string; value: string; evidence: string; source: FactSource; method?: FactMethod | null }[]
  created_at?: string | null
  updated_at?: string | null
}

export interface LanguageInfo {
  code: string
  display_name: string
  native_name: string
  speech_locale: string
  text_intake: SupportLevel
  speech_to_text: SupportLevel
  translation: SupportLevel
  ui: SupportLevel
  notes: string
  offline_text?: boolean
  local_extraction?: string
  voice?: string
}

export interface IntakeCapabilities {
  processing_language: string
  offline_first?: boolean
  languages: LanguageInfo[]
  ai_extraction_available: boolean
  rule_based_fallback_available: boolean
  server_speech_to_text_available: boolean
  speech_to_text_providers?: string[]
  max_audio_bytes: number
  accepted_audio_types: string[]
}

export interface TextIntakeRequest {
  raw_text: string
  language?: string | null
  input_channel?: InputChannel
}

export interface FieldCorrection {
  field: IntakeField
  value: string | null
}

/** Exactly one of `corrections` (structured) or `text` (the citizen's own words, e.g. "No, it is 5 days"). */
export type IntakeCorrectionRequest = { corrections: FieldCorrection[] } | { text: string }

/** The confirmed intake as Phase 3 will consume it. */
export interface IntakeHandoff {
  complaint_id: string
  original_text: string
  language: string
  issue: ExtractedFact | null
  location: ExtractedFact | null
  duration: ExtractedFact | null
  entities: ExtractedEntity[]
  evidence: IntakeResult['evidence']
  translated_text: string | null
  confirmation_status: ConfirmationStatus
  processing_mode: ProcessingMode | null
}

// ---------------------------------------------------------------- Classification & Reasoning (Phase 3)
// Mirrors backend/app/schemas/classification.py. No numeric confidence: controlled states only.

export type ClassificationStatus = 'CLASSIFIED' | 'NEEDS_INFO' | 'AMBIGUOUS' | 'UNSUPPORTED_CLASSIFICATION'
export type ConfidenceState = 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'AMBIGUOUS' | 'UNSUPPORTED'
export type LocationPrecision = 'EXACT' | 'LANDMARK' | 'VAGUE' | 'MISSING'
export type JurisdictionStatus = 'RESOLVED' | 'UNRESOLVED' | 'AMBIGUOUS' | 'UNSUPPORTED' | 'NOT_REQUIRED'

export interface RetrievedKnowledge {
  doc_id: string
  source_id: string
  source_name: string
  source_type: string
  source_version: string
  official: boolean
  record_type: string
  record_id: string
  category: string | null
  department_id: string | null
  language: string | null
  content: string
  /** Retrieval score of the local embedding. Not a confidence; never shown as one. */
  similarity: number
}

export interface ClassificationEvidence {
  kind: 'citizen' | 'knowledge'
  field: string
  text: string
  source: string
}

export interface ClassificationCandidate {
  category: string
  record_id: string
  display_name: string
  retrieved: boolean
  best_similarity: number | null
  rule_matched: boolean
  decision: 'selected' | 'rejected' | 'suppressed' | 'ambiguous' | 'suggested'
  reason: string
}

export interface ClassificationResult {
  complaint_id: string
  status: ComplaintStatus
  classification_status: ClassificationStatus
  confidence_state: ConfidenceState
  category: string | null
  category_record_id: string | null
  category_name: string | null
  responsible_department: { department_id: string; name: string; source_id: string; mapping_record_id: string; label: string } | null
  jurisdiction: {
    status: JurisdictionStatus
    jurisdiction_id: string | null
    name: string | null
    matched_place: string | null
    matched_words: string | null
    source_id: string | null
    location_precision: LocationPrecision
    note: string | null
  }
  required_information: { field: string; requirement: 'REQUIRED' | 'OPTIONAL'; present: boolean; detail: string | null }[]
  missing_information: string[]
  clarification_questions: ClarificationQuestion[]
  candidates: ClassificationCandidate[]
  rule_matches: { rule_id: string; rule_type: string; category: string | null; pattern: string; language: string; citizen_words: string; source: string }[]
  retrieved_sources: RetrievedKnowledge[]
  evidence: ClassificationEvidence[]
  reasoning: { step: string; detail: string; source_ids: string[] }[]
  explanation: string
  service_guideline: string | null
  service_timeline: { policy_id: string; duration_hours: number; note: string } | null
  processing_mode: ProcessingMode
  provider_trace: ProviderTraceStep[]
  rejected_ai_output: string[]
  safety_flags: string[]
  language: string
  answers: { text: string; asked_for: 'locality' | 'category'; recorded_at: string }[]
  knowledge_base_version: string | null
  demo_data: boolean
  created_at: string | null
  updated_at: string | null
}

export interface ClassificationExplanation {
  complaint_id: string
  classification_status: ClassificationStatus
  explanation: string
  reasoning: ClassificationResult['reasoning']
  source_ids: string[]
  demo_data: boolean
}

// ---------------------------------------------------------------- Complaint drafting (Phase 4)
// Mirrors backend/app/schemas/drafting.py. Category, department and jurisdiction are locked (Phase 3).

export type DraftValidationStatus = 'VALID' | 'FALLBACK_USED' | 'NEEDS_REVIEW' | 'INVALID'
export type DraftReviewStatus = 'PENDING_REVIEW' | 'APPROVED' | 'SUPERSEDED'

export interface DraftSections {
  subject: string
  summary: string
  issue_text: string
  location_text: string
  duration_text: string
  requested_action: string
}

export interface ComplaintDraft {
  draft_id: string
  complaint_id: string
  version: number
  origin: 'generated' | 'citizen_edit'
  based_on_version: number | null
  sections: DraftSections
  body: string
  category: string
  category_name: string
  department_id: string
  department_name: string
  jurisdiction_id: string | null
  jurisdiction_name: string | null
  location: Record<string, string | null>
  duration: string | null
  chronology: string[]
  supporting_facts: string[]
  evidence_references: { kind: 'citizen' | 'classification' | 'knowledge'; field: string; text: string; source: string }[]
  source_ids: string[]
  citizen_statement: string | null
  citizen_language: string
  draft_language: string
  language_note: string | null
  processing_mode: ProcessingMode
  validation_status: DraftValidationStatus
  validation_issues: string[]
  /** Citizen edits: information the citizen added that is not verified system evidence. */
  citizen_added_information?: string[]
  review_status: DraftReviewStatus
  explanation: string
  ai_generated_notice: string
  generated_at: string
  created_by: 'agent' | 'citizen'
  demo_data: boolean
}

export interface DraftView {
  complaint_id: string
  status: ComplaintStatus
  current: ComplaintDraft
  versions: { version: number; origin: 'generated' | 'citizen_edit'; validation_status: DraftValidationStatus; review_status: DraftReviewStatus; subject: string; generated_at: string; created_by: string }[]
  approved_version?: number | null
}

export type DraftEditRequest = { based_on_version: number } & Partial<DraftSections>
