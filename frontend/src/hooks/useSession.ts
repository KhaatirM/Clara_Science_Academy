import { useCallback, useEffect, useState } from 'react'
import { fetchSession } from '../api/client'
import type { SchoolTimezone, SessionUser } from '../types/session'
import { DEFAULT_SCHOOL_TIMEZONE } from '../utils/schoolTimezone'

interface UseSessionResult {
  user: SessionUser | null
  schoolTimezone: SchoolTimezone | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

export function useSession(): UseSessionResult {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [schoolTimezone, setSchoolTimezone] = useState<SchoolTimezone | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSession()
      if (!data.authenticated || !data.user) {
        window.location.href = data.login_url || '/login'
        return
      }
      setUser(data.user)
      setSchoolTimezone(
        data.school_timezone?.iana
          ? data.school_timezone
          : { iana: DEFAULT_SCHOOL_TIMEZONE, clock: '', zone: '' },
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load session')
      setUser(null)
      setSchoolTimezone(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { user, schoolTimezone, loading, error, refresh }
}
