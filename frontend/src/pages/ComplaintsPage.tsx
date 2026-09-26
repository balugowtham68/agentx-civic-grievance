import { Link } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState } from '../components/AsyncStates'
import { PageHeader } from '../components/Layout'
import { StatusBadge } from '../components/StatusBadge'
import { useApi } from '../hooks/useApi'
import { spandanApi } from '../services/spandanApi'

export function ComplaintsPage() {
  const complaints = useApi((signal) => spandanApi.listComplaints({}, signal), 'complaints')

  return (
    <>
      <PageHeader title="Complaints" subtitle="Every grievance SPANDAN AI has received." />
      {complaints.status === 'loading' && <LoadingState label="Loading complaints…" />}
      {complaints.status === 'error' && <ErrorState error={complaints.error} onRetry={complaints.reload} />}
      {complaints.status === 'success' &&
        (complaints.data.items.length === 0 ? (
          <EmptyState title="No complaints yet" />
        ) : (
          <ul className="space-y-3">
            {complaints.data.items.map((c) => (
              <li key={c.id}>
                <Link
                  to={`/complaints/${c.id}`}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white p-4 shadow-sm hover:ring-2 hover:ring-blue-200"
                >
                  <span>
                    <span className="block font-semibold">{c.issue ?? 'Awaiting understanding'}</span>
                    <span className="text-sm text-slate-500">
                      {c.tracking_id ?? 'Not filed yet'} · {new Date(c.created_at).toLocaleString()}
                    </span>
                  </span>
                  <StatusBadge status={c.status} />
                </Link>
              </li>
            ))}
          </ul>
        ))}
    </>
  )
}
