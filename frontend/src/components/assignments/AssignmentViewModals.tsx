import { useEffect, useMemo, useState } from 'react'
import type { StudentBrief } from '../../types/classDetail'
import {
  fetchReopenStatus,
  grantAssignmentRedo,
  grantGroupExtensions,
  grantIndividualExtensions,
  reopenAssignment,
  unvoidAssignment,
  type ReopenStatusStudent,
} from '../../api/assignmentViewActions'

function ModalShell({
  title,
  subtitle,
  tone,
  onClose,
  children,
  footer,
}: {
  title: string
  subtitle?: string
  tone: 'teal' | 'orange' | 'sky' | 'emerald' | 'red'
  onClose: () => void
  children: React.ReactNode
  footer: React.ReactNode
}) {
  const header =
    tone === 'teal'
      ? 'from-teal-700 to-cyan-800'
      : tone === 'orange'
        ? 'from-orange-600 to-amber-700'
        : tone === 'sky'
          ? 'from-sky-600 to-blue-700'
          : tone === 'emerald'
            ? 'from-emerald-600 to-green-700'
            : 'from-red-700 to-rose-800'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" role="dialog" aria-modal>
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-xl">
        <div className={`flex items-start justify-between bg-gradient-to-r ${header} px-5 py-4 text-white`}>
          <div>
            <h2 className="text-lg font-bold">{title}</h2>
            {subtitle ? <p className="text-sm text-white/85">{subtitle}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="rounded-full p-1 hover:bg-white/15" aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>
        <div className="space-y-4 p-5">{children}</div>
        <div className="flex justify-end gap-2 border-t border-slate-100 bg-slate-50 px-5 py-4">{footer}</div>
      </div>
    </div>
  )
}

function StudentCheckboxGrid({
  students,
  selectedIds,
  onChange,
  disabledIds,
}: {
  students: StudentBrief[]
  selectedIds: number[]
  onChange: (ids: number[]) => void
  disabledIds?: Set<number>
}) {
  const allEnabled = students.filter((s) => !disabledIds?.has(s.id)).map((s) => s.id)
  const allSelected = allEnabled.length > 0 && allEnabled.every((id) => selectedIds.includes(id))

  return (
    <div>
      <label className="mb-2 flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold">
        <input
          type="checkbox"
          checked={allSelected}
          onChange={(e) => onChange(e.target.checked ? allEnabled : [])}
        />
        Select all students
      </label>
      <div className="max-h-52 overflow-y-auto rounded-xl border border-slate-200 p-3">
        {students.length ? (
          <ul className="space-y-2">
            {students.map((student) => {
              const disabled = disabledIds?.has(student.id)
              return (
                <li key={student.id}>
                  <label className={`flex items-center gap-2 text-sm ${disabled ? 'opacity-50' : 'cursor-pointer'}`}>
                    <input
                      type="checkbox"
                      disabled={disabled}
                      checked={selectedIds.includes(student.id)}
                      onChange={() => {
                        if (disabled) return
                        onChange(
                          selectedIds.includes(student.id)
                            ? selectedIds.filter((x) => x !== student.id)
                            : [...selectedIds, student.id],
                        )
                      }}
                    />
                    <span>
                      {student.display_name}
                      {student.grade_level != null ? ` (Grade ${student.grade_level})` : ''}
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="text-sm text-hub-muted">No students available.</p>
        )}
      </div>
    </div>
  )
}

export function GrantExtensionModal({
  open,
  assignmentId,
  classId,
  isGroup,
  students,
  currentDueDate,
  onClose,
  onSuccess,
}: {
  open: boolean
  assignmentId: number
  classId: number
  isGroup: boolean
  students: StudentBrief[]
  currentDueDate?: string | null
  onClose: () => void
  onSuccess: (message: string) => void
}) {
  const [dueDate, setDueDate] = useState('')
  const [reason, setReason] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setDueDate('')
    setReason('')
    setSelectedIds([])
    setError(null)
  }, [open])

  if (!open) return null

  const submit = async () => {
    if (!dueDate) {
      setError('Choose a new due date.')
      return
    }
    if (!selectedIds.length) {
      setError('Select at least one student.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const payload = {
        assignmentId,
        extendedDueDate: dueDate,
        reason,
        studentIds: selectedIds,
      }
      const result = isGroup
        ? await grantGroupExtensions(payload)
        : await grantIndividualExtensions({ ...payload, classId })
      onSuccess(result.message || 'Extensions granted.')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not grant extensions')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalShell
      title="Grant extensions"
      subtitle="Extend deadline for students"
      tone="teal"
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={submitting} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold">
            Cancel
          </button>
          <button type="button" onClick={() => void submit()} disabled={submitting} className="rounded-lg bg-teal-700 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60">
            {submitting ? 'Granting…' : 'Grant extensions'}
          </button>
        </>
      }
    >
      <p className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
        Extensions are tracked and visible to students on their dashboard.
      </p>
      <div>
        <label className="mb-1 block text-sm font-bold text-hub-text">New due date</label>
        <input
          type="datetime-local"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
        />
        {currentDueDate ? (
          <p className="mt-1 text-xs text-hub-muted">
            Current due date: {new Date(currentDueDate).toLocaleString()}
          </p>
        ) : null}
      </div>
      <StudentCheckboxGrid students={students} selectedIds={selectedIds} onChange={setSelectedIds} />
      <div>
        <label className="mb-1 block text-sm font-bold text-hub-text">Reason (optional)</label>
        <textarea
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Medical leave, family emergency…"
        />
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </ModalShell>
  )
}

export function RedoOpportunityModal({
  open,
  assignmentId,
  students,
  onClose,
  onSuccess,
}: {
  open: boolean
  assignmentId: number
  students: StudentBrief[]
  onClose: () => void
  onSuccess: (message: string) => void
}) {
  const [deadline, setDeadline] = useState('')
  const [reason, setReason] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    const next = new Date()
    next.setDate(next.getDate() + 7)
    setDeadline(next.toISOString().slice(0, 10))
    setReason('')
    setSelectedIds([])
    setError(null)
  }, [open])

  if (!open) return null

  const submit = async () => {
    if (!selectedIds.length) {
      setError('Select at least one student.')
      return
    }
    if (!deadline) {
      setError('Choose a deadline.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await grantAssignmentRedo({
        assignmentId,
        redoDeadline: deadline,
        reason,
        studentIds: selectedIds,
      })
      onSuccess(result.message || 'Redo granted.')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not grant redo')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalShell
      title="Redo / reopen"
      subtitle="Grant redo or reopen access"
      tone="orange"
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={submitting} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold">
            Cancel
          </button>
          <button type="button" onClick={() => void submit()} disabled={submitting} className="rounded-lg bg-orange-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60">
            {submitting ? 'Granting…' : 'Grant'}
          </button>
        </>
      }
    >
      <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
        If a student already submitted, this grants a tracked redo. If not, it reopens access so they can submit.
      </p>
      <div>
        <label className="mb-1 block text-sm font-bold text-hub-text">Deadline</label>
        <input
          type="date"
          value={deadline}
          min={new Date().toISOString().slice(0, 10)}
          onChange={(e) => setDeadline(e.target.value)}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
        />
      </div>
      <StudentCheckboxGrid students={students} selectedIds={selectedIds} onChange={setSelectedIds} />
      <div>
        <label className="mb-1 block text-sm font-bold text-hub-text">Reason (optional)</label>
        <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </ModalShell>
  )
}

export function ReopenAssignmentModal({
  open,
  assignmentId,
  isQuiz,
  maxAttempts,
  onClose,
  onSuccess,
}: {
  open: boolean
  assignmentId: number
  isQuiz: boolean
  maxAttempts?: number | null
  onClose: () => void
  onSuccess: (message: string) => void
}) {
  const [rows, setRows] = useState<ReopenStatusStudent[]>([])
  const [loading, setLoading] = useState(false)
  const [reason, setReason] = useState('')
  const [additionalAttempts, setAdditionalAttempts] = useState(1)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setReason('')
    setAdditionalAttempts(1)
    setSelectedIds([])
    setError(null)
    setLoading(true)
    fetchReopenStatus(assignmentId)
      .then((data) => setRows(data.students || []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load students'))
      .finally(() => setLoading(false))
  }, [open, assignmentId])


  if (!open) return null

  const submit = async () => {
    if (!selectedIds.length) {
      setError('Select at least one student.')
      return
    }
    if (isQuiz && additionalAttempts <= 0) {
      setError('Enter additional attempts for quiz assignments.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await reopenAssignment({
        assignmentId,
        studentIds: selectedIds,
        reason,
        additionalAttempts: isQuiz ? additionalAttempts : 0,
      })
      onSuccess(result.message || 'Assignment reopened.')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not reopen assignment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalShell
      title="Reopen assignment"
      subtitle="Allow selected students to submit again"
      tone="sky"
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={submitting} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold">
            Cancel
          </button>
          <button type="button" onClick={() => void submit()} disabled={submitting || loading} className="rounded-lg bg-sky-700 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60">
            {submitting ? 'Reopening…' : 'Reopen'}
          </button>
        </>
      }
    >
      {loading ? <p className="text-sm text-hub-muted">Loading students…</p> : null}
      {!loading ? (
        <>
          {isQuiz ? (
            <div>
              <label className="mb-1 block text-sm font-bold text-hub-text">Additional attempts</label>
              <input
                type="number"
                min={1}
                value={additionalAttempts}
                onChange={(e) => setAdditionalAttempts(Number(e.target.value) || 0)}
                className="w-32 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
              {maxAttempts ? <p className="mt-1 text-xs text-hub-muted">Quiz max attempts: {maxAttempts}</p> : null}
            </div>
          ) : null}
          <div className="max-h-52 overflow-y-auto rounded-xl border border-slate-200 p-3">
            {rows.map((row) => {
              const disabled = row.grade_is_voided
              const status = row.grade_is_voided
                ? 'Grade voided — unvoid first'
                : row.has_reopening
                  ? 'Already reopened'
                  : row.needs_reopening
                    ? row.reason_needs_reopening || 'Needs reopening'
                    : ''
              return (
                <label
                  key={row.student_id}
                  className={`mb-2 flex gap-2 rounded-lg border px-3 py-2 text-sm ${disabled ? 'border-slate-200 bg-slate-50 opacity-60' : 'border-slate-200 cursor-pointer hover:border-sky-300'}`}
                >
                  <input
                    type="checkbox"
                    disabled={disabled}
                    checked={selectedIds.includes(row.student_id)}
                    onChange={() => {
                      if (disabled) return
                      setSelectedIds((prev) =>
                        prev.includes(row.student_id)
                          ? prev.filter((x) => x !== row.student_id)
                          : [...prev, row.student_id],
                      )
                    }}
                  />
                  <span>
                    <span className="font-semibold">{row.name}</span>
                    {status ? <span className="mt-0.5 block text-xs text-hub-muted">{status}</span> : null}
                  </span>
                </label>
              )
            })}
          </div>
          <div>
            <label className="mb-1 block text-sm font-bold text-hub-text">Reason (optional)</label>
            <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </div>
        </>
      ) : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </ModalShell>
  )
}

export function UnvoidAssignmentModal({
  open,
  assignmentId,
  type,
  students,
  voidedStudentIds,
  onClose,
  onSuccess,
}: {
  open: boolean
  assignmentId: number
  type: 'individual' | 'group'
  students: StudentBrief[]
  voidedStudentIds: number[]
  onClose: () => void
  onSuccess: (message: string) => void
}) {
  const [scope, setScope] = useState<'all' | 'specific'>('all')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const voidedSet = useMemo(() => new Set(voidedStudentIds), [voidedStudentIds])
  const voidedStudents = students.filter((s) => voidedSet.has(s.id))

  useEffect(() => {
    if (!open) return
    setScope('all')
    setSelectedIds([])
    setError(null)
  }, [open])

  if (!open) return null

  const submit = async () => {
    if (scope === 'specific' && !selectedIds.length) {
      setError('Select at least one student.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await unvoidAssignment({
        assignmentId,
        type,
        unvoidAll: scope === 'all',
        studentIds: selectedIds,
      })
      onSuccess(result.message || 'Assignment restored.')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not restore assignment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalShell
      title="Restore assignment"
      subtitle="Include back in grade calculations"
      tone="emerald"
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={submitting} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold">
            Cancel
          </button>
          <button type="button" onClick={() => void submit()} disabled={submitting} className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60">
            {submitting ? 'Restoring…' : 'Restore'}
          </button>
        </>
      }
    >
      <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
        Restoring will include this assignment back in grade calculations. Original grades are restored when available.
      </p>
      <fieldset className="space-y-2">
        <label className="flex cursor-pointer gap-3 rounded-xl border border-slate-200 p-3">
          <input type="radio" checked={scope === 'all'} onChange={() => setScope('all')} />
          <span>
            <span className="block text-sm font-semibold">Restore for entire class</span>
            <span className="text-xs text-hub-muted">All voided grades will be restored</span>
          </span>
        </label>
        <label className="flex cursor-pointer gap-3 rounded-xl border border-slate-200 p-3">
          <input type="radio" checked={scope === 'specific'} onChange={() => setScope('specific')} />
          <span>
            <span className="block text-sm font-semibold">Restore for selected students</span>
            <span className="text-xs text-hub-muted">Choose specific voided students</span>
          </span>
        </label>
      </fieldset>
      {scope === 'specific' ? (
        <StudentCheckboxGrid students={voidedStudents} selectedIds={selectedIds} onChange={setSelectedIds} />
      ) : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </ModalShell>
  )
}
