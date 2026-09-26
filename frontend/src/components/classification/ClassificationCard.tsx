import { useState, type FormEvent } from 'react'
import type { Translator } from '../../i18n/strings'
import type { ClassificationResult } from '../../types/api'

interface Props {
  result: ClassificationResult
  t: Translator
  busy: boolean
  onAnswer: (text: string) => void
  onRetry: () => void
}

/** Every source id the decision relied on (KB records and the rules that matched). */
function sourceIds(result: ClassificationResult): string[] {
  const ids = new Set<string>()
  result.evidence.filter((e) => e.kind === 'knowledge').forEach((e) => ids.add(e.source))
  result.rule_matches.forEach((m) => ids.add(m.rule_id))
  if (result.responsible_department) ids.add(result.responsible_department.department_id)
  return [...ids].sort()
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-slate-100 py-3 last:border-0">
      <dt className="text-sm font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-lg">{children}</dd>
    </div>
  )
}

function AnswerForm({ result, t, busy, onAnswer }: Omit<Props, 'onRetry'>) {
  const [answer, setAnswer] = useState('')
  const options =
    result.classification_status === 'AMBIGUOUS'
      ? result.candidates.filter((c) => c.decision === 'ambiguous' || c.decision === 'suggested')
      : []

  function submit(event: FormEvent) {
    event.preventDefault()
    if (answer.trim()) {
      onAnswer(answer.trim())
      setAnswer('')
    }
  }

  return (
    <form onSubmit={submit} className="mt-3" aria-label={t('sendAnswer')}>
      {options.length > 0 && (
        <fieldset>
          <legend className="font-semibold">{t('chooseOne')}</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {options.map((option) => (
              <button
                key={option.category}
                type="button"
                disabled={busy}
                onClick={() => onAnswer(option.display_name)}
                className="min-h-12 rounded-lg border-2 border-blue-600 bg-white px-4 font-semibold text-blue-700 disabled:opacity-50"
              >
                {option.display_name}
              </button>
            ))}
          </div>
        </fieldset>
      )}
      <label htmlFor="classification-answer" className="mt-3 block font-semibold">
        {options.length > 0 ? t('orType') : t('answerLabel')}
      </label>
      <input
        id="classification-answer"
        value={answer}
        maxLength={1000}
        onChange={(event) => setAnswer(event.target.value)}
        className="mt-1 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3"
      />
      <button type="submit" disabled={busy || !answer.trim()} className="mt-3 min-h-12 rounded-lg bg-blue-600 px-6 font-semibold text-white disabled:opacity-50">
        {t('sendAnswer')}
      </button>
    </form>
  )
}

/**
 * Phase 3 view: how SPANDAN AI classified the confirmed complaint, why (citizen evidence +
 * configured civic knowledge), and the sources. Never shows confidence percentages,
 * similarity scores, prompts or embeddings.
 */
export function ClassificationCard({ result, t, busy, onAnswer, onRetry }: Props) {
  const status = result.classification_status
  const question = result.clarification_questions[0]
  const citizen = result.evidence.filter((e) => e.kind === 'citizen' && e.field !== 'issue')
  const knowledge = result.evidence.filter((e) => e.kind === 'knowledge' && e.field !== 'guideline')
  const usedAi = result.processing_mode === 'MIXED' || result.processing_mode === 'OPTIONAL_AI'
  const jurisdiction = result.jurisdiction
  const title =
    status === 'CLASSIFIED' ? t('classifiedTitle')
    : status === 'AMBIGUOUS' ? t('needClarification')
    : status === 'NEEDS_INFO' ? t('stillNeed')
    : t('unsupportedTitle')

  return (
    <section aria-labelledby="classification-heading" className="rounded-lg bg-white p-6 shadow-sm" data-testid="classification">
      <h2 id="classification-heading" className="text-2xl font-bold">
        {title}
      </h2>
      {result.demo_data && (
        <p role="note" className="mt-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          {t('demoLabel')}
        </p>
      )}

      {status === 'CLASSIFIED' && (
        <dl className="mt-4">
          <Row label={t('category')}>{result.category_name}</Row>
          <Row label={t('department')}>{result.responsible_department?.name}</Row>
          <Row label={t('jurisdiction')}>
            {jurisdiction.name ?? t('jurisdictionUnknown')}
            {jurisdiction.matched_words && (
              <span className="mt-1 block text-sm text-slate-600">
                {t('youSaid')}: “{jurisdiction.matched_words}”
              </span>
            )}
          </Row>
        </dl>
      )}

      {status !== 'CLASSIFIED' && result.category_name && (
        <p className="mt-4 text-slate-700">
          <span className="font-semibold">{t('looksLike')}:</span> {result.category_name}{' '}
          <span className="text-sm text-slate-500">({t('proposedNote')})</span>
        </p>
      )}

      {question && status !== 'CLASSIFIED' && (
        <div className="mt-4 rounded-lg border-2 border-blue-200 bg-blue-50 p-4">
          <p className="font-semibold text-blue-900" lang={question.language}>
            {question.text}
          </p>
          <AnswerForm result={result} t={t} busy={busy} onAnswer={onAnswer} />
        </div>
      )}

      <div className="mt-6">
        <h3 className="font-semibold">{t('why')}</h3>
        <ul className="mt-2 list-disc space-y-1 pl-6 text-slate-700">
          {citizen.map((item) => (
            <li key={`c-${item.field}-${item.text}`}>
              {item.source === 'citizen_statement' ? t('youSaid') : t('youToldUs')}: “{item.text}”
            </li>
          ))}
          {knowledge.map((item) => (
            <li key={`k-${item.field}-${item.source}`}>
              {t('configuredRule')}: {item.text} ({item.source})
            </li>
          ))}
        </ul>
        <p className="mt-3 text-slate-700">{result.explanation}</p>
      </div>

      <div className="mt-4">
        <h3 className="font-semibold">{t('sources')}</h3>
        <ul className="mt-2 flex flex-wrap gap-2" aria-label={t('sources')}>
          {sourceIds(result).map((id) => (
            <li key={id} className="rounded-full bg-slate-100 px-3 py-1 font-mono text-sm">
              {id}
            </li>
          ))}
        </ul>
      </div>

      <p role="note" data-testid="classification-mode" className="mt-4 text-sm text-slate-600">
        <span className="font-semibold">{t('processing')}:</span>{' '}
        {usedAi ? t('classificationProcessingAi') : t('classificationProcessing')}
      </p>

      {status === 'UNSUPPORTED_CLASSIFICATION' && !question && (
        <button type="button" onClick={onRetry} disabled={busy} className="mt-4 min-h-12 rounded-lg border-2 border-slate-300 px-6 font-semibold disabled:opacity-50">
          {t('retryClassification')}
        </button>
      )}
    </section>
  )
}
