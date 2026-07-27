import { useCallback, useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { fetchParentHome, selectParentChild } from '../api/parentPortal'
import { ParentEmptyChildren, ParentPageShell, ParentQuickLinks } from '../components/parent/ParentPageShell'
import type { ManagementOutletContext } from '../types/layout'
import type { ParentHomeResponse } from '../types/parentPortal'

function StatCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string
  value: string
  hint?: string
  icon: string
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
          <i className={`bi ${icon}`} aria-hidden />
        </span>
        <div>
          <div className="text-xl font-extrabold text-hub-text">{value}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
          {hint ? <div className="text-xs text-hub-muted">{hint}</div> : null}
        </div>
      </div>
    </div>
  )
}

export function ParentHomePage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const [data, setData] = useState<ParentHomeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchParentHome())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load family portal')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function onSelectChild(studentId: number) {
    setBusy(true)
    setError(null)
    try {
      await selectParentChild(studentId)
      setData(await fetchParentHome())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not switch child')
    } finally {
      setBusy(false)
    }
  }

  const summary = data?.summary
  const childName = data?.active_child?.display_name || 'your child'

  return (
    <ParentPageShell
      title={`Welcome, ${data?.parent_display_name || user.username}`}
      subtitle={
        data?.school_year?.name
          ? `School year ${data.school_year.name}`
          : 'Follow your child\'s progress'
      }
      childrenList={data?.children || []}
      activeChildId={data?.active_child_id ?? null}
      onSelectChild={onSelectChild}
      childBusy={busy}
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      {data && !data.children.length ? <ParentEmptyChildren /> : null}

      {data && data.children.length && summary ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon="bi-graph-up"
              label="GPA"
              value={summary.gpa.toFixed(2)}
              hint={childName}
            />
            <StatCard
              icon="bi-clipboard-check"
              label="Attendance"
              value={
                summary.attendance_rate != null ? `${summary.attendance_rate}%` : '—'
              }
              hint={`${summary.attendance_summary.Present} present`}
            />
            <StatCard
              icon="bi-journal-bookmark"
              label="Classes"
              value={String(summary.classes.length)}
            />
            <StatCard
              icon="bi-file-earmark-pdf"
              label="Report cards"
              value={String(data.report_card_count)}
              hint="Director-approved"
            />
          </div>

          <ParentQuickLinks />

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-teal-100 bg-gradient-to-r from-teal-50 to-white px-5 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">Class averages</h2>
              </div>
              <div className="p-4">
                {summary.classes.length ? (
                  <ul className="mb-0 space-y-2">
                    {summary.classes.map((c) => (
                      <li
                        key={c.id}
                        className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5"
                      >
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-hub-text">{c.name}</div>
                          <div className="text-xs text-hub-muted">{c.teacher_name}</div>
                        </div>
                        <span className="text-sm font-bold text-teal-800">
                          {c.average != null ? `${c.average}%` : '—'}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mb-0 text-sm text-hub-muted">No class grades yet.</p>
                )}
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-teal-100 bg-gradient-to-r from-teal-50 to-white px-5 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">Recent grades</h2>
                <Link to="/parent/grades" className="text-xs font-semibold text-teal-800 hover:underline">
                  View all
                </Link>
              </div>
              <div className="p-4">
                {summary.recent_grades.length ? (
                  <ul className="mb-0 space-y-2">
                    {summary.recent_grades.map((g, idx) => (
                      <li
                        key={`${g.assignment_title}-${idx}`}
                        className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-semibold text-hub-text">
                              {g.assignment_title}
                            </div>
                            <div className="text-xs text-hub-muted">
                              {g.class_name}
                              {g.graded_at_display ? ` · ${g.graded_at_display}` : ''}
                            </div>
                          </div>
                          <span className="text-sm font-bold text-teal-800">
                            {g.percentage != null ? `${g.percentage}%` : '—'}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mb-0 text-sm text-hub-muted">No recent grades yet.</p>
                )}
              </div>
            </section>
          </div>
        </div>
      ) : null}
    </ParentPageShell>
  )
}
