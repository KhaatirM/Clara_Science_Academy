import { useCallback, useEffect, useState } from 'react'
import { fetchSession } from '../api/client'
import type { AppVersionInfo, SchoolTimezone, SessionUser } from '../types/session'
import { DEFAULT_SCHOOL_TIMEZONE } from '../utils/schoolTimezone'
import { applyUserTheme } from '../utils/userTheme'
import { showAppToasts } from '../utils/appToast'

interface UseSessionResult {
  user: SessionUser | null
  schoolTimezone: SchoolTimezone | null
  appVersion: AppVersionInfo | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/** Avoid duplicate login toasts if /api/spa/me runs twice (e.g. React Strict Mode). */
let sessionFlashesShown = false

export function useSession(): UseSessionResult {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [schoolTimezone, setSchoolTimezone] = useState<SchoolTimezone | null>(null)
  const [appVersion, setAppVersion] = useState<AppVersionInfo | null>(null)
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
      setAppVersion(data.app_version || null)
      applyUserTheme(data.user.theme)
      setSchoolTimezone(
        data.school_timezone?.iana
          ? data.school_timezone
          : { iana: DEFAULT_SCHOOL_TIMEZONE, clock: '', zone: '' },
      )
      if (!sessionFlashesShown && data.flashes?.length) {
        sessionFlashesShown = true
        showAppToasts(
          data.flashes.map((f) => ({
            message: f.message,
            tone: f.category,
          })),
        )
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load session')
      setUser(null)
      setSchoolTimezone(null)
      setAppVersion(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { user, schoolTimezone, appVersion, loading, error, refresh }
}
