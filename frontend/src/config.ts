/** Runtime configuration read from VITE_* environment variables (see ../.env.example). */

const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export const config = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '') ||
    DEFAULT_API_BASE_URL,
} as const
