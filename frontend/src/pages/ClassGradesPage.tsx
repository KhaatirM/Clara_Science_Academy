import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchClassGrades } from '../api/classes'
import { ClassSubpageShell } from '../components/classes/ClassSubpageShell'
import type { ClassGradesResponse } from '../types/classDetail'

export function ClassGradesPage() {
  const { classId } = useParams()
  const id = Number(classId)
  const [data, setData] = useState<ClassGradesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassGrades(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load grades')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  if (!id) return null

  return (
    <ClassSubpageShell
      eyebrow="Class grades"
      title={data?.class.name || 'Grades'}
      subtitle="Read-only grade overview for this class."
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {data && data.columns.length ? (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                <th className="sticky left-0 bg-slate-50 px-4 py-3">Student</th>
                <th className="px-3 py-3">Average</th>
                {data.columns.map((col) => (
                  <th key={col.key} className="min-w-[7rem] px-3 py-3">
                    <div className="truncate">{col.title}</div>
                    <div className="text-[0.65rem] font-normal normal-case text-hub-muted">{col.type}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => (
                <tr key={row.student.id} className="border-b border-slate-100 hover:bg-slate-50/80">
                  <td className="sticky left-0 bg-white px-4 py-2 font-semibold text-hub-text">{row.student.display_name}</td>
                  <td className="px-3 py-2 font-bold text-teal-800">{row.average}</td>
                  {data.columns.map((col) => (
                    <td key={col.key} className="px-3 py-2 text-hub-muted">
                      {row.grades[col.key]?.grade ?? '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : data ? (
        <p className="text-hub-muted">No assignments or enrolled students yet.</p>
      ) : null}
    </ClassSubpageShell>
  )
}
