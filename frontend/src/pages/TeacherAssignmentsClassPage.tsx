import { AssignmentsClassPage } from './AssignmentsClassPage'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'

export function TeacherAssignmentsClassPage() {
  return (
    <ManagementPageShell>
      <AssignmentsClassPage scope="teacher" />
    </ManagementPageShell>
  )
}
