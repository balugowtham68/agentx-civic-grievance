import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '../src/App'

const health = { status: 'ok', service: 'AGENT X', version: '0.1.0', environment: 'test', database: 'ok', configuration: {} }
const complaint = {
  id: 'c1',
  tracking_id: null,
  issue: null,
  status: 'CREATED',
  authority_status: 'NONE',
  escalation_state: 'NONE',
  created_at: '2026-01-01T09:00:00Z',
  updated_at: '2026-01-01T09:00:00Z',
  citizen_input: 'వీధి దీపం పనిచేయడం లేదు',
  input_channel: 'text',
  language: 'te',
  location: null,
  duration: null,
  category: null,
  department_id: null,
  jurisdiction_id: null,
  drafted_complaint: null,
  sla_start: null,
  sla_deadline: null,
}
const audit = {
  total: 1,
  items: [
    {
      id: 1,
      complaint_id: 'c1',
      event_type: 'complaint.created',
      actor_type: 'citizen',
      actor_name: 'citizen',
      summary: 'Citizen submitted a grievance',
      payload: {},
      evidence: [],
      occurred_at: '2026-01-01T09:00:00Z',
      sim_time: null,
    },
  ],
}

function mockBackend(routes: Record<string, { body: unknown; status?: number }>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname
    const route = routes[path]
    if (!route) {
      return new Response(JSON.stringify({ error: { code: 'not_found', message: 'Not Found', details: [], request_id: 'r1' } }), { status: 404 })
    }
    return new Response(JSON.stringify(route.body), { status: route.status ?? 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('App', () => {
  it('renders the home page with the simulation banner and backend status', async () => {
    mockBackend({ '/health': { body: health } })
    renderAt('/')

    expect(screen.getByRole('heading', { name: 'Report a civic problem' })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/Mock government API/)
    expect(await screen.findByText(/Server running/)).toBeInTheDocument()
  })

  it('navigates to the complaints list and shows complaints from the API', async () => {
    mockBackend({ '/health': { body: health }, '/api/v1/complaints': { body: { items: [complaint], total: 1 } } })
    renderAt('/')

    await userEvent.click(screen.getByRole('link', { name: 'Complaints' }))

    expect(await screen.findByText('Awaiting understanding')).toBeInTheDocument()
    expect(screen.getByText('Received')).toBeInTheDocument()
  })

  it('shows complaint detail with the citizen text and audit trail', async () => {
    mockBackend({
      '/api/v1/complaints/c1': { body: complaint },
      '/api/v1/complaints/c1/audit': { body: audit },
    })
    renderAt('/complaints/c1')

    expect(await screen.findByText('వీధి దీపం పనిచేయడం లేదు')).toBeInTheDocument()
    expect(screen.getByText('Citizen submitted a grievance')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit trail (1)' })).toBeInTheDocument()
  })

  it('shows a structured error with retry when the API fails', async () => {
    mockBackend({})
    renderAt('/complaints/missing')

    expect(await screen.findByRole('alert')).toHaveTextContent('Not found')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('renders the authority route and a not-found page for unknown routes', () => {
    mockBackend({})
    renderAt('/authority')
    expect(screen.getByRole('heading', { name: 'Authority dashboard' })).toBeInTheDocument()
  })

  it('renders not found for unknown routes', () => {
    mockBackend({})
    renderAt('/nope')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
