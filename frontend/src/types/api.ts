/**
 * TypeScript mirrors of the backend contracts (backend/app/schemas).
 * Keep in sync with /openapi.json. A change here is a contract change: tell the team.
 */

export type ComplaintStatus =
  | 'CREATED'
  | 'NEEDS_INFO'
  | 'UNDERSTOOD'
  | 'CLASSIFIED'
  | 'NEEDS_REVIEW'
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
