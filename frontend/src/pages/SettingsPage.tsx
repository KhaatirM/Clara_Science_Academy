import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { fetchSettingsHub, updateTheme } from '../api/settings'
import { getCsrfToken } from '../api/client'
import { BugReportsPanel } from '../components/settings/BugReportsPanel'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { SettingsHubResponse } from '../types/settings'
import { spaRoute } from '../utils/spaRoute'
import { applyUserTheme } from '../utils/userTheme'

type SettingsTab = 'account' | 'preferences' | 'google' | 'bug-reports'

const TABS: Array<{ id: SettingsTab; label: string; icon: string }> = [
  { id: 'account', label: 'Account', icon: 'bi-person' },
  { id: 'preferences', label: 'Preferences', icon: 'bi-sliders' },
  { id: 'google', label: 'Google', icon: 'bi-google' },
  { id: 'bug-reports', label: 'Bug reports', icon: 'bi-bug' },
]

export default function SettingsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const isBugReportsRoute = location.pathname.includes('/bug-reports')
  const [tab, setTab] = useState<SettingsTab>('account')
  const activeTab: SettingsTab = isBugReportsRoute ? 'bug-reports' : tab

  const [data, setData] = useState<SettingsHubResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [theme, setTheme] = useState('default')
  const [savingTheme, setSavingTheme] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const hub = await fetchSettingsHub()
      setData(hub)
      setTheme(hub.preferences.saved_theme)
      applyUserTheme(hub.preferences.theme)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load settings.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const themeGroups = useMemo(() => {
    const groups = new Map<string, SettingsHubResponse['preferences']['theme_options']>()
    for (const option of data?.preferences.theme_options || []) {
      const list = groups.get(option.group) || []
      list.push(option)
      groups.set(option.group, list)
    }
    return groups
  }, [data?.preferences.theme_options])

  function switchTab(next: SettingsTab) {
    setTab(next)
    if (next === 'bug-reports') navigate(spaRoute('/management/settings/bug-reports'))
    else navigate(spaRoute('/management/settings'))
  }

  async function handleThemeSave() {
    if (data?.preferences.theme_locked) {
      setMessage('Theme is locked by a site-wide override set by Tech.')
      return
    }
    setSavingTheme(true)
    setMessage(null)
    try {
      const result = await updateTheme(theme)
      if (result.success) {
        const saved = result.theme || theme
        applyUserTheme(saved)
        setTheme(saved)
        setData((prev) =>
          prev
            ? {
                ...prev,
                preferences: {
                  ...prev.preferences,
                  theme: saved,
                  saved_theme: saved,
                },
              }
            : prev,
        )
        setMessage('Theme updated.')
      } else {
        setMessage(result.message || 'Could not update theme.')
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not update theme.')
    } finally {
      setSavingTheme(false)
    }
  }

  function handleThemePreview(nextTheme: string) {
    setTheme(nextTheme)
    if (!data?.preferences.theme_locked) {
      applyUserTheme(nextTheme)
    }
  }

  async function handleGoogleDisconnect() {
    if (!window.confirm('Disconnect your Google account?')) return
    const token = getCsrfToken()
    const body = new FormData()
    if (token) body.set('csrf_token', token)
    const response = await fetch(data?.google.disconnect_url || '/management/google-account/disconnect', {
      method: 'POST',
      body,
      credentials: 'same-origin',
      headers: token ? { 'X-CSRFToken': token } : undefined,
    })
    if (response.ok) {
      setMessage('Google account disconnected.')
      await load()
    } else {
      setMessage('Could not disconnect Google account.')
    }
  }

  if (loading && !data) {
    return <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted">Loading settings…</div>
  }

  if (error || !data) {
    return <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">{error || 'Could not load settings.'}</div>
  }

  return (
    <ManagementPageShell director={data.is_director}>
      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Settings</p>
          <h1 className="mt-1 text-2xl font-bold text-hub-text">Account &amp; preferences</h1>
          <p className="mt-2 text-sm text-hub-muted">
            <i className="bi bi-person mr-1" aria-hidden />
            {data.account.username} · {data.account.role}
          </p>
        </div>
        <Link
          to={spaRoute(data.urls.home)}
          className="spa-mgmt-btn-ghost px-4 py-2 text-sm"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          Dashboard
        </Link>
      </header>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-sm font-bold text-hub-text">{data.google.connected ? 'Connected' : 'Not linked'}</div>
          <div className="text-sm text-hub-muted">Google Classroom</div>
        </div>
        <div className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-sm font-bold text-hub-text">{data.preferences.theme}</div>
          <div className="text-sm text-hub-muted">Theme</div>
        </div>
        <div className="spa-mgmt-stat p-4 shadow-sm">
          <div className="truncate text-sm font-bold text-hub-text">{data.account.email || '—'}</div>
          <div className="text-sm text-hub-muted">Email</div>
        </div>
        <div className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-sm font-bold text-hub-text">Secure</div>
          <div className="text-sm text-hub-muted">Password</div>
        </div>
      </div>

      {message ? (
        <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">{message}</div>
      ) : null}

      <div className="mt-5 flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => switchTab(tab.id)}
            className={['spa-mgmt-tab', activeTab === tab.id ? 'is-active' : ''].join(' ')}
          >
            <i className={`bi ${tab.icon}`} aria-hidden />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-5 spa-mgmt-card p-5 shadow-sm">
        {activeTab === 'account' ? (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-hub-text">Account settings</h2>
            <label className="block text-sm text-hub-muted">
              Username
              <input
                readOnly
                value={data.account.username}
                className="mt-1 w-full max-w-md rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm text-hub-muted">
              Email
              <input
                readOnly
                value={data.account.email || ''}
                placeholder="No email set"
                className="mt-1 w-full max-w-md rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              />
            </label>
            <a
              href={data.urls.change_password}
              className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600"
            >
              <i className="bi bi-lock-fill" aria-hidden />
              Change password
            </a>
            <p className="text-xs text-hub-muted">
              Contact your school administrator if you need to update your account email.
            </p>
          </div>
        ) : null}

        {activeTab === 'preferences' ? (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-hub-text">Preferences</h2>
            {data.preferences.theme_locked ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                A site-wide theme ({data.preferences.site_theme_override}) is active. Personal theme
                changes are disabled until Tech removes the override.
              </div>
            ) : null}
            <label className="block text-sm text-hub-muted">
              Theme
              <select
                value={theme}
                disabled={data.preferences.theme_locked}
                onChange={(e) => handleThemePreview(e.target.value)}
                className="mt-1 w-full max-w-md rounded-xl border border-slate-200 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-50"
              >
                {[...themeGroups.entries()].map(([group, options]) => (
                  <optgroup key={group} label={group}>
                    {options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <p className="text-xs text-hub-muted">
              Changes apply immediately to the sidebar and page background. Click save to keep your
              preference for future visits.
            </p>
            <button
              type="button"
              disabled={savingTheme || data.preferences.theme_locked}
              onClick={() => void handleThemeSave()}
              className="spa-mgmt-btn-primary px-4 py-2 text-sm"
            >
              Save theme
            </button>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-hub-muted">
              <p className="font-semibold text-hub-text">School operations</p>
              <p className="mt-1">
                Manage academic years and schedule end-of-year closure from the dedicated pages below.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  to={spaRoute('/management/school-years')}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
                >
                  <i className="bi bi-calendar3" aria-hidden />
                  School years
                </Link>
                <Link
                  to={spaRoute('/management/school-year/closure/schedule')}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
                >
                  <i className="bi bi-flag-fill" aria-hidden />
                  End-of-year closure
                </Link>
              </div>
            </div>
          </div>
        ) : null}

        {activeTab === 'google' ? (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-hub-text">Google Classroom integration</h2>
            {data.google.connected ? (
              <>
                <p className="text-sm text-emerald-700">
                  <i className="bi bi-check-circle-fill mr-1" aria-hidden />
                  Your Google account is linked and ready for Classroom, Forms, and Drive folders in
                  Class Notes.
                </p>
                <div className="flex flex-wrap gap-2">
                  <a
                    href={data.google.connect_url}
                    className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
                  >
                    <i className="bi bi-google mr-1" aria-hidden />
                    Reconnect Google account
                  </a>
                  <button
                    type="button"
                    onClick={() => void handleGoogleDisconnect()}
                    className="rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
                  >
                    Disconnect Google account
                  </button>
                </div>
                <p className="text-xs text-hub-muted">
                  If Class Notes says access expired, use Reconnect and approve Drive access. Signing in
                  with Google on the login page is not enough.
                </p>
              </>
            ) : (
              <>
                <p className="text-sm text-hub-muted">
                  {data.google.needs_reconnect
                    ? 'Your previous Google connection could not be read. Disconnect is not needed — connect again below (approve Drive when asked). Signing in with Google alone is not enough.'
                    : 'Connect your Google account in Settings to use Classroom, Forms, and Drive folders in Class Notes. Signing in with Google alone is not enough.'}
                </p>
                <a
                  href={data.google.connect_url}
                  className="spa-mgmt-btn-primary px-4 py-2 text-sm hover:brightness-105"
                >
                  <i className="bi bi-google" aria-hidden />
                  {data.google.needs_reconnect ? 'Reconnect Google account' : 'Connect Google account'}
                </a>
              </>
            )}
          </div>
        ) : null}

        {activeTab === 'bug-reports' ? <BugReportsPanel /> : null}
      </div>
    </ManagementPageShell>
  )
}
