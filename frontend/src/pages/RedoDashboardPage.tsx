import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { fetchRedoDashboard, grantRedoRequest, rejectRedoRequest, revokeRedo } from '../api/redo'
import { ManagementPageHero, ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { ActiveRedoItem, RedoDashboardResponse, RedoRequestItem, ReopeningItem } from '../types/redo'
import { useAssignmentWorkspaceScope, assignmentWorkspaceHubPath } from '../utils/assignmentWorkspaceScope'

function formatDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function defaultDeadline() {
  const d = new Date()
  d.setDate(d.getDate() + 7)
  return d.toISOString().slice(0, 10)
}

function StatCard({ icon, value, label, tone }: { icon: string; value: string | number; label: string; tone: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/90 bg-white p-4 shadow-sm">
      <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${tone}`}>
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-2xl font-extrabold text-hub-text">{value}</div>
        <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function statusBadge(status: string, isOverdue?: boolean) {
  if (status === 'graded') return 'bg-emerald-100 text-emerald-900'
  if (status === 'submitted') return 'bg-sky-100 text-sky-900'
  if (status === 'overdue' || isOverdue) return 'bg-red-100 text-red-800'
  if (status === 'reopened') return 'bg-violet-100 text-violet-900'
  return 'bg-amber-100 text-amber-900'
}

function statusLabel(status: string) {
  if (status === 'graded') return 'Graded'
  if (status === 'submitted') return 'Submitted'
  if (status === 'overdue') return 'Past deadline'
  if (status === 'reopened') return 'Reopened'
  return 'Pending'
}

/** Redo scores are stored as points; show percent using the assignment's total. */
function formatRedoScore(points: number | null | undefined, percent: number | null | undefined, totalPoints: number | null | undefined) {
  if (points == null && percent == null) return '—'
  const total = totalPoints != null && totalPoints > 0 ? totalPoints : 100
  const pct =
    percent != null && !Number.isNaN(Number(percent))
      ? Number(percent)
      : points != null
        ? Math.round((Number(points) / total) * 1000) / 10
        : null
  if (pct == null) return '—'
  if (total === 100) return `${pct}%`
  const ptsLabel = points != null ? String(points) : '—'
  return `${ptsLabel}/${total} (${pct}%)`
}

function matchesFilters(
  item: { class: { id: number | null }; search_text: string; status?: string },
  classId: string,
  status: string,
  search: string,
) {
  if (classId && String(item.class.id) !== classId) return false
  const q = search.trim().toLowerCase()
  if (q && !item.search_text.includes(q)) return false
  if (status && item.status !== status) return false
  return true
}

export function RedoDashboardPage() {
  const workspaceScope = useAssignmentWorkspaceScope()
  const hubPath = assignmentWorkspaceHubPath(workspaceScope)
  const [data, setData] = useState<RedoDashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [classFilter, setClassFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [grantModal, setGrantModal] = useState<RedoRequestItem | null>(null)
  const [grantDeadline, setGrantDeadline] = useState(defaultDeadline())

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchRedoDashboard(workspaceScope))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load redo dashboard')
    } finally {
      setLoading(false)
    }
  }, [workspaceScope])

  useEffect(() => {
    void load()
  }, [load])

  const filteredRequests = useMemo(() => {
    if (!data) return []
    return data.redo_requests.filter((r) => {
      if (classFilter && String(r.class.id) !== classFilter) return false
      const q = search.trim().toLowerCase()
      if (q && !r.search_text.includes(q)) return false
      if (statusFilter && statusFilter !== 'pending') return false
      return true
    })
  }, [data, classFilter, statusFilter, search])

  const filteredReopenings = useMemo(() => {
    if (!data) return []
    return data.reopenings.filter((r) => {
      if (!matchesFilters({ ...r, status: 'reopened' }, classFilter, statusFilter, search)) return false
      return !statusFilter || statusFilter === 'reopened'
    })
  }, [data, classFilter, statusFilter, search])

  const filteredRedos = useMemo(() => {
    if (!data) return []
    return data.redos.filter((r) => matchesFilters(r, classFilter, statusFilter, search))
  }, [data, classFilter, statusFilter, search])

  const runAction = async (fn: () => Promise<{ message: string }>) => {
    setBusy(true)
    setToast(null)
    try {
      const res = await fn()
      setToast(res.message)
      setGrantModal(null)
      await load()
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  const clearFilters = () => {
    setClassFilter('')
    setStatusFilter('')
    setSearch('')
  }

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-4 !rounded-2xl">
        <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15">
            <i className="bi bi-arrow-repeat text-xl" aria-hidden />
          </span>
          <div>
            <h1 className="text-2xl font-extrabold">Redo dashboard</h1>
            <p className="max-w-2xl text-sm text-white/85">
              Pending student requests, active reopenings, and redo opportunities in one place.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to={hubPath}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/30 bg-white/10 px-3 py-2 text-sm font-semibold hover:bg-white/20"
          >
            <i className="bi bi-arrow-left" aria-hidden />
            Back
          </Link>
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-white px-3 py-2 text-sm font-semibold text-slate-900"
          >
            <i className="bi bi-arrow-clockwise" aria-hidden />
            Refresh
          </button>
        </div>
        </div>
      </ManagementPageHero>

      {toast ? (
        <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-4 py-2.5 text-sm text-teal-900">{toast}</div>
      ) : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div>
      ) : null}

      {data ? (
        <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard icon="bi-arrow-repeat" value={data.stats.active_redos} label="Active redos" tone="bg-amber-100 text-amber-800" />
          <StatCard icon="bi-check-circle" value={data.stats.completed_redos} label="Completed" tone="bg-emerald-100 text-emerald-800" />
          <StatCard icon="bi-graph-up-arrow" value={`${data.stats.improvement_rate}%`} label="Avg improvement" tone="bg-sky-100 text-sky-800" />
          <StatCard icon="bi-alarm" value={data.stats.overdue_redos} label="Past redo deadline" tone="bg-red-100 text-red-800" />
        </div>
      ) : null}

      <section className="mb-4 rounded-2xl border border-white/90 bg-white p-4 shadow-lg">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-hub-text">
          <i className="bi bi-funnel-fill text-amber-600" aria-hidden />
          Filters
        </div>
        <div className="grid gap-3 md:grid-cols-12 md:items-end">
          <div className="md:col-span-3">
            <label className="mb-1 block text-xs font-bold uppercase text-hub-muted" htmlFor="redo-class">
              Class
            </label>
            <select
              id="redo-class"
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-semibold"
            >
              <option value="">All classes</option>
              {data?.classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-3">
            <label className="mb-1 block text-xs font-bold uppercase text-hub-muted" htmlFor="redo-status">
              Status
            </label>
            <select
              id="redo-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-semibold"
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="submitted">Submitted</option>
              <option value="graded">Graded</option>
              <option value="overdue">Past redo deadline</option>
              <option value="reopened">Reopened</option>
            </select>
          </div>
          <div className="md:col-span-4">
            <label className="mb-1 block text-xs font-bold uppercase text-hub-muted" htmlFor="redo-search">
              Student
            </label>
            <input
              id="redo-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by student name…"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="button"
              onClick={clearFilters}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Clear
            </button>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="rounded-2xl bg-white p-12 text-center text-hub-muted shadow-lg">Loading…</div>
      ) : !data?.meta.has_active_school_year ? (
        <div className="rounded-2xl bg-white p-12 text-center text-hub-muted shadow-lg">No active school year.</div>
      ) : (
        <div className="space-y-4">
          <RedoSection title="Pending redo requests" subtitle="Grant to set a new deadline, or reject the request." tone="border-amber-300 bg-amber-50">
            {filteredRequests.length ? (
              <DataTable
                headers={['Student', 'Assignment', 'Class', 'Reason', 'Requested', 'Actions']}
                rows={filteredRequests.map((r) => [
                  r.student.display_name,
                  r.assignment.title,
                  r.class.name,
                  r.reason || 'No reason',
                  formatDate(r.requested_at),
                  <div key={r.id} className="flex gap-1">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        setGrantDeadline(defaultDeadline())
                        setGrantModal(r)
                      }}
                      className="rounded-lg bg-emerald-600 px-2 py-1 text-xs font-semibold text-white"
                    >
                      Grant
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void runAction(() => rejectRedoRequest(r.id, workspaceScope))}
                      className="rounded-lg border border-red-300 px-2 py-1 text-xs font-semibold text-red-700"
                    >
                      Reject
                    </button>
                  </div>,
                ])}
              />
            ) : (
              <EmptyRow message="No pending redo requests match your filters." />
            )}
          </RedoSection>

          <RedoSection title="Active reopenings" subtitle="Assignments opened again so students can submit. Graded reopenings leave this list automatically." tone="border-violet-300 bg-violet-50">
            {filteredReopenings.length ? (
              <DataTable
                headers={['Student', 'Assignment', 'Class', 'Reopened', 'Attempts', 'Actions']}
                rows={filteredReopenings.map((r: ReopeningItem) => [
                  r.student.display_name,
                  r.assignment.title,
                  r.class.name,
                  formatDate(r.reopened_at),
                  r.attempts_label ?? (r.additional_attempts > 0 ? String(r.additional_attempts) : '—'),
                  r.grade_url ? (
                    <a key={`g-${r.id}`} href={r.grade_url} className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold">
                      Grade
                    </a>
                  ) : (
                    '—'
                  ),
                ])}
              />
            ) : (
              <EmptyRow message="No active reopenings match your filters." />
            )}
          </RedoSection>

          <RedoSection title="Active redo opportunities" subtitle="Granted redos with deadlines and grading workflow." tone="border-teal-300 bg-teal-50">
            {filteredRedos.length ? (
              <DataTable
                headers={['Student', 'Assignment', 'Class', 'Original', 'Status', 'Deadline', 'Final', 'Actions']}
                rows={filteredRedos.map((r: ActiveRedoItem) => [
                  r.student.display_name,
                  r.assignment.title,
                  r.class.name,
                  r.original_grade != null
                    ? formatRedoScore(r.original_grade, r.original_percent, r.total_points ?? r.assignment.total_points)
                    : 'N/A',
                  <span key={`st-${r.id}`} className={`rounded-full px-2 py-0.5 text-xs font-bold ${statusBadge(r.status, r.is_overdue)}`}>
                    {statusLabel(r.status)}
                  </span>,
                  formatDate(r.redo_deadline),
                  r.final_grade != null
                    ? formatRedoScore(r.final_grade, r.final_percent, r.total_points ?? r.assignment.total_points)
                    : '—',
                  <div key={`act-${r.id}`} className="flex gap-1">
                    {r.grade_url ? (
                      <a href={r.grade_url} className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold">
                        Grade
                      </a>
                    ) : null}
                    {!r.is_used ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          if (window.confirm('Revoke this redo permission?')) {
                            void runAction(() => revokeRedo(r.id, workspaceScope))
                          }
                        }}
                        className="rounded-lg border border-red-300 px-2 py-1 text-xs font-semibold text-red-700"
                      >
                        Revoke
                      </button>
                    ) : null}
                  </div>,
                ])}
              />
            ) : (
              <EmptyRow message="No active redo opportunities match your filters." />
            )}
          </RedoSection>
        </div>
      )}

      {grantModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
            <h2 className="text-lg font-bold text-hub-text">Grant redo</h2>
            <p className="mt-1 text-sm text-hub-muted">
              {grantModal.student.display_name} · {grantModal.assignment.title}
            </p>
            <label className="mt-4 block text-sm font-semibold text-hub-muted" htmlFor="redo-deadline">
              Redo deadline
            </label>
            <input
              id="redo-deadline"
              type="date"
              value={grantDeadline}
              onChange={(e) => setGrantDeadline(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setGrantModal(null)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold">
                Cancel
              </button>
              <button
                type="button"
                disabled={busy || !grantDeadline}
                onClick={() => void runAction(() => grantRedoRequest(grantModal.id, grantDeadline, workspaceScope))}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white"
              >
                Grant redo
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </ManagementPageShell>
  )
}

function RedoSection({
  title,
  subtitle,
  tone,
  children,
}: {
  title: string
  subtitle: string
  tone: string
  children: ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
      <div className={`border-b px-4 py-3 ${tone}`}>
        <h2 className="font-bold text-hub-text">{title}</h2>
        <p className="text-sm text-hub-muted">{subtitle}</p>
      </div>
      <div className="p-0">{children}</div>
    </section>
  )
}

function DataTable({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
            {headers.map((h) => (
              <th key={h} className="px-3 py-2.5">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-100 hover:bg-slate-50/80">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2.5 align-top text-hub-text">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EmptyRow({ message }: { message: string }) {
  return <div className="px-6 py-10 text-center text-sm text-hub-muted">{message}</div>
}
