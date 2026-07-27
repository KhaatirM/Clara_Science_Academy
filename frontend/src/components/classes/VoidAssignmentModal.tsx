import { useEffect, useState } from 'react'
import { getCsrfToken } from '../../api/client'
import type { StudentBrief } from '../../types/classDetail'

export type VoidAssignmentTarget = {
  id: number
  title: string
  type: 'individual' | 'group'
}

type VoidScope = 'all' | 'specific'

export function VoidAssignmentModal({
  target,
  students,
  onClose,
  onSuccess,
}: {
  target: VoidAssignmentTarget | null
  students: StudentBrief[]
  onClose: () => void
  onSuccess: (message: string) => void
}) {
  const [scope, setScope] = useState<VoidScope>('all')
  const [reason, setReason] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!target) return
    setScope('all')
    setReason('')
    setSelectedIds([])
    setError(null)
    setSubmitting(false)
  }, [target])

  if (!target) return null

  const toggleStudent = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const submit = async () => {
    if (scope === 'specific' && !selectedIds.length) {
      setError('Select at least one student.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const formData = new FormData()
      const token = getCsrfToken()
      if (token) formData.append('csrf_token', token)
      formData.append('assignment_type', target.type)
      formData.append('reason', reason.trim() || 'Voided by administrator')
      formData.append('void_all', scope === 'all' ? 'true' : 'false')
      if (scope === 'specific') {
        selectedIds.forEach((id) => formData.append('student_ids', String(id)))
      }
      const response = await fetch(`/management/void-assignment/${target.id}`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
        body: formData,
      })
      const data = (await response.json()) as { success?: boolean; message?: string }
      if (!response.ok || !data.success) {
        throw new Error(data.message || 'Could not void assignment')
      }
      onSuccess(data.message || 'Assignment voided.')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not void assignment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" role="dialog" aria-modal aria-labelledby="void-modal-title">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-red-100 bg-gradient-to-r from-red-700 to-rose-800 px-5 py-4 text-white">
          <h2 id="void-modal-title" className="flex items-center gap-2 text-lg font-bold">
            <i className="bi bi-slash-circle" aria-hidden />
            Void assignment
          </h2>
          <button type="button" onClick={onClose} className="rounded-full p-1 hover:bg-white/15" aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>

        <div className="space-y-4 p-5">
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            <i className="bi bi-exclamation-triangle me-2" aria-hidden />
            Voiding excludes this assignment from grade calculations. Quarter grades are recalculated immediately.
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Assignment</p>
            <p className="mt-1 font-semibold text-hub-text">{target.title}</p>
            <span
              className={`mt-1 inline-block rounded-full border px-2 py-0.5 text-[0.65rem] font-semibold ${
                target.type === 'group'
                  ? 'border-sky-300 bg-sky-50 text-sky-800'
                  : 'border-teal-300 bg-teal-50 text-teal-800'
              }`}
            >
              {target.type === 'group' ? 'Group' : 'Individual'}
            </span>
          </div>

          <fieldset>
            <legend className="mb-2 text-sm font-bold text-hub-text">Void for</legend>
            <div className="space-y-2">
              <label className="flex cursor-pointer gap-3 rounded-xl border border-slate-200 p-3 hover:border-red-200">
                <input
                  type="radio"
                  name="void_scope"
                  checked={scope === 'all'}
                  onChange={() => setScope('all')}
                  className="mt-0.5"
                />
                <span>
                  <span className="block text-sm font-semibold text-hub-text">All students</span>
                  <span className="text-xs text-hub-muted">Void for every enrolled student in this class</span>
                </span>
              </label>
              <label className="flex cursor-pointer gap-3 rounded-xl border border-slate-200 p-3 hover:border-red-200">
                <input
                  type="radio"
                  name="void_scope"
                  checked={scope === 'specific'}
                  onChange={() => setScope('specific')}
                  className="mt-0.5"
                />
                <span>
                  <span className="block text-sm font-semibold text-hub-text">Specific students</span>
                  <span className="text-xs text-hub-muted">Choose which students to void for</span>
                </span>
              </label>
            </div>
          </fieldset>

          {scope === 'specific' ? (
            <div>
              <p className="mb-2 text-sm font-bold text-hub-text">Select students</p>
              <div className="max-h-48 overflow-y-auto rounded-xl border border-slate-200 p-3">
                {students.length ? (
                  <ul className="space-y-2">
                    {students.map((student) => (
                      <li key={student.id}>
                        <label className="flex cursor-pointer items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(student.id)}
                            onChange={() => toggleStudent(student.id)}
                          />
                          <span>
                            {student.display_name}
                            {student.grade_level != null ? ` (Grade ${student.grade_level})` : ''}
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-hub-muted">No enrolled students.</p>
                )}
              </div>
            </div>
          ) : null}

          <div>
            <label htmlFor="void-reason" className="mb-1 block text-sm font-bold text-hub-text">
              Reason for voiding
            </label>
            <textarea
              id="void-reason"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Assignment canceled, late enrollment…"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-red-400 focus:outline-none focus:ring-2 focus:ring-red-200"
            />
          </div>

          {error ? <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div> : null}
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 bg-slate-50 px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void submit()}
            disabled={submitting}
            className="inline-flex items-center gap-1.5 rounded-full bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 disabled:opacity-60"
          >
            {submitting ? (
              <>
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Voiding…
              </>
            ) : (
              <>
                <i className="bi bi-slash-circle" aria-hidden />
                Void assignment
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
