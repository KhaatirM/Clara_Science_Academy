import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'

type GradesReport = {
  kind: 'grades'
  student: {
    id: number
    name: string
    first_name: string
    last_name: string
    grade_level: number
    student_id: string
    date_of_birth: string
    address: string
  }
  school_year: { id: number; name: string }
  classes: Array<{ id: number; name: string; subject?: string | null }>
  grades_by_quarter: Record<
    string,
    Array<{
      class_id: number | string
      class_name: string
      letter?: string | null
      percentage?: number | null
      assignments_count?: number | null
    }>
  >
  generated_at: string
  urls: { printable: string; pdf: string; back: string }
}

type AttendanceReport = {
  kind: 'attendance'
  student: {
    id: number
    name: string
    first_name: string
    last_name: string
    grade_level: number
    student_id: string
    date_of_birth: string
  }
  school_year: { id: number; name: string }
  stats: {
    total_records: number
    present_count: number
    late_count: number
    absent_count: number
    excused_absent_count: number
    unexcused_absent_count: number
    attendance_rate: number
  }
  records_by_month: Array<{
    month: string
    records: Array<{
      id: number
      date: string
      date_display: string
      status: string
      class_name: string
      notes: string
    }>
  }>
  generated_at: string
  urls: { printable: string; pdf: string; back: string }
}

export function TeacherStudentReportPage({ kind }: { kind: 'grades' | 'attendance' }) {
  const { studentId = '' } = useParams()
  const id = Number(studentId)
  const [data, setData] = useState<GradesReport | AttendanceReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!Number.isFinite(id) || id <= 0) {
      setError('Invalid student')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    const path =
      kind === 'grades'
        ? `/api/spa/teacher/students/${id}/grades`
        : `/api/spa/teacher/students/${id}/attendance`
    void apiFetch<GradesReport | AttendanceReport>(path)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load report'))
      .finally(() => setLoading(false))
  }, [id, kind])

  const title = kind === 'grades' ? 'Student grades report' : 'Student attendance report'

  if (loading) {
    return (
      <TeacherTabShell eyebrow="Students" title={title} subtitle="Loading…" stats={[]}>
        <div className="py-12 text-center text-hub-muted">Loading report…</div>
      </TeacherTabShell>
    )
  }

  if (error || !data) {
    return (
      <TeacherTabShell eyebrow="Students" title={title} subtitle="Unavailable" stats={[]}>
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center text-rose-800">
          <p>{error || 'Report not found.'}</p>
          <Link to="/teacher/students" className="mt-4 inline-block font-semibold underline">
            Back to students
          </Link>
        </div>
      </TeacherTabShell>
    )
  }

  return (
    <TeacherTabShell
      eyebrow="Students"
      title={title}
      subtitle={`${data.student.name} · ${data.school_year.name}`}
      stats={
        kind === 'attendance' && data.kind === 'attendance'
          ? [
              {
                label: 'Attendance rate',
                value: `${data.stats.attendance_rate}%`,
                icon: 'bi-graph-up',
                tone: 'assignments' as const,
              },
              {
                label: 'Present',
                value: data.stats.present_count,
                icon: 'bi-check-circle',
                tone: 'classes' as const,
              },
              {
                label: 'Absent',
                value: data.stats.absent_count,
                icon: 'bi-x-circle',
                tone: 'notifications' as const,
              },
              {
                label: 'Late',
                value: data.stats.late_count,
                icon: 'bi-clock',
                tone: 'students' as const,
              },
            ]
          : [
              {
                label: 'Student ID',
                value: data.student.student_id,
                icon: 'bi-person-badge',
                tone: 'students' as const,
              },
              {
                label: 'Grade',
                value: data.student.grade_level,
                icon: 'bi-mortarboard',
                tone: 'classes' as const,
              },
              {
                label: 'Classes',
                value: data.kind === 'grades' ? data.classes.length : 0,
                icon: 'bi-journal-bookmark',
                tone: 'assignments' as const,
              },
            ]
      }
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Link
          to="/teacher/students"
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
        >
          Back to students
        </Link>
        <a
          href={data.urls.printable}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-teal-300 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-900"
        >
          Open printable view
        </a>
        <a
          href={data.urls.pdf}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-900"
        >
          Download PDF
        </a>
      </div>

      <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Info label="Student" value={data.student.name} />
          <Info label="Student ID" value={data.student.student_id} />
          <Info label="Grade level" value={String(data.student.grade_level)} />
          <Info label="School year" value={data.school_year.name} />
        </div>

        {data.kind === 'grades' ? <GradesTable report={data} /> : <AttendanceTables report={data} />}
      </div>
    </TeacherTabShell>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2">
      <div className="text-[0.68rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      <div className="text-sm font-semibold text-hub-text">{value}</div>
    </div>
  )
}

function GradesTable({ report }: { report: GradesReport }) {
  const quarters = ['Q1', 'Q2', 'Q3', 'Q4']
  const classNames = Array.from(
    new Set(
      quarters.flatMap((q) => (report.grades_by_quarter[q] || []).map((row) => row.class_name)),
    ),
  ).sort()

  if (!classNames.length) {
    return <p className="text-sm text-hub-muted">No quarter grades on file for this school year.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr className="bg-teal-700 text-white">
            <th className="px-3 py-2 text-left font-semibold">Class</th>
            {quarters.map((q) => (
              <th key={q} className="px-3 py-2 text-center font-semibold">
                {q}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {classNames.map((className) => (
            <tr key={className} className="border-b border-slate-100 odd:bg-slate-50/60">
              <td className="px-3 py-2 font-medium text-hub-text">{className}</td>
              {quarters.map((q) => {
                const row = (report.grades_by_quarter[q] || []).find((r) => r.class_name === className)
                const label = row
                  ? `${row.letter || '—'}${row.percentage != null ? ` (${row.percentage}%)` : ''}`
                  : '—'
                return (
                  <td key={q} className="px-3 py-2 text-center font-semibold text-hub-text">
                    {label}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AttendanceTables({ report }: { report: AttendanceReport }) {
  if (!report.records_by_month.length) {
    return <p className="text-sm text-hub-muted">No attendance records for this school year.</p>
  }

  return (
    <div className="space-y-5">
      {report.records_by_month.map((group) => (
        <section key={group.month}>
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-hub-muted">{group.month}</h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Class</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Notes</th>
                </tr>
              </thead>
              <tbody>
                {group.records.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-3 py-2">{row.date_display}</td>
                    <td className="px-3 py-2">{row.class_name}</td>
                    <td className="px-3 py-2 font-semibold">{row.status}</td>
                    <td className="px-3 py-2 text-hub-muted">{row.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  )
}

export function TeacherStudentGradesReportPage() {
  return <TeacherStudentReportPage kind="grades" />
}

export function TeacherStudentAttendanceReportPage() {
  return <TeacherStudentReportPage kind="attendance" />
}
