import { useState, type FormEvent } from 'react'
import type { Translator, UIKey } from '../../i18n/strings'
import type {
  ExtractedFact,
  FieldCorrection,
  IntakeCorrectionRequest,
  IntakeField,
  IntakeResult,
  LanguageInfo,
} from '../../types/api'

const FIELDS: IntakeField[] = ['issue', 'location', 'duration']

const LANGUAGE_SOURCE: Record<IntakeResult['language']['method'], UIKey> = {
  declared: 'langDeclared',
  script: 'langScript',
  heuristic: 'langHeuristic',
  provider: 'langProvider',
  default: 'langDefault',
}

interface Props {
  result: IntakeResult
  languages: LanguageInfo[]
  t: Translator
  busy: boolean
  onAnswer: (text: string) => void
  onCorrect: (body: IntakeCorrectionRequest) => void
  onConfirm: () => void
  onRetry: () => void
}

function FactRow({ label, fact, t }: { label: string; fact: ExtractedFact | null; t: Translator }) {
  return (
    <div className="border-b border-slate-100 py-3 last:border-0">
      <dt className="text-sm font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-lg">
        {fact ? (
          <>
            <span className="font-medium">{fact.value}</span>
            <span className="mt-1 block text-sm text-slate-600">
              {fact.source === 'citizen_correction' ? t('youToldUs') : t('youSaid')}: “{fact.source_span}”
            </span>
            {fact.quality === 'vague' && <span className="mt-1 block text-sm text-amber-800">{t('vagueHint')}</span>}
          </>
        ) : (
          <span className="text-slate-500 italic">{t('notProvided')}</span>
        )}
      </dd>
    </div>
  )
}

function CorrectionForm({ result, t, busy, onSave, onCancel }: {
  result: IntakeResult
  t: Translator
  busy: boolean
  onSave: (corrections: FieldCorrection[]) => void
  onCancel: () => void
}) {
  const [values, setValues] = useState<Record<IntakeField, string>>({
    issue: result.extracted.issue?.value ?? '',
    location: result.extracted.location?.value ?? '',
    duration: result.extracted.duration?.value ?? '',
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    const changed: FieldCorrection[] = FIELDS.filter((field) => values[field].trim() !== (result.extracted[field]?.value ?? '')).map(
      (field) => ({ field, value: values[field].trim() || null }),
    )
    if (changed.length === 0) onCancel()
    else onSave(changed)
  }

  return (
    <form onSubmit={submit} className="space-y-4" aria-label="Correct the details">
      {FIELDS.map((field) => (
        <div key={field}>
          <label htmlFor={`correct-${field}`} className="block font-semibold">
            {t(field as UIKey)}
          </label>
          <input
            id={`correct-${field}`}
            value={values[field]}
            maxLength={300}
            onChange={(event) => setValues({ ...values, [field]: event.target.value })}
            className="mt-1 min-h-12 w-full rounded-lg border border-slate-300 px-3"
          />
        </div>
      ))}
      <p className="text-sm text-slate-600">{t('clearValue')}</p>
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={busy} className="min-h-12 rounded-lg bg-blue-600 px-6 font-semibold text-white disabled:opacity-50">
          {t('saveChanges')}
        </button>
        <button type="button" onClick={onCancel} className="min-h-12 rounded-lg border border-slate-300 px-6 font-semibold">
          {t('cancel')}
        </button>
      </div>
    </form>
  )
}

/** Offline vs online processing, always stated in words (not colour alone). */
function ProcessingIndicator({ result, t }: { result: IntakeResult; t: Translator }) {
  const mode = result.processing_mode
  if (!mode) return null
  const online = mode === 'OPTIONAL_AI' || mode === 'MIXED'
  const text = online ? t('modeAi') : mode === 'OFFLINE_LOCAL_MODEL' ? t('modeLocalModel') : t('modeOffline')
  return (
    <p
      role="note"
      data-testid="processing-mode"
      className={`mt-3 rounded-lg p-3 text-sm ${online ? 'bg-blue-50 text-blue-900' : 'bg-green-50 text-green-900'}`}
    >
      <span className="font-semibold">{t('processing')}:</span> {text}
    </p>
  )
}

function languageName(code: string, languages: LanguageInfo[]): string {
  const info = languages.find((lang) => lang.code === code)
  if (!info) return code
  return info.native_name === info.display_name ? info.display_name : `${info.native_name} (${info.display_name})`
}

function FreeTextCorrection({ t, busy, onSend }: { t: Translator; busy: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim()) {
      onSend(text.trim())
      setText('')
    }
  }
  return (
    <form onSubmit={submit} className="mt-4" aria-label={t('sendCorrection')}>
      <label htmlFor="correction-text" className="block font-semibold">
        {t('correctInWords')}
      </label>
      <div className="mt-1 flex flex-wrap gap-3">
        <input
          id="correction-text"
          value={text}
          maxLength={1000}
          placeholder={t('correctionPlaceholder')}
          onChange={(event) => setText(event.target.value)}
          className="min-h-12 flex-1 rounded-lg border border-slate-300 px-3"
        />
        <button type="submit" disabled={busy || !text.trim()} className="min-h-12 rounded-lg border-2 border-blue-600 px-6 font-semibold text-blue-700 disabled:opacity-50">
          {t('sendCorrection')}
        </button>
      </div>
    </form>
  )
}

export function UnderstoodCard({ result, languages, t, busy, onAnswer, onCorrect, onConfirm, onRetry }: Props) {
  const [editing, setEditing] = useState(false)
  const [answer, setAnswer] = useState('')
  const failed = result.intake_status === 'FAILED' || result.intake_status === 'NEEDS_LANGUAGE'
  const confirmed = result.citizen_confirmation_status === 'CONFIRMED'
  const canContinue = result.intake_status === 'COMPLETED' && !confirmed

  function sendAnswer(event: FormEvent) {
    event.preventDefault()
    if (answer.trim()) {
      onAnswer(answer.trim())
      setAnswer('')
    }
  }

  return (
    <section aria-labelledby="understood-heading" className="rounded-lg bg-white p-6 shadow-sm">
      <h2 id="understood-heading" className="text-2xl font-bold">
        {t('understoodTitle')}
      </h2>

      <p className="mt-2 rounded-lg bg-slate-50 p-3 text-slate-700" lang={result.language.language}>
        <span className="font-semibold">{result.transcript ? t('heardAs') : t('original')}:</span> {result.original_text}
      </p>

      {result.intake_status !== 'NEEDS_LANGUAGE' && (
        <p className="mt-2 text-slate-700" data-testid="language-row">
          <span className="font-semibold">{t('languageRow')}:</span> {languageName(result.language.language, languages)} —{' '}
          {t(LANGUAGE_SOURCE[result.language.method])}
          {result.language.transliterated && `, ${t('romanised')}`}
        </p>
      )}

      <ProcessingIndicator result={result} t={t} />

      {(result.safety_flags ?? []).length > 0 && (
        <p role="note" className="mt-3 rounded-lg bg-amber-50 p-3 text-amber-900">
          {t('safetyNotice')}
        </p>
      )}
      {result.translation.status === 'FAILED' && (
        <p role="note" className="mt-3 rounded-lg bg-amber-50 p-3 text-amber-900">
          {t('translationFailed')}
        </p>
      )}

      {failed && (
        <div role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
          <p className="font-semibold">{t('failedTitle')}</p>
          <p className="mt-1">{result.intake_status === 'NEEDS_LANGUAGE' ? t('needsLanguage') : t('failedBody')}</p>
          <button type="button" onClick={onRetry} disabled={busy} className="mt-3 min-h-12 rounded-lg bg-red-700 px-5 font-semibold text-white disabled:opacity-50">
            {t('retry')}
          </button>
        </div>
      )}

      {editing ? (
        <div className="mt-4">
          <CorrectionForm
            result={result}
            t={t}
            busy={busy}
            onCancel={() => setEditing(false)}
            onSave={(corrections) => {
              onCorrect({ corrections })
              setEditing(false)
            }}
          />
        </div>
      ) : (
        <dl className="mt-4">
          {FIELDS.map((field) => (
            <FactRow key={field} label={t(field as UIKey)} fact={result.extracted[field]} t={t} />
          ))}
          {result.extracted.entities.length > 0 && (
            <div className="py-3">
              <dt className="text-sm font-semibold uppercase tracking-wide text-slate-500">{t('otherDetails')}</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                {result.extracted.entities.map((entity) => (
                  <span key={`${entity.type}-${entity.value}`} className="rounded-full bg-slate-100 px-3 py-1 text-sm">
                    {entity.value}
                  </span>
                ))}
              </dd>
            </div>
          )}
        </dl>
      )}

      {!editing && result.clarification_questions.length > 0 && (
        <form onSubmit={sendAnswer} className="mt-4 rounded-lg border-2 border-blue-200 bg-blue-50 p-4" aria-label={t('needFromYou')}>
          <p className="font-semibold text-blue-900">{t('needFromYou')}</p>
          <ul className="mt-1 list-disc pl-6" lang={result.clarification_questions[0].language}>
            {result.clarification_questions.map((question) => (
              <li key={question.field}>{question.text}</li>
            ))}
          </ul>
          <label htmlFor="clarification-answer" className="mt-3 block font-semibold">
            {t('answerLabel')}
          </label>
          <input
            id="clarification-answer"
            value={answer}
            maxLength={1000}
            onChange={(event) => setAnswer(event.target.value)}
            className="mt-1 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3"
          />
          <button type="submit" disabled={busy || !answer.trim()} className="mt-3 min-h-12 rounded-lg bg-blue-600 px-6 font-semibold text-white disabled:opacity-50">
            {t('sendAnswer')}
          </button>
        </form>
      )}

      {!editing && !confirmed && !failed && (
        <FreeTextCorrection t={t} busy={busy} onSend={(text) => onCorrect({ text })} />
      )}

      {canContinue && !editing && (
        <p role="status" className="mt-6 font-medium text-slate-800">
          {t('awaitingConfirmation')}
        </p>
      )}

      {confirmed ? (
        <div role="status" className="mt-6 rounded-lg bg-green-50 p-4 text-green-900">
          <p className="text-lg font-semibold">{t('confirmedTitle')}</p>
          <p className="mt-1">{t('confirmedBody')}</p>
        </div>
      ) : (
        !editing && (
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={() => setEditing(true)} disabled={busy} className="min-h-12 rounded-lg border-2 border-slate-300 px-6 font-semibold disabled:opacity-50">
              {t('edit')}
            </button>
            <button type="button" onClick={onConfirm} disabled={busy || !canContinue} className="min-h-12 rounded-lg bg-green-700 px-6 font-semibold text-white disabled:opacity-50">
              {t('continue')}
            </button>
          </div>
        )
      )}
    </section>
  )
}
