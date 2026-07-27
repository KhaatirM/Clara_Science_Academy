import { useMemo, useState } from 'react'
import type { QuizSubmissionRow } from '../../../api/assignmentWorkspace'
import type { AssignmentWorkspaceScope } from '../../../utils/assignmentWorkspaceScope'
import {
  QuizSubmissionCard,
  quizFilterCounts,
  quizRowMatchesFilter,
  type QuizSubmissionFilter,
} from './QuizSubmissionCard'

type Props = {
  assignmentId: number
  totalPoints: number
  hasOpenEnded: boolean
  rows: QuizSubmissionRow[]
  workspaceScope?: AssignmentWorkspaceScope
  onSaved: () => void
}

const FILTERS: {
  id: QuizSubmissionFilter
  label: string
  icon: string
  active: string
  idle: string
}[] = [
  {
    id: 'all',
    label: 'All',
    icon: 'bi-list-ul',
    active: 'bg-slate-800 text-white border-slate-800',
    idle: 'border-slate-300 bg-white text-slate-700 hover:border-slate-400',
  },
  {
    id: 'submitted',
    label: 'Submitted',
    icon: 'bi-check-circle',
    active: 'bg-sky-600 text-white border-sky-600',
    idle: 'border-sky-300 bg-white text-sky-900 hover:bg-sky-50',
  },
  {
    id: 'late',
    label: 'Late',
    icon: 'bi-clock-history',
    active: 'bg-amber-500 text-white border-amber-500',
    idle: 'border-amber-300 bg-white text-amber-900 hover:bg-amber-50',
  },
  {
    id: 'not_submitted',
    label: 'Not submitted',
    icon: 'bi-x-circle',
    active: 'bg-red-600 text-white border-red-600',
    idle: 'border-red-300 bg-white text-red-800 hover:bg-red-50',
  },
  {
    id: 'graded',
    label: 'Graded',
    icon: 'bi-star',
    active: 'bg-emerald-600 text-white border-emerald-600',
    idle: 'border-emerald-300 bg-white text-emerald-900 hover:bg-emerald-50',
  },
]

export function QuizSubmissionsPanel({
  assignmentId,
  totalPoints,
  hasOpenEnded,
  rows,
  workspaceScope = 'management',
  onSaved,
}: Props) {
  const [filter, setFilter] = useState<QuizSubmissionFilter>('all')
  const counts = useMemo(() => quizFilterCounts(rows, totalPoints), [rows, totalPoints])

  const visible = useMemo(
    () => rows.filter((row) => quizRowMatchesFilter(row, filter, totalPoints)),
    [filter, rows, totalPoints],
  )

  return (
    <div className="space-y-4">
      {hasOpenEnded ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <i className="bi bi-pencil-square me-2" />
          This quiz includes open-ended questions. Expand each student card to score short answers and essays.
        </div>
      ) : (
        <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
          <i className="bi bi-lightning-charge-fill me-2" />
          Fully auto-graded quiz — review attempts and answers below.
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = filter === f.id
          const count = counts[f.id]
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-semibold transition ${
                active ? f.active : f.idle
              }`}
            >
              <i className={`bi ${f.icon}`} aria-hidden />
              {f.label}
              <span className={`rounded-full px-1.5 py-0.5 text-xs ${active ? 'bg-white/20' : 'bg-slate-100'}`}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {visible.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-10 text-center text-sm text-hub-muted">
          <i className="bi bi-inbox mb-2 block text-2xl" aria-hidden />
          No submissions match this filter.
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map((row) => (
            <QuizSubmissionCard
              key={row.student.id}
              row={row}
              totalPoints={totalPoints}
              hasOpenEnded={hasOpenEnded}
              assignmentId={assignmentId}
              workspaceScope={workspaceScope}
              onSaved={onSaved}
            />
          ))}
        </div>
      )}
    </div>
  )
}
