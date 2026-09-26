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

    // ------------------------------------------------------------ citizen intake (Phase 2)
    intakeCapabilities: (signal?: AbortSignal) => client.get<IntakeCapabilities>(`${V1}/intake/capabilities`, { signal }),

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

    classificationExplanation: (id: string, signal?: AbortSignal) =>
      client.get<ClassificationExplanation>(`${V1}/classification/${encodeURIComponent(id)}/explanation`, { signal }),
  }
}

export type SpandanApi = ReturnType<typeof createSpandanApi>

export const spandanApi = createSpandanApi()
