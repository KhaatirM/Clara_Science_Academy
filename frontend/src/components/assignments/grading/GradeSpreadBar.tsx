import { useMemo } from 'react'
import {
  bucketFromDraft,
  type GradeBucket,
  type SpreadFilter,
} from './gradeUtils'

type DraftScore = { score: string; isVoided: boolean }

const BUCKET_STYLE: Record<GradeBucket, { pill: string; bar: string; label: string }> = {
  A: { pill: 'bg-emerald-100 text-emerald-800', bar: 'bg-emerald-500', label: 'A' },
  B: { pill: 'bg-sky-100 text-sky-800', bar: 'bg-sky-500', label: 'B' },
  C: { pill: 'bg-amber-100 text-amber-900', bar: 'bg-amber-500', label: 'C' },
  D: { pill: 'bg-orange-100 text-orange-900', bar: 'bg-orange-500', label: 'D' },
  F: { pill: 'bg-red-100 text-red-800', bar: 'bg-red-600', label: 'F' },
  ungraded: { pill: 'bg-slate-100 text-slate-600', bar: 'bg-slate-300', label: 'Not entered' },
}

const FILTERS: { id: SpreadFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'passing', label: 'Passing' },
  { id: 'failing', label: 'Failing' },
  { id: 'ungraded', label: 'Not entered' },
]

type Props = {
  drafts: Record<string, DraftScore>
  totalPoints: number
  filter: SpreadFilter
  onFilterChange: (f: SpreadFilter) => void
}

export function GradeSpreadBar({ drafts, totalPoints, filter, onFilterChange }: Props) {
  const counts = useMemo(() => {
    const c: Record<GradeBucket, number> = { A: 0, B: 0, C: 0, D: 0, F: 0, ungraded: 0 }
    for (const d of Object.values(drafts)) {
      if (d.isVoided) continue
      const b = bucketFromDraft(d.score, totalPoints, d.isVoided)
      c[b] += 1
    }
    return c
  }, [drafts, totalPoints])

  const gradedTotal = counts.A + counts.B + counts.C + counts.D + counts.F
  const barTotal = gradedTotal + counts.ungraded || 1

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-bold text-hub-text">
          <i className="bi bi-bar-chart-fill me-2 text-violet-600" />
          Grade spread
        </h2>
        <div className="flex flex-wrap gap-1 rounded-lg bg-slate-100 p-0.5">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => onFilterChange(f.id)}
              className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                filter === f.id
                  ? 'bg-white text-violet-800 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {(['A', 'B', 'C', 'D', 'F', 'ungraded'] as GradeBucket[]).map((b) => (
          <span
            key={b}
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${BUCKET_STYLE[b].pill}`}
          >
            <span className={`h-2 w-2 rounded-full ${BUCKET_STYLE[b].bar}`} />
            {BUCKET_STYLE[b].label} <strong>{counts[b]}</strong>
          </span>
        ))}
      </div>

      <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-slate-100">
        {(['A', 'B', 'C', 'D', 'F', 'ungraded'] as GradeBucket[]).map((b) => {
          const w = (counts[b] / barTotal) * 100
          if (w <= 0) return null
          return (
            <div
              key={b}
              className={`${BUCKET_STYLE[b].bar} transition-all`}
              style={{ width: `${w}%` }}
              title={`${BUCKET_STYLE[b].label}: ${counts[b]}`}
            />
          )
        })}
      </div>

      <p className="mt-2 text-xs text-hub-muted">
        <i className="bi bi-info-circle me-1" />
        Entering <strong>0</strong> is a real grade (F). Leaving points blank means not entered yet.
        Voided students are excluded.
      </p>
    </div>
  )
}
