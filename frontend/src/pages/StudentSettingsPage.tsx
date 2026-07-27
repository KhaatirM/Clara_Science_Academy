import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  fetchStudentBugReports,
  fetchStudentSettingsHub,
  submitStudentBugReport,
  updateStudentLowGradeThreshold,
  updateStudentTheme,
} from '../api/studentTabs'
import { BugReportsPanel } from '../components/settings/BugReportsPanel'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { StudentSettingsResponse } from '../types/studentTabs'
import { applyUserTheme } from '../utils/userTheme'

type SettingsTab = 'account' | 'preferences' | 'academic' | 'bug-reports'

const TABS: Array<{ id: SettingsTab; label: string; icon: string }> = [
  { id: 'account', label: 'Account', icon: 'bi-person' },
  { id: 'preferences', label: 'Preferences', icon: 'bi-sliders' },
  { id: 'academic', label: 'Academic', icon: 'bi-mortarboard' },
  { id: 'bug-reports', label: 'Bug reports', icon: 'bi-bug' },
]

export function StudentSettingsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const isBugReportsRoute = location.pathname.includes('/bug-reports')
  const [tab, setTab] = useState<SettingsTab>('account')
  const activeTab: SettingsTab = isBugReportsRoute ? 'bug-reports' : tab

  const [data, setData] = useState<StudentSettingsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [theme, setTheme] = useState('default')
  const [threshold, setThreshold] = useState(70)
  const [savingTheme, setSavingTheme] = useState(false)
  const [savingThreshold, setSavingThreshold] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const hub = await fetchStudentSettingsHub()
      setData(hub)
      setTheme(hub.preferences.saved_theme)
      setThreshold(hub.preferences.low_grade_threshold)
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
    const groups = new Map<string, StudentSettingsResponse['preferences']['theme_options']>()
    for (const option of data?.preferences.theme_options || []) {
      const list = groups.get(option.group) || []
      list.push(option)
      groups.set(option.group, list)
    }
    return groups
  }, [data?.preferences.theme_options])

  function switchTab(next: SettingsTab) {
    setTab(next)
    if (next === 'bug-reports') navigate('/student/settings/bug-reports')
    else navigate('/student/settings')
  }

  async function handleThemeSave() {
    if (data?.preferences.theme_locked) {
      setMessage('Theme is locked by a site-wide override set by Tech.')
      return
    }
    setSavingTheme(true)
    setMessage(null)
    try {
      const result = await updateStudentTheme(theme)
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

  async function handleThresholdSave() {
    setSavingThreshold(true)
    setMessage(null)
    try {
      const result = await updateStudentLowGradeThreshold(threshold)
      if (result.success) {
        const saved = result.threshold ?? threshold
        setThreshold(saved)
        setData((prev) =>
          prev
            ? {
                ...prev,
                preferences: { ...prev.preferences, low_grade_threshold: saved },
              }
            : prev,
        )
        setMessage('Low grade threshold updated.')
      } else {
        setMessage(result.message || 'Could not update threshold.')
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not update threshold.')
    } finally {
      setSavingThreshold(false)
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

  const student = data.account.student

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
                  Settings
                </p>
                <h1 className="text-2xl font-bold tracking-tight md:text-3xl">
                  Account & preferences
                </h1>
                <p className="mb-0 mt-1 text-sm text-teal-50/95">
                  {data.account.username} · {data.account.role}
                </p>
              </div>
              <Link
                to="/student"
                className="inline-flex items-center rounded-full bg-white px-4 py-2 text-sm font-bold text-teal-900 hover:bg-teal-50"
              >
                <i className="bi bi-house-door me-1" aria-hidden />
                Home
              </Link>
            </div>
          </header>

          <div className="mb-4 flex flex-wrap gap-2" role="tablist">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={activeTab === item.id}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold ${
                  activeTab === item.id
                    ? 'bg-teal-700 text-white'
                    : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
                onClick={() => switchTab(item.id)}
              >
                <i className={`bi ${item.icon}`} aria-hidden />
                {item.label}
              </button>
            ))}
          </div>

          {message ? (
            <div className="mb-4 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
              {message}
            </div>
          ) : null}

          {activeTab === 'account' ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-lg font-bold text-hub-text">Account</h2>
              <dl className="mb-4 grid gap-3 sm:grid-cols-2">
                <Info label="Username" value={data.account.username} />
                <Info label="Email" value={data.account.email || 'Not set'} />
                <Info label="Full name" value={student?.full_name || '—'} />
                <Info label="Student ID" value={student?.state_id || '—'} />
                <Info
                  label="Grade level"
                  value={student?.grade_level != null ? String(student.grade_level) : '—'}
                />
                <Info label="Role" value={data.account.role || 'Student'} />
              </dl>
              <a
                href={data.urls.change_password}
                className="inline-flex rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
              >
                Change password
              </a>
            </section>
          ) : null}

          {activeTab === 'preferences' ? (
            <section className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-lg font-bold text-hub-text">Theme</h2>
                {data.preferences.theme_locked ? (
                  <p className="mb-3 text-sm text-hub-muted">
                    Theme is locked by a site-wide override.
                  </p>
                ) : null}
                {[...themeGroups.entries()].map(([group, options]) => (
                  <div key={group} className="mb-4">
                    <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      {group}
                    </h3>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {options.map((option) => (
                        <label
                          key={option.value}
                          className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                            theme === option.value
                              ? 'border-teal-400 bg-teal-50 font-semibold text-teal-900'
                              : 'border-slate-200 bg-slate-50 text-hub-text'
                          }`}
                        >
                          <input
                            type="radio"
                            name="theme"
                            value={option.value}
                            checked={theme === option.value}
                            onChange={() => {
                              setTheme(option.value)
                              if (!data.preferences.theme_locked) applyUserTheme(option.value)
                            }}
                          />
                          {option.label}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  disabled={savingTheme || data.preferences.theme_locked}
                  onClick={() => void handleThemeSave()}
                  className="rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-60"
                >
                  {savingTheme ? 'Saving…' : 'Save theme'}
                </button>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-2 text-lg font-bold text-hub-text">Low grade threshold</h2>
                <p className="mb-3 text-sm text-hub-muted">
                  Assignments at or below this percentage appear in “Grades to improve”.
                </p>
                <div className="flex flex-wrap items-end gap-3">
                  <label className="block text-sm">
                    <span className="mb-1 block font-semibold text-hub-muted">Threshold (%)</span>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={threshold}
                      onChange={(e) => setThreshold(Number(e.target.value))}
                      className="w-28 rounded-lg border border-slate-300 px-3 py-2"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={savingThreshold}
                    onClick={() => void handleThresholdSave()}
                    className="rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-60"
                  >
                    {savingThreshold ? 'Saving…' : 'Save threshold'}
                  </button>
                </div>
              </div>
            </section>
          ) : null}

          {activeTab === 'academic' ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-lg font-bold text-hub-text">Academic</h2>
              <dl className="grid gap-3 sm:grid-cols-3">
                <Info label="School year" value={data.academic.school_year?.name || 'None'} />
                <Info label="Enrolled classes" value={String(data.academic.enrollment_count)} />
                <Info label="GPA" value={data.academic.gpa.toFixed(2)} />
              </dl>
            </section>
          ) : null}

          {activeTab === 'bug-reports' ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-lg font-bold text-hub-text">Bug reports</h2>
              <BugReportsPanel
                fetchReports={fetchStudentBugReports}
                submitReport={submitStudentBugReport}
              />
            </section>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
      <dt className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-hub-muted">{label}</dt>
      <dd className="mb-0 text-sm font-semibold text-hub-text">{value}</dd>
    </div>
  )
}
