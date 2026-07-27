import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'

interface RecordsResponse {
  class: { id: number; name: string; subject: string | null }
  students: { id: number; display_name: string; student_id: string | null }[]
  records_by_date: Record<string, { id: number; student_id: number; display_name: string; status: string; notes: string }[]>
  summary: { total: number; present: number; late: number; absent: number; rate: number }
  filters: { start_date: string; end_date: string; student_id: number | null; status: string }
}

type Scope = 'teacher' | 'management'

function recordsApiBase(scope: Scope, classId: number) {
  return scope === 'teacher'
    ? `/api/spa/teacher/attendance/records/${classId}`
    : `/api/spa/attendance/records/${classId}`
}

function hubPath(scope: Scope) {
  return scope === 'teacher' ? '/teacher/attendance' : '/management/attendance'
}

export function ClassAttendanceRecordsPage({ scope }: { scope: Scope }) {
  const { classId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const id = Number(classId)
  const [data, setData] = useState<RecordsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      const start = searchParams.get('start_date')
      const end = searchParams.get('end_date')
      const student = searchParams.get('student_id')
      const status = searchParams.get('status')
      if (start) params.set('start_date', start)
      if (end) params.set('end_date', end)
      if (student) params.set('student_id', student)
      if (status) params.set('status', status)
      const qs = params.toString() ? `?${params}` : ''
      setData(await apiFetch<RecordsResponse>(`${recordsApiBase(scope, id)}${qs}`))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load records')
    } finally {
      setLoading(false)
    }
  }, [id, scope, searchParams])

  useEffect(() => {
    void load()
  }, [load])

  const content = loading ? (
    <div className="rounded-2xl bg-white p-10 text-center text-hub-muted">Loading records…</div>
  ) : error || !data ? (
    <div className="rounded-2xl bg-white p-8 shadow-sm">
      <p className="text-red-700">{error || 'Could not load records'}</p>
      <Link to={hubPath(scope)} className="mt-4 inline-block font-semibold text-teal-700">
        Back to attendance
      </Link>
    </div>
  ) : (
    <div className="space-y-4">
      <header className="rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 p-6 text-white shadow-lg">
        <p className="text-sm font-semibold uppercase tracking-wide text-white/70">Attendance records</p>
        <h1 className="text-2xl font-bold">{data.class.name}</h1>
        <p className="text-sm text-white/85">{data.class.subject || 'General'}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link
            to={hubPath(scope)}
            className="rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-sm font-semibold"
          >
            Hub
          </Link>
          <Link
            to={scope === 'teacher' ? `/teacher/attendance/take/${id}` : `/management/attendance/take/${id}`}
            className="rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-sm font-semibold"
          >
            Take attendance
          </Link>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-4">
        {[
          ['Total', data.summary.total],
          ['Present', data.summary.present],
          ['Late', data.summary.late],
          ['Rate', `${data.summary.rate}%`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-2xl font-extrabold text-hub-text">{value}</div>
            <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">{label}</div>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-4">
          <input
            type="date"
            defaultValue={data.filters.start_date}
            onChange={(e) => {
              const p = new URLSearchParams(searchParams)
              p.set('start_date', e.target.value)
              setSearchParams(p)
            }}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
          <input
            type="date"
            defaultValue={data.filters.end_date}
            onChange={(e) => {
              const p = new URLSearchParams(searchParams)
              p.set('end_date', e.target.value)
              setSearchParams(p)
            }}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
          <select
            defaultValue={data.filters.student_id ? String(data.filters.student_id) : ''}
            onChange={(e) => {
              const p = new URLSearchParams(searchParams)
              if (e.target.value) p.set('student_id', e.target.value)
              else p.delete('student_id')
              setSearchParams(p)
            }}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="">All students</option>
            {data.students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.display_name}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Filter status"
            defaultValue={data.filters.status}
            onBlur={(e) => {
              const p = new URLSearchParams(searchParams)
              if (e.target.value.trim()) p.set('status', e.target.value.trim())
              else p.delete('status')
              setSearchParams(p)
            }}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(data.records_by_date).map(([dateKey, rows]) => (
          <section key={dateKey} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 bg-slate-50 px-4 py-3 font-bold text-hub-text">
              <i className="bi bi-calendar3 me-2" />
              {dateKey}
            </div>
            <div className="divide-y divide-slate-100">
              {rows.map((row) => (
                <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                  <span className="font-semibold text-hub-text">{row.display_name}</span>
                  <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold">{row.status}</span>
                  {row.notes ? <span className="text-hub-muted">{row.notes}</span> : null}
                </div>
              ))}
            </div>
          </section>
        ))}
        {!Object.keys(data.records_by_date).length ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-sm text-hub-muted">
            No records for this filter range.
          </div>
        ) : null}
      </div>
    </div>
  )

  if (scope === 'teacher') {
    return (
      <TeacherTabShell
        eyebrow="Attendance"
        title="Class records"
        subtitle={data?.class.name || 'Attendance history'}
        stats={[]}
      >
        {content}
      </TeacherTabShell>
    )
  }

  return <div className="mx-auto max-w-[1100px]">{content}</div>
}

export function TeacherAttendanceRecordsPage() {
  return <ClassAttendanceRecordsPage scope="teacher" />
}

export function ManagementAttendanceRecordsPage() {
  return <ClassAttendanceRecordsPage scope="management" />
}
