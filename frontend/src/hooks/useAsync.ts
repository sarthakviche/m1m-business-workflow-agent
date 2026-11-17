import { useCallback, useEffect, useState } from 'react'

interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/** Runs an async loader on mount; exposes loading/error state and a reload. */
export function useAsync<T>(loader: () => Promise<T>): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    loader()
      .then((result) => { if (!cancelled) setData(result) })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Something went wrong.')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
    // The loader is a stable module-level API call; re-run only on reload().
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  return { data, error, loading, reload }
}
