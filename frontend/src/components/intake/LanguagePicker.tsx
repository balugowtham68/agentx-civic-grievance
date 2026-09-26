import type { Translator } from '../../i18n/strings'
import type { LanguageInfo } from '../../types/api'

interface Props {
  languages: LanguageInfo[]
  value: string
  onChange: (code: string) => void
  t: Translator
  disabled?: boolean
}

export function LanguagePicker({ languages, value, onChange, t, disabled }: Props) {
  const selected = languages.find((lang) => lang.code === value)
  return (
    <div>
      <label htmlFor="intake-language" className="block font-semibold">
        {t('languageLabel')}
      </label>
      <select
        id="intake-language"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3 sm:w-72"
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.native_name === lang.display_name ? lang.display_name : `${lang.native_name} — ${lang.display_name}`}
          </option>
        ))}
      </select>
      {selected && selected.ui === 'FALLBACK' && <p className="mt-1 text-sm text-slate-600">{t('uiFallbackNote')}</p>}
    </div>
  )
}
