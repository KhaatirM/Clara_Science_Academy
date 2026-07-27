import type { GradeStudentRow } from '../../../api/assignmentWorkspace'
import {
  bucketFromDraft,
  formatShortWhen,
  initials,
  letterFromPercent,
  percentFromScore,
  scoreFromPercent,
} from './gradeUtils'

export type GradeRowDraft = {
  score: string
  comment: string
  submission_type: string
  submission_notes_type: string
  submission_notes: string
}

type Props = {
  row: GradeStudentRow
  draft: GradeRowDraft
  totalPoints: number
  maxGradingPoints: number
  disabled: boolean
  selected?: boolean
  onSelectChange?: (checked: boolean) => void
  onChange: (patch: Partial<GradeRowDraft>) => void
  gradeHistoryUrl?: string | null
}

const LETTER_PRESETS = [
  { letter: 'A', pct: 95, cls: 'bg-emerald-500 hover:bg-emerald-600' },
  { letter: 'B', pct: 85, cls: 'bg-sky-500 hover:bg-sky-600' },
  { letter: 'C', pct: 75, cls: 'bg-amber-500 hover:bg-amber-600' },
  { letter: 'D', pct: 65, cls: 'bg-orange-500 hover:bg-orange-600' },
]

const SCORE_PRESETS = [100, 90, 80, 70, 0]

function submissionBadge(type: string | undefined, submittedAt: string | null | undefined) {
  if (type === 'in_person') {
    return {
      label: 'Submitted (Paper)',
      cls: 'bg-amber-100 text-amber-900',
      icon: 'bi-file-earmark-text-fill',
      time: formatShortWhen(submittedAt),
    }
  }
  if (type === 'online') {
    return {
      label: 'Submitted (Online)',
      cls: 'bg-emerald-100 text-emerald-800',
      icon: 'bi-cloud-upload-fill',
      time: formatShortWhen(submittedAt),
    }
  }
  return {
    label: 'Not submitted',
    cls: 'bg-slate-100 text-slate-600',
    icon: 'bi-clock-history',
    time: null,
  }
}

export function PdfPaperGradeCard({
  row,
  draft,
  totalPoints,
  maxGradingPoints,
  disabled,
  selected = false,
  onSelectChange,
  onChange,
  gradeHistoryUrl,
}: Props) {
  const voided = row.grade.is_voided
  const pct = percentFromScore(draft.score, totalPoints)
  const bucket = bucketFromDraft(draft.score, totalPoints, voided)
  const badge = submissionBadge(
    draft.submission_type !== 'not_submitted' ? draft.submission_type : undefined,
    row.submission?.submitted_at,
  )
  const showNotesOther = draft.submission_notes_type === 'Other'
  const commentLen = draft.comment.length

  const perfBorder =
    voided
      ? 'border-slate-300'
      : bucket === 'A'
        ? 'border-emerald-300'
        : bucket === 'B'
          ? 'border-sky-300'
          : bucket === 'C'
            ? 'border-amber-300'
            : bucket === 'D'
              ? 'border-orange-300'
              : bucket === 'F'
                ? 'border-red-300'
                : 'border-slate-200'

  return (
    <div
      className={`rounded-xl border-2 bg-white shadow-sm transition ${perfBorder} ${voided ? 'opacity-70' : ''}`}
      data-grade-bucket={voided ? 'voided' : bucket}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-4 py-3">
        {onSelectChange && !disabled ? (
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => onSelectChange(e.target.checked)}
            className="h-4 w-4 shrink-0 rounded border-slate-300 text-violet-600"
            aria-label={`Select ${row.student.display_name}`}
          />
        ) : null}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-indigo-700 text-sm font-bold text-white">
          {initials(row.student.display_name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-bold text-hub-text">{row.student.display_name}</div>
          <div className="truncate text-xs text-hub-muted">
            {(row.student as { email?: string }).email || 'No email'}
          </div>
        </div>
        <div className="text-right">
          {voided ? (
            <span className="rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-bold uppercase text-slate-600">
              Voided
            </span>
          ) : (
            <>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${badge.cls}`}
              >
                <i className={`bi ${badge.icon}`} />
                {badge.label}
              </span>
              {badge.time ? (
                <div className="mt-0.5 text-[0.65rem] text-hub-muted">{badge.time}</div>
              ) : null}
            </>
          )}
        </div>
      </div>

      <div className="grid gap-3 p-4 lg:grid-cols-12">
        {/* Status row */}
        <div className="grid gap-2 sm:grid-cols-2 lg:col-span-12">
          <div>
            <label className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
              Submission status
            </label>
            <select
              disabled={disabled}
              value={draft.submission_type}
              onChange={(e) => onChange({ submission_type: e.target.value })}
              className="mt-0.5 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            >
              <option value="not_submitted">Not submitted</option>
              <option value="in_person">Submitted (Paper/In-Person)</option>
              <option value="online">Submitted (Online)</option>
            </select>
          </div>
          <div>
            <label className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
              Submission notes
            </label>
            <select
              disabled={disabled}
              value={draft.submission_notes_type}
              onChange={(e) => onChange({ submission_notes_type: e.target.value })}
              className="mt-0.5 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            >
              <option value="On-Time">On-Time</option>
              <option value="Late">Late</option>
              <option value="Other">Other</option>
            </select>
            {showNotesOther ? (
              <input
                type="text"
                disabled={disabled}
                value={draft.submission_notes}
                onChange={(e) => onChange({ submission_notes: e.target.value })}
                placeholder="e.g. Resubmitted, Excused…"
                className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
              />
            ) : null}
          </div>
        </div>

        {/* Points */}
        <div className="lg:col-span-4">
          <label className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
            Points earned
          </label>
          <div className="mt-1.5 grid grid-cols-4 gap-1.5">
            {LETTER_PRESETS.map((p) => (
              <button
                key={p.letter}
                type="button"
                disabled={disabled}
                title={`${p.letter} (${p.pct}%)`}
                onClick={() => onChange({ score: scoreFromPercent(p.pct, totalPoints) })}
                className={`h-9 rounded-lg text-sm font-bold text-white ${p.cls} disabled:opacity-40`}
              >
                {p.letter}
              </button>
            ))}
          </div>
          <div className="mt-1.5 grid grid-cols-5 gap-1.5">
            {SCORE_PRESETS.map((n) => (
              <button
                key={n}
                type="button"
                disabled={disabled}
                onClick={() => onChange({ score: String(n) })}
                className="flex h-9 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-40"
              >
                {n === 100 ? '💯' : n}
              </button>
            ))}
          </div>
          <div className="mt-2 flex items-center gap-1">
            <input
              type="number"
              min={0}
              max={maxGradingPoints}
              step="0.1"
              disabled={disabled}
              value={draft.score}
              onChange={(e) => onChange({ score: e.target.value })}
              placeholder="0"
              className="w-full rounded-lg border border-slate-200 px-2 py-2 text-lg font-bold text-hub-text"
            />
            <span className="shrink-0 text-sm font-semibold text-hub-muted">/ {totalPoints}</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all"
              style={{ width: `${Math.min(pct ?? 0, 100)}%` }}
            />
          </div>
          <div className="mt-0.5 text-xs text-hub-muted">{pct != null ? `${pct}%` : '—'}</div>
        </div>

        {/* Feedback */}
        <div className="lg:col-span-5">
          <label className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
            Feedback
          </label>
          <textarea
            disabled={disabled}
            value={draft.comment}
            onChange={(e) => onChange({ comment: e.target.value.slice(0, 500) })}
            rows={4}
            maxLength={500}
            placeholder="Add constructive feedback for the student…"
            className="mt-0.5 w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
          <div className="text-right text-xs text-hub-muted">{commentLen}/500</div>
        </div>

        {/* Current grade */}
        <div className="lg:col-span-3">
          <label className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
            Current grade
          </label>
          <div className="mt-0.5 rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
            {voided ? (
              <div className="text-sm font-semibold text-slate-500">Voided</div>
            ) : pct != null ? (
              <>
                <div className="text-2xl font-extrabold text-emerald-700">
                  {draft.score}
                  <span className="text-base font-normal text-hub-muted"> / {totalPoints}</span>
                </div>
                <div className="text-sm text-hub-muted">
                  ({pct}%) {letterFromPercent(pct)}
                </div>
              </>
            ) : (
              <div className="text-sm text-hub-muted">Not entered</div>
            )}
            {gradeHistoryUrl ? (
              <a
                href={gradeHistoryUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-violet-700 hover:underline"
              >
                <i className="bi bi-clock-history" />
                History
              </a>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
