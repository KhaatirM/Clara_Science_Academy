import { useState } from 'react'
import type { AssignmentViewResponse } from '../../api/assignmentWorkspace'

type Attachment = NonNullable<AssignmentViewResponse['attachments']>[number]

function formatDueDate(iso: string | null | undefined) {
  if (!iso) return 'No due date'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'No due date'
  return d.toLocaleString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatAssignmentType(type: string | null | undefined) {
  if (!type) return 'N/A'
  const t = type.toLowerCase()
  if (t === 'pdf' || t === 'paper' || t === 'pdf_paper') return 'PDF/Paper'
  if (t === 'quiz') return 'Quiz'
  if (t === 'discussion') return 'Discussion'
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function statusBadgeClass(status: string | null | undefined, allVoided: boolean) {
  if (allVoided) return 'bg-red-800 text-white'
  const s = (status || 'active').toLowerCase()
  if (s === 'active') return 'bg-emerald-600 text-white'
  if (s === 'inactive') return 'bg-slate-600 text-white'
  if (s === 'draft') return 'bg-amber-500 text-white'
  return 'bg-slate-500 text-white'
}

export function AssignmentViewHeader({
  title,
  className,
  teacherName,
  status,
  allVoided,
}: {
  title: string
  className: string
  teacherName: string
  status: string | null | undefined
  allVoided: boolean
}) {
  return (
    <div className="mb-5 rounded-2xl bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 px-5 py-4 text-white shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-extrabold tracking-tight">
            <i className="bi bi-file-earmark-text" aria-hidden />
            {title}
          </h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold">
              <i className="bi bi-book" aria-hidden />
              {className}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold">
              <i className="bi bi-person" aria-hidden />
              {teacherName}
            </span>
          </div>
        </div>
        <span
          className={`rounded-lg px-3 py-1 text-xs font-bold uppercase tracking-wide ${statusBadgeClass(status, allVoided)}`}
        >
          {allVoided ? (
            <>
              <i className="bi bi-slash-circle me-1" aria-hidden />
              Voided
            </>
          ) : (
            (status || 'Active').toUpperCase()
          )}
        </span>
      </div>
    </div>
  )
}

function DetailItem({
  icon,
  iconClass,
  label,
  children,
}: {
  icon: string
  iconClass: string
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-2.5">
      <i className={`bi ${icon} mt-0.5 text-lg ${iconClass}`} aria-hidden />
      <div className="min-w-0">
        <div className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
        <div className="text-sm font-semibold text-hub-text">{children}</div>
      </div>
    </div>
  )
}

export function AssignmentDetailsGrid({
  dueDate,
  quarter,
  assignmentType,
}: {
  dueDate: string | null | undefined
  quarter: string | null | undefined
  assignmentType: string | null | undefined
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <DetailItem icon="bi-calendar-event" iconClass="text-blue-600" label="Due Date">
        {formatDueDate(dueDate)}
      </DetailItem>
      <DetailItem icon="bi-grid-3x3" iconClass="text-emerald-600" label="Quarter">
        {quarter || 'N/A'}
      </DetailItem>
      <DetailItem icon="bi-file-earmark" iconClass="text-amber-600" label="Type">
        <span className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-900">
          {formatAssignmentType(assignmentType)}
        </span>
      </DetailItem>
    </div>
  )
}

export function DocumentViewer({
  attachments,
  single,
}: {
  attachments?: Attachment[]
  single?: AssignmentViewResponse['attachment']
}) {
  const docs =
    attachments && attachments.length > 0
      ? attachments
      : single
        ? [{ index: 0, name: single.name, is_pdf: single.is_pdf, view_url: single.view_url, download_url: single.download_url }]
        : []

  if (docs.length === 0) return null

  return (
    <DocumentViewerInner docs={docs} />
  )
}

function DocumentViewerInner({ docs }: { docs: Attachment[] }) {
  const [activeIndex, setActiveIndex] = useState(0)
  const active = docs[activeIndex] ?? docs[0]

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-bold text-hub-text">
            <i className="bi bi-file-earmark-pdf text-red-600" aria-hidden />
            {docs.length > 1 ? 'Assignment Documents' : 'Assignment Document'}
          </h2>
          <p className="text-xs text-hub-muted">{active.name}</p>
        </div>
        <a
          href={active.download_url}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-slate-400"
          download
        >
          <i className="bi bi-download" aria-hidden />
          Download
        </a>
      </div>

      {docs.length > 1 ? (
        <div className="flex flex-wrap gap-1 border-b border-slate-100 bg-slate-50 px-3 py-2">
          {docs.map((doc, idx) => (
            <button
              key={doc.index}
              type="button"
              onClick={() => setActiveIndex(idx)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                idx === activeIndex
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:ring-indigo-300'
              }`}
            >
              Doc {idx + 1}
            </button>
          ))}
        </div>
      ) : null}

      <div className="bg-slate-100">
        {active.is_pdf ? (
          <iframe
            title={active.name}
            src={`${active.view_url}#toolbar=0&navpanes=0&scrollbar=1&zoom=page-width`}
            className="block h-[min(90vh,900px)] w-full border-0 bg-white"
          />
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
            <i className="bi bi-file-earmark-text text-5xl text-slate-400" aria-hidden />
            <p className="text-sm font-semibold text-hub-text">{active.name}</p>
            <a
              href={active.download_url}
              className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              download
            >
              <i className="bi bi-download" aria-hidden />
              Download document
            </a>
          </div>
        )}
      </div>
    </div>
  )
}

export function AssignmentOverviewCard({
  stats,
  totalPoints,
  allVoided,
  partiallyVoided,
  voidedCount,
  enrolledCount,
  isGroup,
}: {
  stats: AssignmentViewResponse['stats']
  totalPoints?: number
  allVoided: boolean
  partiallyVoided: boolean
  voidedCount: number
  enrolledCount: number
  isGroup: boolean
}) {
  const submitted = isGroup ? (stats.groups_submitted ?? stats.submissions_count ?? 0) : (stats.submissions_count ?? 0)

  return (
    <div className={`overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm ${allVoided ? 'ring-1 ring-red-200' : ''}`}>
      <div
        className={`px-4 py-3 text-sm font-bold text-white ${
          allVoided ? 'bg-gradient-to-r from-red-800 to-red-900' : 'bg-gradient-to-r from-blue-600 to-blue-700'
        }`}
      >
        <i className="bi bi-graph-up-arrow me-2" aria-hidden />
        Assignment Overview
      </div>
      <div className="space-y-3 p-4">
        {allVoided ? (
          <div className="flex gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
            <i className="bi bi-slash-circle mt-0.5 shrink-0" aria-hidden />
            <div>
              <strong>Voided for the entire class</strong>
              <p className="mt-0.5 text-xs opacity-90">Excluded from grade calculations.</p>
            </div>
          </div>
        ) : null}
        {partiallyVoided && !allVoided ? (
          <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-hub-muted">
            <i className="bi bi-slash-circle me-1" aria-hidden />
            <strong>{voidedCount}</strong> of <strong>{enrolledCount}</strong> students voided — stats count only
            non-voided students.
          </p>
        ) : null}

        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Submitted" value={allVoided ? '—' : submitted} note="Student submissions" accent="border-t-blue-600" />
          <MetricTile label="Graded" value={allVoided ? '—' : (stats.graded_count ?? 0)} note="With active grades" accent="border-t-emerald-600" />
          <MetricTile label="Awaiting Grade" value={allVoided ? '—' : (stats.pending_count ?? 0)} note="Not graded yet" accent="border-t-amber-500" />
          <MetricTile label="Enrolled" value={stats.total_students ?? 0} note={allVoided ? 'All voided' : 'Students in class'} accent="border-t-violet-600" />
        </div>

        {!allVoided ? (
          <>
            <ProgressRow label="Submission Progress" value={stats.submission_rate ?? 0} tone="bg-blue-600" />
            <ProgressRow label="Grading Progress" value={stats.grading_rate ?? 0} tone="bg-emerald-600" />
          </>
        ) : null}

        <div className="space-y-1 border-t border-slate-100 pt-3 text-sm text-slate-700">
          <div className="flex items-center gap-2">
            <i className="bi bi-star-fill text-amber-500" aria-hidden />
            Total Points: <strong>{totalPoints ?? 'N/A'}</strong>
          </div>
          <div className="flex items-center gap-2">
            <i className="bi bi-speedometer2 text-emerald-600" aria-hidden />
            Class Avg:{' '}
            <strong>
              {allVoided
                ? '—'
                : stats.average_score != null && stats.average_score > 0
                  ? `${stats.average_score}%`
                  : 'N/A'}
            </strong>
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricTile({
  label,
  value,
  note,
  accent,
}: {
  label: string
  value: string | number
  note: string
  accent: string
}) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white px-3 py-2 ${accent} border-t-[3px]`}>
      <div className="text-[0.65rem] font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-2xl font-extrabold text-slate-900">{value}</div>
      <div className="text-[0.65rem] text-slate-500">{note}</div>
    </div>
  )
}

function ProgressRow({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="mb-1 flex justify-between text-xs font-semibold text-slate-700">
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  )
}

export function ClassDetailsCard({
  classInfo,
}: {
  classInfo: {
    name?: string
    subject?: string | null
    grade_level?: string | number | null
    teacher_name?: string
  }
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="bg-gradient-to-r from-emerald-600 to-green-700 px-4 py-3 text-sm font-bold text-white">
        <i className="bi bi-mortarboard-fill me-2" aria-hidden />
        Class Details
      </div>
      <div className="divide-y divide-dashed divide-slate-200 p-4 text-sm">
        <DetailRow icon="bi-book" label="Class" value={classInfo.name || 'N/A'} />
        <DetailRow icon="bi-journal-text" label="Subject" value={classInfo.subject || 'N/A'} />
        <DetailRow icon="bi-grid-3x3-gap" label="Grade Level" value={classInfo.grade_level != null ? String(classInfo.grade_level) : 'N/A'} />
        <DetailRow icon="bi-person-badge" label="Teacher" value={classInfo.teacher_name || 'N/A'} />
      </div>
    </div>
  )
}

function DetailRow({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
      <span className="flex items-center gap-2 text-slate-600">
        <i className={`bi ${icon}`} aria-hidden />
        {label}
      </span>
      <span className="text-right font-semibold text-slate-900">{value}</span>
    </div>
  )
}

type ActionItem = {
  key: string
  label: string
  icon: string
  onClick?: () => void
  href?: string
  disabled?: boolean
  className: string
}

export function AssignmentActionsCard({
  editHref,
  submissionsHref,
  onGrade,
  onExtensions,
  onReopen,
  onRedo,
  onUnvoid,
  onVoid,
  onDelete,
  onBack,
  actions,
}: {
  editHref?: string
  submissionsHref?: string
  onGrade: () => void
  onExtensions: () => void
  onReopen: () => void
  onRedo: () => void
  onUnvoid: () => void
  onVoid: () => void
  onDelete: () => void
  onBack: () => void
  actions: {
    show_reopen?: boolean
    show_redo?: boolean
    show_unvoid?: boolean
    grade_disabled?: boolean
    grade_disabled_label?: string | null
  }
}) {
  const cellClass =
    'flex flex-col items-center justify-center gap-1 rounded-xl border px-2 py-3 text-center text-[0.68rem] font-bold transition'

  const actionsList: ActionItem[] = [
    { key: 'edit', label: 'Edit', icon: 'bi-pencil-square', href: editHref, className: 'border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100' },
    { key: 'submissions', label: 'Submissions', icon: 'bi-file-earmark-arrow-up', href: submissionsHref, className: 'border-slate-800 bg-white text-slate-900 hover:bg-slate-50' },
    {
      key: 'grade',
      label: actions.grade_disabled ? (actions.grade_disabled_label || 'Auto-Graded') : 'Grade',
      icon: 'bi-check-circle-fill',
      onClick: onGrade,
      disabled: Boolean(actions.grade_disabled),
      className: actions.grade_disabled
        ? 'border-violet-300 bg-violet-100 text-violet-700 opacity-60 cursor-not-allowed'
        : 'border-violet-700 bg-violet-700 text-white hover:bg-violet-800',
    },
    { key: 'extensions', label: 'Extensions', icon: 'bi-clock-history', onClick: onExtensions, className: 'border-teal-400 bg-teal-50 text-teal-900 hover:bg-teal-100' },
  ]

  if (actions.show_redo) {
    actionsList.push({ key: 'redo', label: 'Redo / reopen', icon: 'bi-arrow-repeat', onClick: onRedo, className: 'border-orange-400 bg-orange-50 text-orange-900 hover:bg-orange-100' })
  }
  if (actions.show_reopen) {
    actionsList.push({ key: 'reopen', label: 'Reopen', icon: 'bi-arrow-repeat', onClick: onReopen, className: 'border-orange-400 bg-orange-50 text-orange-900 hover:bg-orange-100' })
  }
  if (actions.show_unvoid) {
    actionsList.push({ key: 'unvoid', label: 'Unvoid', icon: 'bi-arrow-counterclockwise', onClick: onUnvoid, className: 'border-emerald-400 bg-emerald-50 text-emerald-900 hover:bg-emerald-100' })
  }

  actionsList.push(
    { key: 'void', label: 'Void', icon: 'bi-slash-circle', onClick: onVoid, className: 'border-red-400 bg-red-50 text-red-900 hover:bg-red-100' },
    { key: 'remove', label: 'Remove', icon: 'bi-trash', onClick: onDelete, className: 'border-pink-300 bg-pink-50 text-pink-900 hover:bg-pink-100' },
    { key: 'back', label: 'Back', icon: 'bi-arrow-left-circle', onClick: onBack, className: 'border-slate-300 bg-slate-50 text-slate-800 hover:bg-slate-100' },
  )

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 bg-slate-50 px-4 py-3 text-sm font-bold text-hub-text">
        <i className="bi bi-lightning-fill me-2 text-blue-600" aria-hidden />
        Actions
      </div>
      <div className="grid grid-cols-3 gap-2 p-3 sm:grid-cols-3">
        {actionsList.map((action) =>
          action.href ? (
            <a
              key={action.key}
              href={action.href}
              className={`${cellClass} ${action.className}`}
            >
              <i className={`bi ${action.icon} text-lg`} aria-hidden />
              {action.label}
            </a>
          ) : (
            <button
              key={action.key}
              type="button"
              disabled={action.disabled}
              onClick={action.onClick}
              className={`${cellClass} disabled:opacity-50 ${action.className}`}
            >
              <i className={`bi ${action.icon} text-lg`} aria-hidden />
              {action.label}
            </button>
          ),
        )}
      </div>
    </div>
  )
}
