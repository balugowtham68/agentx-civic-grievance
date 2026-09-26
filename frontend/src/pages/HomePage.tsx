import { useApi } from '../hooks/useApi'
import { spandanApi } from '../services/spandanApi'
import { IntakePage } from './IntakePage'

function BackendStatus() {
  const health = useApi((signal) => spandanApi.health(signal), 'health')
  if (health.status === 'loading') return <p className="text-slate-500">Checking server…</p>
  if (health.status === 'error') return <p className="font-medium text-red-700">Server unreachable: {health.error.message}</p>
  return (
    <p className="font-medium text-green-800">
      Server {health.data.status === 'ok' ? 'running' : 'degraded'} · database {health.data.database}
    </p>
  )
}

/** Citizen entry point: the Phase 2 intake flow, plus a small server status line. */
export function HomePage() {
  return (
    <>
      <IntakePage />
      <section className="mt-8 rounded-lg bg-white p-4 text-sm shadow-sm" aria-label="Server status">
        <BackendStatus />
      </section>
    </>
  )
}
