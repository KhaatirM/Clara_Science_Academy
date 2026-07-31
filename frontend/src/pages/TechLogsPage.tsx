import { useCallback, useEffect, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { fetchTechActivityLog, fetchTechAuditLogs } from '../api/tech'
import {
  ManagementPageHero,
  ManagementPageShell,
} from '../components/layout/ManagementPageShell'

type LogsTab = 'activity' | 'audit'

const fieldClass =
  'w-full rounded-xl border border-[color-mix(in_srgb,var(--spa-mgmt-accent)_22%,var(--spa-mgmt-border))] bg-[var(--spa-mgmt-surface)] px-3 py-2.5 text-sm text-hub-text shadow-sm outline-none transition focus:border-[var(--spa-mgmt-accent)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--spa-mgmt-accent)_25%,transparent)]'
const labelClass = 'text-xs font-semibold uppercase tracking-wide text-hub-muted'

function formatDetails(details: unknown): string {
  if (details == null || details === '') return '—'
  if (typeof details === 'string') {
    try {
      const parsed = JSON.parse(details)
      return formatDetailsObject(parsed)
    } catch {
      return details
    }
  }
  if (typeof details === 'object') return formatDetailsObject(details as Record<string, unknown>)
  return String(details)
}

function formatDetailsObject(obj: Record<string, unknown>): string {
  const parts: string[] = []
  for (const [key, value] of Object.entries(obj)) {
    if (value == null || value === '') continue
    parts.push(`${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`)
  }
  return parts.length ? parts.join(' · ') : '—'
}

function statusTone(code: number | null | undefined) {
  if (code == null) return 'bg-slate-100 text-slate-700'
  if (code >= 200 && code < 300) return 'bg-emerald-100 text-emerald-800'
  if (code >= 300 && code < 400) return 'bg-sky-100 text-sky-800'
  if (code >= 400) return 'bg-rose-100 text-rose-800'
  return 'bg-slate-100 text-slate-700'
}

export function TechLogsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const tab: LogsTab = rawTab === 'audit' ? 'audit' : 'activity'

  function setTab(next: LogsTab) {
    const nextParams = new URLSearchParams(searchParams)
    if (next === 'activity') nextParams.delete('tab')
    else nextParams.set('tab', next)
    setSearchParams(nextParams, { replace: true })
  }

  const tabMeta = {
    activity: {
      label: 'Activity',
      icon: 'bi-activity',
      hint: 'User actions across the portal — logins, updates, and system events.',
    },
    audit: {
      label: 'Audit',
      icon: 'bi-journal-text',
      hint: 'HTTP request trail for management and tech endpoints.',
    },
  } as const

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
              Tech · Observability
            </p>
            <h1 className="mb-0 text-3xl font-bold tracking-tight">Logs</h1>
            <p className="mb-0 mt-2 max-w-xl text-sm spa-mgmt-hero-muted">{tabMeta[tab].hint}</p>
          </div>
          {tab === 'audit' ? (
            <a
              href="/tech/audit-logs/export.csv?legacy=1"
              className="inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-sm font-semibold text-white no-underline hover:bg-white/25"
            >
              <i className="bi bi-download" aria-hidden />
              Export CSV
            </a>
          ) : null}
        </div>
      </ManagementPageHero>

      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Log sections">
        {(['activity', 'audit'] as const).map((t) => (
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

      {tab === 'activity' ? <ActivityLogPanel /> : <AuditLogPanel />}
    </ManagementPageShell>
  )
}

/** @deprecated use TechLogsPage */
export function TechActivityLogPage() {
  return <Navigate to="/tech/logs?tab=activity" replace />
}

/** @deprecated use TechLogsPage */
export function TechAuditLogsPage() {
  return <Navigate to="/tech/logs?tab=audit" replace />
}

function ActivityLogPanel() {
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState({
    user_id: '',
    action: searchParams.get('action') || '',
    start_date: '',
    end_date: '',
    limit: '100',
  })
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(
        await fetchTechActivityLog({
          user_id: filters.user_id || undefined,
          action: filters.action || undefined,
          start_date: filters.start_date || undefined,
          end_date: filters.end_date || undefined,
          limit: Number(filters.limit) || 100,
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load activity log')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    void load()
  }, [load])

  const logs = (data?.logs || []) as any[]
  const okCount = logs.filter((l) => l.success).length
  const failCount = logs.length - okCount

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-hub-text">{logs.length}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Shown</div>
        </article>
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-emerald-700">{okCount}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Succeeded</div>
        </article>
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-rose-700">{failCount}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Failed</div>
        </article>
      </div>

      <section className="spa-mgmt-card overflow-hidden shadow-sm">
        <div className="spa-mgmt-accent-bar" />
        <div className="flex flex-col gap-3 p-4 lg:flex-row lg:flex-wrap lg:items-end">
          <label className="flex min-w-[10rem] flex-1 flex-col gap-1.5 sm:max-w-[14rem]">
            <span className={labelClass}>User</span>
            <select
              className={fieldClass}
              value={filters.user_id}
              onChange={(e) => setFilters((f) => ({ ...f, user_id: e.target.value }))}
            >
              <option value="">All users</option>
              {(data?.users || []).map((u: any) => (
                <option key={u.id} value={u.id}>
                  {u.username}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[10rem] flex-1 flex-col gap-1.5 sm:max-w-[14rem]">
            <span className={labelClass}>Action</span>
            <select
              className={fieldClass}
              value={filters.action}
              onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}
            >
              <option value="">All actions</option>
              {(data?.actions || []).map((a: string) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[9rem] flex-col gap-1.5">
            <span className={labelClass}>From</span>
            <input
              type="date"
              className={fieldClass}
              value={filters.start_date}
              onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))}
            />
          </label>
          <label className="flex min-w-[9rem] flex-col gap-1.5">
            <span className={labelClass}>To</span>
            <input
              type="date"
              className={fieldClass}
              value={filters.end_date}
              onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))}
            />
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
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading activity…</div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : logs.length === 0 ? (
        <div className="spa-mgmt-card border-dashed px-6 py-12 text-center shadow-sm">
          <i className="bi bi-inbox mb-2 text-2xl text-hub-muted" aria-hidden />
          <p className="mb-0 font-semibold text-hub-text">No activity entries</p>
          <p className="mb-0 mt-1 text-sm text-hub-muted">Try widening the date range or clearing filters.</p>
        </div>
      ) : (
        <div className="spa-mgmt-card overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[60rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--spa-mgmt-border)] bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_55%,var(--spa-mgmt-surface))]">
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    When
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    User
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Action
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Result
                  </th>
                  <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr
                    key={log.id}
                    className="border-b border-[color-mix(in_srgb,var(--spa-mgmt-border)_70%,transparent)] last:border-b-0 hover:bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_40%,transparent)]"
                  >
                    <td className="whitespace-nowrap px-4 py-3 align-top text-hub-muted">
                      {log.timestamp_display}
                    </td>
                    <td className="px-4 py-3 align-top font-medium text-hub-text">
                      {log.username || '—'}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span className="spa-mgmt-badge">{log.action}</span>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${
                          log.success
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {log.success ? 'OK' : log.error_message || 'Failed'}
                      </span>
                    </td>
                    <td className="max-w-md px-4 py-3 align-top text-xs leading-relaxed text-hub-muted">
                      {formatDetails(log.details)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function AuditLogPanel() {
  const [filters, setFilters] = useState({ q: '', method: '', page: 1 })
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(
        await fetchTechAuditLogs({
          q: filters.q || undefined,
          method: filters.method || undefined,
          page: filters.page,
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load audit logs')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    void load()
  }, [load])

  const logs = (data?.logs || []) as any[]

  return (
    <div className="space-y-4">
      <section className="spa-mgmt-card overflow-hidden shadow-sm">
        <div className="spa-mgmt-accent-bar" />
        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="flex min-w-[14rem] flex-[2] flex-col gap-1.5">
            <span className={labelClass}>Search path / endpoint</span>
            <input
              className={fieldClass}
              placeholder="/management/…"
              value={filters.q}
              onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value, page: 1 }))}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void load()
              }}
            />
          </label>
          <label className="flex min-w-[9rem] flex-col gap-1.5 sm:max-w-[11rem]">
            <span className={labelClass}>Method</span>
            <select
              className={fieldClass}
              value={filters.method}
              onChange={(e) => setFilters((f) => ({ ...f, method: e.target.value, page: 1 }))}
            >
              <option value="">All methods</option>
              {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
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
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">
          Loading audit trail…
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : logs.length === 0 ? (
        <div className="spa-mgmt-card border-dashed px-6 py-12 text-center shadow-sm">
          <i className="bi bi-journal-x mb-2 text-2xl text-hub-muted" aria-hidden />
          <p className="mb-0 font-semibold text-hub-text">No audit entries</p>
        </div>
      ) : (
        <>
          <div className="spa-mgmt-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[64rem] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--spa-mgmt-border)] bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_55%,var(--spa-mgmt-surface))]">
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      When
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      User
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Method
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Status
                    </th>
                    <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Path
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Time (ms)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((row) => (
                    <tr
                      key={row.id}
                      className="border-b border-[color-mix(in_srgb,var(--spa-mgmt-border)_70%,transparent)] last:border-b-0 hover:bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_40%,transparent)]"
                    >
                      <td className="whitespace-nowrap px-4 py-3 align-top text-hub-muted">
                        {row.created_display}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="font-medium text-hub-text">{row.user_role || '—'}</div>
                        <div className="text-xs text-hub-muted">ID {row.user_id ?? '—'}</div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <span className="spa-mgmt-badge">{row.method}</span>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <span
                          className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${statusTone(row.status_code)}`}
                        >
                          {row.status_code}
                        </span>
                      </td>
                      <td className="max-w-lg break-all px-4 py-3 align-top font-mono text-xs text-hub-text">
                        {row.path}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 align-top text-hub-muted">
                        {row.duration_ms ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="spa-mgmt-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
              disabled={filters.page <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
            >
              Previous
            </button>
            <span className="text-sm text-hub-muted">
              Page {data?.pagination?.page || 1} / {data?.pagination?.pages || 1}
            </span>
            <button
              type="button"
              className="spa-mgmt-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
              disabled={filters.page >= (data?.pagination?.pages || 1)}
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}
