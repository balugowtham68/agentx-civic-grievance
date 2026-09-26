/* Shared fixtures for the Phase 3/4 frontend tests (mocked backend, no network). */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AppRoutes } from '../src/App'
import type { ClassificationResult, IntakeResult } from '../src/types/api'

export const capabilities = {
  processing_language: 'en',
  offline_first: true,
  languages: [
    { code: 'en', display_name: 'English', native_name: 'English', speech_locale: 'en-IN', text_intake: 'SUPPORTED', speech_to_text: 'PARTIALLY_SUPPORTED', translation: 'SUPPORTED', ui: 'SUPPORTED', notes: '' },
  ],
  ai_extraction_available: false,
  rule_based_fallback_available: true,
  server_speech_to_text_available: false,
  max_audio_bytes: 10485760,
  accepted_audio_types: ['audio/webm'],
}

export function fact(value: string, span: string) {
  return { value, source_span: span, source: 'citizen_statement' as const, statement_index: 0, confidence: null, method: 'lexicon' as const, quality: 'clear' as const }
}

export const understood: IntakeResult = {
  complaint_id: 'c1',
  input_channel: 'text',
  status: 'UNDERSTANDING',
  intake_status: 'COMPLETED',
  original_text: 'The street light near Main Road has not been working for three days.',
  transcript: null,
  language: { language: 'en', confidence: null, method: 'declared', transliterated: false, script: null, supported: true },
  original_language: 'en',
  processing_language: 'en',
  translation: { status: 'NOT_REQUIRED', source_language: 'en', target_language: 'en', translated_text: null, provider: null, error: null },
  translated_text: null,
  extracted: {
    issue: fact('street light not working', 'street light near Main Road has not been working'),
    location: fact('near Main Road', 'near Main Road'),
    duration: fact('three days', 'for three days'),
    entities: [],
  },
  rejected_facts: [],
  missing_information: [],
  missing_fields: [],
  clarification_questions: [],
  extraction: { status: 'COMPLETED', method: 'offline_rules', provider: 'offline_rules', fallback_reason: null, error: null },
  confidence: null,
  processing_mode: 'OFFLINE_RULE',
  provider_trace: [],
  safety_flags: [],
  citizen_confirmation_status: 'PENDING',
  evidence: [],
}
export const confirmedIntake: IntakeResult = { ...understood, status: 'UNDERSTOOD', citizen_confirmation_status: 'CONFIRMED' }

export const classified: ClassificationResult = {
  complaint_id: 'c1',
  status: 'CLASSIFIED',
  classification_status: 'CLASSIFIED',
  confidence_state: 'SUPPORTED',
  category: 'streetlight',
  category_record_id: 'CAT-STREETLIGHT',
  category_name: 'Streetlight Maintenance',
  responsible_department: { department_id: 'DEPT-ELECTRICAL', name: 'Electrical Maintenance Department (demo)', source_id: 'SRC-DEMO-DEPARTMENTS', mapping_record_id: 'CAT-STREETLIGHT', label: 'DEMO CIVIC RULE' },
  jurisdiction: { status: 'RESOLVED', jurisdiction_id: 'WARD-7', name: 'Ward 7 (demo)', matched_place: 'Main Road', matched_words: 'Main Road', source_id: 'SRC-DEMO-JURISDICTIONS', location_precision: 'EXACT', note: null },
  required_information: [],
  missing_information: [],
  clarification_questions: [],
  candidates: [{ category: 'streetlight', record_id: 'CAT-STREETLIGHT', display_name: 'Streetlight Maintenance', retrieved: true, best_similarity: 0.4, rule_matched: true, decision: 'selected', reason: 'configured rule matched' }],
  rule_matches: [{ rule_id: 'CAT-STREETLIGHT', rule_type: 'category_pattern', category: 'streetlight', pattern: 'street light', language: 'en', citizen_words: 'street light', source: 'original_text' }],
  retrieved_sources: [],
  evidence: [
    { kind: 'citizen', field: 'issue', text: 'street light near Main Road has not been working', source: 'citizen_statement' },
    { kind: 'citizen', field: 'category', text: 'street light', source: 'citizen_statement' },
    { kind: 'knowledge', field: 'category', text: 'Streetlight Maintenance', source: 'CAT-STREETLIGHT' },
    { kind: 'knowledge', field: 'department', text: 'Electrical Maintenance Department (demo)', source: 'DEPT-ELECTRICAL' },
    { kind: 'knowledge', field: 'jurisdiction', text: 'Ward 7 (demo): Main Road', source: 'WARD-7' },
  ],
  reasoning: [],
  explanation: 'Your complaint was classified as Streetlight Maintenance because you reported “street light”.',
  service_guideline: null,
  service_timeline: null,
  processing_mode: 'OFFLINE_RULE',
  provider_trace: [],
  rejected_ai_output: [],
  safety_flags: [],
  language: 'en',
  answers: [],
  knowledge_base_version: 'abc',
  demo_data: true,
  created_at: null,
  updated_at: null,
}

export const needsInfo: ClassificationResult = {
  ...classified,
  status: 'NEEDS_INFO',
  classification_status: 'NEEDS_INFO',
  category: 'garbage',
  category_name: 'Garbage Collection',
  jurisdiction: { ...classified.jurisdiction, status: 'UNRESOLVED', jurisdiction_id: null, name: null, matched_words: null, location_precision: 'VAGUE' },
  missing_information: ['location_detail', 'jurisdiction'],
  clarification_questions: [{ field: 'locality', text: 'I understood: garbage not collected. Please provide the area, street, ward, or nearby landmark.', language: 'en' }],
  explanation: 'This looks like Garbage Collection.',
}

export const ambiguous: ClassificationResult = {
  ...classified,
  status: 'NEEDS_INFO',
  classification_status: 'AMBIGUOUS',
  confidence_state: 'AMBIGUOUS',
  category: null,
  category_name: null,
  responsible_department: null,
  candidates: [
    { category: 'water_leakage', record_id: 'CAT-WATER-LEAKAGE', display_name: 'Water Leakage', retrieved: true, best_similarity: 0.3, rule_matched: false, decision: 'ambiguous', reason: '' },
    { category: 'water_supply', record_id: 'CAT-WATER-SUPPLY', display_name: 'Water Supply Interruption', retrieved: true, best_similarity: 0.35, rule_matched: false, decision: 'ambiguous', reason: '' },
  ],
  clarification_questions: [{ field: 'category', text: 'Is the issue a water leak, no water supply, or a drainage problem?', language: 'en' }],
  explanation: 'Your description could fit more than one civic category.',
}

export type Route = { status?: number; body: unknown } | (() => { status?: number; body: unknown })

export function mockBackend(routes: Record<string, Route>) {
  const calls: { path: string; init: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const path = new URL(String(input)).pathname
    calls.push({ path, init })
    const route = routes[`${init.method ?? 'GET'} ${path}`]
    if (!route) return new Response(JSON.stringify({ error: { code: 'not_found', message: 'Not Found', details: [], request_id: null } }), { status: 404 })
    const { status = 200, body } = typeof route === 'function' ? route() : route
    return new Response(JSON.stringify(body), { status })
  }))
  return calls
}

export const BASE: Record<string, Route> = {
  'GET /api/v1/intake/capabilities': { body: capabilities },
  'GET /health': { body: { status: 'ok', service: 'SPANDAN AI', version: '0.1.0', environment: 'test', database: 'ok', configuration: {} } },
  'POST /api/v1/intake/text': { status: 201, body: understood },
  'POST /api/v1/intake/c1/confirm': { body: confirmedIntake },
}

export async function submitAndConfirm() {
  render(
    <MemoryRouter initialEntries={['/']}>
      <AppRoutes />
    </MemoryRouter>,
  )
  await userEvent.type(screen.getByLabelText('Describe the problem'), 'The street light near Main Road has not been working')
  await userEvent.click(screen.getByRole('button', { name: 'Submit' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Continue' }))
}

