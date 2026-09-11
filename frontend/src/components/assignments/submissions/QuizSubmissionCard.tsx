import { useMemo, useState } from 'react'
import {
  saveQuizOpenEndedGrades,
  type QuizAttemptDetail,
  type QuizSubmissionRow,
} from '../../../api/assignmentWorkspace'
import type { AssignmentWorkspaceScope } from '../../../utils/assignmentWorkspaceScope'
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

function questionTypeLabel(type: string) {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function officialGradePercent(row: QuizSubmissionRow, totalPoints: number): number | null {
  if (row.is_voided) return null
  const pct = row.grade?.percentage
  if (pct != null) return Math.round(Number(pct) * 10) / 10
  const score = row.grade?.score ?? row.grade?.points_earned
  if (score == null || totalPoints <= 0) return null
  return Math.round((Number(score) / totalPoints) * 1000) / 10
}

export function isQuizGraded(row: QuizSubmissionRow, totalPoints: number) {
  return officialGradePercent(row, totalPoints) != null
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
      border: 'border-l-sky-500',
      bg: 'bg-white',
      badge: 'bg-sky-100 text-sky-900',
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

export type QuizSubmissionFilter = 'all' | 'submitted' | 'late' | 'not_submitted' | 'graded'

export function quizRowMatchesFilter(
  row: QuizSubmissionRow,
  filter: QuizSubmissionFilter,
  totalPoints: number,
) {
  if (filter === 'all') return true
  if (filter === 'submitted') return row.has_submission
  if (filter === 'late') return row.status === 'late'
  if (filter === 'not_submitted') return !row.has_submission
  if (filter === 'graded') return isQuizGraded(row, totalPoints) && !row.is_voided
  return true
}

export function quizFilterCounts(rows: QuizSubmissionRow[], totalPoints: number) {
  return {
    all: rows.length,
    submitted: rows.filter((r) => r.has_submission).length,
    late: rows.filter((r) => r.status === 'late').length,
    not_submitted: rows.filter((r) => !r.has_submission).length,
    graded: rows.filter((r) => isQuizGraded(r, totalPoints) && !r.is_voided).length,
  }
}

type Draft = { comment: string; questions: Record<number, string> }

type Props = {
  row: QuizSubmissionRow
  totalPoints: number
  hasOpenEnded: boolean
  assignmentId: number
  workspaceScope: AssignmentWorkspaceScope
  onSaved: () => void
}

function attemptPercent(att: QuizAttemptDetail | null | undefined, totalPoints: number): number | null {
  if (!att?.parsed_score) return null
  if (att.parsed_score.percentage != null) return Math.round(Number(att.parsed_score.percentage) * 10) / 10
  if (totalPoints <= 0) return null
  return Math.round((Number(att.parsed_score.earned) / totalPoints) * 1000) / 10
}

export function QuizSubmissionCard({
  row,
  totalPoints,
  hasOpenEnded,
  assignmentId,
  workspaceScope,
  onSaved,
}: Props) {
  const [expanded, setExpanded] = useState(false)
  const manualQs = row.questions.filter((q) => q.needs_manual_grade)
  const [draft, setDraft] = useState<Draft>(() => {
    const questions: Record<number, string> = {}
    for (const q of manualQs) {
      questions[q.question_id] = q.points_earned != null ? String(q.points_earned) : ''
    }
    return { comment: row.grade?.comment || '', questions }
  })
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  const attempts = row.quiz_attempt_details?.length ? row.quiz_attempt_details : []
  const answersAttemptNum =
    row.answers_attempt_num ?? (attempts.length ? attempts[attempts.length - 1].attempt_num : null)
  const [selectedAttemptNum, setSelectedAttemptNum] = useState<number>(
    () => answersAttemptNum ?? attempts[attempts.length - 1]?.attempt_num ?? 1,
  )

  const selectedAttempt = useMemo(
    () => attempts.find((a) => a.attempt_num === selectedAttemptNum) ?? attempts[attempts.length - 1] ?? null,
    [attempts, selectedAttemptNum],
  )
  const viewingAnswersAttempt = selectedAttemptNum === answersAttemptNum
  const selectedPct = attemptPercent(selectedAttempt, totalPoints)
  const officialPct = officialGradePercent(row, totalPoints)
  const officialScore = row.grade?.score ?? row.grade?.points_earned
  const barPct = selectedPct ?? (viewingAnswersAttempt && row.auto_points > 0 && totalPoints > 0
    ? Math.round((row.auto_points / totalPoints) * 1000) / 10
    : officialPct)

  const accent = statusAccent(row.status)
  const graded = isQuizGraded(row, totalPoints)

  async function saveManualGrades() {
    if (!manualQs.length) return
    setSaving(true)
    setSaveMsg(null)
    try {
      await saveQuizOpenEndedGrades(
        assignmentId,
        [
          {
            student_id: row.student.id,
            comment: draft.comment,
            questions: manualQs.map((q) => ({
              question_id: q.question_id,
              points: draft.questions[q.question_id] ?? '',
            })),
          },
        ],
        workspaceScope,
      )
      setSaveMsg('Grades saved')
      onSaved()
    } catch (e) {
      setSaveMsg(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

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
              {row.quiz_attempts > 0 ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-bold text-indigo-900">
                  <i className="bi bi-arrow-repeat" />
                  {row.quiz_attempts} {row.quiz_attempts === 1 ? 'attempt' : 'attempts'}
                </span>
              ) : null}
              {graded && officialPct != null ? (
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${GRADE_TONES[gradeToneFromPercent(officialPct)].solid}`}
                >
                  <i className="bi bi-star-fill" />
                  On file: {officialPct}%
                </span>
              ) : row.has_submission && hasOpenEnded ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-200 px-2.5 py-0.5 text-xs font-bold text-amber-950">
                  <i className="bi bi-pencil" />
                  Needs review
                </span>
              ) : null}
            </>
          )}
        </div>
      </div>

      <div className="grid gap-4 px-4 py-4 lg:grid-cols-2">
        <div className="space-y-2 text-sm">
          {row.has_submission ? (
            <>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-hub-muted">
                  <i className="bi bi-calendar3 me-1" />
                  Latest submit:
                </span>
                <strong className="text-hub-text">{formatSubmissionWhen(row.submitted_at)}</strong>
              </div>
              {officialScore != null && !row.is_voided ? (
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-hub-muted">
                    <i className="bi bi-star me-1" />
                    Official grade on file (best):
                  </span>
                  <strong className="text-hub-text">
                    {officialScore} / {totalPoints}
                    {officialPct != null ? ` (${officialPct}%)` : ''}
                  </strong>
                </div>
              ) : null}

              {attempts.length > 1 ? (
                <div className="mt-2 space-y-2">
                  <label className="block text-xs font-bold uppercase tracking-wide text-hub-muted" htmlFor={`attempt-${row.student.id}`}>
                    View attempt
                  </label>
                  <select
                    id={`attempt-${row.student.id}`}
                    value={selectedAttemptNum}
                    onChange={(e) => setSelectedAttemptNum(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-hub-text"
                  >
                    {attempts.map((att) => {
                      const labelScore = att.parsed_score
                        ? `${att.parsed_score.earned}/${att.parsed_score.total} (${att.parsed_score.percentage}%)`
                        : 'no auto score'
                      const answersTag = att.attempt_num === answersAttemptNum ? ' · answers shown below' : ''
                      return (
                        <option key={att.attempt_num} value={att.attempt_num}>
                          Attempt {att.attempt_num} — {formatSubmissionWhen(att.submitted_at)} — {labelScore}
                          {answersTag}
                        </option>
                      )
                    })}
                  </select>
                  <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                    <table className="min-w-full text-xs">
                      <thead className="bg-slate-50 text-left text-hub-muted">
                        <tr>
                          <th className="px-3 py-2">#</th>
                          <th className="px-3 py-2">Submitted</th>
                          <th className="px-3 py-2">Auto score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attempts.map((att) => {
                          const selected = att.attempt_num === selectedAttemptNum
                          return (
                            <tr
                              key={att.attempt_num}
                              className={`cursor-pointer border-t border-slate-100 ${
                                selected ? 'bg-indigo-50' : 'hover:bg-slate-50'
                              }`}
                              onClick={() => setSelectedAttemptNum(att.attempt_num)}
                            >
                              <td className="px-3 py-2 font-semibold">
                                {att.attempt_num}
                                {att.attempt_num === answersAttemptNum ? (
                                  <span className="ms-1 text-[0.65rem] font-bold uppercase text-indigo-700">
                                    answers
                                  </span>
                                ) : null}
                              </td>
                              <td className="px-3 py-2">{formatSubmissionWhen(att.submitted_at)}</td>
                              <td className="px-3 py-2">
                                {att.parsed_score ? (
                                  <>
                                    {att.parsed_score.earned} / {att.parsed_score.total}
                                    <span className="text-hub-muted"> ({att.parsed_score.percentage}%)</span>
                                  </>
                                ) : (
                                  <span className="text-hub-muted">—</span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : row.auto_points > 0 ? (
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-hub-muted">
                    <i className="bi bi-lightning-charge me-1" />
                    Auto-graded:
                  </span>
                  <strong className="text-hub-text">{row.auto_points} pts</strong>
                </div>
              ) : null}
            </>
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-950">
              <i className="bi bi-exclamation-triangle me-2" />
              <strong>No quiz attempt recorded.</strong>
            </div>
          )}
        </div>

        <div className="flex flex-col justify-center gap-2">
          {barPct != null && !row.is_voided ? (
            <div
              className={`overflow-hidden rounded-xl border ${GRADE_TONES[gradeToneFromPercent(barPct)].badge}`}
            >
              <div
                className={`flex items-center gap-2 px-3 py-2 text-sm font-bold text-white transition-all ${GRADE_TONES[gradeToneFromPercent(barPct)].bar}`}
                style={{ width: `${Math.min(barPct, 100)}%`, minWidth: '8rem' }}
              >
                <i className="bi bi-bar-chart-fill" />
                Attempt {selectedAttempt?.attempt_num ?? '—'}: {barPct}%
              </div>
            </div>
          ) : row.has_submission && !row.is_voided ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-sm text-hub-muted">
              {hasOpenEnded ? 'Open-ended items need manual scoring' : 'Awaiting final grade'}
            </div>
          ) : null}
          {selectedAttempt?.parsed_score ? (
            <p className="text-center text-xs text-hub-muted">
              Selected attempt auto score:{' '}
              <strong className="text-hub-text">
                {selectedAttempt.parsed_score.earned} / {selectedAttempt.parsed_score.total}
              </strong>
            </p>
          ) : viewingAnswersAttempt && row.auto_points > 0 ? (
            <p className="text-center text-xs text-hub-muted">
              Current answers auto-total: <strong className="text-hub-text">{row.auto_points} pts</strong>
            </p>
          ) : null}
          {officialPct != null && selectedPct != null && officialPct !== selectedPct ? (
            <p className="text-center text-xs text-hub-muted">
              Official on-file grade remains <strong>{officialPct}%</strong> (best attempt).
            </p>
          ) : null}
        </div>
      </div>

      {row.has_submission ? (
        <div className="border-t border-slate-100 px-4 py-3">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-sm font-semibold text-indigo-900 hover:bg-indigo-50"
          >
            <span>
              <i className="bi bi-ui-checks-grid me-2" />
              {expanded ? 'Hide' : 'Review'} questions & answers ({row.questions.length})
              {answersAttemptNum != null ? ` · attempt ${answersAttemptNum}` : ''}
            </span>
            <i className={`bi ${expanded ? 'bi-chevron-up' : 'bi-chevron-down'}`} />
          </button>

          {expanded ? (
            <div className="mt-3 space-y-3">
              {!viewingAnswersAttempt ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                  <i className="bi bi-info-circle me-1" />
                  Answers below are from <strong>attempt {answersAttemptNum}</strong> (latest). Prior attempt
                  answer text is not stored — switch to attempt {answersAttemptNum} to grade open-ended items.
                </div>
              ) : (
                <div className="rounded-xl border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-sm text-indigo-950">
                  Showing answers for <strong>attempt {answersAttemptNum}</strong> (most recent).
                </div>
              )}

              {row.questions.map((q) => (
                <div
                  key={q.question_id}
                  className={`rounded-xl border p-4 ${
                    q.needs_manual_grade
                      ? 'border-amber-200 bg-amber-50/50'
                      : q.is_correct
                        ? 'border-emerald-200 bg-emerald-50/40'
                        : q.is_correct === false
                          ? 'border-red-200 bg-red-50/40'
                          : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                        Q{q.order}
                      </span>
                      <span className="ms-2 rounded-full bg-slate-200 px-2 py-0.5 text-[0.65rem] font-bold uppercase text-slate-700">
                        {questionTypeLabel(q.type)}
                      </span>
                      <span className="ms-1 text-xs text-hub-muted">({q.max_points} pts)</span>
                    </div>
                    {!q.needs_manual_grade && q.is_correct != null ? (
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                          q.is_correct ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {q.is_correct ? 'Correct' : 'Incorrect'}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm font-semibold text-hub-text">{q.question_text}</p>
                  <div className="mt-2 rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-hub-text">
                    {q.answer_display?.trim() ? q.answer_display : (
                      <span className="text-hub-muted">No answer</span>
                    )}
                  </div>
                  {!q.needs_manual_grade ? (
                    <p className="mt-2 text-xs font-semibold text-hub-muted">
                      {q.points_earned ?? 0} / {q.max_points} points
                    </p>
                  ) : hasOpenEnded && !row.is_voided && viewingAnswersAttempt ? (
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      <label className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                        Points (max {q.max_points})
                      </label>
                      <input
                        type="number"
                        min={0}
                        max={q.max_points}
                        step="0.1"
                        value={draft.questions[q.question_id] ?? ''}
                        onChange={(e) =>
                          setDraft((prev) => ({
                            ...prev,
                            questions: { ...prev.questions, [q.question_id]: e.target.value },
                          }))
                        }
                        className="w-24 rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                      />
                    </div>
                  ) : q.needs_manual_grade ? (
                    <p className="mt-2 text-xs text-hub-muted">
                      Switch to attempt {answersAttemptNum} to enter points for this answer.
                    </p>
                  ) : null}
                </div>
              ))}

              {manualQs.length > 0 && hasOpenEnded && !row.is_voided && viewingAnswersAttempt ? (
                <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-4">
                  <label className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Overall comment
                  </label>
                  <input
                    type="text"
                    value={draft.comment}
                    onChange={(e) => setDraft((prev) => ({ ...prev, comment: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    placeholder="Feedback for this student"
                  />
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                    {saveMsg ? <span className="text-sm text-teal-800">{saveMsg}</span> : <span />}
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => void saveManualGrades()}
                      className="rounded-full bg-violet-700 px-5 py-2 text-sm font-semibold text-white hover:bg-violet-800 disabled:opacity-60"
                    >
                      {saving ? 'Saving…' : 'Save manual grades'}
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}
