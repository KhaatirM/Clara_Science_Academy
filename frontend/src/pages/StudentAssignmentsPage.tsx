import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  fetchStudentAssignments,
  requestStudentExtension,
  requestStudentRedo,
  submitStudentAssignment,
} from '../api/studentAssignments'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { GradeTone } from '../utils/gradeDisplay'
import { GRADE_TONES, gradeToneFromLetter, gradeToneFromPercent } from '../utils/gradeDisplay'
import type {
  StudentAssignmentAction,
  StudentAssignmentBucket,
  StudentAssignmentCard,
  StudentAssignmentsResponse,
  StudentLowGradeItem,
} from '../types/studentAssignments'

type ModalState =
  | { kind: 'detail'; card: StudentAssignmentCard; bucket: StudentAssignmentBucket }
  | { kind: 'extension'; card: StudentAssignmentCard }
  | { kind: 'submit'; card: StudentAssignmentCard }
  | { kind: 'redo'; card: StudentAssignmentCard }
  | null

/** True only when a numeric grade exists (ignore placeholder N/A grade rows). */
function isEffectivelyGraded(card: StudentAssignmentCard) {
  const g = card.grade
  if (!g) return false
  if (g.percentage != null && !Number.isNaN(Number(g.percentage))) return true
  if (g.letter) return true
  return false
}

/** Client-side action resolution so buttons still show if the API flags are stale/missing. */
function resolvePrimaryAction(
  card: StudentAssignmentCard,
  bucket: StudentAssignmentBucket,
): StudentAssignmentAction | null {
  if (bucket === 'upcoming') {
    return { label: 'Not yet available', url: null, kind: 'locked', disabled: true }
  }
  if (bucket === 'inactive') return null

  const atype = (card.assignment_type || 'pdf').toLowerCase()
  if (atype === 'quiz' || atype.includes('quiz')) {
    const attempts = card.attempts_remaining
    const label =
      attempts != null && attempts > 0 ? `Retake quiz (${attempts} left)` : 'Take quiz'
    return {
      label: card.primary_action?.kind === 'quiz' ? card.primary_action.label : label,
      url: `/student/take-quiz/${card.id}`,
      kind: 'quiz',
      disabled: false,
    }
  }
  if (atype === 'discussion' || atype.includes('discussion')) {
    return {
      label: 'Open discussion',
      url: `/student/discussion/${card.id}`,
      kind: 'discussion',
      disabled: false,
    }
  }
  if (isEffectivelyGraded(card)) return null
  return {
    label: card.has_submission ? 'Resubmit' : 'Submit',
    url: null,
    kind: 'submit',
    disabled: false,
  }
}

function canRequestExtension(card: StudentAssignmentCard, bucket: StudentAssignmentBucket) {
  if (card.can_request_extension === true) return true
  return (
    bucket === 'active' &&
    !card.is_group &&
    !isEffectivelyGraded(card) &&
    !card.extension
  )
}

function canRequestRedo(card: StudentAssignmentCard, bucket: StudentAssignmentBucket) {
  if (card.can_request_redo === true) return true
  return bucket === 'inactive' && !card.is_group && !card.redo
}

export function StudentAssignmentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const classId = searchParams.get('class_id') || ''
  const status = searchParams.get('status') || ''
  const startDate = searchParams.get('start_date') || ''
  const endDate = searchParams.get('end_date') || ''

  const [data, setData] = useState<StudentAssignmentsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDates, setShowDates] = useState(Boolean(startDate || endDate))
  const [lowGradesOpen, setLowGradesOpen] = useState(false)
  const [modal, setModal] = useState<ModalState>(null)

  const [draftClass, setDraftClass] = useState(classId)
  const [draftStatus, setDraftStatus] = useState(status)
  const [draftStart, setDraftStart] = useState(startDate)
  const [draftEnd, setDraftEnd] = useState(endDate)
  const navigate = useNavigate()

  useEffect(() => {
    setDraftClass(classId)
    setDraftStatus(status)
    setDraftStart(startDate)
    setDraftEnd(endDate)
  }, [classId, status, startDate, endDate])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(
        await fetchStudentAssignments({
          class_id: classId ? Number(classId) : '',
          status,
          start_date: startDate,
          end_date: endDate,
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load assignments')
    } finally {
      setLoading(false)
    }
  }, [classId, status, startDate, endDate])

  useEffect(() => {
    void load()
  }, [load])

  const applyFilters = (e?: React.FormEvent) => {
    e?.preventDefault()
    const next = new URLSearchParams()
    if (draftClass) next.set('class_id', draftClass)
    if (draftStatus) next.set('status', draftStatus)
    if (draftStart) next.set('start_date', draftStart)
    if (draftEnd) next.set('end_date', draftEnd)
    setSearchParams(next)
  }

  const clearFilters = () => {
    setDraftClass('')
    setDraftStatus('')
    setDraftStart('')
    setDraftEnd('')
    setSearchParams({})
  }

  const selectedClassName = useMemo(() => {
    if (!classId || !data?.classes?.length) return null
    const match = data.classes.find((c) => String(c.id) === String(classId))
    return match?.name || null
  }, [classId, data?.classes])

  const openDetail = (card: StudentAssignmentCard, bucket: StudentAssignmentBucket) =>
    setModal({ kind: 'detail', card, bucket })
  const openExtension = (card: StudentAssignmentCard) => setModal({ kind: 'extension', card })
  const openSubmit = (card: StudentAssignmentCard) => setModal({ kind: 'submit', card })
  const openRedo = (card: StudentAssignmentCard) => setModal({ kind: 'redo', card })

  const handlePrimaryAction = (card: StudentAssignmentCard, bucket: StudentAssignmentBucket) => {
    const action = resolvePrimaryAction(card, bucket)
    if (!action || action.disabled) return
    if (action.kind === 'submit') {
      openSubmit(card)
      return
    }
    if ((action.kind === 'quiz' || action.kind === 'discussion') && action.url) {
      navigate(action.url.replace(/^\/app/, ''))
      return
    }
    if (action.url) {
      window.location.href = action.url
    }
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          <header className="mgmt-home-hero mb-4">
            <div>
              <p className="mgmt-home-eyebrow">Student portal</p>
              <h1 className="mgmt-home-title">My assignments</h1>
              <p className="mgmt-home-date">
                <i className="bi bi-clipboard-check me-1" aria-hidden />
                Track and complete your coursework
              </p>
            </div>
            <div className="mgmt-home-hero-actions flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setLowGradesOpen(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-800"
              >
                <i className="bi bi-graph-down-arrow" aria-hidden />
                Grades to improve
                {data?.low_grades.items.length ? (
                  <span className="rounded-lg bg-white/95 px-2 py-0.5 text-xs font-bold text-teal-800">
                    {data.low_grades.items.length}
                  </span>
                ) : null}
              </button>
            </div>
          </header>

          <form
            onSubmit={applyFilters}
            className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 lg:items-end">
              <label className="block text-sm">
                <span className="mb-1 block font-semibold text-hub-muted">Class</span>
                <select
                  value={draftClass}
                  onChange={(e) => setDraftClass(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">All classes</option>
                  {(data?.classes || []).map((c) => (
                    <option key={c.id} value={String(c.id)}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-semibold text-hub-muted">Show</span>
                <select
                  value={draftStatus}
                  onChange={(e) => setDraftStatus(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">All</option>
                  <option value="Active">To do (Active)</option>
                  <option value="Upcoming">Upcoming</option>
                  <option value="Inactive">Completed / Past</option>
                </select>
              </label>
              <button
                type="submit"
                className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
              >
                Apply
              </button>
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
              >
                Clear
              </button>
            </div>
            {selectedClassName ? (
              <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-950">
                <i className="bi bi-funnel-fill text-teal-700" aria-hidden />
                <span>
                  Showing assignments for <strong>{selectedClassName}</strong>
                </span>
                <button
                  type="button"
                  onClick={clearFilters}
                  className="ms-auto rounded-full border border-teal-300 bg-white px-2.5 py-0.5 text-xs font-semibold text-teal-800 hover:bg-teal-100"
                >
                  Clear class filter
                </button>
              </div>
            ) : null}
            <button
              type="button"
              onClick={() => setShowDates((v) => !v)}
              className="mt-3 text-sm font-semibold text-hub-muted hover:text-teal-800"
            >
              <i className="bi bi-calendar-range me-1" aria-hidden />
              Date range (optional)
            </button>
            {showDates ? (
              <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <input
                  type="date"
                  value={draftStart}
                  onChange={(e) => setDraftStart(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                <input
                  type="date"
                  value={draftEnd}
                  onChange={(e) => setDraftEnd(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            ) : null}
          </form>

          {loading && !data ? <p className="text-hub-muted">Loading assignments…</p> : null}
          {error ? (
            <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          ) : null}

          {data && !data.has_active_school_year ? (
            <div className="school-year-closed-banner" role="status">
              <span className="school-year-closed-banner__icon" aria-hidden>
                <i className="bi bi-calendar-x" />
              </span>
              <div>
                <p className="school-year-closed-banner__title">School year closed</p>
                <p className="school-year-closed-banner__text mb-0">
                  There is no active school year, so assignments are hidden.
                </p>
              </div>
            </div>
          ) : null}

          {data?.has_active_school_year ? (
            <div className="space-y-8">
              <AssignmentSection
                title="Upcoming"
                icon="bi-calendar-event text-sky-600"
                count={data.counts.upcoming}
                accent="border-sky-400"
                empty="No upcoming assignments at this time."
                items={data.upcoming}
                bucket="upcoming"
                defaultOpen
                onView={openDetail}
                onExtension={openExtension}
                onRedo={openRedo}
                onPrimary={handlePrimaryAction}
              />
              <AssignmentSection
                title="Active"
                icon="bi-check-circle-fill text-emerald-600"
                count={data.counts.active}
                accent="border-emerald-500"
                empty="No active assignments right now."
                items={data.active}
                bucket="active"
                defaultOpen
                onView={openDetail}
                onExtension={openExtension}
                onRedo={openRedo}
                onPrimary={handlePrimaryAction}
              />
              <AssignmentSection
                title="Completed / Past"
                icon="bi-archive text-slate-500"
                count={data.counts.inactive}
                accent="border-slate-300"
                empty="No completed or past assignments."
                items={data.inactive}
                bucket="inactive"
                defaultOpen
                onView={openDetail}
                onExtension={openExtension}
                onRedo={openRedo}
                onPrimary={handlePrimaryAction}
              />
            </div>
          ) : null}
        </div>
      </div>

      {modal?.kind === 'detail' ? (
        <AssignmentDetailModal
          card={modal.card}
          bucket={modal.bucket}
          onClose={() => setModal(null)}
          onExtension={() => setModal({ kind: 'extension', card: modal.card })}
          onSubmit={() => setModal({ kind: 'submit', card: modal.card })}
          onRedo={() => setModal({ kind: 'redo', card: modal.card })}
          onPrimary={() => {
            const { card, bucket } = modal
            setModal(null)
            handlePrimaryAction(card, bucket)
          }}
        />
      ) : null}
      {modal?.kind === 'extension' ? (
        <ExtensionRequestModal
          card={modal.card}
          onClose={() => setModal(null)}
          onSuccess={async () => {
            setModal(null)
            await load()
          }}
        />
      ) : null}
      {modal?.kind === 'submit' ? (
        <SubmitAssignmentModal
          card={modal.card}
          onClose={() => setModal(null)}
          onSuccess={async () => {
            setModal(null)
            await load()
          }}
        />
      ) : null}
      {modal?.kind === 'redo' ? (
        <RedoRequestModal
          card={modal.card}
          onClose={() => setModal(null)}
          onSuccess={async () => {
            setModal(null)
            await load()
          }}
        />
      ) : null}
      {lowGradesOpen && data ? (
        <LowGradesModal
          data={data}
          onClose={() => setLowGradesOpen(false)}
          onView={(card, bucket) => {
            setLowGradesOpen(false)
            openDetail(card, bucket)
          }}
        />
      ) : null}
    </ManagementPageShell>
  )
}

function AssignmentSection({
  title,
  icon,
  count,
  accent,
  empty,
  items,
  bucket,
  defaultOpen = true,
  onView,
  onExtension,
  onRedo,
  onPrimary,
}: {
  title: string
  icon: string
  count: number
  accent: string
  empty: string
  items: StudentAssignmentCard[]
  bucket: StudentAssignmentBucket
  defaultOpen?: boolean
  onView: (card: StudentAssignmentCard, bucket: StudentAssignmentBucket) => void
  onExtension: (card: StudentAssignmentCard) => void
  onRedo: (card: StudentAssignmentCard) => void
  onPrimary: (card: StudentAssignmentCard, bucket: StudentAssignmentBucket) => void
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`mb-3 flex w-full items-center justify-between gap-3 border-t-4 ${accent} pt-3 text-left`}
        aria-expanded={open}
      >
        <div>
          <h2 className="mb-0 text-lg font-bold text-hub-text">
            <i className={`bi ${icon} me-2`} aria-hidden />
            {title}
          </h2>
          <p className="mb-0 text-sm text-hub-muted">{count} assignment(s)</p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm">
          {open ? 'Hide' : 'Show'}
          <span aria-hidden>{open ? '▴' : '▾'}</span>
        </span>
      </button>
      {open ? (
        items.length ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {items.map((card) => (
              <AssignmentCard
                key={`${card.is_group ? 'g' : 'i'}-${card.id}`}
                card={card}
                bucket={bucket}
                onView={onView}
                onExtension={onExtension}
                onRedo={onRedo}
                onPrimary={onPrimary}
              />
            ))}
          </div>
        ) : (
          <p className="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-hub-muted">
            {empty}
          </p>
        )
      ) : null}
    </section>
  )
}

function typeBadgeClass(type: string) {
  if (type === 'quiz') return 'bg-violet-100 text-violet-800'
  if (type === 'discussion') return 'bg-sky-100 text-sky-800'
  return 'bg-amber-100 text-amber-900'
}

function formatTimeRemaining(dueIso: string | null) {
  if (!dueIso) return 'No due date'
  const due = new Date(dueIso)
  if (Number.isNaN(due.getTime())) return '—'
  const diffMs = due.getTime() - Date.now()
  if (diffMs < 0) {
    const overdueDays = Math.ceil(Math.abs(diffMs) / 86400000)
    return overdueDays <= 1 ? 'Overdue' : `Overdue by ${overdueDays} days`
  }
  const days = Math.floor(diffMs / 86400000)
  const hours = Math.floor((diffMs % 86400000) / 3600000)
  if (days > 0) return `${days}d ${hours}h remaining`
  if (hours > 0) return `${hours}h remaining`
  const mins = Math.max(1, Math.floor((diffMs % 3600000) / 60000))
  return `${mins}m remaining`
}

/** Grade colors follow the score, so a D never looks like an A. */
function cardGradeTone(card: StudentAssignmentCard): GradeTone {
  if (!card.grade.has_grade) return 'none'
  if (card.grade.percentage != null) return gradeToneFromPercent(card.grade.percentage)
  return gradeToneFromLetter(card.grade.letter)
}

function statusBanner(card: StudentAssignmentCard) {
  if (card.bucket === 'inactive' && !card.grade.has_grade) {
    return {
      tone: 'bg-slate-100 text-slate-800 border-slate-200',
      title: 'Completed / past',
      message: 'This assignment is no longer active. You can still review details here.',
      pill: 'Inactive',
    }
  }
  if (card.grade.has_grade) {
    return {
      tone: GRADE_TONES[cardGradeTone(card)].badge,
      title: 'Graded',
      message: 'Your work has been graded and reviewed.',
      pill: card.grade.letter || 'Graded',
    }
  }
  if (card.has_submission) {
    return {
      tone: 'bg-amber-50 text-amber-950 border-amber-200',
      title: 'Under review',
      message: 'Your teacher is reviewing your submission.',
      pill: 'Submitted',
    }
  }
  if (card.bucket === 'upcoming') {
    return {
      tone: 'bg-sky-50 text-sky-950 border-sky-200',
      title: 'Upcoming',
      message: card.open_display
        ? `Opens ${card.open_display}. You can review instructions now.`
        : 'Not open yet. You can review instructions now.',
      pill: 'Upcoming',
    }
  }
  return {
    tone: 'bg-rose-50 text-rose-950 border-rose-200',
    title: 'Ready to start',
    message: 'Use the actions below to begin this assignment.',
    pill: 'Not started',
  }
}

function AssignmentCard({
  card,
  bucket,
  onView,
  onExtension,
  onRedo,
  onPrimary,
}: {
  card: StudentAssignmentCard
  bucket: StudentAssignmentBucket
  onView: (card: StudentAssignmentCard, bucket: StudentAssignmentBucket) => void
  onExtension: (card: StudentAssignmentCard) => void
  onRedo: (card: StudentAssignmentCard) => void
  onPrimary: (card: StudentAssignmentCard, bucket: StudentAssignmentBucket) => void
}) {
  const action = resolvePrimaryAction(card, bucket)
  const showExtension = canRequestExtension(card, bucket)
  const showRedo = canRequestRedo(card, bucket)

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-start justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${typeBadgeClass(card.assignment_type)}`}>
          {card.type_label}
        </span>
        <div className="flex flex-wrap justify-end gap-1">
          {card.is_group ? (
            <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs font-semibold text-teal-900">
              Group
            </span>
          ) : null}
          {card.grade.has_grade && card.grade.letter ? (
            <span
              className={`rounded-full border px-2 py-0.5 text-xs font-bold ${GRADE_TONES[cardGradeTone(card)].badge}`}
            >
              {card.grade.letter}
            </span>
          ) : card.student_status === 'Extended' ? (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900">
              Extension
            </span>
          ) : null}
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="text-base font-bold text-hub-text">{card.title}</h3>
        {card.is_group ? (
          <div className="rounded-lg border-l-4 border-teal-500 bg-slate-50 px-3 py-2 text-xs text-hub-muted">
            {card.group_name ? (
              <>
                <div className="font-semibold text-teal-800">Your group: {card.group_name}</div>
                {card.group_leader ? <div>Leader: {card.group_leader}</div> : null}
              </>
            ) : (
              <div>You are not assigned to a group for this assignment yet.</div>
            )}
          </div>
        ) : null}
        <p className="mb-0 text-sm text-hub-muted">
          <i className="bi bi-book me-1" aria-hidden />
          {card.class_name}
        </p>
        <p className="mb-0 text-sm text-hub-muted">
          <i className="bi bi-person me-1" aria-hidden />
          {card.teacher_name}
        </p>
        {card.open_display ? (
          <p className="mb-0 text-sm text-hub-muted">
            <i className="bi bi-calendar-event me-1" aria-hidden />
            Opens: {card.open_display}
          </p>
        ) : null}
        <p className="mb-0 text-sm text-hub-muted">
          <i className="bi bi-calendar-check me-1" aria-hidden />
          Due: {card.due_display}
        </p>
        {card.total_points != null ? (
          <p className="mb-0 text-sm text-hub-muted">
            <i className="bi bi-star me-1" aria-hidden />
            {card.total_points} points
          </p>
        ) : null}
        {card.description_preview ? (
          <p className="mb-0 text-sm text-hub-muted">{card.description_preview}</p>
        ) : null}
        {card.download_url && card.attachment_name ? (
          <a href={card.download_url} className="text-sm font-semibold text-teal-700 hover:underline">
            <i className="bi bi-paperclip me-1" aria-hidden />
            {card.attachment_name}
          </a>
        ) : null}
        {card.grade.feedback_preview ? (
          <div className="rounded-lg border-l-4 border-teal-500 bg-slate-50 px-3 py-2 text-xs text-hub-muted">
            <div className="font-semibold text-teal-800">Teacher feedback</div>
            <p className="mb-0 mt-1">{card.grade.feedback_preview}</p>
          </div>
        ) : null}
        {card.extension ? (
          <span className="w-fit rounded-full bg-sky-100 px-2 py-0.5 text-xs font-semibold text-sky-900">
            Extension {card.extension.status.toLowerCase()}
          </span>
        ) : null}
        {card.redo ? (
          <span className="w-fit rounded-full bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-900">
            Redo {card.redo.status.toLowerCase()}
          </span>
        ) : null}
      </div>
      <div className="mt-auto flex flex-wrap gap-2 border-t border-slate-100 px-4 py-3">
        <button
          type="button"
          onClick={() => onView(card, bucket)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          View
        </button>
        {showExtension ? (
          <button
            type="button"
            onClick={() => onExtension(card)}
            className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100"
          >
            Request Extension
          </button>
        ) : null}
        {showRedo ? (
          <button
            type="button"
            onClick={() => onRedo(card)}
            className="rounded-lg border border-violet-300 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-900 hover:bg-violet-100"
          >
            Request Redo
          </button>
        ) : null}
        {action ? (
          action.disabled ? (
            <button
              type="button"
              disabled
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-400"
            >
              <i className="bi bi-lock me-1" aria-hidden />
              {action.label}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onPrimary(card, bucket)}
              className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              {action.label}
            </button>
          )
        ) : null}
      </div>
    </article>
  )
}

function AssignmentDetailModal({
  card,
  bucket,
  onClose,
  onExtension,
  onSubmit,
  onRedo,
  onPrimary,
}: {
  card: StudentAssignmentCard
  bucket: StudentAssignmentBucket
  onClose: () => void
  onExtension: () => void
  onSubmit: () => void
  onRedo: () => void
  onPrimary: () => void
}) {
  const banner = statusBanner({ ...card, bucket })
  const action = resolvePrimaryAction(card, bucket)
  const showSubmit = action?.kind === 'submit' && !action.disabled
  const showNavigate =
    action && !action.disabled && (action.kind === 'quiz' || action.kind === 'discussion') && action.url
  const showExtension = canRequestExtension(card, bucket)
  const showRedo = canRequestRedo(card, bucket)
  const hasActions = Boolean(showNavigate || showSubmit || showExtension || showRedo)
  const typeIcon =
    card.assignment_type === 'quiz'
      ? 'bi-question-circle-fill'
      : card.assignment_type === 'discussion'
        ? 'bi-chat-dots-fill'
        : 'bi-file-earmark-text-fill'
  const instructions = cleanAssignmentDescription(card.description)

  return (
    <div
      className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/55 p-4 backdrop-blur-[2px]"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200/80"
        role="dialog"
        aria-labelledby="assignment-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative overflow-hidden bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-700 px-5 py-5 text-white">
          <div
            className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -bottom-16 left-8 h-36 w-36 rounded-full bg-emerald-400/20"
            aria-hidden
          />
          <div className="relative flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25">
              <i className={`bi ${typeIcon} text-2xl`} aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <div className="mb-1.5 flex flex-wrap gap-1.5">
                <span className="rounded-full bg-white/15 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ring-1 ring-white/25">
                  {card.type_label}
                </span>
                {card.quarter != null ? (
                  <span className="rounded-full bg-white/15 px-2.5 py-0.5 text-[11px] font-bold ring-1 ring-white/25">
                    Q{card.quarter}
                  </span>
                ) : null}
                {card.is_group ? (
                  <span className="rounded-full bg-amber-300/25 px-2.5 py-0.5 text-[11px] font-bold text-amber-50 ring-1 ring-amber-200/40">
                    Group
                  </span>
                ) : null}
              </div>
              <h2 id="assignment-detail-title" className="text-xl font-bold leading-tight">
                {card.title}
              </h2>
              <p className="mb-0 mt-1 text-sm text-teal-50/95">
                {card.class_name}
                {card.teacher_name ? ` · ${card.teacher_name}` : ''}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl bg-white/10 px-2.5 py-1.5 text-sm font-semibold text-white hover:bg-white/20"
              aria-label="Close"
            >
              <i className="bi bi-x-lg" aria-hidden />
            </button>
          </div>

          <div className="relative mt-4 flex flex-wrap gap-2 text-xs">
            {card.total_points != null ? (
              <span className="rounded-full bg-white/15 px-2.5 py-1 font-semibold ring-1 ring-white/20">
                <i className="bi bi-star me-1" aria-hidden />
                {card.total_points} pts
              </span>
            ) : null}
            <span className="rounded-full bg-white/20 px-2.5 py-1 font-bold ring-1 ring-white/25">
              {banner.pill}
            </span>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
          <div
            className={`rounded-2xl border px-4 py-3 ${banner.tone}`}
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/70">
                <i
                  className={`bi ${
                    card.grade.has_grade
                      ? 'bi-trophy-fill text-emerald-700'
                      : card.has_submission
                        ? 'bi-hourglass-split text-amber-700'
                        : bucket === 'upcoming'
                          ? 'bi-calendar2-week text-sky-700'
                          : bucket === 'inactive'
                            ? 'bi-archive text-slate-600'
                            : 'bi-play-circle-fill text-rose-700'
                  }`}
                  aria-hidden
                />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-bold">{banner.title}</div>
                <p className="mb-0 mt-0.5 text-sm opacity-90">{banner.message}</p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.45fr_1fr]">
            <div className="space-y-4">
              <section className="rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50/80 to-white p-4 shadow-sm">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-teal-950">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-700 text-white">
                    <i className="bi bi-journal-text text-xs" aria-hidden />
                  </span>
                  Instructions
                </h3>
                {instructions ? (
                  <p className="mb-0 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                    {instructions}
                  </p>
                ) : (
                  <p className="mb-0 text-sm text-hub-muted">No description provided.</p>
                )}
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-hub-text">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                    <i className="bi bi-calendar3 text-xs" aria-hidden />
                  </span>
                  Timeline
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                    <div className="text-[11px] font-bold uppercase tracking-wide text-hub-muted">
                      Due date
                    </div>
                    <div className="mt-0.5 font-semibold text-hub-text">{card.due_display}</div>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                    <div className="text-[11px] font-bold uppercase tracking-wide text-hub-muted">
                      Time remaining
                    </div>
                    <div className="mt-0.5 font-semibold text-hub-text">
                      {formatTimeRemaining(card.due_date)}
                    </div>
                  </div>
                  {card.open_display ? (
                    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5 sm:col-span-2">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-hub-muted">
                        Opens
                      </div>
                      <div className="mt-0.5 font-semibold text-hub-text">{card.open_display}</div>
                    </div>
                  ) : null}
                </div>
              </section>
            </div>

            <div className="space-y-4">
              <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-hub-text">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                    <i className="bi bi-folder2-open text-xs" aria-hidden />
                  </span>
                  Materials
                </h3>
                {card.download_url && card.attachment_name ? (
                  <a
                    href={card.download_url}
                    className="inline-flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-800 hover:bg-teal-100"
                  >
                    <i className="bi bi-paperclip" aria-hidden />
                    {card.attachment_name}
                  </a>
                ) : (
                  <p className="mb-0 text-sm text-hub-muted">No attachment for this assignment.</p>
                )}
                <p className="mb-0 mt-2 text-xs text-hub-muted">
                  {card.assignment_type === 'quiz'
                    ? 'Quizzes open in the quiz player. Start when you are ready.'
                    : card.assignment_type === 'discussion'
                      ? 'Join the discussion to post and reply to classmates.'
                      : 'Upload a file (PDF, DOC, images, and similar) when you submit.'}
                </p>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-hub-text">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                    <i className="bi bi-person-check text-xs" aria-hidden />
                  </span>
                  Your progress
                </h3>
                <dl className="space-y-2 text-sm">
                  <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                    <dt className="text-hub-muted">Status</dt>
                    <dd className="mb-0 font-semibold text-hub-text">{card.student_status}</dd>
                  </div>
                  {card.total_points != null ? (
                    <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                      <dt className="text-hub-muted">Points</dt>
                      <dd className="mb-0 font-semibold text-hub-text">{card.total_points}</dd>
                    </div>
                  ) : null}
                  {card.attempts_remaining != null ? (
                    <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                      <dt className="text-hub-muted">Attempts left</dt>
                      <dd className="mb-0 font-semibold text-hub-text">{card.attempts_remaining}</dd>
                    </div>
                  ) : null}
                  {card.group_name ? (
                    <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                      <dt className="text-hub-muted">Group</dt>
                      <dd className="mb-0 font-semibold text-hub-text">{card.group_name}</dd>
                    </div>
                  ) : null}
                </dl>
              </section>

              {card.grade.has_grade ? (
                <section
                  className={`rounded-2xl border p-4 shadow-sm ${GRADE_TONES[cardGradeTone(card)].panel}`}
                >
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-hub-text">
                    <span
                      className={`flex h-7 w-7 items-center justify-center rounded-lg ${GRADE_TONES[cardGradeTone(card)].solid}`}
                    >
                      <i className="bi bi-chat-square-text text-xs" aria-hidden />
                    </span>
                    Grade &amp; feedback
                  </h3>
                  <p className={`mb-2 text-lg font-bold ${GRADE_TONES[cardGradeTone(card)].text}`}>
                    {card.grade.display}
                    {card.grade.letter ? ` (${card.grade.letter})` : ''}
                  </p>
                  <p className="mb-0 whitespace-pre-wrap text-sm text-slate-700">
                    {card.grade.feedback || 'No written feedback.'}
                  </p>
                </section>
              ) : null}
            </div>
          </div>
        </div>

        <div className="border-t border-slate-200 bg-slate-50/90 px-5 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Close
            </button>
            <div className="flex flex-wrap gap-2">
              {showExtension ? (
                <button
                  type="button"
                  onClick={onExtension}
                  className="rounded-full border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 hover:bg-amber-100"
                >
                  <i className="bi bi-clock-history me-1" aria-hidden />
                  Extension
                </button>
              ) : null}
              {showRedo ? (
                <button
                  type="button"
                  onClick={onRedo}
                  className="rounded-full border border-violet-300 bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-900 hover:bg-violet-100"
                >
                  <i className="bi bi-arrow-repeat me-1" aria-hidden />
                  Redo
                </button>
              ) : null}
              {showNavigate ? (
                <button
                  type="button"
                  onClick={onPrimary}
                  className="rounded-full bg-gradient-to-r from-teal-700 to-emerald-600 px-4 py-2 text-sm font-bold text-white shadow-sm hover:from-teal-800 hover:to-emerald-700"
                >
                  {action?.label}
                  <i className="bi bi-arrow-right ms-1" aria-hidden />
                </button>
              ) : null}
              {showSubmit ? (
                <button
                  type="button"
                  onClick={onSubmit}
                  className="rounded-full bg-gradient-to-r from-teal-700 to-emerald-600 px-4 py-2 text-sm font-bold text-white shadow-sm hover:from-teal-800 hover:to-emerald-700"
                >
                  {action?.label || 'Submit'}
                  <i className="bi bi-upload ms-1" aria-hidden />
                </button>
              ) : null}
              {!hasActions ? (
                <p className="mb-0 text-xs text-hub-muted">
                  {bucket === 'inactive'
                    ? card.redo
                      ? `Redo ${card.redo.status.toLowerCase()}.`
                      : 'This assignment is inactive.'
                    : 'No actions available right now.'}
                </p>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function cleanAssignmentDescription(raw: string | null | undefined) {
  if (!raw) return ''
  let text = raw
  if (text.includes('**Discussion Prompt:**')) {
    text = text.split('**Discussion Prompt:**')[1] ?? text
  }
  for (const marker of ['**Instructions:**', '**Participation Requirements:**']) {
    if (text.includes(marker)) {
      text = text.split(marker)[0] ?? text
    }
  }
  return text.replace(/\*\*/g, '').trim()
}

function ExtensionRequestModal({
  card,
  onClose,
  onSuccess,
}: {
  card: StudentAssignmentCard
  onClose: () => void
  onSuccess: () => Promise<void>
}) {
  const defaultDate = card.due_date ? card.due_date.slice(0, 10) : ''
  const [reason, setReason] = useState('')
  const [requestedDueDate, setRequestedDueDate] = useState(defaultDate)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await requestStudentExtension({
        assignmentId: card.id,
        reason: reason.trim(),
        requestedDueDate,
      })
      await onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit extension request')
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[1600] flex items-center justify-center bg-slate-900/55 p-4 backdrop-blur-[2px]"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200/80"
        role="dialog"
        aria-labelledby="extension-request-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative overflow-hidden bg-gradient-to-br from-amber-700 via-amber-600 to-orange-500 px-5 py-5 text-white">
          <div
            className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -bottom-14 left-8 h-32 w-32 rounded-full bg-orange-300/25"
            aria-hidden
          />
          <div className="relative flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25">
              <i className="bi bi-clock-history text-2xl" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-amber-100">
                Need more time?
              </p>
              <h2 id="extension-request-title" className="text-xl font-bold leading-tight">
                Request extension
              </h2>
              <p className="mb-0 mt-1 truncate text-sm text-amber-50/95">{card.title}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-xl bg-white/10 px-2.5 py-1.5 text-sm font-semibold text-white hover:bg-white/20 disabled:opacity-60"
              aria-label="Close"
            >
              <i className="bi bi-x-lg" aria-hidden />
            </button>
          </div>
          <div className="relative mt-4 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-white/15 px-2.5 py-1 font-semibold ring-1 ring-white/20">
              <i className="bi bi-book me-1" aria-hidden />
              {card.class_name}
            </span>
            <span className="rounded-full bg-white/15 px-2.5 py-1 font-semibold ring-1 ring-white/20">
              <i className="bi bi-calendar-event me-1" aria-hidden />
              Current due {card.due_display}
            </span>
          </div>
        </div>

        <form onSubmit={submit} className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
            <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50/60 px-4 py-3 text-sm text-amber-950">
              <div className="flex items-start gap-2">
                <i className="bi bi-info-circle-fill mt-0.5 text-amber-600" aria-hidden />
                <p className="mb-0">
                  Your teacher will review this request. If approved, the due date updates for you.
                </p>
              </div>
            </div>

            <label className="block text-sm">
              <span className="mb-1.5 flex items-center gap-2 font-bold text-hub-text">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 text-amber-800">
                  <i className="bi bi-chat-left-text text-xs" aria-hidden />
                </span>
                Reason for extension
              </span>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                rows={4}
                placeholder="Please explain why you need more time…"
                className="w-full rounded-2xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-200"
              />
            </label>

            <label className="block text-sm">
              <span className="mb-1.5 flex items-center gap-2 font-bold text-hub-text">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 text-amber-800">
                  <i className="bi bi-calendar2-plus text-xs" aria-hidden />
                </span>
                Requested new due date
              </span>
              <input
                type="date"
                value={requestedDueDate}
                onChange={(e) => setRequestedDueDate(e.target.value)}
                required
                className="w-full rounded-2xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-200"
              />
              <span className="mt-1.5 block text-xs text-hub-muted">
                Pick a date after the current due date when possible.
              </span>
            </label>

            {error ? (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                <i className="bi bi-exclamation-triangle me-1" aria-hidden />
                {error}
              </div>
            ) : null}
          </div>

          <div className="border-t border-slate-200 bg-slate-50/90 px-5 py-3">
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded-full bg-gradient-to-r from-amber-600 to-orange-500 px-4 py-2 text-sm font-bold text-white shadow-sm hover:from-amber-700 hover:to-orange-600 disabled:opacity-60"
              >
                {submitting ? (
                  <>
                    <i className="bi bi-hourglass-split me-1" aria-hidden />
                    Submitting…
                  </>
                ) : (
                  <>
                    <i className="bi bi-send me-1" aria-hidden />
                    Submit request
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

function RedoRequestModal({
  card,
  onClose,
  onSuccess,
}: {
  card: StudentAssignmentCard
  onClose: () => void
  onSuccess: () => Promise<void>
}) {
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await requestStudentRedo({
        assignmentId: card.id,
        reason: reason.trim(),
      })
      await onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit redo request')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[1600] flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl" role="dialog">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-hub-text">Request Redo</h2>
          <p className="mb-0 text-sm text-hub-muted">{card.title}</p>
        </div>
        <form onSubmit={submit} className="space-y-4 px-5 py-4">
          <label className="block text-sm">
            <span className="mb-1 block font-semibold text-hub-muted">Reason for redo request</span>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="Please explain why you would like to redo this assignment…"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            Your request will be sent to your teacher. They can grant a redo from the Redo Dashboard.
          </div>
          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </div>
          ) : null}
          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-full bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800 disabled:opacity-60"
            >
              {submitting ? 'Submitting…' : 'Submit request'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function SubmitAssignmentModal({
  card,
  onClose,
  onSuccess,
}: {
  card: StudentAssignmentCard
  onClose: () => void
  onSuccess: () => Promise<void>
}) {
  const [file, setFile] = useState<File | null>(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const isResubmit = card.has_submission && !isEffectivelyGraded(card)

  const pickFile = (next: File | null) => {
    setFile(next)
    setError(null)
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Please choose a file to upload.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await submitStudentAssignment({
        assignmentId: card.id,
        isGroup: card.is_group,
        file,
        notes: notes.trim() || undefined,
      })
      await onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit assignment')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[1600] flex items-center justify-center bg-slate-900/55 p-4 backdrop-blur-[2px]">
      <div
        className="flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200/80"
        role="dialog"
        aria-labelledby="submit-assignment-title"
      >
        <div className="relative overflow-hidden bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-700 px-5 py-5 text-white">
          <div
            className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -bottom-16 left-10 h-36 w-36 rounded-full bg-emerald-400/20"
            aria-hidden
          />
          <div className="relative flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25">
              <i className="bi bi-cloud-upload text-2xl" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-teal-100">
                {isResubmit ? 'Replace previous upload' : 'Ready to turn in'}
              </p>
              <h2 id="submit-assignment-title" className="text-xl font-bold leading-tight">
                {isResubmit ? 'Resubmit assignment' : 'Submit assignment'}
              </h2>
              <p className="mb-0 mt-1 truncate text-sm text-teal-50/95">{card.title}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-xl bg-white/10 px-2.5 py-1.5 text-sm font-semibold text-white hover:bg-white/20"
              aria-label="Close"
            >
              <i className="bi bi-x-lg" aria-hidden />
            </button>
          </div>
          <div className="relative mt-4 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-white/15 px-2.5 py-1 font-semibold ring-1 ring-white/20">
              <i className="bi bi-book me-1" aria-hidden />
              {card.class_name}
            </span>
            <span className="rounded-full bg-white/15 px-2.5 py-1 font-semibold ring-1 ring-white/20">
              <i className="bi bi-calendar-check me-1" aria-hidden />
              Due {card.due_display}
            </span>
            {card.total_points != null ? (
              <span className="rounded-full bg-white/15 px-2.5 py-1 font-semibold ring-1 ring-white/20">
                <i className="bi bi-star me-1" aria-hidden />
                {card.total_points} pts
              </span>
            ) : null}
            {card.is_group ? (
              <span className="rounded-full bg-amber-300/25 px-2.5 py-1 font-semibold text-amber-50 ring-1 ring-amber-200/40">
                <i className="bi bi-people-fill me-1" aria-hidden />
                Counts for your group
              </span>
            ) : null}
          </div>
        </div>

        <form onSubmit={submit} className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
            <div>
              <div className="mb-2 flex items-center justify-between gap-2">
                <label className="text-sm font-bold text-hub-text" htmlFor="student-submit-file">
                  <i className="bi bi-file-earmark-arrow-up me-1 text-teal-700" aria-hidden />
                  Upload your file
                </label>
                <span className="text-xs text-hub-muted">Required</span>
              </div>

              <div
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    fileInputRef.current?.click()
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
                onDragEnter={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={(e) => {
                  e.preventDefault()
                  setDragOver(false)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOver(false)
                  const dropped = e.dataTransfer.files?.[0] || null
                  pickFile(dropped)
                }}
                className={`cursor-pointer rounded-2xl border-2 border-dashed px-4 py-8 text-center transition ${
                  dragOver
                    ? 'border-teal-500 bg-teal-50 shadow-inner'
                    : file
                      ? 'border-teal-300 bg-teal-50/60'
                      : 'border-slate-300 bg-slate-50 hover:border-teal-400 hover:bg-teal-50/40'
                }`}
              >
                <input
                  ref={fileInputRef}
                  id="student-submit-file"
                  type="file"
                  className="hidden"
                  onChange={(e) => pickFile(e.target.files?.[0] || null)}
                />
                {!file ? (
                  <>
                    <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-teal-700 shadow-sm ring-1 ring-slate-200">
                      <i className="bi bi-cloud-arrow-up text-2xl" aria-hidden />
                    </div>
                    <p className="mb-1 text-sm font-bold text-hub-text">
                      {dragOver ? 'Drop file to attach' : 'Drag & drop, or click to browse'}
                    </p>
                    <p className="mb-3 text-xs text-hub-muted">
                      PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, GIF, or MD
                    </p>
                    <span className="inline-flex items-center gap-2 rounded-full border border-teal-300 bg-white px-3 py-1.5 text-xs font-semibold text-teal-800">
                      <i className="bi bi-folder2-open" aria-hidden />
                      Choose file
                    </span>
                  </>
                ) : (
                  <div className="mx-auto flex max-w-md items-start gap-3 rounded-2xl border border-teal-200 bg-white px-4 py-3 text-left shadow-sm">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
                      <i className="bi bi-file-earmark-check text-xl" aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="mb-0 truncate text-sm font-bold text-hub-text">{file.name}</p>
                      <p className="mb-0 text-xs text-hub-muted">{formatFileSize(file.size)}</p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        pickFile(null)
                        if (fileInputRef.current) fileInputRef.current.value = ''
                      }}
                      className="rounded-lg border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                    >
                      Remove
                    </button>
                  </div>
                )}
              </div>
            </div>

            <label className="block text-sm">
              <span className="mb-2 flex items-center justify-between gap-2">
                <span className="font-bold text-hub-text">
                  <i className="bi bi-chat-left-text me-1 text-teal-700" aria-hidden />
                  Notes for your teacher
                </span>
                <span className="text-xs font-normal text-hub-muted">Optional</span>
              </span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Add context, explain your approach, or note anything your teacher should know…"
                className="w-full resize-y rounded-2xl border border-slate-300 bg-white px-3.5 py-3 text-sm text-hub-text shadow-sm outline-none ring-teal-600/0 transition focus:border-teal-500 focus:ring-4 focus:ring-teal-600/15"
              />
            </label>

            <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3">
              <p className="mb-2 text-sm font-bold text-sky-950">
                <i className="bi bi-info-circle me-1" aria-hidden />
                Before you submit
              </p>
              <ul className="mb-0 space-y-1.5 text-xs text-sky-900">
                <li className="flex gap-2">
                  <i className="bi bi-check2 text-sky-700" aria-hidden />
                  Double-check you selected the correct file
                </li>
                <li className="flex gap-2">
                  <i className="bi bi-check2 text-sky-700" aria-hidden />
                  Make sure your work is complete and ready to grade
                </li>
                {isResubmit ? (
                  <li className="flex gap-2">
                    <i className="bi bi-check2 text-sky-700" aria-hidden />
                    Resubmitting replaces your previous upload
                  </li>
                ) : null}
              </ul>
            </div>

            {error ? (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                <i className="bi bi-exclamation-triangle me-1" aria-hidden />
                {error}
              </div>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 bg-slate-50/80 px-5 py-4">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-full border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !file}
              className="inline-flex items-center gap-2 rounded-full bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Uploading…
                </>
              ) : (
                <>
                  <i className={`bi ${isResubmit ? 'bi-arrow-repeat' : 'bi-cloud-upload'}`} aria-hidden />
                  {isResubmit ? 'Resubmit' : 'Submit assignment'}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function LowGradesModal({
  data,
  onClose,
  onView,
}: {
  data: StudentAssignmentsResponse
  onClose: () => void
  onView: (card: StudentAssignmentCard, bucket: StudentAssignmentBucket) => void
}) {
  const [classFilter, setClassFilter] = useState('')
  const [sort, setSort] = useState('recent')
  const items = useMemo(() => {
    let list = [...data.low_grades.items]
    if (classFilter) list = list.filter((i) => i.class_name === classFilter)
    list.sort((a, b) => {
      if (sort === 'lowest') return a.percentage - b.percentage
      if (sort === 'highest') return b.percentage - a.percentage
      if (sort === 'class') return a.class_name.localeCompare(b.class_name)
      if (sort === 'oldest') {
        return (a.graded_at || '').localeCompare(b.graded_at || '')
      }
      return (b.graded_at || '').localeCompare(a.graded_at || '')
    })
    return list
  }, [classFilter, data.low_grades.items, sort])

  const avg = data.low_grades.summary.avg_percentage
  const threshold = data.low_grades.threshold

  const findCard = (
    item: StudentLowGradeItem,
  ): { card: StudentAssignmentCard; bucket: StudentAssignmentBucket } | null => {
    for (const bucket of ['active', 'inactive', 'upcoming'] as const) {
      const pool = data[bucket]
      const card = pool.find((c) => c.id === item.assignment_id && c.is_group === item.is_group)
      if (card) return { card, bucket }
    }
    return null
  }

  const gradeTone = (pct: number) => {
    if (pct < 50) return 'from-rose-600 to-red-500'
    if (pct < 70) return 'from-orange-500 to-amber-500'
    return 'from-amber-500 to-yellow-500'
  }

  return (
    <div
      className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/55 p-4 backdrop-blur-[2px]"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200/80"
        role="dialog"
        aria-labelledby="low-grades-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative overflow-hidden bg-gradient-to-br from-rose-800 via-rose-700 to-orange-600 px-5 py-5 text-white">
          <div
            className="pointer-events-none absolute -right-10 -top-10 h-44 w-44 rounded-full bg-white/10"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -bottom-16 left-10 h-36 w-36 rounded-full bg-orange-300/20"
            aria-hidden
          />
          <div className="relative flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25">
              <i className="bi bi-graph-down-arrow text-2xl" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-rose-100">
                Focus list
              </p>
              <h2 id="low-grades-title" className="text-xl font-bold leading-tight">
                Grades to improve
              </h2>
              <p className="mb-0 mt-1 text-sm text-rose-50/95">
                Graded work below {threshold}% — review feedback and plan your next step.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl bg-white/10 px-2.5 py-1.5 text-sm font-semibold text-white hover:bg-white/20"
              aria-label="Close"
            >
              <i className="bi bi-x-lg" aria-hidden />
            </button>
          </div>

          <div className="relative mt-4 grid gap-2 sm:grid-cols-3">
            <div className="rounded-2xl bg-white/12 px-3.5 py-2.5 ring-1 ring-white/20">
              <div className="text-[11px] font-bold uppercase tracking-wide text-rose-100">Below threshold</div>
              <div className="mt-0.5 text-2xl font-bold">{data.low_grades.items.length}</div>
            </div>
            <div className="rounded-2xl bg-white/12 px-3.5 py-2.5 ring-1 ring-white/20">
              <div className="text-[11px] font-bold uppercase tracking-wide text-rose-100">Threshold</div>
              <div className="mt-0.5 text-2xl font-bold">{threshold}%</div>
            </div>
            <div className="rounded-2xl bg-white/12 px-3.5 py-2.5 ring-1 ring-white/20">
              <div className="text-[11px] font-bold uppercase tracking-wide text-rose-100">Average</div>
              <div className="mt-0.5 text-2xl font-bold">
                {avg != null ? `${Number(avg).toFixed(1)}%` : '—'}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 border-b border-slate-200 bg-slate-50/80 px-5 py-3">
          <label className="min-w-[10rem] flex-1 text-sm">
            <span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-hub-muted">
              Class
            </span>
            <select
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-200"
            >
              <option value="">All classes</option>
              {data.low_grades.classes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="min-w-[12rem] flex-1 text-sm">
            <span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-hub-muted">
              Sort
            </span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-200"
            >
              <option value="recent">Most recent first</option>
              <option value="oldest">Oldest first</option>
              <option value="lowest">Lowest grade first</option>
              <option value="highest">Highest grade first</option>
              <option value="class">By class</option>
            </select>
          </label>
        </div>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4 sm:p-5">
          {items.length ? (
            items.map((item: StudentLowGradeItem) => {
              const found = findCard(item)
              return (
                <article
                  key={`${item.is_group ? 'g' : 'i'}-${item.assignment_id}`}
                  className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-rose-200 hover:shadow-md"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1.5 flex flex-wrap gap-1.5">
                        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-slate-700">
                          {item.assignment_type || 'Assignment'}
                        </span>
                        {item.is_group ? (
                          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-bold text-amber-900">
                            Group
                          </span>
                        ) : null}
                        {item.letter ? (
                          <span className="rounded-full bg-rose-100 px-2.5 py-0.5 text-[11px] font-bold text-rose-800">
                            {item.letter}
                          </span>
                        ) : null}
                      </div>
                      <h3 className="text-base font-bold text-hub-text">{item.title}</h3>
                      <p className="mb-0 mt-0.5 text-sm text-hub-muted">
                        <i className="bi bi-book me-1" aria-hidden />
                        {item.class_name}
                        {item.graded_display ? (
                          <>
                            {' · '}
                            <i className="bi bi-calendar-check me-1" aria-hidden />
                            Graded {item.graded_display}
                          </>
                        ) : null}
                      </p>
                      {item.feedback ? (
                        <div className="mt-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                          <div className="mb-1 text-[11px] font-bold uppercase tracking-wide text-hub-muted">
                            Teacher feedback
                          </div>
                          <p className="mb-0 text-sm leading-relaxed text-slate-700">
                            {item.feedback.length > 220
                              ? `${item.feedback.slice(0, 220).trim()}…`
                              : item.feedback}
                          </p>
                        </div>
                      ) : (
                        <p className="mb-0 mt-2 text-xs text-hub-muted">No written feedback.</p>
                      )}
                    </div>

                    <div className="flex shrink-0 items-center gap-3 sm:flex-col sm:items-end">
                      <div
                        className={`rounded-2xl bg-gradient-to-br ${gradeTone(item.percentage)} px-3.5 py-2.5 text-center text-white shadow-sm`}
                      >
                        <div className="text-2xl font-bold leading-none">{item.percentage}%</div>
                        <div className="mt-1 text-[11px] font-semibold uppercase tracking-wide opacity-90">
                          {item.letter || 'Score'}
                        </div>
                      </div>
                      {found ? (
                        <button
                          type="button"
                          onClick={() => onView(found.card, found.bucket)}
                          className="rounded-full bg-gradient-to-r from-teal-700 to-emerald-600 px-4 py-2 text-sm font-bold text-white shadow-sm hover:from-teal-800 hover:to-emerald-700"
                        >
                          View
                          <i className="bi bi-arrow-right ms-1" aria-hidden />
                        </button>
                      ) : null}
                    </div>
                  </div>
                </article>
              )
            })
          ) : (
            <div className="rounded-2xl border border-dashed border-rose-200 bg-rose-50/40 px-6 py-12 text-center">
              <i className="bi bi-emoji-smile mb-3 block text-4xl text-rose-300" aria-hidden />
              <p className="mb-0 text-sm font-semibold text-hub-text">
                {data.low_grades.items.length
                  ? 'No assignments match the selected class filter.'
                  : `No graded work below ${threshold}% right now.`}
              </p>
              <p className="mb-0 mt-1 text-sm text-hub-muted">
                {data.low_grades.items.length
                  ? 'Try another class or clear the filter.'
                  : 'Nice work — keep it up.'}
              </p>
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 bg-slate-50/90 px-5 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="mb-0 text-xs text-hub-muted">
              Showing {items.length} of {data.low_grades.items.length}
            </p>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
