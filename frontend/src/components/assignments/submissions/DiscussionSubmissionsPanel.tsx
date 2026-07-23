import { useState } from 'react'
import {
  saveIndividualStudentGrade,
  type DiscussionSubmissionRow,
} from '../../../api/assignmentWorkspace'
import { formatWhen, StudentAvatar } from './submissionsShared'
import type { AssignmentWorkspaceScope } from '../../../utils/assignmentWorkspaceScope'

type Props = {
  assignmentId: number
  totalPoints: number
  rows: DiscussionSubmissionRow[]
  workspaceScope?: AssignmentWorkspaceScope
  onSaved: () => void
}

type Draft = { score: string; comment: string }

function CheckItem({ met, label }: { met: boolean; label: string }) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <span
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          met ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'
        }`}
      >
        <i className={`bi ${met ? 'bi-check-lg' : 'bi-dash'}`} />
      </span>
      <span className={met ? 'text-hub-text' : 'text-amber-900'}>{label}</span>
    </div>
  )
}

export function DiscussionSubmissionsPanel({
  assignmentId,
  totalPoints,
  rows,
  workspaceScope = 'management',
  onSaved,
}: Props) {
  const [drafts, setDrafts] = useState<Record<number, Draft>>(() => {
    const init: Record<number, Draft> = {}
    for (const row of rows) {
      const score = row.grade?.score ?? row.grade?.points_earned
      init[row.student.id] = {
        score: score != null && score > 0 ? String(score) : '',
        comment: row.grade?.comment || '',
      }
    }
    return init
  })
  const [savingId, setSavingId] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<number | null>(rows[0]?.student.id ?? null)

  async function saveRow(row: DiscussionSubmissionRow) {
    const draft = drafts[row.student.id]
    if (!draft) return
    setSavingId(row.student.id)
    setMessage(null)
    try {
      await saveIndividualStudentGrade(assignmentId, row.student.id, {
        score: draft.score,
        comment: draft.comment,
      }, workspaceScope)
      setMessage(`Saved grade for ${row.student.display_name}`)
      onSaved()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-950">
        Review participation and grade each student here. Discussion assignments are graded on the
        submissions page.
      </div>

      {message ? (
        <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          {message}
        </div>
      ) : null}

      {rows.map((row) => {
        const open = expanded === row.student.id
        const draft = drafts[row.student.id] || { score: '', comment: '' }
        const p = row.participation
        const pct =
          draft.score && totalPoints > 0
            ? Math.round((parseFloat(draft.score) / totalPoints) * 1000) / 10
            : null

        return (
          <div
            key={row.student.id}
            className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
          >
            <button
              type="button"
              onClick={() => setExpanded(open ? null : row.student.id)}
              className="flex w-full items-center gap-3 px-4 py-4 text-left hover:bg-slate-50"
            >
              <StudentAvatar name={row.student.display_name} />
              <div className="min-w-0 flex-1">
                <div className="font-bold text-hub-text">{row.student.display_name}</div>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                      p.requirements_met
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-900'
                    }`}
                  >
                    {p.requirements_met ? 'Requirements met' : 'Needs participation'}
                  </span>
                  <span className="text-xs text-hub-muted">
                    {p.threads_count} post{p.threads_count !== 1 ? 's' : ''} · {p.replies_count}{' '}
                    repl{p.replies_count !== 1 ? 'ies' : 'y'}
                  </span>
                </div>
              </div>
              <div className="text-right">
                {row.is_voided ? (
                  <span className="text-xs font-bold uppercase text-slate-500">Voided</span>
                ) : row.grade?.score != null ? (
                  <span className="font-bold text-hub-text">
                    {row.grade.score}
                    <span className="text-sm font-normal text-hub-muted"> / {totalPoints}</span>
                  </span>
                ) : (
                  <span className="text-sm text-hub-muted">Not graded</span>
                )}
              </div>
              <i className={`bi ${open ? 'bi-chevron-up' : 'bi-chevron-down'} text-hub-muted`} />
            </button>

            {open ? (
              <div className="border-t border-slate-100 px-4 py-4">
                <div className="mb-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <h3 className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Participation checklist
                    </h3>
                    <div className="mt-3 space-y-2">
                      <CheckItem
                        met={p.initial_posts_met}
                        label={`Initial post${p.min_initial_posts !== 1 ? 's' : ''}: ${p.threads_count} / ${p.min_initial_posts} required`}
                      />
                      <CheckItem
                        met={p.replies_met}
                        label={`Replies to discussion: ${p.replies_count} / ${p.min_replies} required`}
                      />
                      <CheckItem
                        met={p.peer_threads_replied > 0}
                        label={`Responded to other students' threads: ${p.peer_threads_replied}`}
                      />
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                    <div className="text-3xl font-extrabold text-hub-text">{p.total_posts}</div>
                    <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Total posts
                    </div>
                  </div>
                </div>

                <div className="mb-4 max-h-96 space-y-3 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <h3 className="text-sm font-bold text-hub-text">
                    <i className="bi bi-chat-square-text me-2" />
                    Student posts
                  </h3>
                  {row.threads.length === 0 && row.replies.length === 0 ? (
                    <p className="text-sm text-hub-muted">No posts yet.</p>
                  ) : null}
                  {row.threads.map((thread) => (
                    <div
                      key={`t-${thread.id}`}
                      className="rounded-lg border-l-4 border-blue-500 bg-white p-3 shadow-sm"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="font-semibold text-blue-800">
                          <i className="bi bi-chat-left-text me-1" />
                          {thread.title || 'Discussion post'}
                          {thread.is_pinned ? (
                            <span className="ms-2 rounded-full bg-amber-100 px-2 py-0.5 text-[0.65rem] font-bold text-amber-800">
                              Pinned
                            </span>
                          ) : null}
                        </div>
                        <span className="text-xs text-hub-muted">{formatWhen(thread.created_at)}</span>
                      </div>
                      <div
                        className="prose prose-sm mt-2 max-w-none text-hub-text"
                        dangerouslySetInnerHTML={{ __html: thread.content }}
                      />
                    </div>
                  ))}
                  {row.replies.map((reply) => (
                    <div
                      key={`r-${reply.id}`}
                      className={`ms-4 rounded-lg border-l-4 bg-white p-3 shadow-sm ${
                        reply.is_peer_thread ? 'border-teal-500' : 'border-slate-400'
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="text-sm font-semibold text-slate-700">
                          <i className="bi bi-reply me-1" />
                          Reply to &ldquo;{reply.thread_title}&rdquo;
                          {reply.is_peer_thread ? (
                            <span className="ms-2 text-xs font-normal text-teal-700">
                              (peer thread)
                            </span>
                          ) : null}
                        </div>
                        <span className="text-xs text-hub-muted">{formatWhen(reply.created_at)}</span>
                      </div>
                      <div
                        className="prose prose-sm mt-2 max-w-none text-hub-text"
                        dangerouslySetInnerHTML={{ __html: reply.content }}
                      />
                    </div>
                  ))}
                </div>

                {!row.is_voided ? (
                  <>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <label className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                          Score (out of {totalPoints})
                        </label>
                        <input
                          type="number"
                          min={0}
                          max={totalPoints}
                          step="0.01"
                          value={draft.score}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [row.student.id]: { ...draft, score: e.target.value },
                            }))
                          }
                          className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                        />
                        {pct != null ? (
                          <p className="mt-1 text-xs text-hub-muted">{pct}%</p>
                        ) : null}
                      </div>
                      <div>
                        <label className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                          Comment
                        </label>
                        <input
                          type="text"
                          value={draft.comment}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [row.student.id]: { ...draft, comment: e.target.value },
                            }))
                          }
                          className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                          placeholder="Participation feedback"
                        />
                      </div>
                    </div>
                    <div className="mt-4 flex justify-end">
                      <button
                        type="button"
                        disabled={savingId === row.student.id}
                        onClick={() => void saveRow(row)}
                        className="rounded-full bg-violet-700 px-5 py-2 text-sm font-semibold text-white hover:bg-violet-800 disabled:opacity-60"
                      >
                        {savingId === row.student.id ? 'Saving…' : 'Save grade'}
                      </button>
                    </div>
                  </>
                ) : null}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
