import { useParams } from 'react-router-dom'

import { TakeAttendanceWorkspace } from '../components/attendance/TakeAttendanceWorkspace'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'

export function TeacherTakeAttendancePage() {
  const { classId = '' } = useParams()
  const id = Number(classId)

  return (
    <TeacherTabShell eyebrow="Attendance" title="Take attendance" subtitle="Class period attendance" stats={[]}>
      <TakeAttendanceWorkspace
        classId={id}
        apiBase={`/api/spa/teacher/attendance/take/${id}`}
        hubPath="/teacher/attendance"
        classViewPath={`/teacher/classes/${id}`}
        recordsPath={`/teacher/attendance/records/${id}`}
        shell="teacher"
      />
    </TeacherTabShell>
  )
}

export default function TakeClassAttendancePage() {
  const { classId = '' } = useParams()
  const id = Number(classId)

  return (
    <ManagementPageShell>
      <TakeAttendanceWorkspace
        classId={id}
        apiBase={`/api/spa/attendance/take/${id}`}
        hubPath="/management/attendance"
        classViewPath={`/management/classes/${id}`}
        recordsPath={`/management/attendance/records/${id}`}
        shell="management"
      />
    </ManagementPageShell>
  )
}
