import { useCallback, useEffect, useState } from 'react'
import { fetchClassAnalytics } from '../../api/classTools'
import type { ClassAnalyticsResponse } from '../../types/classTools'

type Props = {
  open: boolean
  classId: number
  onClose: () => void
  scope?: 'management' | 'teacher'
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
      <i className={`bi ${icon} mb-1 block text-xl text-teal-700`} aria-hidden />
      <div className="text-2xl font-bold text-hub-text">{value}</div>
      <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
    </div>
  )
}

export function ClassAnalyticsModal({ open, classId, onClose, scope = 'management' }: Props) {
  const [data, setData] = useState<ClassAnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassAnalytics(classId, scope))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [classId, scope])

  useEffect(() => {
    if (open && classId) void load()
  }, [open, classId, load])

  if (!open) return null

  const summary = data?.summary

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between bg-violet-700 px-5 py-4 text-white">
          <div>
            <h2 className="text-lg font-bold">
              <i className="bi bi-graph-up me-2" aria-hidden />
              Reports &amp; Analytics
            </h2>
            {data ? <p className="mt-0.5 text-sm text-white/80">{data.name}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="text-white/80 hover:text-white" aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          {loading ? <p className="text-hub-muted">Loading analytics…</p> : null}
          {error ? <p className="text-red-700">{error}</p> : null}
          {data && summary ? (
            <div className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard label="Students" value={summary.students} icon="bi-people-fill" />
                <StatCard label="Groups" value={summary.groups} icon="bi-people" />
                <StatCard label="Group assignments" value={summary.group_assignments} icon="bi-journal-text" />
              </div>

              {data.groups.length > 0 ? (
                <section>
                  <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-hub-muted">Groups</h3>
                  <ul className="space-y-2">
                    {data.groups.map((g) => (
                      <li key={g.id} className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 text-sm">
                        <span className="font-semibold text-hub-text">{g.name}</span>
                        <span className="text-hub-muted">{g.member_count} members</span>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {data.group_assignments.length > 0 ? (
                <section>
                  <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-hub-muted">Group assignments</h3>
                  <ul className="space-y-2">
                    {data.group_assignments.map((a) => (
                      <li key={a.id} className="rounded-xl border border-slate-200 px-4 py-3 text-sm">
                        <div className="font-semibold text-hub-text">{a.title}</div>
                        <div className="mt-0.5 text-hub-muted">
                          {a.status || 'No status'}
                          {a.due_date ? ` · Due ${new Date(a.due_date).toLocaleDateString()}` : ''}
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {!data.groups.length && !data.group_assignments.length ? (
                <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-hub-muted">
                  No group data yet for this class. Create groups and group assignments to see analytics here.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
