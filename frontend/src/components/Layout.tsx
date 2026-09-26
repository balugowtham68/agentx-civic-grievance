import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Report a problem', end: true },
  { to: '/complaints', label: 'Complaints', end: false },
  { to: '/authority', label: 'Authority', end: false },
]

/** Honesty requirement: every screen states that this is a prototype with a mock government API. */
export function SimulationBanner() {
  return (
    <div role="note" className="bg-amber-100 px-4 py-2 text-center text-sm font-medium text-amber-950">
      Prototype · Mock government API · Demo data · Simulated time
    </div>
  )
}

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <SimulationBanner />
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <NavLink to="/" className="flex flex-col leading-tight" aria-label="SPANDAN AI home">
            <span className="text-xl font-bold tracking-tight">SPANDAN AI</span>
            <span className="text-sm text-slate-600">Listen. Respond. Resolve.</span>
          </NavLink>
          <nav aria-label="Main">
            <ul className="flex flex-wrap gap-1">
              {NAV.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `inline-flex min-h-12 items-center rounded-lg px-4 font-medium ${isActive ? 'bg-blue-600 text-white' : 'text-slate-700 hover:bg-slate-100'}`
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 px-4 py-4 text-center text-sm text-slate-500">
        SPANDAN AI — Listen. Respond. Resolve. · Build for Billions
      </footer>
    </div>
  )
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      {subtitle && <p className="mt-1 text-slate-600">{subtitle}</p>}
    </div>
  )
}
