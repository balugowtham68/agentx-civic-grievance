import { useCallback, useEffect, useEffectEvent, useState } from 'react'
import { ApiError } from '../services/apiClient'

/**
 * Loading/error convention for every data-fetching screen:
 *   status 'loading' -> <LoadingState/>, 'error' -> <ErrorState/>, 'success' -> content.
 *
 * `key` identifies the request: when it changes (e.g. a new complaint id) the data is
 * refetched. Requests are aborted on unmount or key change.
 */
export type AsyncState<T> =
  | { status: 'loading'; data: undefined; error: undefined }
  | { status: 'success'; data: T; error: undefined }
  | { status: 'error'; data: undefined; error: ApiError }

const LOADING = { status: 'loading', data: undefined, error: undefined } as const

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  return new ApiError(0, 'unknown_error', error instanceof Error ? error.message : 'Something went wrong')
}

export function useApi<T>(
  load: (signal: AbortSignal) => Promise<T>,
  key: string,
): AsyncState<T> & { reload: () => void } {
  const [attempt, setAttempt] = useState(0)
  const requestKey = `${key}#${attempt}`
  const [settled, setSettled] = useState<{ key: string; state: AsyncState<T> } | null>(null)
  const runLoad = useEffectEvent((signal: AbortSignal) => load(signal))

  useEffect(() => {
    const controller = new AbortController()
    runLoad(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setSettled({ key: requestKey, state: { status: 'success', data, error: undefined } })
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setSettled({ key: requestKey, state: { status: 'error', data: undefined, error: toApiError(error) } })
        }
      })
    return () => controller.abort()
  }, [requestKey])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const state: AsyncState<T> = settled?.key === requestKey ? settled.state : LOADING
  return { ...state, reload }
}
