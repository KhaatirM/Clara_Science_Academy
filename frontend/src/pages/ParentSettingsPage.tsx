import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchParentSettings, updateParentTheme } from '../api/parentPortal'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { ParentSettingsResponse } from '../types/parentPortal'
import { applyUserTheme } from '../utils/userTheme'

export function ParentSettingsPage() {
  const [data, setData] = useState<ParentSettingsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [theme, setTheme] = useState('default')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const hub = await fetchParentSettings()
      setData(hub)
      setTheme(hub.preferences.saved_theme)
      applyUserTheme(hub.preferences.theme)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const themeGroups = useMemo(() => {
    const groups = new Map<string, ParentSettingsResponse['preferences']['theme_options']>()
    for (const option of data?.preferences.theme_options || []) {
      const list = groups.get(option.group) || []
      list.push(option)
      groups.set(option.group, list)
    }
    return groups
  }, [data])

  async function handleThemeSave() {
    if (data?.preferences.theme_locked) {
      setMessage('Theme is locked by a site-wide override set by Tech.')
      return
    }
    setSaving(true)
    setMessage(null)
    setError(null)
    try {
      const res = await updateParentTheme(theme)
      setMessage(res.message || 'Theme saved.')
      if (res.theme) applyUserTheme(res.theme)
      else applyUserTheme(theme)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save theme')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <header>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-hub-muted">
              Family portal
            </p>
            <h1 className="mb-0 text-2xl font-bold text-slate-900">Settings</h1>
            <p className="mb-0 mt-1 text-sm text-hub-muted">Account and appearance</p>
          </header>

          {loading ? <p className="text-hub-muted">Loading…</p> : null}
          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          ) : null}
          {message ? (
            <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
              {message}
            </div>
          ) : null}

          {data ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-base font-bold text-hub-text">Account</h2>
                <dl className="mb-0 space-y-2 text-sm">
                  <div className="flex justify-between gap-3">
                    <dt className="text-hub-muted">Name</dt>
                    <dd className="mb-0 font-semibold text-hub-text">{data.account.display_name}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-hub-muted">Username</dt>
                    <dd className="mb-0 font-mono text-hub-text">{data.account.username}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-hub-muted">Email</dt>
                    <dd className="mb-0 text-hub-text">{data.account.email || '—'}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-hub-muted">Role</dt>
                    <dd className="mb-0 text-hub-text">{data.account.role}</dd>
                  </div>
                </dl>
                {data.children.length ? (
                  <div className="mt-4 border-t border-slate-100 pt-4">
                    <p className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Linked children
                    </p>
                    <ul className="mb-0 space-y-1 text-sm">
                      {data.children.map((c) => (
                        <li key={c.id} className="font-semibold text-hub-text">
                          {c.display_name}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-base font-bold text-hub-text">Theme</h2>
                {data.preferences.theme_locked ? (
                  <p className="mb-3 text-sm text-amber-800">
                    Theme is locked by a site-wide override.
                  </p>
                ) : null}
                <div className="space-y-4">
                  {[...themeGroups.entries()].map(([group, options]) => (
                    <div key={group}>
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                        {group}
                      </p>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {options.map((opt) => (
                          <label
                            key={opt.value}
                            className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                              theme === opt.value
                                ? 'border-teal-400 bg-teal-50 font-semibold text-teal-900'
                                : 'border-slate-200 bg-white text-hub-text'
                            }`}
                          >
                            <input
                              type="radio"
                              name="theme"
                              value={opt.value}
                              checked={theme === opt.value}
                              disabled={data.preferences.theme_locked || saving}
                              onChange={() => setTheme(opt.value)}
                            />
                            {opt.label}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  disabled={saving || data.preferences.theme_locked}
                  onClick={() => void handleThemeSave()}
                  className="mt-4 rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                >
                  {saving ? 'Saving…' : 'Save theme'}
                </button>
              </section>
            </div>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}
