import { useParams } from 'react-router-dom'
import { ErrorState, LoadingState } from '../components/AsyncStates'
import { PageHeader } from '../components/Layout'
import { StatusBadge } from '../components/StatusBadge'
import { useApi } from '../hooks/useApi'
import { agentXApi } from '../services/agentxApi'

/** Complaint detail + audit trail. Tracking, SLA and explanations are added in Phase 9. */
export function ComplaintDetailPage() {
  const { id = '' } = useParams()
  const detail = useApi(
    async (signal) => {
      const [complaint, audit] = await Promise.all([
        agentXApi.getComplaint(id, signal),
        agentXApi.getComplaintAudit(id, signal),
      ])
      return { complaint, audit }
    },
    `complaint:${id}`,
  )

  if (detail.status === 'loading') return <LoadingState label="Loading complaint…" />
  if (detail.status === 'error') return <ErrorState error={detail.error} onRetry={detail.reload} />

  const { complaint, audit } = detail.data
  return (
    <>
      <PageHeader title={complaint.issue ?? 'Complaint'} subtitle={complaint.tracking_id ?? 'Not filed yet'} />
      <section className="rounded-lg bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={complaint.status} />
          <span className="text-sm text-slate-600">Authority: {complaint.authority_status}</span>
        </div>
        <h2 className="mt-6 font-semibold">In the citizen's words</h2>
        <p className="mt-1 whitespace-pre-line rounded-lg bg-slate-50 p-4" lang={complaint.language ?? undefined}>
          {complaint.citizen_input}
        </p>
      </section>
      <section className="mt-6 rounded-lg bg-white p-6 shadow-sm" aria-labelledby="audit-heading">
        <h2 id="audit-heading" className="text-xl font-semibold">
          Audit trail ({audit.total})
        </h2>
        <ol className="mt-4 space-y-3 border-l-2 border-slate-200 pl-4">
          {audit.items.map((event) => (
            <li key={event.id}>
              <p className="font-medium">{event.summary}</p>
              <p className="text-sm text-slate-500">
                {event.event_type} · {event.actor_name} · {new Date(event.occurred_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ol>
      </section>
    </>
  )
}
