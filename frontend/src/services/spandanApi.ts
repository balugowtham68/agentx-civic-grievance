import type {
  AuditEventListResponse,
  ClassificationExplanation,
  ClassificationResult,
  DraftEditRequest,
  DraftView,
  Complaint,
  ComplaintCreateRequest,
  ComplaintListResponse,
  ComplaintStatus,
  ComplaintStatusResponse,
  HealthResponse,
  IntakeCapabilities,
  IntakeCorrectionRequest,
  IntakeHandoff,
  IntakeResult,
  TextIntakeRequest,
} from '../types/api'
import { apiClient, type ApiClient } from './apiClient'

const V1 = '/api/v1'

/** Typed backend calls. Pass a client to test with a mocked fetch. */
export function createSpandanApi(client: ApiClient = apiClient) {
  return {
    health: (signal?: AbortSignal) => client.get<HealthResponse>('/health', { signal }),

    createComplaint: (body: ComplaintCreateRequest) => client.post<Complaint>(`${V1}/complaints`, body),

    listComplaints: (params: { status?: ComplaintStatus[]; limit?: number; offset?: number } = {}, signal?: AbortSignal) =>
      client.get<ComplaintListResponse>(`${V1}/complaints`, { query: params, signal }),

    getComplaint: (id: string, signal?: AbortSignal) =>
      client.get<Complaint>(`${V1}/complaints/${encodeURIComponent(id)}`, { signal }),

    getComplaintStatus: (id: string, signal?: AbortSignal) =>
      client.get<ComplaintStatusResponse>(`${V1}/complaints/${encodeURIComponent(id)}/status`, { signal }),

    getComplaintAudit: (id: string, signal?: AbortSignal) =>
      client.get<AuditEventListResponse>(`${V1}/complaints/${encodeURIComponent(id)}/audit`, { signal }),

    trackByTrackingId: (trackingId: string, signal?: AbortSignal) =>
      client.get<ComplaintStatusResponse>(`${V1}/track/${encodeURIComponent(trackingId)}`, { signal }),

    // Asynchronous Autonomous Pipeline APIs
    validateCivicIntent: (text: string, language?: string) =>
      client.post<{
        is_civic: boolean
        confidence: number
        category: string | null
        reason: string | null
        message: string | null
        suggested_questions: Array<{
          id: string
          question: string
          options: string[]
        }>
      }>(`${V1}/complaints/validate-intent`, { text, language }),

    submitComplaintFast: (body: {
      text: string
      language?: string | null
      location?: string | null
      latitude?: number | null
      longitude?: number | null
      channel?: string
      photo_data?: string | null
      photo_name?: string | null
      diagnostic_details?: Record<string, any> | null
    }) =>
      client.post<{
        complaint_id: string
        tracking_id: string
        status: string
        message: string
        created_at: string
      }>(`${V1}/complaints/submit`, body),

    getComplaintTimeline: (id: string, signal?: AbortSignal) =>
      client.get<{
        complaint_id: string
        tracking_id: string
        status: string
        issue: string | null
        location: string | null
        department_id: string | null
        jurisdiction_id: string | null
        timeline: Array<{
          id: string
          complaint_id: string
          stage: string
          message: string
          timestamp: string
          details: Record<string, any>
          icon: string
        }>
      }>(`${V1}/complaints/${encodeURIComponent(id)}/timeline`, { signal }),

    confirmComplaintLocation: (id: string, body: { confirmed: boolean; corrected_location?: string }) =>
      client.post<{ status: string; location: string }>(`${V1}/complaints/${encodeURIComponent(id)}/location/confirm`, body),

    confirmDraft: (id: string, body: { confirmed: boolean; edited_text?: string } = { confirmed: true }) =>
      client.post<{ status: string; complaint_id: string; message: string; deadline?: string }>(
        `${V1}/complaints/${encodeURIComponent(id)}/confirm-draft`,
        body
      ),

    // ------------------------------------------------------------ citizen intake (Phase 2)
    intakeCapabilities: (signal?: AbortSignal) => client.get<IntakeCapabilities>(`${V1}/intake/capabilities`, { signal }),

    detectLanguage: (text: string, audioLanguage?: string | null, audioConfidence?: number | null) =>
      client.post<{
        language: string | null
        language_name: string
        confidence: number
        confidence_tier: 'HIGH' | 'MEDIUM' | 'LOW'
        needs_confirmation: boolean
        method: string
        reason_code: string
        english_translation?: string
        signals: {
          audio?: { language?: string | null; confidence?: number | null; source?: string } | null
          script?: { dominant_script?: string | null; script_language?: string | null; native_char_ratio?: number; latin_char_ratio?: number; is_code_mixed?: boolean } | null
          lexical?: { language?: string | null; confidence?: number; marker_scores?: Record<string, number>; matched_markers?: string[]; english_loanword_count?: number } | null
          classifier?: { predicted_language?: string | null; confidence?: number; probabilities?: Record<string, number> } | null
          llm?: { language?: string | null; confidence?: number; reason_code?: string | null; executed?: boolean } | null
        }
      }>(`/api/v1/language/detect`, {
        text,
        audio_language: audioLanguage ?? null,
        audio_confidence: audioConfidence ?? null,
      }),

    detectAudio: (audioBlob: Blob) =>
      client.request<{
        transcript: string
        language: string | null
        language_name: string
        confidence: number
        confidence_tier: 'HIGH' | 'MEDIUM' | 'LOW'
        needs_confirmation: boolean
        method: string
        reason_code: string
        english_translation?: string
        signals: Record<string, any>
      }>(`/api/v1/language/detect-audio`, {
        method: 'POST',
        rawBody: audioBlob,
      }),

    submitTextIntake: (body: TextIntakeRequest) => client.post<IntakeResult>(`${V1}/intake/text`, body),

    submitVoiceIntake: (audio: Blob, language?: string | null) =>
      client.request<IntakeResult>(`${V1}/intake/voice`, { method: 'POST', rawBody: audio, query: { language } }),

    getIntake: (id: string, signal?: AbortSignal) => client.get<IntakeResult>(`${V1}/intake/${encodeURIComponent(id)}`, { signal }),

    retryIntake: (id: string, language?: string | null) =>
      client.post<IntakeResult>(`${V1}/intake/${encodeURIComponent(id)}/process`, { language: language ?? null }),

    answerClarification: (id: string, text: string) =>
      client.post<IntakeResult>(`${V1}/intake/${encodeURIComponent(id)}/answer`, { text }),

    /** Structured corrections, or the citizen's own words: { text: 'No, it is 5 days' }. */
    correctIntake: (id: string, body: IntakeCorrectionRequest) =>
      client.post<IntakeResult>(`${V1}/intake/${encodeURIComponent(id)}/correction`, body),

    confirmIntake: (id: string) => client.post<IntakeResult>(`${V1}/intake/${encodeURIComponent(id)}/confirm`, {}),

    intakeHandoff: (id: string, signal?: AbortSignal) =>
      client.get<IntakeHandoff>(`${V1}/intake/${encodeURIComponent(id)}/handoff`, { signal }),

    // ------------------------------------------------------------ classification (Phase 3)
    /** Only works after the citizen confirmed the intake (UNDERSTOOD); 409 otherwise. */
    runClassification: (id: string) => client.post<ClassificationResult>(`${V1}/classification/${encodeURIComponent(id)}/run`, {}),

    getClassification: (id: string, signal?: AbortSignal) =>
      client.get<ClassificationResult>(`${V1}/classification/${encodeURIComponent(id)}`, { signal }),

    retryClassification: (id: string) =>
      client.post<ClassificationResult>(`${V1}/classification/${encodeURIComponent(id)}/retry`, {}),

    answerClassification: (id: string, text: string) =>
      client.post<ClassificationResult>(`${V1}/classification/${encodeURIComponent(id)}/answer`, { text }),

    // ------------------------------------------------------------ drafting (Phase 4)
    /** Only CLASSIFIED complaints can be drafted (409 otherwise). Nothing is filed. */
    runDrafting: (id: string) => client.post<DraftView>(`${V1}/drafting/${encodeURIComponent(id)}/run`, {}),

    getDraft: (id: string, signal?: AbortSignal) => client.get<DraftView>(`${V1}/drafting/${encodeURIComponent(id)}`, { signal }),

    editDraft: (id: string, body: DraftEditRequest) =>
      client.post<DraftView>(`${V1}/drafting/${encodeURIComponent(id)}/edit`, body),

    approveDraft: (id: string, version: number) =>
      client.post<DraftView>(`${V1}/drafting/${encodeURIComponent(id)}/approve`, { version }),

    fileComplaint: (id: string) => 
      client.post<Complaint>(`${V1}/complaints/${encodeURIComponent(id)}/file`, {}),

    classificationExplanation: (id: string, signal?: AbortSignal) =>
      client.get<ClassificationExplanation>(`${V1}/classification/${encodeURIComponent(id)}/explanation`, { signal }),
  }
}

export type SpandanApi = ReturnType<typeof createSpandanApi>

export const spandanApi = createSpandanApi()
