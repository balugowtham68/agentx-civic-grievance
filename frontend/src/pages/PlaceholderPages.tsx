import { Link } from 'react-router-dom'
import { PageHeader } from '../components/Layout'

/** Authority dashboard: escalation queue and officer actions arrive in Phases 8-9. */
export function AuthorityPage() {
  return (
    <>
      <PageHeader title="Authority dashboard" subtitle="For ward officers and departments." />
      <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-slate-600">
        Escalation queue and officer actions (acknowledge, in progress, resolve, close) will appear here.
      </p>
    </>
  )
}

export function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" />
      <Link to="/" className="font-semibold text-blue-700 underline">
        Go to the start page
      </Link>
    </>
  )
}
