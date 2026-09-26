import { useState, type FormEvent } from 'react'
import type { Translator, UIKey } from '../../i18n/strings'
import type { DraftEditRequest, DraftSections, DraftValidationStatus, DraftView } from '../../types/api'

interface Props {
  view: DraftView
  t: Translator
  busy: boolean
  onEdit: (body: DraftEditRequest) => void
  onApprove: (version: number) => void
}

const FIELDS: { key: keyof DraftSections; label: UIKey; multiline: boolean }[] = [
  { key: 'subject', label: 'draftSubject', multiline: false },
  { key: 'summary', label: 'draftSummary', multiline: true },
  { key: 'issue_text', label: 'draftIssue', multiline: true },
  { key: 'location_text', label: 'draftLocation', multiline: true },
  { key: 'duration_text', label: 'draftDuration', multiline: false },
  { key: 'requested_action', label: 'draftAction', multiline: true },
]

const VALIDATION_TEXT: Record<DraftValidationStatus, UIKey> = {
  VALID: 'validValid',
  FALLBACK_USED: 'validFallback',
  NEEDS_REVIEW: 'validNeedsReview',
  INVALID: 'validNeedsReview',
}

function EditForm({ view, t, busy, onSave, onCancel }: { view: DraftView; t: Translator; busy: boolean; onSave: (b: DraftEditRequest) => void; onCancel: () => void }) {
  const [values, setValues] = useState<DraftSections>(view.current.sections)

  function submit(event: FormEvent) {
    event.preventDefault()
    const changes: Partial<DraftSections> = {}
    for (const { key } of FIELDS) {
      if (values[key].trim() !== view.current.sections[key]) changes[key] = values[key].trim()
    }
    if (Object.keys(changes).length === 0) onCancel()
    else onSave({ based_on_version: view.current.version, ...changes })
  }

  return (
    <form onSubmit={submit} className="mt-4 space-y-4" aria-label={t('editDraft')}>
      {FIELDS.map(({ key, label, multiline }) => (
        <div key={key}>
          <label htmlFor={`draft-${key}`} className="block font-semibold">
            {t(label)}
          </label>
          {multiline ? (
            <textarea
              id={`draft-${key}`}
              value={values[key]}
              rows={3}
              maxLength={1500}
              onChange={(event) => setValues({ ...values, [key]: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 p-3"
            />
          ) : (
            <input
              id={`draft-${key}`}
              value={values[key]}
              maxLength={key === 'subject' ? 200 : 1500}
              onChange={(event) => setValues({ ...values, [key]: event.target.value })}
              className="mt-1 min-h-12 w-full rounded-lg border border-slate-300 px-3"
            />
          )}
        </div>
      ))}
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={busy} className="min-h-12 rounded-lg bg-blue-600 px-6 font-semibold text-white disabled:opacity-50">
          {t('saveDraftEdits')}
        </button>
        <button type="button" onClick={onCancel} className="min-h-12 rounded-lg border border-slate-300 px-6 font-semibold">
          {t('cancel')}
        </button>
      </div>
    </form>
  )
}

/**
 * Phase 4 view: the grounded complaint draft for citizen review. Category, department and
 * jurisdiction come from the classification and are not editable. There is no filing action:
 * approval only marks the draft as reviewed (DRAFTED).
 */
export function DraftCard({ view, t, busy, onEdit, onApprove }: Props) {
  const [editing, setEditing] = useState(false)
  const draft = view.current
  const approved = draft.review_status === 'APPROVED'

  return (
    <section aria-labelledby="draft-heading" className="rounded-lg bg-white p-6 shadow-sm" data-testid="draft">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="draft-heading" className="text-2xl font-bold">
          {t('draftTitle')}
        </h2>
        <span className="text-sm text-slate-600" data-testid="draft-version">
          {t('draftVersion')} {draft.version}
          {draft.origin === 'citizen_edit' ? ` (${t('editedByYou')})` : ''} · {view.versions.length} total
        </span>
      </div>
      <p role="note" className="mt-2 rounded-lg bg-amber-50 p-3 font-medium text-amber-900">
        {t('aiNotice')}
      </p>

      <p className="mt-3 text-sm" data-testid="draft-validation">
        <span className="font-semibold">{t('draftValidation')}:</span> {t(VALIDATION_TEXT[draft.validation_status])}
      </p>
      {(draft.citizen_added_information ?? []).length > 0 && (
        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" data-testid="citizen-added">
          <p className="font-semibold">{t('citizenAdded')}</p>
          <ul className="mt-1 list-disc pl-6">
            {(draft.citizen_added_information ?? []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {editing ? (
        <EditForm
          view={view}
          t={t}
          busy={busy}
          onCancel={() => setEditing(false)}
          onSave={(body) => {
            onEdit(body)
            setEditing(false)
          }}
        />
      ) : (
        <>
          <dl className="mt-4 space-y-3">
            {FIELDS.map(({ key, label }) => (
              <div key={key}>
                <dt className="text-sm font-semibold uppercase tracking-wide text-slate-500">{t(label)}</dt>
                <dd className="mt-1">{draft.sections[key]}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-4 rounded-lg bg-slate-50 p-4">
            <p className="text-sm font-semibold text-slate-600">{t('lockedFacts')}</p>
            <dl className="mt-2 grid gap-2 sm:grid-cols-3">
              <div>
                <dt className="text-sm text-slate-500">{t('category')}</dt>
                <dd className="font-medium">{draft.category_name}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">{t('department')}</dt>
                <dd className="font-medium">{draft.department_name}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">{t('jurisdiction')}</dt>
                <dd className="font-medium">{draft.jurisdiction_name ?? t('jurisdictionUnknown')}</dd>
              </div>
            </dl>
          </div>

          <div className="mt-4">
            <p className="font-semibold">{t('yourWords')}</p>
            <ul className="mt-1 list-disc pl-6 text-slate-700">
              {draft.supporting_facts.map((fact) => (
                <li key={fact}>{fact}</li>
              ))}
            </ul>
          </div>

          <details className="mt-4">
            <summary className="cursor-pointer font-semibold">{t('draftBody')}</summary>
            <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 font-sans text-slate-800" data-testid="draft-body">
              {draft.body}
            </pre>
          </details>
        </>
      )}

      {view.versions.length > 1 && (
        <details className="mt-4" data-testid="version-history">
          <summary className="cursor-pointer font-semibold">{t('versionHistory')}</summary>
          <ol className="mt-2 space-y-1 text-sm text-slate-700">
            {view.versions.map((v) => (
              <li key={v.version}>
                {t('draftVersion')} {v.version} · {v.origin === 'citizen_edit' ? t('editedByYou') : t('versionGenerated')}
                {v.review_status === 'APPROVED' ? ` · ${t('versionApproved')}` : ''}
                {v.review_status === 'SUPERSEDED' ? ` · ${t('versionSuperseded')}` : ''} — {v.subject}
              </li>
            ))}
          </ol>
        </details>
      )}

      {draft.language_note && <p className="mt-3 text-sm text-slate-600">{draft.language_note}</p>}
      <p className="mt-3 text-sm text-slate-600">{draft.explanation}</p>
      <p role="note" data-testid="draft-mode" className="mt-2 text-sm text-slate-600">
        <span className="font-semibold">{t('draftWording')}:</span>{' '}
        {draft.processing_mode === 'MIXED' ? t('draftWordingMixed') : t('draftWordingOffline')}
      </p>

      {approved ? (
        <p role="status" className="mt-4 rounded-lg bg-green-50 p-4 font-medium text-green-900">
          {t('draftApproved')}
        </p>
      ) : (
        !editing && (
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={() => setEditing(true)} disabled={busy} className="min-h-12 rounded-lg border-2 border-slate-300 px-6 font-semibold disabled:opacity-50">
              {t('editDraft')}
            </button>
            <button type="button" onClick={() => onApprove(draft.version)} disabled={busy} className="min-h-12 rounded-lg bg-green-700 px-6 font-semibold text-white disabled:opacity-50">
              {t('approveDraft')}
            </button>
          </div>
        )
      )}
      <p className="mt-2 text-sm text-slate-500">{t('noFilingNote')}</p>
    </section>
  )
}
