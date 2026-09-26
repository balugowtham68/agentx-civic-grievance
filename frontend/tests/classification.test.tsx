import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ambiguous, BASE, classified, mockBackend, needsInfo, submitAndConfirm } from './helpers'

describe('Classification (Phase 3)', () => {
  it('classifies right after confirmation and explains why, with sources', async () => {
    const calls = mockBackend({ ...BASE, 'POST /api/v1/classification/c1/run': { body: classified } })
    await submitAndConfirm()

    const card = await screen.findByTestId('classification')
    expect(within(card).getByRole('heading', { name: 'How SPANDAN AI classified it' })).toBeInTheDocument()
    expect(within(card).getByText('Streetlight Maintenance')).toBeInTheDocument()
    expect(within(card).getByText('Electrical Maintenance Department (demo)')).toBeInTheDocument()
    expect(within(card).getByText('Ward 7 (demo)')).toBeInTheDocument()
    expect(within(card).getByText('You said: “street light”')).toBeInTheDocument()
    expect(within(card).getByText(/Configured rule: Streetlight Maintenance \(CAT-STREETLIGHT\)/)).toBeInTheDocument()
    const sources = within(card).getByRole('list', { name: 'Sources' })
    expect(within(sources).getByText('DEPT-ELECTRICAL')).toBeInTheDocument()
    expect(within(sources).getByText('WARD-7')).toBeInTheDocument()
    expect(within(card).getByText(/not official government data/)).toBeInTheDocument()
    expect(within(card).getByTestId('classification-mode')).toHaveTextContent('Classified offline using the local civic knowledge base.')
    expect(card.textContent).not.toMatch(/%|0\.4|similarity|confidence/i)
    const order = calls.map((c) => c.path).filter((p) => p.includes('/c1/'))
    expect(order).toEqual(['/api/v1/intake/c1/confirm', '/api/v1/classification/c1/run'])
  })

  it('asks for missing locality and re-classifies after the answer', async () => {
    const calls = mockBackend({
      ...BASE,
      'POST /api/v1/classification/c1/run': { body: needsInfo },
      'POST /api/v1/classification/c1/answer': { body: { ...classified, category_name: 'Garbage Collection' } },
    })
    await submitAndConfirm()

    const card = await screen.findByTestId('classification')
    expect(within(card).getByRole('heading', { name: 'What we still need' })).toBeInTheDocument()
    expect(within(card).getByText(/Please provide the area, street, ward, or nearby landmark/)).toBeInTheDocument()
    expect(within(card).getByText(/Not final until the missing information is given/)).toBeInTheDocument()

    await userEvent.type(within(card).getByLabelText('Your answer'), 'Gandhi Nagar')
    await userEvent.click(within(card).getByRole('button', { name: 'Send answer' }))

    expect(await screen.findByRole('heading', { name: 'How SPANDAN AI classified it' })).toBeInTheDocument()
    const request = calls.find((c) => c.path === '/api/v1/classification/c1/answer')!
    expect(JSON.parse(String(request.init.body))).toEqual({ text: 'Gandhi Nagar' })
  })

  it('asks the citizen to choose when the complaint is ambiguous', async () => {
    const calls = mockBackend({
      ...BASE,
      'POST /api/v1/classification/c1/run': { body: ambiguous },
      'POST /api/v1/classification/c1/answer': { body: needsInfo },
    })
    await submitAndConfirm()

    const card = await screen.findByTestId('classification')
    expect(within(card).getByRole('heading', { name: 'We need clarification' })).toBeInTheDocument()
    expect(within(card).getByText('Is the issue a water leak, no water supply, or a drainage problem?')).toBeInTheDocument()
    await userEvent.click(within(card).getByRole('button', { name: 'Water Leakage' }))

    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/classification/c1/answer')).toBe(true))
    const request = calls.find((c) => c.path === '/api/v1/classification/c1/answer')!
    expect(JSON.parse(String(request.init.body))).toEqual({ text: 'Water Leakage' })
  })

  it('says honestly when it cannot classify', async () => {
    mockBackend({
      ...BASE,
      'POST /api/v1/classification/c1/run': {
        body: { ...ambiguous, classification_status: 'UNSUPPORTED_CLASSIFICATION', status: 'NEEDS_REVIEW', candidates: [], clarification_questions: [], explanation: 'SPANDAN AI could not match this complaint. Nothing was guessed.' },
      },
    })
    await submitAndConfirm()
    const card = await screen.findByTestId('classification')
    expect(within(card).getByRole('heading', { name: 'We could not classify this' })).toBeInTheDocument()
    expect(within(card).getByText(/Nothing was guessed/)).toBeInTheDocument()
    expect(within(card).getByRole('button', { name: 'Try classification again' })).toBeInTheDocument()
  })

  it('shows a safe error with retry when the knowledge base is unavailable', async () => {
    let attempts = 0
    mockBackend({
      ...BASE,
      'POST /api/v1/classification/c1/run': () => {
        attempts += 1
        return attempts === 1
          ? { status: 503, body: { error: { code: 'knowledge_base_unavailable', message: 'Civic knowledge base is not ready', details: [], request_id: 'r1' } } }
          : { body: classified }
      },
    })
    await submitAndConfirm()

    expect(await screen.findByRole('alert')).toHaveTextContent('Civic knowledge base is not ready')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'How SPANDAN AI classified it' })).toBeInTheDocument()
  })

  it('says when the optional AI was consulted', async () => {
    mockBackend({ ...BASE, 'POST /api/v1/classification/c1/run': { body: { ...classified, processing_mode: 'MIXED' } } })
    await submitAndConfirm()
    expect(await screen.findByTestId('classification-mode')).toHaveTextContent('the optional online AI was consulted and checked')
  })
})
