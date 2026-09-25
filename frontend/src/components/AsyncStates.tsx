import type { ReactNode } from 'react'
import type { ApiError } from '../services/apiClient'

/** Shared state components so every screen shows loading, errors and emptiness the same way. */

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 rounded-lg bg-white p-6 text-slate-600 shadow-sm">
      <span className="size-5 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" aria-hidden="true" />
      {label}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-900">
      <p className="font-semibold">{error.status === 404 ? 'Not found' : 'Something went wrong'}</p>
      <p className="mt-1">{error.message}</p>
      {error.requestId && <p className="mt-2 text-sm text-red-700">Reference: {error.requestId}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-4 min-h-12 rounded-lg bg-red-700 px-5 font-semibold text-white hover:bg-red-800">
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
      <p className="font-semibold text-slate-800">{title}</p>
      {children && <div className="mt-2">{children}</div>}
    </div>
  )
}
