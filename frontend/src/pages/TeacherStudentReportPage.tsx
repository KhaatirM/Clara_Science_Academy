import { Link, useParams } from 'react-router-dom'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'

export function TeacherStudentReportPage({ kind }: { kind: 'grades' | 'attendance' }) {
  const { studentId = '' } = useParams()
  const id = Number(studentId)
  const legacySrc =
    kind === 'grades' ? `/teacher/student/${id}/grades` : `/teacher/student/${id}/attendance`
  const title = kind === 'grades' ? 'Student grades report' : 'Student attendance report'

  return (
    <TeacherTabShell eyebrow="Students" title={title} subtitle="Printable report" stats={[]}>
      <div className="mb-3 flex flex-wrap gap-2">
        <Link
          to="/teacher/students"
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
        >
          Back to students
        </Link>
        <a
          href={legacySrc}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-teal-300 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-900"
        >
          Open printable view
        </a>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <iframe title={title} src={legacySrc} className="h-[75vh] w-full border-0" />
      </div>
    </TeacherTabShell>
  )
}

export function TeacherStudentGradesReportPage() {
  return <TeacherStudentReportPage kind="grades" />
}

export function TeacherStudentAttendanceReportPage() {
  return <TeacherStudentReportPage kind="attendance" />
}
