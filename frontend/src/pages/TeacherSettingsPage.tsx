import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import {
  fetchTeacherBugReports,
  fetchTeacherSettingsHub,
  submitTeacherBugReport,
  updateTeacherTheme,
} from '../api/teacherTabs'
import { getCsrfToken } from '../api/client'
import { BugReportsPanel } from '../components/settings/BugReportsPanel'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { TeacherSettingsResponse } from '../types/teacherTabs'
import { applyUserTheme } from '../utils/userTheme'

type SettingsTab = 'account' | 'preferences' | 'google' | 'bug-reports'

const TABS: Array<{ id: SettingsTab; label: string; icon: string }> = [
  { id: 'account', label: 'Account', icon: 'bi-person' },
  { id: 'preferences', label: 'Preferences', icon: 'bi-sliders' },
  { id: 'google', label: 'Google', icon: 'bi-google' },
  { id: 'bug-reports', label: 'Bug reports', icon: 'bi-bug' },
]

export function TeacherSettingsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const isBugReportsRoute = location.pathname.includes('/bug-reports')
  const [tab, setTab] = useState<SettingsTab>('account')
  const activeTab: SettingsTab = isBugReportsRoute ? 'bug-reports' : tab

  const [data, setData] = useState<TeacherSettingsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [theme, setTheme] = useState('default')
  const [savingTheme, setSavingTheme] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const hub = await fetchTeacherSettingsHub()
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
    const groups = new Map<string, TeacherSettingsResponse['preferences']['theme_options']>()
    for (const option of data?.preferences.theme_options || []) {
      const list = groups.get(option.group) || []
      list.push(option)
      groups.set(option.group, list)
    }
    return groups
  }, [data?.preferences.theme_options])

  function switchTab(next: SettingsTab) {
    setTab(next)
    if (next === 'bug-reports') navigate('/teacher/settings/bug-reports')
    else navigate('/teacher/settings')
  }

  async function handleThemeSave() {
    if (data?.preferences.theme_locked) {
      setMessage('Theme is locked by a site-wide override set by Tech.')
      return
    }
    setSavingTheme(true)
    setMessage(null)
    try {
      const result = await updateTeacherTheme(theme)
      if (result.success) {
        const saved = result.theme || theme
        applyUserTheme(saved)
        setTheme(saved)
        setData((prev) =>
          prev
            ? {
                ...prev,
                preferences: { ...prev.preferences, theme: saved, saved_theme: saved },
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
    const response = await fetch(data?.google.disconnect_url || '/teacher/google-account/disconnect', {
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
    return (
      <ManagementPageShell>
        <div className="p-8 text-center text-muted">Loading settings…</div>
      </ManagementPageShell>
    )
  }

  if (error || !data) {
    return (
      <ManagementPageShell>
        <div className="alert alert-danger m-3">{error || 'Could not load settings.'}</div>
      </ManagementPageShell>
    )
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          <header className="mgmt-home-hero">
            <div>
              <p className="mgmt-home-eyebrow">Settings</p>
              <h1 className="mgmt-home-title">Account &amp; preferences</h1>
              <p className="mgmt-home-date">
                <i className="bi bi-person me-1" aria-hidden />
                {data.account.username} · {data.account.role}
              </p>
            </div>
            <div className="mgmt-home-hero-actions">
              <Link to="/teacher" className="mgmt-home-switch-link">
                <i className="bi bi-grid me-1" aria-hidden />
                Home
              </Link>
            </div>
          </header>

          <div className="teacher-settings-tabs" role="tablist">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={activeTab === item.id}
                className={`teacher-settings-tab${activeTab === item.id ? ' is-active' : ''}`}
                onClick={() => switchTab(item.id)}
              >
                <i className={`bi ${item.icon}`} aria-hidden />
                {item.label}
              </button>
            ))}
          </div>

          {message ? <div className="alert alert-info mt-3">{message}</div> : null}

          {activeTab === 'account' ? (
            <section className="teacher-settings-panel">
              <h2>Account</h2>
              <dl className="teacher-settings-dl">
                <div>
                  <dt>Username</dt>
                  <dd>{data.account.username}</dd>
                </div>
                <div>
                  <dt>Email</dt>
                  <dd>{data.account.email || 'Not set'}</dd>
                </div>
                <div>
                  <dt>Role</dt>
                  <dd>{data.account.role}</dd>
                </div>
              </dl>
              <a href={data.urls.change_password} className="teacher-class-card__btn teacher-class-card__btn--view">
                Change password
              </a>
            </section>
          ) : null}

          {activeTab === 'preferences' ? (
            <section className="teacher-settings-panel">
              <h2>Theme</h2>
              {data.preferences.theme_locked ? (
                <p className="text-muted">Theme is locked by a site-wide override.</p>
              ) : null}
              {[...themeGroups.entries()].map(([group, options]) => (
                <div key={group} className="mb-4">
                  <h3 className="teacher-settings-group">{group}</h3>
                  <div className="teacher-settings-themes">
                    {options.map((option) => (
                      <label key={option.value} className="teacher-settings-theme">
                        <input
                          type="radio"
                          name="theme"
                          value={option.value}
                          checked={theme === option.value}
                          onChange={() => handleThemePreview(option.value)}
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
              <button
                type="button"
                className="teacher-class-card__btn teacher-class-card__btn--assignment"
                disabled={savingTheme || data.preferences.theme_locked}
                onClick={() => void handleThemeSave()}
              >
                Save theme
              </button>
            </section>
          ) : null}

          {activeTab === 'google' ? (
            <section className="teacher-settings-panel">
              <h2>Google account</h2>
              <p>
                {data.google.connected
                  ? 'Your Google account is connected for Classroom and Forms.'
                  : 'Connect Google to link Classroom courses and export quizzes.'}
              </p>
              {data.google.connected ? (
                <button
                  type="button"
                  className="teacher-class-card__btn teacher-class-card__btn--google-unlink"
                  onClick={() => void handleGoogleDisconnect()}
                >
                  Disconnect Google
                </button>
              ) : (
                <a href={data.google.connect_url} className="teacher-class-card__btn teacher-class-card__btn--google-link">
                  Connect Google account
                </a>
              )}
            </section>
          ) : null}

          {activeTab === 'bug-reports' ? (
            <section className="teacher-settings-panel">
              <BugReportsPanel fetchReports={fetchTeacherBugReports} submitReport={submitTeacherBugReport} />
            </section>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}
