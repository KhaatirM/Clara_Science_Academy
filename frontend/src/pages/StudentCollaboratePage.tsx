import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import {
  fetchStudentCollaborate,
  submitCollaborateConflict,
  submitCollaborateFeedback,
  submitCollaborateJournal,
} from '../api/studentCollaborate'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type {
  StudentCollaborateFeedbackSession,
  StudentCollaborateGroupAssignment,
  StudentCollaborateResponse,
} from '../types/studentCollaborate'

type ModalKind = 'feedback' | 'journal' | 'conflict' | null
type HistoryTab = 'feedback' | 'journals' | 'conflicts'

function severityTone(level: string) {
  const s = (level || '').toLowerCase()
  if (s === 'critical') return 'bg-rose-100 text-rose-800'
  if (s === 'high') return 'bg-amber-100 text-amber-900'
  if (s === 'medium') return 'bg-sky-100 text-sky-800'
  return 'bg-slate-100 text-slate-700'
}

function statusTone(status: string) {
  const s = (status || '').toLowerCase()
  if (s === 'resolved') return 'bg-emerald-100 text-emerald-800'
  if (s === 'investigating') return 'bg-sky-100 text-sky-800'
  if (s === 'escalated') return 'bg-rose-100 text-rose-800'
  return 'bg-amber-100 text-amber-900'
}

export function StudentCollaboratePage() {
  const [data, setData] = useState<StudentCollaborateResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [modal, setModal] = useState<ModalKind>(null)
  const [historyTab, setHistoryTab] = useState<HistoryTab>('feedback')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchStudentCollaborate())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load collaborate hub')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const onSubmitted = async (msg: string) => {
    setMessage(msg)
    setModal(null)
    await load()
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading collaborate hub…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <>
              <CollaborateBody
                data={data}
                message={message}
                historyTab={historyTab}
                onHistoryTab={setHistoryTab}
                onOpenModal={setModal}
                onDismissMessage={() => setMessage(null)}
              />
              {modal === 'feedback' ? (
                <FeedbackModal
                  sessions={data.available_feedback_sessions}
                  onClose={() => setModal(null)}
                  onSubmitted={onSubmitted}
                />
              ) : null}
              {modal === 'journal' ? (
                <JournalModal
                  assignments={data.group_assignments}
                  onClose={() => setModal(null)}
                  onSubmitted={onSubmitted}
                />
              ) : null}
              {modal === 'conflict' ? (
                <ConflictModal
                  data={data}
                  onClose={() => setModal(null)}
                  onSubmitted={onSubmitted}
                />
              ) : null}
            </>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function CollaborateBody({
  data,
  message,
  historyTab,
  onHistoryTab,
  onOpenModal,
  onDismissMessage,
}: {
  data: StudentCollaborateResponse
  message: string | null
  historyTab: HistoryTab
  onHistoryTab: (tab: HistoryTab) => void
  onOpenModal: (kind: ModalKind) => void
  onDismissMessage: () => void
}) {
  return (
    <>
      <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
              Student portal
            </p>
            <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Collaborate</h1>
            <p className="mb-0 mt-1 max-w-xl text-sm text-teal-50/95">
              Peer feedback, reflection journals, and conflict reports for group work
              {data.school_year_name ? ` · ${data.school_year_name}` : ''}
            </p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <HeroStat icon="bi-arrow-repeat" label="360° feedback" value={data.stats.feedback} />
          <HeroStat icon="bi-journal-text" label="Journals" value={data.stats.journals} />
          <HeroStat icon="bi-exclamation-triangle" label="Conflicts" value={data.stats.conflicts} />
          <HeroStat icon="bi-inbox" label="Open feedback" value={data.stats.open_feedback} />
        </div>
      </header>

      {message ? (
        <div className="mb-4 flex items-start justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
          <span>
            <i className="bi bi-check-circle-fill me-2 text-emerald-700" aria-hidden />
            {message}
          </span>
          <button type="button" className="font-semibold text-emerald-800" onClick={onDismissMessage}>
            Dismiss
          </button>
        </div>
      ) : null}

      <div className="mb-4 grid gap-4 md:grid-cols-3">
        <ActionCard
          tone="from-cyan-700 to-teal-600"
          icon="bi-arrow-repeat"
          title="360° feedback"
          body="Rate peers on collaboration and contribution when your teacher opens a session."
          cta={
            data.available_feedback_sessions.length
              ? `Give feedback (${data.available_feedback_sessions.length})`
              : 'No open sessions'
          }
          disabled={!data.available_feedback_sessions.length}
          onClick={() => onOpenModal('feedback')}
        />
        <ActionCard
          tone="from-emerald-700 to-teal-600"
          icon="bi-journal-text"
          title="Reflection journal"
          body="Reflect on group work—what went well, what was hard, and what you learned."
          cta="Write a journal"
          disabled={!data.group_assignments.length}
          onClick={() => onOpenModal('journal')}
        />
        <ActionCard
          tone="from-rose-600 to-orange-500"
          icon="bi-exclamation-triangle-fill"
          title="Report a conflict"
          body="Confidentially flag group issues so your teacher can help resolve them."
          cta="Report conflict"
          disabled={!data.group_assignments.length}
          onClick={() => onOpenModal('conflict')}
        />
      </div>

      {!data.group_assignments.length ? (
        <div className="mb-4 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-hub-muted">
          Journals and conflict reports become available once you are placed in a class group with
          group assignments.
        </div>
      ) : null}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="mb-0 text-base font-bold text-hub-text">
            <i className="bi bi-clock-history me-2 text-teal-700" aria-hidden />
            Your history
          </h2>
        </div>
        <div className="flex flex-wrap gap-2 border-b border-slate-100 px-4 py-3">
          {(
            [
              ['feedback', `Feedback (${data.feedback_history.length})`],
              ['journals', `Journals (${data.journal_history.length})`],
              ['conflicts', `Conflicts (${data.conflict_history.length})`],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => onHistoryTab(id)}
              className={`rounded-full px-3 py-1.5 text-sm font-semibold ${
                historyTab === id
                  ? 'bg-teal-700 text-white'
                  : 'border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="p-4">
          {historyTab === 'feedback' ? <FeedbackHistoryList items={data.feedback_history} /> : null}
          {historyTab === 'journals' ? <JournalHistoryList items={data.journal_history} /> : null}
          {historyTab === 'conflicts' ? <ConflictHistoryList items={data.conflict_history} /> : null}
        </div>
      </section>
    </>
  )
}

function HeroStat({ icon, label, value }: { icon: string; label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3 backdrop-blur-sm">
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-100">
        <i className={`bi ${icon} me-1`} aria-hidden />
        {label}
      </p>
      <p className="mb-0 text-2xl font-bold">{value}</p>
    </div>
  )
}

function ActionCard({
  tone,
  icon,
  title,
  body,
  cta,
  disabled,
  onClick,
}: {
  tone: string
  icon: string
  title: string
  body: string
  cta: string
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <article className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className={`bg-gradient-to-r ${tone} px-4 py-4 text-white`}>
        <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-2xl bg-white/20 text-xl">
          <i className={`bi ${icon}`} aria-hidden />
        </div>
        <h3 className="mb-0 text-lg font-bold">{title}</h3>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <p className="mb-0 flex-1 text-sm text-hub-muted">{body}</p>
        <button
          type="button"
          disabled={disabled}
          onClick={onClick}
          className="rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {cta}
        </button>
      </div>
    </article>
  )
}

function EmptyHistory({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-hub-muted">
      {label}
    </div>
  )
}

function FeedbackHistoryList({
  items,
}: {
  items: StudentCollaborateResponse['feedback_history']
}) {
  if (!items.length) return <EmptyHistory label="No 360° feedback submitted yet." />
  return (
    <ul className="mb-0 space-y-2">
      {items.map((item) => (
        <li
          key={item.id}
          className="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-3"
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="mb-0.5 font-semibold text-hub-text">{item.session_title}</p>
              <p className="mb-0 text-sm text-hub-muted">
                For {item.target_name}
                {item.class_name ? ` · ${item.class_name}` : ''}
              </p>
              {item.preview ? (
                <p className="mb-0 mt-1 text-sm text-hub-muted">{item.preview}</p>
              ) : null}
            </div>
            <div className="text-right text-xs text-hub-muted">
              <p className="mb-1">{item.submitted_display || '—'}</p>
              {item.is_anonymous ? (
                <span className="rounded-full bg-slate-200 px-2 py-0.5 font-semibold text-slate-700">
                  Anonymous
                </span>
              ) : (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-800">
                  Submitted
                </span>
              )}
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function JournalHistoryList({
  items,
}: {
  items: StudentCollaborateResponse['journal_history']
}) {
  if (!items.length) return <EmptyHistory label="No reflection journals yet." />
  return (
    <ul className="mb-0 space-y-2">
      {items.map((item) => (
        <li
          key={item.id}
          className="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-3"
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="mb-0.5 font-semibold text-hub-text">{item.assignment_title}</p>
              <p className="mb-0 text-sm text-hub-muted">{item.group_name}</p>
              {item.reflection_preview ? (
                <p className="mb-0 mt-1 text-sm text-hub-muted">{item.reflection_preview}</p>
              ) : null}
            </div>
            <div className="text-right text-xs">
              <p className="mb-1 text-hub-muted">{item.submitted_display || '—'}</p>
              <p className="mb-0 font-semibold text-teal-800">
                Collab {item.collaboration_rating}/5 · Learn {item.learning_rating}/5
              </p>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function ConflictHistoryList({
  items,
}: {
  items: StudentCollaborateResponse['conflict_history']
}) {
  if (!items.length) return <EmptyHistory label="No conflict reports yet." />
  return (
    <ul className="mb-0 space-y-2">
      {items.map((item) => (
        <li
          key={item.id}
          className="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-3"
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="mb-0.5 font-semibold text-hub-text">{item.assignment_title}</p>
              <p className="mb-1 text-sm text-hub-muted">
                {item.group_name} · {item.conflict_type_label}
              </p>
              {item.description_preview ? (
                <p className="mb-0 text-sm text-hub-muted">{item.description_preview}</p>
              ) : null}
            </div>
            <div className="flex flex-col items-end gap-1 text-xs">
              <p className="mb-0 text-hub-muted">{item.reported_display || '—'}</p>
              <span className={`rounded-full px-2 py-0.5 font-semibold capitalize ${severityTone(item.severity_level)}`}>
                {item.severity_level || '—'}
              </span>
              <span className={`rounded-full px-2 py-0.5 font-semibold ${statusTone(item.status)}`}>
                {item.status_label}
              </span>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function ModalShell({
  title,
  tone,
  onClose,
  children,
}: {
  title: string
  tone: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/45 p-3 sm:items-center">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="Close" onClick={onClose} />
      <div className="relative z-10 flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className={`bg-gradient-to-r ${tone} px-4 py-3 text-white`}>
          <div className="flex items-center justify-between gap-2">
            <h2 className="mb-0 text-lg font-bold">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full bg-white/20 px-2 py-1 text-sm font-bold hover:bg-white/30"
            >
              Close
            </button>
          </div>
        </div>
        <div className="overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  )
}

function FeedbackModal({
  sessions,
  onClose,
  onSubmitted,
}: {
  sessions: StudentCollaborateFeedbackSession[]
  onClose: () => void
  onSubmitted: (msg: string) => Promise<void>
}) {
  const [sessionId, setSessionId] = useState(sessions[0]?.id ? String(sessions[0].id) : '')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [anonymous, setAnonymous] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const session = useMemo(
    () => sessions.find((s) => String(s.id) === sessionId) || null,
    [sessions, sessionId],
  )

  useEffect(() => {
    setAnswers({})
  }, [sessionId])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!session) return
    setBusy(true)
    setError(null)
    try {
      const payloadAnswers: Record<string, string | number> = {}
      for (const c of session.criteria) {
        const raw = answers[c.name]
        if (c.type === 'rating' || c.type === 'scale') {
          if (raw) payloadAnswers[c.name] = Number(raw)
          else if (c.required) throw new Error(`Please rate ${c.name}`)
        } else if (raw) {
          payloadAnswers[c.name] = raw
        } else if (c.required) {
          throw new Error(`Please complete ${c.name}`)
        }
      }
      const res = await submitCollaborateFeedback({
        feedback360_id: session.id,
        answers: payloadAnswers,
        is_anonymous: anonymous,
      })
      await onSubmitted(res.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit feedback')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell title="Submit 360° feedback" tone="from-cyan-700 to-teal-600" onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-3">
        {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p> : null}
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Session</span>
          <select
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            required
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title} · {s.target_name} ({s.class_name})
              </option>
            ))}
          </select>
        </label>
        {session?.description ? (
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-hub-muted">{session.description}</p>
        ) : null}
        {session?.criteria.map((c) => (
          <label key={c.name} className="block text-sm">
            <span className="mb-1 block font-semibold text-hub-muted">
              {c.name.replace(/_/g, ' ')}
              {c.required ? ' *' : ''}
            </span>
            {c.description ? <span className="mb-1 block text-xs text-hub-muted">{c.description}</span> : null}
            {c.type === 'text' ? (
              <textarea
                value={answers[c.name] || ''}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [c.name]: e.target.value }))}
                rows={3}
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                required={c.required}
              />
            ) : (
              <select
                value={answers[c.name] || ''}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [c.name]: e.target.value }))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                required={c.required}
              >
                <option value="">Select rating…</option>
                {Array.from({ length: c.scale_max - c.scale_min + 1 }, (_, i) => c.scale_min + i).map(
                  (n) => (
                    <option key={n} value={n}>
                      {n} / {c.scale_max}
                    </option>
                  ),
                )}
              </select>
            )}
          </label>
        ))}
        <label className="flex items-center gap-2 text-sm text-hub-text">
          <input
            type="checkbox"
            checked={anonymous}
            onChange={(e) => setAnonymous(e.target.checked)}
            className="rounded border-slate-300"
          />
          Submit anonymously
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-full bg-teal-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-60"
        >
          {busy ? 'Submitting…' : 'Submit feedback'}
        </button>
      </form>
    </ModalShell>
  )
}

function JournalModal({
  assignments,
  onClose,
  onSubmitted,
}: {
  assignments: StudentCollaborateGroupAssignment[]
  onClose: () => void
  onSubmitted: (msg: string) => Promise<void>
}) {
  const [assignmentKey, setAssignmentKey] = useState(
    assignments[0] ? `${assignments[0].id}:${assignments[0].group_id}` : '',
  )
  const [reflection, setReflection] = useState('')
  const [collab, setCollab] = useState('')
  const [learn, setLearn] = useState('')
  const [challenges, setChallenges] = useState('')
  const [lessons, setLessons] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selected = useMemo(
    () => assignments.find((a) => `${a.id}:${a.group_id}` === assignmentKey) || null,
    [assignments, assignmentKey],
  )

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!selected) return
    setBusy(true)
    setError(null)
    try {
      const res = await submitCollaborateJournal({
        group_assignment_id: selected.id,
        group_id: selected.group_id,
        reflection_text: reflection,
        collaboration_rating: Number(collab),
        learning_rating: Number(learn),
        challenges_faced: challenges,
        lessons_learned: lessons,
      })
      await onSubmitted(res.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit journal')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell title="Write reflection journal" tone="from-emerald-700 to-teal-600" onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-3">
        {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p> : null}
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Group assignment</span>
          <select
            value={assignmentKey}
            onChange={(e) => setAssignmentKey(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            required
          >
            {assignments.map((a) => (
              <option key={`${a.id}-${a.group_id}`} value={`${a.id}:${a.group_id}`}>
                {a.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Reflection *</span>
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            rows={4}
            required
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Share your thoughts on the group work experience…"
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block font-semibold text-hub-muted">Collaboration *</span>
            <select
              value={collab}
              onChange={(e) => setCollab(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">Select…</option>
              {[5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={n}>
                  {n} / 5
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-semibold text-hub-muted">Learning *</span>
            <select
              value={learn}
              onChange={(e) => setLearn(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">Select…</option>
              {[5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={n}>
                  {n} / 5
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Challenges (optional)</span>
          <textarea
            value={challenges}
            onChange={(e) => setChallenges(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Lessons learned (optional)</span>
          <textarea
            value={lessons}
            onChange={(e) => setLessons(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-full bg-teal-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-60"
        >
          {busy ? 'Submitting…' : 'Submit journal'}
        </button>
      </form>
    </ModalShell>
  )
}

function ConflictModal({
  data,
  onClose,
  onSubmitted,
}: {
  data: StudentCollaborateResponse
  onClose: () => void
  onSubmitted: (msg: string) => Promise<void>
}) {
  const assignments = data.group_assignments
  const [assignmentKey, setAssignmentKey] = useState(
    assignments[0] ? `${assignments[0].id}:${assignments[0].group_id}` : '',
  )
  const [conflictType, setConflictType] = useState('')
  const [severity, setSeverity] = useState('')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selected = useMemo(
    () => assignments.find((a) => `${a.id}:${a.group_id}` === assignmentKey) || null,
    [assignments, assignmentKey],
  )

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!selected) return
    setBusy(true)
    setError(null)
    try {
      const res = await submitCollaborateConflict({
        group_assignment_id: selected.id,
        group_id: selected.group_id,
        conflict_type: conflictType,
        severity_level: severity,
        conflict_description: description,
      })
      await onSubmitted(res.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit report')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell title="Report a conflict" tone="from-rose-600 to-orange-500" onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-3">
        <p className="rounded-lg border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-950">
          Confidential reporting — your teacher will review this to help resolve the issue.
        </p>
        {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p> : null}
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Group assignment</span>
          <select
            value={assignmentKey}
            onChange={(e) => setAssignmentKey(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            required
          >
            {assignments.map((a) => (
              <option key={`${a.id}-${a.group_id}`} value={`${a.id}:${a.group_id}`}>
                {a.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Conflict type</span>
          <select
            value={conflictType}
            onChange={(e) => setConflictType(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            required
          >
            <option value="">Select…</option>
            {data.conflict_types.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Severity</span>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            required
          >
            <option value="">Select…</option>
            {data.severity_levels.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Describe the conflict</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            required
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Please provide details…"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-full bg-rose-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-rose-700 disabled:opacity-60"
        >
          {busy ? 'Submitting…' : 'Submit report'}
        </button>
      </form>
    </ModalShell>
  )
}
