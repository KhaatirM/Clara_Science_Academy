import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'

type PendingRow = {
  id: number
  is_group: boolean
  title: string
  assignment_type: string
  status: string
  created_at: string | null
  due_date: string | null
}

type Payload = {
  class: { id: number; name: string }
  pending_individual: PendingRow[]
  pending_group: PendingRow[]
}

export function TeacherAssistantApprovalsPage() {
  const { classId = '' } = useParams()
  const id = Number(classId)
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await apiFetch<Payload>(`/api/spa/teacher/classes/${id}/assistant-approvals`))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load proposals')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  async function act(row: PendingRow, action: 'approve' | 'reject') {
    setBusyId(row.id)
    setMessage(null)
    try {
      const result = await apiFetch<{ success: boolean; message: string }>(
        `/api/spa/teacher/classes/${id}/assistant-approvals/${row.id}/${action}`,
        {
          method: 'POST',
          body: JSON.stringify({ is_group: row.is_group, publish_status: 'Active' }),
        },
      )
      setMessage(result.message)
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusyId(null)
    }
  }

  const rows = [...(data?.pending_individual || []), ...(data?.pending_group || [])]

  return (
    <TeacherTabShell
      eyebrow="Assistant approvals"
      title={data?.class.name || 'Pending proposals'}
      subtitle="Approve or reject assignments proposed by student assistants"
      stats={[]}
      loading={loading}
      error={error}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Link
          to={`/teacher/classes/${id}`}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
        >
          Back to class
        </Link>
      </div>
      {message ? (
        <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-4 py-2 text-sm text-teal-900">
          {message}
        </div>
      ) : null}
      {rows.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-sm text-hub-muted">
          No pending assistant proposals for this class.
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map((row) => (
            <article
              key={`${row.is_group ? 'g' : 'i'}-${row.id}`}
              className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-hub-text">{row.title}</h3>
                  <p className="text-xs text-hub-muted">
                    {row.is_group ? 'Group' : 'Individual'} · {row.assignment_type} · Status {row.status}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => void act(row, 'approve')}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busyId === row.id}
                    onClick={() => void act(row, 'reject')}
                    className="rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-semibold text-red-800 disabled:opacity-60"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </TeacherTabShell>
  )
}

export default TeacherAssistantApprovalsPage
