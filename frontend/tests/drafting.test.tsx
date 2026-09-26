import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { ComplaintDraft, DraftView } from '../src/types/api'
import { ambiguous, BASE, classified, mockBackend, submitAndConfirm } from './helpers'

const sections = {
  subject: 'Complaint regarding non-functional streetlight',
  summary: 'A streetlight on Main Road has reportedly not been functioning for approximately three days.',
  issue_text: 'Non-functional streetlight. Citizen\'s words: “Street light on Main Road has not been working”.',
  location_text: 'As described by the citizen: “on Main Road”. Matched to Main Road, Ward 7 (demo) (WARD-7) in the prototype jurisdiction configuration.',
  duration_text: 'Approximately three days (citizen\'s words: “for three days”).',
  requested_action: 'Kindly inspect the reported streetlight and take the necessary maintenance action.',
}

const v1: ComplaintDraft = {
  draft_id: 'd1',
  complaint_id: 'c1',
  version: 1,
  origin: 'generated',
  based_on_version: null,
  sections,
  body: 'Subject: Complaint regarding non-functional streetlight\n\nA streetlight on Main Road has reportedly not been functioning for approximately three days.',
  category: 'streetlight',
  category_name: 'Streetlight Maintenance',
  department_id: 'DEPT-ELECTRICAL',
  department_name: 'Electrical Maintenance Department (demo)',
  jurisdiction_id: 'WARD-7',
  jurisdiction_name: 'Ward 7 (demo)',
  location: { citizen_words: 'on Main Road', resolved_place: 'Main Road', jurisdiction_id: 'WARD-7', precision: 'EXACT' },
  duration: 'three days',
  chronology: ['The citizen reports the issue has lasted approximately three days.'],
  supporting_facts: ['Issue in the citizen\'s words: “Street light on Main Road has not been working”', 'Location in the citizen\'s words: “on Main Road”'],
  evidence_references: [],
  source_ids: ['CAT-STREETLIGHT', 'DEPT-ELECTRICAL', 'WARD-7'],
  citizen_statement: 'Street light on Main Road has not been working for three days.',
  citizen_language: 'en',
  draft_language: 'en',
  language_note: null,
  processing_mode: 'OFFLINE_RULE',
  validation_status: 'VALID',
  validation_issues: [],
  review_status: 'PENDING_REVIEW',
  explanation: 'Draft generated from your confirmed complaint details (Phase 2) and the classification result.',
  ai_generated_notice: 'AI-generated draft — please review before filing.',
  generated_at: '2026-01-01T09:00:00Z',
  created_by: 'agent',
  demo_data: true,
}

const summary = (d: ComplaintDraft) => ({
  version: d.version, origin: d.origin, validation_status: d.validation_status, review_status: d.review_status,
  subject: d.sections.subject, generated_at: d.generated_at, created_by: d.created_by,
})
const view1: DraftView = { complaint_id: 'c1', status: 'DRAFTING', current: v1, versions: [summary(v1)] }

const WITH_CLASSIFICATION = { ...BASE, 'POST /api/v1/classification/c1/run': { body: classified } }

async function openDraft() {
  await submitAndConfirm()
  await userEvent.click(await screen.findByRole('button', { name: 'Generate complaint draft' }))
  return screen.findByTestId('draft')
}

describe('Complaint drafting (Phase 4)', () => {
  it('generates the draft from the classified complaint and labels it for review', async () => {
    const calls = mockBackend({ ...WITH_CLASSIFICATION, 'POST /api/v1/drafting/c1/run': { status: 201, body: view1 } })
    const card = await openDraft()

    expect(within(card).getByText('AI-generated draft — please review before filing.')).toBeInTheDocument()
    expect(within(card).getByText('Complaint regarding non-functional streetlight')).toBeInTheDocument()
    expect(within(card).getByText(sections.summary)).toBeInTheDocument()
    expect(within(card).getByText('Streetlight Maintenance')).toBeInTheDocument()
    expect(within(card).getByText('Electrical Maintenance Department (demo)')).toBeInTheDocument()
    expect(within(card).getByText('Ward 7 (demo)')).toBeInTheDocument()
    expect(within(card).getByTestId('draft-version')).toHaveTextContent('Version 1')
    expect(within(card).getByTestId('draft-validation')).toHaveTextContent('Checked against your confirmed facts')
    expect(within(card).getByTestId('draft-mode')).toHaveTextContent('offline templates (no external AI)')
    expect(calls.some((c) => c.path === '/api/v1/drafting/c1/run')).toBe(true)
  })

  it('never offers filing, tracking or later-phase actions', async () => {
    mockBackend({ ...WITH_CLASSIFICATION, 'POST /api/v1/drafting/c1/run': { status: 201, body: view1 } })
    const card = await openDraft()
    expect(screen.queryByRole('button', { name: /file|submit|track|escalat/i })).not.toBeInTheDocument()
    expect(card.textContent).not.toMatch(/tracking id|CIV-\d|SLA|escalat|deadline/i)
    expect(within(card).getByText('Nothing is submitted to any government office in this step.')).toBeInTheDocument()
  })

  it('shows a loading state while drafting', async () => {
    mockBackend(WITH_CLASSIFICATION)
    const backend = globalThis.fetch
    let release: (value: Response) => void = () => {}
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
      new URL(String(input)).pathname === '/api/v1/drafting/c1/run'
        ? new Promise<Response>((resolve) => { release = resolve })
        : backend(input, init),
    ))
    await submitAndConfirm()
    await userEvent.click(await screen.findByRole('button', { name: 'Generate complaint draft' }))

    expect(await screen.findByText('Preparing your complaint draft…')).toBeInTheDocument()
    await act(async () => release(new Response(JSON.stringify(view1), { status: 201 })))
    expect(await screen.findByTestId('draft')).toBeInTheDocument()
  })

  it('lets the citizen edit the wording, saving a new version', async () => {
    const v2: ComplaintDraft = {
      ...v1, draft_id: 'd2', version: 2, origin: 'citizen_edit', based_on_version: 1, created_by: 'citizen',
      sections: { ...sections, subject: 'Streetlight not working on Main Road' },
    }
    const calls = mockBackend({
      ...WITH_CLASSIFICATION,
      'POST /api/v1/drafting/c1/run': { status: 201, body: view1 },
      'POST /api/v1/drafting/c1/edit': { body: { ...view1, current: v2, versions: [summary(v1), summary(v2)] } },
    })
    const card = await openDraft()

    await userEvent.click(within(card).getByRole('button', { name: 'Edit wording' }))
    const subject = within(card).getByLabelText('Subject')
    await userEvent.clear(subject)
    await userEvent.type(subject, 'Streetlight not working on Main Road')
    await userEvent.click(within(card).getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText('Streetlight not working on Main Road')).toBeInTheDocument()
    expect(screen.getByTestId('draft-version')).toHaveTextContent('Version 2 (edited by you) · 2 total')
    expect(screen.getByTestId('version-history')).toHaveTextContent('Version 1 · generated')
    const request = calls.find((c) => c.path === '/api/v1/drafting/c1/edit')!
    expect(JSON.parse(String(request.init.body))).toEqual({ based_on_version: 1, subject: 'Streetlight not working on Main Road' })
  })

  it('shows when an edit adds unconfirmed details', async () => {
    const flagged: ComplaintDraft = {
      ...v1, version: 2, origin: 'citizen_edit', validation_status: 'NEEDS_REVIEW',
      citizen_added_information: ["resolution: 'was repaired'", 'new wording not in the confirmed complaint: previously'],
    }
    mockBackend({ ...WITH_CLASSIFICATION, 'POST /api/v1/drafting/c1/run': { status: 201, body: { ...view1, current: flagged } } })
    const card = await openDraft()
    expect(within(card).getByTestId('draft-validation')).toHaveTextContent('adds details that were not in your confirmed complaint')
    const added = within(card).getByTestId('citizen-added')
    expect(added).toHaveTextContent('Added by you — not verified by SPANDAN AI')
    expect(added).toHaveTextContent("resolution: 'was repaired'")
  })

  it('approves the draft without filing it', async () => {
    const calls = mockBackend({
      ...WITH_CLASSIFICATION,
      'POST /api/v1/drafting/c1/run': { status: 201, body: view1 },
      'POST /api/v1/drafting/c1/approve': { body: { ...view1, status: 'DRAFTED', current: { ...v1, review_status: 'APPROVED' } } },
    })
    const card = await openDraft()
    await userEvent.click(within(card).getByRole('button', { name: 'Approve draft' }))

    expect(await screen.findByText('Draft approved and ready for filing. Filing is a later phase and has not happened yet.')).toBeInTheDocument()
    expect(screen.queryByText(/complaint filed|government notified|tracking id generated|officer assigned|SLA started|escalated/i)).not.toBeInTheDocument()
    const request = calls.find((c) => c.path === '/api/v1/drafting/c1/approve')!
    expect(JSON.parse(String(request.init.body))).toEqual({ version: 1 })
    expect(screen.queryByRole('button', { name: 'Approve draft' })).not.toBeInTheDocument()
  })

  it('shows a controlled error when a draft is not available', async () => {
    mockBackend({
      ...WITH_CLASSIFICATION,
      'POST /api/v1/drafting/c1/run': {
        status: 409,
        body: { error: { code: 'complaint_not_classified', message: 'Draft unavailable. Reason: required classification/location information is incomplete.', details: [], request_id: 'r2' } },
      },
    })
    await submitAndConfirm()
    await userEvent.click(await screen.findByRole('button', { name: 'Generate complaint draft' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Draft unavailable')
    expect(screen.queryByTestId('draft')).not.toBeInTheDocument()
  })

  it('does not offer drafting before classification succeeds', async () => {
    mockBackend({ ...BASE, 'POST /api/v1/classification/c1/run': { body: ambiguous } })
    await submitAndConfirm()
    await screen.findByTestId('classification')
    expect(screen.queryByRole('button', { name: 'Generate complaint draft' })).not.toBeInTheDocument()
  })

  it('renders non-English citizen words verbatim', async () => {
    const tamil: ComplaintDraft = {
      ...v1,
      citizen_language: 'ta',
      sections: { ...sections, summary: 'A streetlight at the location described by the citizen as “காந்தி நகரில்” has reportedly not been functioning.' },
      supporting_facts: ['Issue in the citizen\'s words: “தெரு விளக்கு மூன்று நாட்களாக எரியவில்லை”'],
      language_note: 'The citizen wrote in Tamil. The draft is in English and quotes the citizen\'s own words; no machine translation was generated.',
    }
    mockBackend({ ...WITH_CLASSIFICATION, 'POST /api/v1/drafting/c1/run': { status: 201, body: { ...view1, current: tamil } } })
    const card = await openDraft()
    expect(within(card).getByText(/“காந்தி நகரில்”/)).toBeInTheDocument()
    expect(within(card).getByText(/தெரு விளக்கு மூன்று நாட்களாக எரியவில்லை/)).toBeInTheDocument()
    await waitFor(() => expect(within(card).getByText(/no machine translation was generated/)).toBeInTheDocument())
  })
})
