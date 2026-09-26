import type { LanguageInfo } from '../types/api'

/** Offline default (mirrors backend/config/languages.json) so the citizen can still choose a language if capabilities fail to load. */
export const DEFAULT_LANGUAGES: LanguageInfo[] = [
  ['en', 'English', 'English', 'en-IN'],
  ['ta', 'Tamil', 'தமிழ்', 'ta-IN'],
  ['te', 'Telugu', 'తెలుగు', 'te-IN'],
  ['hi', 'Hindi', 'हिन्दी', 'hi-IN'],
  ['kn', 'Kannada', 'ಕನ್ನಡ', 'kn-IN'],
  ['ml', 'Malayalam', 'മലയാളം', 'ml-IN'],
].map(([code, display_name, native_name, speech_locale]) => ({
  code,
  display_name,
  native_name,
  speech_locale,
  text_intake: code === 'en' ? 'SUPPORTED' : 'PARTIALLY_SUPPORTED',
  speech_to_text: 'PARTIALLY_SUPPORTED',
  translation: code === 'en' ? 'SUPPORTED' : 'FALLBACK',
  ui: code === 'en' ? 'SUPPORTED' : ['ta', 'te', 'hi'].includes(code) ? 'PARTIALLY_SUPPORTED' : 'FALLBACK',
  notes: '',
}))
