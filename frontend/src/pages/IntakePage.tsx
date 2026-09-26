import { useCallback, useState, type FormEvent } from 'react'
import { ErrorState } from '../components/AsyncStates'
import { PageHeader } from '../components/Layout'
import { ClassificationCard } from '../components/classification/ClassificationCard'
import { DraftCard } from '../components/drafting/DraftCard'
import { LanguagePicker } from '../components/intake/LanguagePicker'
import { UnderstoodCard } from '../components/intake/UnderstoodCard'
import { useApi } from '../hooks/useApi'
import { useVoiceInput } from '../hooks/useVoiceInput'
import { DEFAULT_LANGUAGES } from '../i18n/languages'
import { translatorFor } from '../i18n/strings'
import { spandanApi } from '../services/spandanApi'
import { ApiError } from '../services/apiClient'
import type { ClassificationResult, DraftView, InputChannel, IntakeCorrectionRequest, IntakeResult } from '../types/api'

/**
 * Citizen intake (Phase 2): say or type the problem once, check "What I understood",
 * correct, confirm. Then classification (Phase 3) runs on the confirmed facts and shows
 * how SPANDAN AI classified it, why, and from which sources.
 */
export function IntakePage() {
  const capabilities = useApi((signal) => spandanApi.intakeCapabilities(signal), 'intake-capabilities')
  const languages = capabilities.status === 'success' ? capabilities.data.languages : DEFAULT_LANGUAGES
  const serverSpeechToText = capabilities.status === 'success' && capabilities.data.server_speech_to_text_available

  const [language, setLanguage] = useState('en')
  const [text, setText] = useState('')
  const [channel, setChannel] = useState<InputChannel>('text')
  const [result, setResult] = useState<IntakeResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [classification, setClassification] = useState<ClassificationResult | null>(null)
  const [draftView, setDraftView] = useState<DraftView | null>(null)
  const [failedStage, setFailedStage] = useState<'submitting' | 'classifying' | 'drafting' | null>(null)
  const [busyLabel, setBusyLabel] = useState<'submitting' | 'classifying' | 'drafting'>('submitting')
  const t = translatorFor(language)
  const locale = languages.find((lang) => lang.code === language)?.speech_locale ?? 'en-IN'

  const guarded = useCallback(async (label: 'submitting' | 'classifying' | 'drafting', work: () => Promise<void>) => {
    setBusy(true)
    setBusyLabel(label)
    setError(null)
    setFailedStage(null)
    try {
      await work()
    } catch (caught) {
      setFailedStage(label)
      setError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown_error', 'Something went wrong'))
    } finally {
      setBusy(false)
    }
  }, [])

  const run = useCallback(
    (action: () => Promise<IntakeResult>) => guarded('submitting', async () => setResult(await action())),
    [guarded],
  )

  const classify = useCallback(
    (action: () => Promise<ClassificationResult>) => guarded('classifying', async () => setClassification(await action())),
    [guarded],
  )

  const drafting = useCallback(
    (action: () => Promise<DraftView>) => guarded('drafting', async () => setDraftView(await action())),
    [guarded],
  )

  /** Confirm "What I understood", then classify the confirmed facts (Phase 3). */
  const confirmAndClassify = useCallback(
    (complaintId: string) =>
      guarded('submitting', async () => {
        const confirmed = await spandanApi.confirmIntake(complaintId)
        setResult(confirmed)
        if (confirmed.citizen_confirmation_status === 'CONFIRMED') {
          setBusyLabel('classifying')
          setClassification(await spandanApi.runClassification(complaintId))
        }
      }),
    [guarded],
  )

  const onTranscript = useCallback((spoken: string) => {
    setText((current) => (current ? `${current} ${spoken}` : spoken))
    setChannel('voice')
  }, [])
  const onAudio = useCallback(
    (audio: Blob) => void run(() => spandanApi.submitVoiceIntake(audio, language)),
    [run, language],
  )
  const voice = useVoiceInput({ locale, serverSpeechToText, onTranscript, onAudio })

  function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim().length < 3) return
    void run(() => spandanApi.submitTextIntake({ raw_text: text.trim(), language, input_channel: channel }))
  }

  function startOver() {
    setResult(null)
    setText('')
    setChannel('text')
    setError(null)
    setClassification(null)
    setDraftView(null)
  }

  const id = result?.complaint_id ?? ''
  return (
    <>
      <PageHeader title={t('title')} subtitle={t('subtitle')} />

      {!result && (
        <form onSubmit={submit} className="space-y-5 rounded-lg bg-white p-6 shadow-sm">
          <LanguagePicker languages={languages} value={language} onChange={setLanguage} t={t} disabled={busy} />
          <div>
            <label htmlFor="complaint-text" className="block font-semibold">
              {t('complaintLabel')}
            </label>
            <textarea
              id="complaint-text"
              value={text}
              lang={language}
              rows={4}
              maxLength={2000}
              disabled={busy}
              placeholder={t('complaintPlaceholder')}
              onChange={(event) => setText(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 p-3"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {voice.mode === 'none' ? (
              <p className="text-slate-600">{t('voiceUnavailable')}</p>
            ) : voice.active ? (
              <>
                <button type="button" onClick={voice.stop} className="min-h-12 rounded-lg bg-red-600 px-6 font-semibold text-white">
                  {t('stop')}
                </button>
                <span role="status" className="text-slate-700">
                  {voice.mode === 'browser' ? t('listening') : t('recording')}
                </span>
              </>
            ) : (
              <button type="button" onClick={() => void voice.start()} disabled={busy} className="min-h-12 rounded-lg border-2 border-blue-600 px-6 font-semibold text-blue-700 disabled:opacity-50">
                {voice.mode === 'browser' ? t('speak') : t('record')}
              </button>
            )}
            <button type="submit" disabled={busy || text.trim().length < 3} className="min-h-12 rounded-lg bg-blue-600 px-8 font-semibold text-white disabled:opacity-50">
              {t('submit')}
            </button>
          </div>
          {voice.failed && <p role="alert" className="text-red-800">{t('voiceError')}</p>}
        </form>
      )}

      {busy && (
        <p role="status" aria-live="polite" className="mt-4 flex items-center gap-3 rounded-lg bg-white p-4 shadow-sm">
          <span className="size-5 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" aria-hidden="true" />
          {t(busyLabel)}
        </p>
      )}

      {error && (
        <div className="mt-4">
          <ErrorState
            error={error}
            onRetry={
              failedStage === 'drafting' && !draftView
                ? () => void drafting(() => spandanApi.runDrafting(id))
                : failedStage === 'classifying' || (failedStage === 'submitting' && result?.citizen_confirmation_status === 'CONFIRMED')
                  ? () => void classify(() => (classification ? spandanApi.retryClassification(id) : spandanApi.runClassification(id)))
                  : undefined
            }
          />
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {result.intake_status === 'NEEDS_LANGUAGE' && (
            <div className="rounded-lg bg-white p-6 shadow-sm">
              <LanguagePicker languages={languages} value={language} onChange={setLanguage} t={t} disabled={busy} />
            </div>
          )}
          <UnderstoodCard
            result={result}
            languages={languages}
            t={t}
            busy={busy}
            onAnswer={(answer) => void run(() => spandanApi.answerClarification(id, answer))}
            onCorrect={(body: IntakeCorrectionRequest) => void run(() => spandanApi.correctIntake(id, body))}
            onConfirm={() => void confirmAndClassify(id)}
            onRetry={() => void run(() => spandanApi.retryIntake(id, language))}
          />
          {classification && (
            <ClassificationCard
              result={classification}
              t={t}
              busy={busy}
              onAnswer={(answer) => void classify(() => spandanApi.answerClassification(id, answer))}
              onRetry={() => void classify(() => spandanApi.retryClassification(id))}
            />
          )}
          {classification?.classification_status === 'CLASSIFIED' && !draftView && (
            <button
              type="button"
              onClick={() => void drafting(() => spandanApi.runDrafting(id))}
              disabled={busy}
              className="min-h-12 rounded-lg bg-blue-600 px-6 font-semibold text-white disabled:opacity-50"
            >
              {t('generateDraft')}
            </button>
          )}
          {draftView && (
            <DraftCard
              view={draftView}
              t={t}
              busy={busy}
              onEdit={(body) => void drafting(() => spandanApi.editDraft(id, body))}
              onApprove={(version) => void drafting(() => spandanApi.approveDraft(id, version))}
            />
          )}
          <button type="button" onClick={startOver} className="min-h-12 rounded-lg border border-slate-300 bg-white px-6 font-semibold">
            {t('newComplaint')}
          </button>
        </div>
      )}
    </>
  )
}
