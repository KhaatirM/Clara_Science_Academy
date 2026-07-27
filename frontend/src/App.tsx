import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { useSession } from './hooks/useSession'
import { AssignmentGradePage } from './pages/AssignmentGradePage'
import { AssignmentViewPage } from './pages/AssignmentViewPage'
import { AssignmentsClassPage } from './pages/AssignmentsClassPage'
import { CreateAssignmentPage } from './pages/CreateAssignmentPage'
import { CreateGroupClassPickerPage } from './pages/CreateGroupClassPickerPage'
import { CreateGroupDiscussionAssignmentPage } from './pages/CreateGroupDiscussionAssignmentPage'
import { CreateGroupPdfAssignmentPage } from './pages/CreateGroupPdfAssignmentPage'
import { CreateGroupQuizAssignmentPage } from './pages/CreateGroupQuizAssignmentPage'
import { CreateGroupTypePage } from './pages/CreateGroupTypePage'
import { CreateDiscussionAssignmentPage } from './pages/CreateDiscussionAssignmentPage'
import { CreatePdfAssignmentPage } from './pages/CreatePdfAssignmentPage'
import { CreateQuizAssignmentPage } from './pages/CreateQuizAssignmentPage'
import { AssignmentsGradesHubPage } from './pages/AssignmentsGradesHubPage'
import AttendancePage from './pages/AttendancePage'
import AttendanceAnalyticsPage from './pages/AttendanceAnalyticsPage'
import AttendanceReportsPage from './pages/AttendanceReportsPage'
import ReportCardsPage from './pages/ReportCardsPage'
import ReportCardsCategoryPage from './pages/ReportCardsCategoryPage'
import ReportCardsTranscriptsPage from './pages/ReportCardsTranscriptsPage'
import ReportCardGeneratePage from './pages/ReportCardGeneratePage'
import ReportCardDetailPage from './pages/ReportCardDetailPage'
import ReportCardHistoryPage from './pages/ReportCardHistoryPage'
import GradeStandardsHubPage from './pages/GradeStandardsHubPage'
import GradeStandardsEditorPage from './pages/GradeStandardsEditorPage'
import BillingPage from './pages/BillingPage'
import StudentJobsPage from './pages/StudentJobsPage'
import SettingsPage from './pages/SettingsPage'
import { CalendarPage } from './pages/CalendarPage'
import { ClosureDashboardPage } from './pages/ClosureDashboardPage'
import { ClosureSchedulePage } from './pages/ClosureSchedulePage'
import { SchoolYearsPage } from './pages/SchoolYearsPage'
import { ClassEditPage } from './pages/ClassEditPage'
import { ClassGradesPage } from './pages/ClassGradesPage'
import { ClassGroupsPage } from './pages/ClassGroupsPage'
import { ClassRosterPage } from './pages/ClassRosterPage'
import { ClassViewPage } from './pages/ClassViewPage'
import { ClassNotesPage } from './pages/ClassNotesPage'
import { ClassesPage } from './pages/ClassesPage'
import { CoreClassSetupPage } from './pages/CoreClassSetupPage'
import { ExtensionRequestsPage } from './pages/ExtensionRequestsPage'
import { HomePage } from './pages/HomePage'
import { RedoDashboardPage } from './pages/RedoDashboardPage'
import { StaffFormPage } from './pages/StaffFormPage'
import { StaffRosterPage } from './pages/StaffRosterPage'
import { ParentsPage } from './pages/ParentsPage'
import { StudentFormPage } from './pages/StudentFormPage'
import { StudentsPage } from './pages/StudentsPage'
import { TeacherHomePage } from './pages/TeacherHomePage'
import { TeacherClassesPage } from './pages/TeacherClassesPage'
import { TeacherClassViewPage } from './pages/TeacherClassViewPage'
import { TeacherAssistantApprovalsPage } from './pages/TeacherAssistantApprovalsPage'
import {
  TeacherStudentAttendanceReportPage,
  TeacherStudentGradesReportPage,
} from './pages/TeacherStudentReportPage'
import { TeacherStudentsPage } from './pages/TeacherStudentsPage'
import { TeacherAssignmentsGradesPage } from './pages/TeacherAssignmentsGradesPage'
import { TeacherAssignmentsClassPage } from './pages/TeacherAssignmentsClassPage'
import { TeacherAttendancePage } from './pages/TeacherAttendancePage'
import { TeacherTakeAttendancePage } from './pages/TakeClassAttendancePage'
import { ManagementAttendanceRecordsPage, TeacherAttendanceRecordsPage } from './pages/ClassAttendanceRecordsPage'
import { TeacherSchedulePage } from './pages/TeacherSchedulePage'
import { TeacherCalendarPage } from './pages/TeacherCalendarPage'
import { TeacherSettingsPage } from './pages/TeacherSettingsPage'
import { StudentHomePage } from './pages/StudentHomePage'
import { StudentAssignmentsPage } from './pages/StudentAssignmentsPage'
import { StudentClassesPage } from './pages/StudentClassesPage'
import { StudentClassViewPage } from './pages/StudentClassViewPage'
import { StudentGradesPage } from './pages/StudentGradesPage'
import { StudentCollaboratePage } from './pages/StudentCollaboratePage'
import { StudentSchedulePage } from './pages/StudentSchedulePage'
import { StudentCalendarPage } from './pages/StudentCalendarPage'
import { StudentJobsPortalPage } from './pages/StudentJobsPortalPage'
import { StudentSettingsPage } from './pages/StudentSettingsPage'
import { StudentTakeQuizPage } from './pages/StudentTakeQuizPage'
import { ParentHomePage } from './pages/ParentHomePage'
import {
  ParentAttendancePage,
  ParentClassesPage,
  ParentGradesPage,
  ParentReportCardsPage,
} from './pages/ParentPortalTabPages'
import { ParentSettingsPage } from './pages/ParentSettingsPage'
import {
  StudentDiscussionPage,
  StudentDiscussionThreadPage,
} from './pages/StudentDiscussionPage'
import TakeClassAttendancePage from './pages/TakeClassAttendancePage'
import ClassAdminToolPage from './pages/ClassAdminToolPage'
import { EditAssignmentRedirectPage } from './pages/EditAssignmentRedirectPage'
import { AssignmentSubmissionsPage } from './pages/AssignmentSubmissionsPage'
import { TeachersStaffPage } from './pages/TeachersStaffPage'
import { spaHomePath, isStudentShellUser, isTeacherShellUser, isTechShellUser, isParentShellUser } from './config/navTypes'
import { TechHomePage } from './pages/TechHomePage'
import {
  TechDeviceFormPage,
  TechDevicesPage,
  TechSettingsPage,
} from './pages/TechDevicesSettingsPages'
import {
  TechActivityLogPage,
  TechAuditLogsPage,
  TechBugReportsPage,
  TechBugsPage,
  TechErrorReportsPage,
  TechLogsPage,
  TechSystemPage,
  TechUserDetailPage,
  TechUserManagementPage,
} from './pages/TechLogsSystemUsersPages'

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
  const { user, schoolTimezone, appVersion, loading, error } = useSession()

  if (loading) return <LoadingScreen />
  if (error) return <ErrorScreen message={error} />
  if (!user) return <LoadingScreen />

  if (
    !user.management_entry &&
    !user.management_shell &&
    !user.teacher_entry &&
    !user.student_entry &&
    !user.tech_entry &&
    !user.parent_entry
  ) {
    return (
      <ErrorScreen message="Your account does not have access to the React app yet." />
    )
  }

  const studentShell = isStudentShellUser(user)
  const teacherShell = isTeacherShellUser(user)
  const techShell = isTechShellUser(user)
  const parentShell = isParentShellUser(user)
  const homePath = spaHomePath(user)

  return (
    <BrowserRouter basename="/app">
      <Routes>
        <Route element={<AppLayout user={user} schoolTimezone={schoolTimezone} appVersion={appVersion} />}>
          <Route index element={<Navigate to={homePath} replace />} />
          {techShell ? (
            <>
              <Route path="/tech" element={<TechHomePage />} />
              <Route path="/tech/devices" element={<TechDevicesPage />} />
              <Route path="/tech/devices/new" element={<TechDeviceFormPage />} />
              <Route path="/tech/devices/:deviceId/edit" element={<TechDeviceFormPage />} />
              <Route path="/tech/logs" element={<TechLogsPage />} />
              <Route path="/tech/activity-log" element={<TechActivityLogPage />} />
              <Route path="/tech/audit-logs" element={<TechAuditLogsPage />} />
              <Route path="/tech/bugs" element={<TechBugsPage />} />
              <Route path="/tech/error-reports" element={<TechErrorReportsPage />} />
              <Route path="/tech/bug-reports" element={<TechBugReportsPage />} />
              <Route path="/tech/system" element={<TechSystemPage />} />
              <Route path="/tech/users" element={<TechUserManagementPage />} />
              <Route path="/tech/users/:userId" element={<TechUserDetailPage />} />
              <Route path="/tech/settings" element={<TechSettingsPage />} />
              <Route path="*" element={<Navigate to="/tech" replace />} />
            </>
          ) : parentShell ? (
            <>
              <Route path="/parent" element={<ParentHomePage />} />
              <Route path="/parent/grades" element={<ParentGradesPage />} />
              <Route path="/parent/attendance" element={<ParentAttendancePage />} />
              <Route path="/parent/classes" element={<ParentClassesPage />} />
              <Route path="/parent/report-cards" element={<ParentReportCardsPage />} />
              <Route path="/parent/settings" element={<ParentSettingsPage />} />
              <Route path="*" element={<Navigate to="/parent" replace />} />
            </>
          ) : studentShell ? (
            <>
              <Route path="/student" element={<StudentHomePage />} />
              <Route path="/student/assignments" element={<StudentAssignmentsPage />} />
              <Route path="/student/classes" element={<StudentClassesPage />} />
              <Route path="/student/classes/:classId" element={<StudentClassViewPage />} />
              <Route path="/student/classes/:classId/notes" element={<ClassNotesPage />} />
              <Route path="/student/grades" element={<StudentGradesPage />} />
              <Route path="/student/collaborate" element={<StudentCollaboratePage />} />
              <Route path="/student/submissions" element={<Navigate to="/student/collaborate" replace />} />
              <Route path="/student/schedule" element={<StudentSchedulePage />} />
              <Route path="/student/calendar" element={<StudentCalendarPage />} />
              <Route path="/student/jobs" element={<StudentJobsPortalPage />} />
              <Route path="/student/settings" element={<StudentSettingsPage />} />
              <Route path="/student/settings/bug-reports" element={<StudentSettingsPage />} />
              <Route path="/student/take-quiz/:assignmentId" element={<StudentTakeQuizPage />} />
              <Route path="/student/discussion/:assignmentId" element={<StudentDiscussionPage />} />
              <Route
                path="/student/discussion/:assignmentId/thread/:threadId"
                element={<StudentDiscussionThreadPage />}
              />
              <Route path="*" element={<Navigate to="/student" replace />} />
            </>
          ) : teacherShell ? (
            <>
              <Route path="/teacher" element={<TeacherHomePage />} />
              <Route path="/teacher/classes" element={<TeacherClassesPage />} />
              <Route path="/teacher/classes/:classId" element={<TeacherClassViewPage />} />
              <Route path="/teacher/classes/:classId/notes" element={<ClassNotesPage />} />
              <Route path="/teacher/classes/:classId/groups" element={<ClassGroupsPage />} />
              <Route
                path="/teacher/classes/:classId/assistant-approvals"
                element={<TeacherAssistantApprovalsPage />}
              />
              <Route
                path="/teacher/classes/:classId/standards/:grade"
                element={<GradeStandardsEditorPage />}
              />
              <Route path="/teacher/students" element={<TeacherStudentsPage />} />
              <Route
                path="/teacher/students/:studentId/grades"
                element={<TeacherStudentGradesReportPage />}
              />
              <Route
                path="/teacher/students/:studentId/attendance"
                element={<TeacherStudentAttendanceReportPage />}
              />
              <Route path="/teacher/assignments-and-grades" element={<TeacherAssignmentsGradesPage />} />
              <Route path="/teacher/assignments/create" element={<CreateAssignmentPage />} />
              <Route path="/teacher/assignments/create/pdf" element={<CreatePdfAssignmentPage />} />
              <Route path="/teacher/assignments/create/group" element={<CreateGroupClassPickerPage />} />
              <Route path="/teacher/assignments/create/group/:classId" element={<CreateGroupTypePage />} />
              <Route path="/teacher/assignments/create/group/:classId/pdf" element={<CreateGroupPdfAssignmentPage />} />
              <Route path="/teacher/assignments/create/group/:classId/quiz" element={<CreateGroupQuizAssignmentPage />} />
              <Route path="/teacher/assignments/create/group/:classId/discussion" element={<CreateGroupDiscussionAssignmentPage />} />
              <Route path="/teacher/assignments/create/discussion" element={<CreateDiscussionAssignmentPage />} />
              <Route path="/teacher/assignments/create/quiz" element={<CreateQuizAssignmentPage />} />
              <Route path="/teacher/extensions" element={<ExtensionRequestsPage />} />
              <Route path="/teacher/redo" element={<RedoDashboardPage />} />
              <Route path="/teacher/assignments-and-grades/:classId">
                <Route index element={<TeacherAssignmentsClassPage />} />
                <Route path="individual/:assignmentId/view" element={<AssignmentViewPage />} />
                <Route path="individual/:assignmentId/submissions" element={<AssignmentSubmissionsPage />} />
                <Route path="individual/:assignmentId/edit" element={<EditAssignmentRedirectPage />} />
                <Route path="individual/:assignmentId/grade" element={<AssignmentGradePage />} />
                <Route path="group/:assignmentId/view" element={<AssignmentViewPage />} />
                <Route path="group/:assignmentId/submissions" element={<AssignmentSubmissionsPage />} />
                <Route path="group/:assignmentId/edit" element={<EditAssignmentRedirectPage />} />
                <Route path="group/:assignmentId/grade" element={<AssignmentGradePage />} />
              </Route>
              <Route path="/teacher/attendance" element={<TeacherAttendancePage />} />
              <Route path="/teacher/attendance/take/:classId" element={<TeacherTakeAttendancePage />} />
              <Route path="/teacher/attendance/records/:classId" element={<TeacherAttendanceRecordsPage />} />
              <Route path="/teacher/schedule" element={<TeacherSchedulePage />} />
              <Route path="/teacher/calendar" element={<TeacherCalendarPage />} />
              <Route path="/teacher/settings/bug-reports" element={<TeacherSettingsPage />} />
              <Route path="/teacher/settings" element={<TeacherSettingsPage />} />
              <Route path="*" element={<Navigate to="/teacher" replace />} />
            </>
          ) : (
            <>
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
            <Route path="create/group/:classId/discussion" element={<CreateGroupDiscussionAssignmentPage />} />
            <Route path="create/discussion" element={<CreateDiscussionAssignmentPage />} />
            <Route path="create/quiz" element={<CreateQuizAssignmentPage />} />
            <Route path=":classId">
              <Route index element={<AssignmentsClassPage />} />
              <Route path="individual/:assignmentId/view" element={<AssignmentViewPage />} />
              <Route path="individual/:assignmentId/submissions" element={<AssignmentSubmissionsPage />} />
              <Route path="individual/:assignmentId/edit" element={<EditAssignmentRedirectPage />} />
              <Route path="individual/:assignmentId/grade" element={<AssignmentGradePage />} />
              <Route path="group/:assignmentId/view" element={<AssignmentViewPage />} />
              <Route path="group/:assignmentId/submissions" element={<AssignmentSubmissionsPage />} />
              <Route path="group/:assignmentId/edit" element={<EditAssignmentRedirectPage />} />
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
            <Route path=":classId/groups" element={<ClassGroupsPage />} />
            <Route path=":classId/grades" element={<ClassGradesPage />} />
            <Route path=":classId/notes" element={<ClassNotesPage />} />
            <Route path=":classId/tools/:tool" element={<ClassAdminToolPage />} />
            <Route path=":classId" element={<ClassViewPage />} />
          </Route>
          <Route path="/management/students" element={<StudentsPage />} />
          <Route path="/management/students/new" element={<StudentFormPage />} />
          <Route path="/management/parents" element={<ParentsPage />} />
          <Route path="/management/attendance/take/:classId" element={<TakeClassAttendancePage />} />
          <Route path="/management/attendance/records/:classId" element={<ManagementAttendanceRecordsPage />} />
          <Route path="/management/attendance" element={<AttendancePage />} />
          <Route path="/management/attendance/reports" element={<AttendanceReportsPage />} />
          <Route path="/management/attendance/analytics" element={<AttendanceAnalyticsPage />} />
          <Route path="/management/billing" element={<BillingPage />} />
          <Route path="/management/student-jobs" element={<StudentJobsPage />} />
          <Route path="/management/settings">
            <Route index element={<SettingsPage />} />
            <Route path="bug-reports" element={<SettingsPage />} />
          </Route>
          <Route path="/management/report-cards">
            <Route index element={<ReportCardsPage />} />
            <Route path="generate" element={<ReportCardGeneratePage />} />
            <Route path="generate/:studentId" element={<ReportCardGeneratePage />} />
            <Route path="student/:studentId" element={<ReportCardHistoryPage />} />
            <Route path="category/:category" element={<ReportCardsCategoryPage />} />
            <Route path="transcripts" element={<ReportCardsTranscriptsPage />} />
            <Route path="standards/:grade" element={<GradeStandardsHubPage />} />
            <Route path="standards/:grade/:classId" element={<GradeStandardsEditorPage />} />
            <Route path=":reportCardId" element={<ReportCardDetailPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/management" replace />} />
            </>
          )}
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
