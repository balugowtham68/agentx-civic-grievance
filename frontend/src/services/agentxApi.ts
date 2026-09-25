import type {
  AuditEventListResponse,
  Complaint,
  ComplaintCreateRequest,
  ComplaintListResponse,
  ComplaintStatus,
  ComplaintStatusResponse,
  HealthResponse,
} from '../types/api'
import { apiClient, type ApiClient } from './apiClient'

const V1 = '/api/v1'

/** Typed backend calls. Pass a client to test with a mocked fetch. */
export function createAgentXApi(client: ApiClient = apiClient) {
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
  }
}

export type AgentXApi = ReturnType<typeof createAgentXApi>

export const agentXApi = createAgentXApi()
