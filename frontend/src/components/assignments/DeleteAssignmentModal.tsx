import { useEffect, useState } from 'react'
import { removeGroupAssignment, removeIndividualAssignment, type DeleteAssignmentTarget } from '../../api/assignmentActions'

export function DeleteAssignmentModal({
  target,
  classId,
  onClose,
  onSuccess,
}: {
  target: DeleteAssignmentTarget | null
  classId: number
  onClose: () => void
  onSuccess: (message: string) => void
}) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!target) return
    setSubmitting(false)
    setError(null)
  }, [target])

  if (!target) return null

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const res =
        target.type === 'group'
          ? await removeGroupAssignment(target.id)
          : await removeIndividualAssignment(target.id, classId)
      onSuccess(res.message)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete assignment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl" role="dialog" aria-modal="true">
        <h2 className="text-lg font-bold text-hub-text">Delete assignment</h2>
        <p className="mt-2 text-sm text-hub-muted">
          Permanently delete <strong className="text-hub-text">{target.title}</strong>? This removes submissions,
          grades, and files. This cannot be undone.
        </p>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void submit()}
            disabled={submitting}
            className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
          >
            {submitting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}
