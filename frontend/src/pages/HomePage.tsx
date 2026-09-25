import { PageHeader } from '../components/Layout'
import { useApi } from '../hooks/useApi'
import { agentXApi } from '../services/agentxApi'

const LIFECYCLE = ['Understand', 'Classify', 'Draft', 'File', 'Monitor', 'Decide', 'Escalate', 'Explain']

function BackendStatus() {
  const health = useApi((signal) => agentXApi.health(signal), 'health')
  if (health.status === 'loading') return <p className="text-slate-500">Checking server…</p>
  if (health.status === 'error') return <p className="font-medium text-red-700">Server unreachable: {health.error.message}</p>
  return (
    <p className="font-medium text-green-800">
      Server {health.data.status === 'ok' ? 'running' : 'degraded'} · database {health.data.database}
    </p>
  )
}

/** Citizen entry point. The voice/text intake flow is built here in Phase 2. */
export function HomePage() {
  return (
    <>
      <PageHeader title="Report a civic problem" subtitle="Tell us once, in your language. AGENT X follows up for you." />
      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">How it works</h2>
        <ol className="mt-4 flex flex-wrap gap-2" aria-label="Lifecycle">
          {LIFECYCLE.map((step, index) => (
            <li key={step} className="rounded-full bg-slate-100 px-4 py-1 font-medium">
              {index + 1}. {step}
            </li>
          ))}
        </ol>
        <p className="mt-6 rounded-lg border border-dashed border-slate-300 p-4 text-slate-600">
          Voice and text complaint intake will appear here (Phase 2).
        </p>
      </section>
      <section className="mt-6 rounded-lg bg-white p-4 shadow-sm" aria-label="Server status">
        <BackendStatus />
      </section>
    </>
  )
}
