import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { useSession } from './hooks/useSession'
import { AssignmentGradePage } from './pages/AssignmentGradePage'
import { AssignmentViewPage } from './pages/AssignmentViewPage'
import { AssignmentsClassPage } from './pages/AssignmentsClassPage'
import { CreateAssignmentPage } from './pages/CreateAssignmentPage'
import { CreateGroupClassPickerPage } from './pages/CreateGroupClassPickerPage'
import { CreateGroupPdfAssignmentPage } from './pages/CreateGroupPdfAssignmentPage'
import { CreateGroupQuizAssignmentPage } from './pages/CreateGroupQuizAssignmentPage'
import { CreateGroupTypePage } from './pages/CreateGroupTypePage'
import { CreateDiscussionAssignmentPage } from './pages/CreateDiscussionAssignmentPage'
import { CreatePdfAssignmentPage } from './pages/CreatePdfAssignmentPage'
import { CreateQuizAssignmentPage } from './pages/CreateQuizAssignmentPage'
import { AssignmentsGradesHubPage } from './pages/AssignmentsGradesHubPage'
import { CalendarPage } from './pages/CalendarPage'
import { ClosureDashboardPage } from './pages/ClosureDashboardPage'
import { ClosureSchedulePage } from './pages/ClosureSchedulePage'
import { SchoolYearsPage } from './pages/SchoolYearsPage'
import { ClassEditPage } from './pages/ClassEditPage'
import { ClassGradesPage } from './pages/ClassGradesPage'
import { ClassRosterPage } from './pages/ClassRosterPage'
import { ClassViewPage } from './pages/ClassViewPage'
import { ClassesPage } from './pages/ClassesPage'
import { CoreClassSetupPage } from './pages/CoreClassSetupPage'
import { ExtensionRequestsPage } from './pages/ExtensionRequestsPage'
import { HomePage } from './pages/HomePage'
import { RedoDashboardPage } from './pages/RedoDashboardPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { StaffFormPage } from './pages/StaffFormPage'
import { StaffRosterPage } from './pages/StaffRosterPage'
import { ParentsPage } from './pages/ParentsPage'
import { StudentFormPage } from './pages/StudentFormPage'
import { StudentsPage } from './pages/StudentsPage'
import { TeachersStaffPage } from './pages/TeachersStaffPage'

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="rounded-2xl bg-white/90 px-6 py-4 text-hub-muted shadow-lg">
        Loading…
      </div>
    </div>
  )
}

function ErrorScreen({ message }: { message: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="max-w-md rounded-2xl bg-white p-6 shadow-lg">
        <h1 className="text-lg font-bold text-red-700">Could not start app</h1>
        <p className="mt-2 text-sm text-hub-muted">{message}</p>
        <a href="/login" className="mt-4 inline-block text-sm font-semibold text-hub-accent">
          Return to login
        </a>
      </div>
    </div>
  )
}

export default function App() {
  const { user, schoolTimezone, loading, error } = useSession()

  if (loading) return <LoadingScreen />
  if (error) return <ErrorScreen message={error} />
  if (!user) return <LoadingScreen />

  if (!user.management_entry) {
    return (
      <ErrorScreen message="Your account does not have access to the management React app yet." />
    )
  }

  return (
    <BrowserRouter basename="/app">
      <Routes>
        <Route element={<AppLayout user={user} schoolTimezone={schoolTimezone} />}>
          <Route index element={<Navigate to="/management" replace />} />
          <Route path="/management" element={<HomePage />} />
          <Route path="/management/calendar" element={<CalendarPage />} />
          <Route path="/management/school-years" element={<SchoolYearsPage />} />
          <Route path="/management/school-year/closure/schedule" element={<ClosureSchedulePage />} />
          <Route path="/management/school-year/closure/:closureId" element={<ClosureDashboardPage />} />
          <Route path="/management/teachers">
            <Route index element={<TeachersStaffPage />} />
            <Route path="roster" element={<StaffRosterPage />} />
            <Route path="new" element={<StaffFormPage />} />
            <Route path=":staffId/edit" element={<StaffFormPage />} />
          </Route>
          <Route path="/management/assignments">
            <Route index element={<AssignmentsGradesHubPage />} />
            <Route path="create" element={<CreateAssignmentPage />} />
            <Route path="create/pdf" element={<CreatePdfAssignmentPage />} />
            <Route path="create/group" element={<CreateGroupClassPickerPage />} />
            <Route path="create/group/:classId" element={<CreateGroupTypePage />} />
            <Route path="create/group/:classId/pdf" element={<CreateGroupPdfAssignmentPage />} />
            <Route path="create/group/:classId/quiz" element={<CreateGroupQuizAssignmentPage />} />
            <Route path="create/discussion" element={<CreateDiscussionAssignmentPage />} />
            <Route path="create/quiz" element={<CreateQuizAssignmentPage />} />
            <Route path=":classId">
              <Route index element={<AssignmentsClassPage />} />
              <Route path="individual/:assignmentId/view" element={<AssignmentViewPage />} />
              <Route path="individual/:assignmentId/grade" element={<AssignmentGradePage />} />
              <Route path="group/:assignmentId/view" element={<AssignmentViewPage />} />
              <Route path="group/:assignmentId/grade" element={<AssignmentGradePage />} />
            </Route>
          </Route>
          <Route path="/management/extensions" element={<ExtensionRequestsPage />} />
          <Route path="/management/redo" element={<RedoDashboardPage />} />
          <Route path="/management/classes">
            <Route index element={<ClassesPage />} />
            <Route path="core-setup" element={<CoreClassSetupPage />} />
            <Route path=":classId/edit" element={<ClassEditPage />} />
            <Route path=":classId/roster" element={<ClassRosterPage />} />
            <Route path=":classId/grades" element={<ClassGradesPage />} />
            <Route path=":classId" element={<ClassViewPage />} />
          </Route>
          <Route path="/management/students" element={<StudentsPage />} />
          <Route path="/management/students/new" element={<StudentFormPage />} />
          <Route path="/management/parents" element={<ParentsPage />} />
          <Route
            path="/management/report-cards"
            element={
              <PlaceholderPage
                title="Report Cards"
                description="List, generate, and release report cards to families."
                legacyPath="/management/report-cards"
              />
            }
          />
          <Route
            path="/management/settings"
            element={
              <PlaceholderPage
                title="Settings"
                description="School-wide configuration and preferences."
                legacyPath="/management/settings"
              />
            }
          />
          <Route path="*" element={<Navigate to="/management" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
