import { Link } from 'react-router-dom'
import type { PdfSubmissionRow } from '../../../api/assignmentWorkspace'
import { GRADE_TONES, gradeToneFromPercent } from '../../../utils/gradeDisplay'
import { StudentAvatar } from './submissionsShared'

function formatSubmissionWhen(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const date = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  const time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return `${date} at ${time}`
}

function gradePercent(row: PdfSubmissionRow, totalPoints: number): number | null {
  if (row.is_voided) return null
  const pct = row.grade?.percentage
  if (pct != null) return Math.round(Number(pct) * 10) / 10
  const score = row.grade?.score ?? row.grade?.points_earned
  if (score == null || totalPoints <= 0) return null
  return Math.round((Number(score) / totalPoints) * 1000) / 10
}

function isGraded(row: PdfSubmissionRow, totalPoints: number) {
  return gradePercent(row, totalPoints) != null
}

function statusAccent(status: string) {
  if (status === 'late') {
    return {
      border: 'border-l-amber-400',
      bg: 'bg-amber-50/40',
      badge: 'bg-amber-100 text-amber-900',
      icon: 'bi-clock-history',
      label: 'Late',
    }
  }
  if (status === 'on_time') {
    return {
      border: 'border-l-emerald-500',
      bg: 'bg-white',
      badge: 'bg-emerald-100 text-emerald-800',
      icon: 'bi-check-circle-fill',
      label: 'On time',
    }
  }
  return {
    border: 'border-l-red-400',
    bg: 'bg-slate-50/80',
    badge: 'bg-red-100 text-red-800',
    icon: 'bi-x-circle-fill',
    label: 'Not submitted',
  }
}

function submissionTypeBadge(type: string | null | undefined) {
  if (type === 'in_person') {
    return {
      cls: 'bg-amber-200 text-amber-950',
      icon: 'bi-file-earmark-text-fill',
      label: 'Paper/In-Person',
    }
  }
  if (type === 'online') {
    return {
      cls: 'bg-sky-100 text-sky-900',
      icon: 'bi-cloud-upload-fill',
      label: 'Online',
    }
  }
  return null
}

type Props = {
  row: PdfSubmissionRow
  totalPoints: number
  gradePath: string
}

export function PdfSubmissionCard({ row, totalPoints, gradePath }: Props) {
  const accent = statusAccent(row.status)
  const typeBadge = submissionTypeBadge(row.submission_type)
  const pct = gradePercent(row, totalPoints)
  const graded = isGraded(row, totalPoints)
  const hasFile = Boolean(row.download_url && row.file_name)
  const isPaper = row.submission_type === 'in_person'

  return (
    <article
      className={`overflow-hidden rounded-2xl border border-slate-200 border-l-4 shadow-sm transition hover:shadow-md ${accent.border} ${accent.bg}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100/80 px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <StudentAvatar name={row.student.display_name} />
          <div className="min-w-0">
            <h3 className="truncate text-base font-bold text-hub-text">{row.student.display_name}</h3>
            <p className="truncate text-xs text-hub-muted">{row.student.email || 'No email'}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-1.5">
          {row.is_voided ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-700 px-2.5 py-0.5 text-xs font-bold text-white">
              <i className="bi bi-slash-circle" />
              Voided
            </span>
          ) : (
            <>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${accent.badge}`}
              >
                <i className={`bi ${accent.icon}`} />
                {accent.label}
              </span>
              {typeBadge ? (
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${typeBadge.cls}`}
                >
                  <i className={`bi ${typeBadge.icon}`} />
                  {typeBadge.label}
                </span>
              ) : null}
              {graded && pct != null ? (
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${GRADE_TONES[gradeToneFromPercent(pct)].solid}`}
                >
                  <i className="bi bi-star-fill" />
                  Graded: {pct}%
                </span>
              ) : null}
            </>
          )}
        </div>
      </div>

      <div className="grid gap-4 px-4 py-4 lg:grid-cols-2">
        <div className="space-y-2 text-sm">
          {row.status !== 'not_submitted' ? (
            <>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-hub-muted">
                  <i className="bi bi-calendar3 me-1" />
                  Latest submit:
                </span>
                <strong className="text-hub-text">{formatSubmissionWhen(row.submitted_at)}</strong>
              </div>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-hub-muted">
                  <i className="bi bi-file-earmark me-1" />
                  Type:
                </span>
                {typeBadge ? (
                  <strong className={isPaper ? 'text-amber-800' : 'text-sky-800'}>
                    <i className={`bi ${typeBadge.icon} me-1`} />
                    {typeBadge.label}
                  </strong>
                ) : (
                  <strong className="text-hub-text">—</strong>
                )}
              </div>
              {row.submission_notes ? (
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-hub-muted">
                    <i className="bi bi-sticky me-1" />
                    Notes:
                  </span>
                  <span className="text-hub-text">{row.submission_notes}</span>
                </div>
              ) : null}
              {row.grade?.comment ? (
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-hub-muted">
                    <i className="bi bi-chat-left-text me-1" />
                    Feedback:
                  </span>
                  <span className="text-hub-text">{row.grade.comment}</span>
                </div>
              ) : null}
            </>
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-950">
              <i className="bi bi-exclamation-triangle me-2" />
              <strong>No submission received.</strong>
            </div>
          )}
        </div>

        <div className="flex flex-col justify-center">
          {graded && pct != null && !row.is_voided ? (
            <div
              className={`overflow-hidden rounded-xl border ${GRADE_TONES[gradeToneFromPercent(pct)].badge}`}
            >
              <div
                className={`flex items-center gap-2 px-3 py-2 text-sm font-bold text-white transition-all ${GRADE_TONES[gradeToneFromPercent(pct)].bar}`}
                style={{ width: `${Math.min(pct, 100)}%`, minWidth: '8rem' }}
              >
                <i className="bi bi-star-fill" />
                Grade: {pct}%
              </div>
            </div>
          ) : !row.is_voided && row.status !== 'not_submitted' ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-sm text-hub-muted">
              Not graded yet
            </div>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-slate-100 px-4 py-3">
        {hasFile ? (
          <a
            href={row.download_url!}
            className="inline-flex items-center gap-1.5 rounded-lg border border-teal-300 bg-teal-50 px-3 py-1.5 text-sm font-semibold text-teal-900 hover:bg-teal-100"
          >
            <i className="bi bi-download" />
            Download
          </a>
        ) : isPaper && row.status !== 'not_submitted' ? (
          <span className="inline-flex cursor-default items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-900">
            <i className="bi bi-file-earmark-text" />
            Paper submission
          </span>
        ) : null}
        {!row.is_voided ? (
          <Link
            to={gradePath}
            className="inline-flex items-center gap-1.5 rounded-lg border border-violet-300 bg-violet-50 px-3 py-1.5 text-sm font-semibold text-violet-900 hover:bg-violet-100"
          >
            <i className="bi bi-pencil-square" />
            Grade
          </Link>
        ) : null}
      </div>
    </article>
  )
}

export function pdfRowMatchesFilter(
  row: PdfSubmissionRow,
  filter: PdfSubmissionFilter,
  totalPoints: number,
) {
  if (filter === 'all') return true
  if (filter === 'submitted') return row.status !== 'not_submitted'
  if (filter === 'late') return row.status === 'late'
  if (filter === 'not_submitted') return row.status === 'not_submitted'
  if (filter === 'graded') return isGraded(row, totalPoints) && !row.is_voided
  return true
}

export type PdfSubmissionFilter = 'all' | 'submitted' | 'late' | 'not_submitted' | 'graded'

export function pdfFilterCounts(rows: PdfSubmissionRow[], totalPoints: number) {
  return {
    all: rows.length,
    submitted: rows.filter((r) => r.status !== 'not_submitted').length,
    late: rows.filter((r) => r.status === 'late').length,
    not_submitted: rows.filter((r) => r.status === 'not_submitted').length,
    graded: rows.filter((r) => isGraded(r, totalPoints) && !r.is_voided).length,
  }
}
