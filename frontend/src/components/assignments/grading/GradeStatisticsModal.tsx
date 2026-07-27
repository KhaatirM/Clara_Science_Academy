import { useCallback, useEffect, useState } from 'react'
import {
  fetchIndividualAssignmentGradeStatistics,
  type AssignmentGradeStatisticsResponse,
} from '../../../api/assignmentWorkspace'
import type { AssignmentWorkspaceScope } from '../../../utils/assignmentWorkspaceScope'

const RANGE_COLORS: Record<string, string> = {
  '90-100': 'bg-emerald-500',
  '80-89': 'bg-sky-500',
  '70-79': 'bg-amber-500',
  '60-69': 'bg-orange-500',
  '0-59': 'bg-red-500',
}

const RANGE_LABELS: Record<string, string> = {
  '90-100': 'A (90–100%)',
  '80-89': 'B (80–89%)',
  '70-79': 'C (70–79%)',
  '60-69': 'D (60–69%)',
  '0-59': 'F (0–59%)',
}

type Props = {
  open: boolean
  assignmentId: number
  workspaceScope?: AssignmentWorkspaceScope
  onClose: () => void
}

export function GradeStatisticsModal({
  open,
  assignmentId,
  workspaceScope = 'management',
  onClose,
}: Props) {
  const [data, setData] = useState<AssignmentGradeStatisticsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchIndividualAssignmentGradeStatistics(assignmentId, workspaceScope))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load statistics')
    } finally {
      setLoading(false)
    }
  }, [assignmentId, workspaceScope])

  useEffect(() => {
    if (open && assignmentId) void load()
  }, [open, assignmentId, load])

  if (!open) return null

  const stats = data?.stats
  const totalPoints = data?.total_points ?? 100
  const dist = data?.grade_distribution ?? {}
  const distMax = Math.max(...Object.values(dist), 1)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between bg-violet-700 px-5 py-4 text-white">
          <div>
            <h2 className="text-lg font-bold">
              <i className="bi bi-bar-chart-fill me-2" />
              Grade Statistics
            </h2>
            {data ? (
              <p className="mt-0.5 text-sm text-white/80">
                {data.assignment.title} · {data.assignment.class_name}
              </p>
            ) : null}
          </div>
          <button type="button" onClick={onClose} className="text-white/80 hover:text-white">
            <i className="bi bi-x-lg" />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          {loading ? (
            <p className="py-8 text-center text-sm text-hub-muted">Loading statistics…</p>
          ) : error ? (
            <div className="py-6 text-center">
              <p className="text-sm text-red-700">{error}</p>
              <button
                type="button"
                onClick={() => void load()}
                className="mt-3 text-sm font-semibold text-violet-700 hover:underline"
              >
                Retry
              </button>
            </div>
          ) : stats ? (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  {
                    label: 'Average',
                    value: `${stats.average_score} / ${totalPoints}`,
                    sub: stats.average_percentage ? `${stats.average_percentage}%` : null,
                    cls: 'text-violet-700',
                  },
                  {
                    label: 'Median',
                    value: `${stats.median_score} / ${totalPoints}`,
                    sub: null,
                    cls: 'text-emerald-700',
                  },
                  {
                    label: 'Highest',
                    value: `${stats.highest_score} / ${totalPoints}`,
                    sub: null,
                    cls: 'text-sky-700',
                  },
                  {
                    label: 'Lowest',
                    value: stats.graded_count > 0 ? `${stats.lowest_score} / ${totalPoints}` : '—',
                    sub: null,
                    cls: 'text-amber-700',
                  },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <div className={`text-xl font-extrabold ${item.cls}`}>{item.value}</div>
                    {item.sub ? <div className="text-xs text-hub-muted">{item.sub}</div> : null}
                    <div className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
                      {item.label}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 grid grid-cols-3 gap-3">
                <div className="rounded-xl border border-slate-200 p-3 text-center">
                  <div className="text-2xl font-extrabold text-hub-text">{stats.graded_count}</div>
                  <div className="text-xs text-hub-muted">Graded / {stats.total_students}</div>
                </div>
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-center">
                  <div className="text-2xl font-extrabold text-emerald-800">{stats.passing_count}</div>
                  <div className="text-xs text-emerald-700">Passing (≥70%)</div>
                </div>
                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-center">
                  <div className="text-2xl font-extrabold text-red-800">{stats.failing_count}</div>
                  <div className="text-xs text-red-700">Failing (&lt;70%)</div>
                </div>
              </div>

              <div className="mt-5">
                <h3 className="mb-3 text-sm font-bold text-hub-text">
                  <i className="bi bi-bar-chart me-2 text-violet-600" />
                  Grade distribution
                </h3>
                <div className="space-y-2">
                  {Object.keys(RANGE_LABELS).map((key) => {
                    const count = dist[key] ?? 0
                    const pct = (count / distMax) * 100
                    return (
                      <div key={key} className="flex items-center gap-3">
                        <div className="w-28 shrink-0 text-xs font-semibold text-hub-muted">
                          {RANGE_LABELS[key]}
                        </div>
                        <div className="relative h-6 flex-1 overflow-hidden rounded-md bg-slate-100">
                          <div
                            className={`h-full rounded-md ${RANGE_COLORS[key]} transition-all`}
                            style={{ width: `${pct}%`, minWidth: count > 0 ? '1.5rem' : 0 }}
                          />
                        </div>
                        <div className="w-6 shrink-0 text-right text-sm font-bold text-hub-text">
                          {count}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {stats.ungraded_count > 0 ? (
                <p className="mt-4 text-xs text-hub-muted">
                  {stats.ungraded_count} student(s) not yet graded.
                </p>
              ) : null}
            </>
          ) : null}
        </div>

        <div className="border-t border-slate-200 px-5 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-violet-700 px-6 py-2 text-sm font-semibold text-white hover:bg-violet-800"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
