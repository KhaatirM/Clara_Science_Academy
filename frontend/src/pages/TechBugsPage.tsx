import { useCallback, useEffect, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import {
  fetchTechBugReports,
  fetchTechErrorReports,
  submitTechBugReport,
  updateTechBugStatus,
} from '../api/tech'
import { BugReportsPanel } from '../components/settings/BugReportsPanel'
import {
  ManagementPageHero,
  ManagementPageShell,
} from '../components/layout/ManagementPageShell'

const fieldClass =
  'w-full rounded-xl border border-[color-mix(in_srgb,var(--spa-mgmt-accent)_22%,var(--spa-mgmt-border))] bg-[var(--spa-mgmt-surface)] px-3 py-2.5 text-sm text-hub-text shadow-sm outline-none transition focus:border-[var(--spa-mgmt-accent)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--spa-mgmt-accent)_25%,transparent)]'
const labelClass = 'text-xs font-semibold uppercase tracking-wide text-hub-muted'

export function TechBugsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const tab: 'errors' | 'reports' = rawTab === 'reports' ? 'reports' : 'errors'

  function setTab(next: 'errors' | 'reports') {
    const nextParams = new URLSearchParams(searchParams)
    if (next === 'errors') nextParams.delete('tab')
    else nextParams.set('tab', next)
    setSearchParams(nextParams, { replace: true })
  }

  const tabMeta = {
    errors: {
      label: 'Error log',
      icon: 'bi-exclamation-octagon',
      hint: 'Failed actions and system errors captured from the portal.',
    },
    reports: {
      label: 'Reports',
      icon: 'bi-bug',
      hint: 'User-submitted bug reports and triage status.',
    },
  } as const

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div>
          <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
            Tech · Quality
          </p>
          <h1 className="mb-0 text-3xl font-bold tracking-tight">Bugs</h1>
          <p className="mb-0 mt-2 max-w-xl text-sm spa-mgmt-hero-muted">{tabMeta[tab].hint}</p>
        </div>
      </ManagementPageHero>

      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Bug sections">
        {(['errors', 'reports'] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={`spa-mgmt-tab ${tab === t ? 'is-active' : ''}`}
            onClick={() => setTab(t)}
          >
            <i className={`bi ${tabMeta[t].icon}`} aria-hidden />
            {tabMeta[t].label}
          </button>
        ))}
      </div>

      {tab === 'errors' ? (
        <ErrorLogPanel />
      ) : (
        <BugReportsPanel
          fetchReports={fetchTechBugReports}
          submitReport={submitTechBugReport}
          updateStatus={updateTechBugStatus}
        />
      )}
    </ManagementPageShell>
  )
}

/** @deprecated use TechBugsPage */
export function TechErrorReportsPage() {
  return <Navigate to="/tech/bugs?tab=errors" replace />
}

/** @deprecated use TechBugsPage */
export function TechBugReportsPage() {
  return <Navigate to="/tech/bugs?tab=reports" replace />
}

function ErrorLogPanel() {
  const [filters, setFilters] = useState({
    type_filter: 'All',
    status_filter: 'All',
    date_filter: '7d',
  })
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTechErrorReports(filters))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load error reports')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    void load()
  }, [load])

  const entries = (data?.entries || []) as any[]
  const errorCount = entries.filter((e) => String(e.type || '').toLowerCase().includes('error')).length
  const bugCount = entries.filter((e) => String(e.type || '').toLowerCase().includes('bug')).length

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-hub-text">{entries.length}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Shown</div>
        </article>
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-rose-700">{errorCount}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Errors</div>
        </article>
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-amber-700">{bugCount}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Bugs</div>
        </article>
      </div>

      <section className="spa-mgmt-card overflow-hidden shadow-sm">
        <div className="spa-mgmt-accent-bar" />
        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="flex min-w-[9rem] flex-col gap-1.5 sm:max-w-[12rem]">
            <span className={labelClass}>Type</span>
            <select
              className={fieldClass}
              value={filters.type_filter}
              onChange={(e) => setFilters((f) => ({ ...f, type_filter: e.target.value }))}
            >
              {['All', 'Errors', 'Bugs'].map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[9rem] flex-col gap-1.5 sm:max-w-[12rem]">
            <span className={labelClass}>Status</span>
            <select
              className={fieldClass}
              value={filters.status_filter}
              onChange={(e) => setFilters((f) => ({ ...f, status_filter: e.target.value }))}
            >
              {['All', 'open', 'in_progress', 'resolved', 'closed'].map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[9rem] flex-col gap-1.5 sm:max-w-[12rem]">
            <span className={labelClass}>Range</span>
            <select
              className={fieldClass}
              value={filters.date_filter}
              onChange={(e) => setFilters((f) => ({ ...f, date_filter: e.target.value }))}
            >
              <option value="24h">Last 24h</option>
              <option value="7d">Last 7d</option>
              <option value="30d">Last 30d</option>
              <option value="all">All time</option>
            </select>
          </label>
          <button
            type="button"
            className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
            onClick={() => void load()}
          >
            <i className="bi bi-funnel" aria-hidden />
            Apply
          </button>
        </div>
      </section>

      {loading ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading error log…</div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : entries.length === 0 ? (
        <div className="spa-mgmt-card border-dashed px-6 py-12 text-center shadow-sm">
          <i className="bi bi-check2-circle mb-2 text-2xl text-hub-muted" aria-hidden />
          <p className="mb-0 font-semibold text-hub-text">No entries</p>
          <p className="mb-0 mt-1 text-sm text-hub-muted">Nothing matched these filters.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry: any, idx: number) => (
            <article
              key={`${entry.type}-${entry.id || idx}-${entry.timestamp}`}
              className="spa-mgmt-card overflow-hidden shadow-sm"
            >
              <div className="spa-mgmt-accent-bar" />
              <div className="p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="spa-mgmt-badge uppercase">{entry.type}</span>
                  <span className="text-hub-muted">{entry.timestamp_display}</span>
                  {entry.status ? (
                    <span className="rounded-lg bg-amber-100 px-2.5 py-1 font-medium text-amber-900">
                      {entry.status}
                    </span>
                  ) : null}
                </div>
                <h3 className="mb-1 text-base font-semibold text-hub-text">
                  {entry.title || entry.action || 'Entry'}
                </h3>
                <p className="mb-0 text-sm leading-relaxed text-hub-muted">
                  {entry.error_message || entry.description || '—'}
                </p>
                {entry.username ? (
                  <p className="mb-0 mt-2 text-xs text-hub-muted">User: {entry.username}</p>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
