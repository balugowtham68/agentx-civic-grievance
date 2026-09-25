import type { ComplaintStatus } from '../types/api'

const TONE: Record<ComplaintStatus, string> = {
  CREATED: 'bg-slate-100 text-slate-800',
  NEEDS_INFO: 'bg-amber-100 text-amber-900',
  UNDERSTOOD: 'bg-slate-100 text-slate-800',
  CLASSIFIED: 'bg-slate-100 text-slate-800',
  NEEDS_REVIEW: 'bg-amber-100 text-amber-900',
  DRAFTED: 'bg-slate-100 text-slate-800',
  FILED: 'bg-blue-100 text-blue-900',
  FILING_FAILED: 'bg-red-100 text-red-900',
  MONITORING: 'bg-blue-100 text-blue-900',
  WARNING: 'bg-amber-100 text-amber-900',
  BREACHED: 'bg-red-100 text-red-900',
  ESCALATED: 'bg-purple-100 text-purple-900',
  RESOLVED: 'bg-green-100 text-green-900',
  CLOSED: 'bg-green-100 text-green-900',
}

const LABEL: Record<ComplaintStatus, string> = {
  CREATED: 'Received',
  NEEDS_INFO: 'Needs more information',
  UNDERSTOOD: 'Understood',
  CLASSIFIED: 'Classified',
  NEEDS_REVIEW: 'Needs review',
  DRAFTED: 'Draft ready',
  FILED: 'Filed',
  FILING_FAILED: 'Filing failed',
  MONITORING: 'Being monitored',
  WARNING: 'Deadline approaching',
  BREACHED: 'Deadline missed',
  ESCALATED: 'Escalated',
  RESOLVED: 'Resolved',
  CLOSED: 'Closed',
}

/** Status is always shown as text plus colour, never colour alone. */
export function StatusBadge({ status }: { status: ComplaintStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${TONE[status]}`}>
      {LABEL[status]}
    </span>
  )
}
