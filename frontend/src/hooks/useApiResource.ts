import { useCallback, useEffect, useState } from 'react'

import { api, errorMessage } from '../lib/api'

interface Resource<T> {
  data: T | null
  loading: boolean
  error: string
  refresh: () => void
}

export function useApiResource<T>(path: string, token: string): Resource<T> {
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    api<T>(path, { token })
      .then((payload) => {
        if (!active) return
        setData(payload)
        setError('')
      })
      .catch((reason) => {
        if (active) setError(errorMessage(reason))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [path, revision, token])

  const refresh = useCallback(() => {
    setLoading(true)
    setRevision((value) => value + 1)
  }, [])

  return { data, loading, error, refresh }
}
