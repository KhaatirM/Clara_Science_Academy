import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, useParams, useSearchParams } from 'react-router-dom'
import {
  fetchTechActivityLog,
  fetchTechAuditLogs,
  fetchTechBugReports,
  fetchTechErrorReports,
  fetchTechUser,
  fetchTechUsers,
  impersonateTechUser,
  resetTechUserPassword,
  submitTechBugReport,
  updateTechBugStatus,
} from '../api/tech'
import { BugReportsPanel } from '../components/settings/BugReportsPanel'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import { btnMuted, btnPrimary } from './TechHomePage'

type LogsTab = 'activity' | 'audit'

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

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="mb-0 text-2xl font-bold text-slate-900">Logs</h1>
              <p className="mb-0 mt-1 text-sm text-hub-muted">
                User activity events and management HTTP audit trail
              </p>
            </div>
            {tab === 'audit' ? (
              <a href="/tech/audit-logs/export.csv?legacy=1" className={btnMuted}>
                Export CSV
              </a>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={tab === 'activity' ? btnPrimary : btnMuted}
              onClick={() => setTab('activity')}
            >
              Activity
            </button>
            <button
              type="button"
              className={tab === 'audit' ? btnPrimary : btnMuted}
              onClick={() => setTab('audit')}
            >
              Audit
            </button>
          </div>

          {tab === 'activity' ? <ActivityLogPanel /> : <AuditLogPanel />}
        </div>
      </div>
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

  return (
    <>
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:flex-row lg:flex-wrap lg:items-end">
        <label className="flex min-w-[10rem] flex-1 flex-col gap-1.5 sm:max-w-[14rem]">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">User</span>
          <select
            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
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
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Action</span>
          <select
            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
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
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">From</span>
          <input
            type="date"
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            value={filters.start_date}
            onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))}
          />
        </label>
        <label className="flex min-w-[9rem] flex-col gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">To</span>
          <input
            type="date"
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            value={filters.end_date}
            onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))}
          />
        </label>
        <button type="button" className={btnPrimary} onClick={() => void load()}>
          Apply
        </button>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
          Loading activity…
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : logs.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center shadow-sm">
          <p className="mb-0 font-semibold text-slate-800">No activity entries</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full min-w-[60rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  When
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  User
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Action
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Result
                </th>
                <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Details
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr
                  key={log.id}
                  className="border-b border-slate-100 last:border-b-0 hover:bg-teal-50/40"
                >
                  <td className="whitespace-nowrap px-4 py-3 align-top text-slate-700">
                    {log.timestamp_display}
                  </td>
                  <td className="px-4 py-3 align-top font-medium text-slate-900">
                    {log.username || '—'}
                  </td>
                  <td className="px-4 py-3 align-top">
                    <span className="inline-flex rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-800">
                      {log.action}
                    </span>
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
                  <td className="max-w-md px-4 py-3 align-top text-xs leading-relaxed text-slate-600">
                    {formatDetails(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
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
    <>
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:flex-wrap sm:items-end">
        <label className="flex min-w-[14rem] flex-[2] flex-col gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Search path / endpoint
          </span>
          <input
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            placeholder="/management/…"
            value={filters.q}
            onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value, page: 1 }))}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void load()
            }}
          />
        </label>
        <label className="flex min-w-[9rem] flex-col gap-1.5 sm:max-w-[11rem]">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Method
          </span>
          <select
            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
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
        <button type="button" className={btnPrimary} onClick={() => void load()}>
          Apply
        </button>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
          Loading audit trail…
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : logs.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center shadow-sm">
          <p className="mb-0 font-semibold text-slate-800">No audit entries</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[64rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                    When
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                    User
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                    Method
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                    Path
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                    Time (ms)
                  </th>
                </tr>
              </thead>
              <tbody>
                {logs.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-teal-50/40"
                  >
                    <td className="whitespace-nowrap px-4 py-3 align-top text-slate-700">
                      {row.created_display}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="font-medium text-slate-900">{row.user_role || '—'}</div>
                      <div className="text-xs text-hub-muted">ID {row.user_id ?? '—'}</div>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span className="inline-flex rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-800">
                        {row.method}
                      </span>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${statusTone(row.status_code)}`}
                      >
                        {row.status_code}
                      </span>
                    </td>
                    <td className="max-w-lg break-all px-4 py-3 align-top font-mono text-xs text-slate-700">
                      {row.path}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 align-top text-slate-700">
                      {row.duration_ms ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={btnMuted}
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
              className={btnMuted}
              disabled={filters.page >= (data?.pagination?.pages || 1)}
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
            >
              Next
            </button>
          </div>
        </>
      )}
    </>
  )
}

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

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <div>
            <h1 className="mb-0 text-2xl font-bold text-slate-900">Bugs</h1>
            <p className="mb-0 mt-1 text-sm text-hub-muted">
              Failed actions, system errors, and user-submitted bug reports
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={tab === 'errors' ? btnPrimary : btnMuted}
              onClick={() => setTab('errors')}
            >
              Error log
            </button>
            <button
              type="button"
              className={tab === 'reports' ? btnPrimary : btnMuted}
              onClick={() => setTab('reports')}
            >
              Reports
            </button>
          </div>

          {tab === 'errors' ? <ErrorLogPanel /> : (
            <BugReportsPanel
              fetchReports={fetchTechBugReports}
              submitReport={submitTechBugReport}
              updateStatus={updateTechBugStatus}
            />
          )}
        </div>
      </div>
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

  return (
    <>
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:flex-wrap sm:items-end">
        <label className="flex min-w-[9rem] flex-col gap-1.5 sm:max-w-[12rem]">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Type</span>
          <select
            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
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
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</span>
          <select
            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
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
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Range</span>
          <select
            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
            value={filters.date_filter}
            onChange={(e) => setFilters((f) => ({ ...f, date_filter: e.target.value }))}
          >
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7d</option>
            <option value="30d">Last 30d</option>
            <option value="all">All time</option>
          </select>
        </label>
        <button type="button" className={btnPrimary} onClick={() => void load()}>
          Apply
        </button>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
          Loading error log…
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : entries.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center shadow-sm">
          <p className="mb-0 font-semibold text-slate-800">No entries</p>
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry: any, idx: number) => (
            <article
              key={`${entry.type}-${entry.id || idx}-${entry.timestamp}`}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                <span className="rounded-lg bg-slate-100 px-2.5 py-1 font-semibold uppercase text-slate-800">
                  {entry.type}
                </span>
                <span className="text-hub-muted">{entry.timestamp_display}</span>
                {entry.status ? (
                  <span className="rounded-lg bg-amber-100 px-2.5 py-1 font-medium text-amber-900">
                    {entry.status}
                  </span>
                ) : null}
              </div>
              <h3 className="mb-1 text-base font-semibold text-slate-900">
                {entry.title || entry.action || 'Entry'}
              </h3>
              <p className="mb-0 text-sm leading-relaxed text-slate-700">
                {entry.error_message || entry.description || '—'}
              </p>
              {entry.username ? (
                <p className="mb-0 mt-2 text-xs text-hub-muted">User: {entry.username}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </>
  )
}

function portalStatusTone(status: string | null | undefined) {
  const s = (status || '').toLowerCase()
  if (s.includes('active') && !s.includes('inactive')) return 'bg-emerald-100 text-emerald-800'
  if (s.includes('former') || s.includes('inactive') || s.includes('closed')) {
    return 'bg-slate-100 text-slate-700'
  }
  return 'bg-amber-100 text-amber-900'
}

function userMatchesQuery(user: any, q: string) {
  if (!q) return true
  const hay = [user.username, user.role, user.login_id, user.portal_status, user.email]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return hay.includes(q)
}

function UserBucket({ title, users }: { title: string; users: any[] }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
        <h2 className="mb-0 text-sm font-bold text-slate-900">
          {title}{' '}
          <span className="font-normal text-hub-muted">({users.length})</span>
        </h2>
      </div>
      {users.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-hub-muted">None in this group</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-white">
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Username
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Role
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Login ID
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Status
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.id}
                  className="border-b border-slate-100 last:border-b-0 hover:bg-teal-50/40"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {u.username}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-700">{u.role}</td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">
                    {u.login_id || '—'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${portalStatusTone(u.portal_status)}`}
                    >
                      {u.portal_status || '—'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-end">
                    <Link to={`/tech/users/${u.id}`} className={btnMuted}>
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function TechUserManagementPage() {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  useEffect(() => {
    setLoading(true)
    void fetchTechUsers()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load users'))
      .finally(() => setLoading(false))
  }, [])

  const query = q.trim().toLowerCase()
  const buckets = data
    ? [
        {
          title: 'Students (current)',
          users: (data.students_current || []).filter((u: any) => userMatchesQuery(u, query)),
        },
        {
          title: 'Students (former)',
          users: (data.students_former || []).filter((u: any) => userMatchesQuery(u, query)),
        },
        {
          title: 'Staff (current)',
          users: (data.staff_current || []).filter((u: any) => userMatchesQuery(u, query)),
        },
        {
          title: 'Staff (former)',
          users: (data.staff_former || []).filter((u: any) => userMatchesQuery(u, query)),
        },
      ]
    : []

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <div>
            <h1 className="mb-0 text-2xl font-bold text-slate-900">User Management</h1>
            <p className="mb-0 mt-1 text-sm text-hub-muted">
              Portal accounts, password resets, and impersonation
            </p>
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-end">
            <label className="flex min-w-[14rem] flex-1 flex-col gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Search
              </span>
              <input
                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
                placeholder="Username, role, login ID, or status…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
              Loading users…
            </div>
          ) : error ? (
            <div className="alert alert-danger">{error}</div>
          ) : (
            <div className="space-y-4">
              {buckets.map((bucket) => (
                <UserBucket key={bucket.title} title={bucket.title} users={bucket.users} />
              ))}
            </div>
          )}
        </div>
      </div>
    </ManagementPageShell>
  )
}

export function TechUserDetailPage() {
  const { userId = '' } = useParams()
  const id = Number(userId)
  const [data, setData] = useState<any>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchTechUser(id)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load user'))
  }, [id])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <Link to="/tech/users" className={btnMuted}>
            ← Back to users
          </Link>
          {error ? <div className="alert alert-danger">{error}</div> : null}
          {message ? (
            <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
              {message}
            </div>
          ) : null}
          {!data ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
              Loading user…
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h1 className="mb-1 text-2xl font-bold text-slate-900">{data.user.username}</h1>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="text-hub-muted">{data.user.role}</span>
                    <span
                      className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${portalStatusTone(data.user.portal_status)}`}
                    >
                      {data.user.portal_status}
                    </span>
                  </div>
                </div>
              </div>

              {data.profile ? (
                <dl className="mb-5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Name
                    </dt>
                    <dd className="mb-0 mt-0.5 text-sm font-medium text-slate-900">
                      {data.profile.first_name} {data.profile.last_name}
                    </dd>
                  </div>
                  {data.profile.kind === 'student' ? (
                    <>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Student ID
                        </dt>
                        <dd className="mb-0 mt-0.5 font-mono text-sm text-slate-900">
                          {data.profile.student_id || '—'}
                        </dd>
                      </div>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Grade
                        </dt>
                        <dd className="mb-0 mt-0.5 text-sm text-slate-900">
                          {data.profile.grade_level ?? '—'}
                        </dd>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Staff ID
                        </dt>
                        <dd className="mb-0 mt-0.5 font-mono text-sm text-slate-900">
                          {data.profile.staff_id || '—'}
                        </dd>
                      </div>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Position
                        </dt>
                        <dd className="mb-0 mt-0.5 text-sm text-slate-900">
                          {data.profile.position || 'Staff'}
                        </dd>
                      </div>
                    </>
                  )}
                  {data.profile.email ? (
                    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5 sm:col-span-2">
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Email
                      </dt>
                      <dd className="mb-0 mt-0.5 text-sm text-slate-900">{data.profile.email}</dd>
                    </div>
                  ) : null}
                </dl>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className={btnPrimary}
                  onClick={async () => {
                    try {
                      const res = await resetTechUserPassword(id)
                      setMessage(
                        `${res.message}${res.temporary_password ? ` Temp password: ${res.temporary_password}` : ''}`,
                      )
                    } catch (err) {
                      setMessage(err instanceof Error ? err.message : 'Reset failed')
                    }
                  }}
                >
                  Reset password
                </button>
                {data.can_impersonate ? (
                  <button
                    type="button"
                    className={btnMuted}
                    onClick={async () => {
                      if (!window.confirm(`Impersonate ${data.user.username}?`)) return
                      try {
                        const res = await impersonateTechUser(id)
                        window.location.assign(res.redirect || '/app')
                      } catch (err) {
                        setMessage(err instanceof Error ? err.message : 'Impersonate failed')
                      }
                    }}
                  >
                    Impersonate
                  </button>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>
    </ManagementPageShell>
  )
}
