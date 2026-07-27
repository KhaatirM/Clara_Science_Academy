import { Outlet } from 'react-router-dom'
import type { ManagementOutletContext } from '../../types/layout'
import type { AppVersionInfo, SchoolTimezone, SessionUser } from '../../types/session'
import {
  isManagementShellUser,
  isTeacherShellUser,
} from '../../config/navTypes'
import { useLegacyMgmtShell } from '../../hooks/useLegacyStyles'
import { AcademicConcernsHost } from '../academic/AcademicConcernsHost'
import { AppToastHost } from '../toasts/AppToastHost'
import { PortalUpdatesHost } from '../updates/PortalUpdatesHost'
import { Sidebar } from './Sidebar'

interface AppLayoutProps {
  user: SessionUser
  schoolTimezone: SchoolTimezone | null
  appVersion?: AppVersionInfo | null
}

export function AppLayout({ user, schoolTimezone, appVersion }: AppLayoutProps) {
  const legacyShell = useLegacyMgmtShell()
  const outletContext: ManagementOutletContext = { user, schoolTimezone }
  const showAcademicConcerns =
    isManagementShellUser(user) || isTeacherShellUser(user)
  const academicScope = isTeacherShellUser(user) ? 'teacher' : 'management'

  return (
    <div className="flex h-dvh w-full overflow-hidden">
      <Sidebar user={user} schoolTimezone={schoolTimezone} />
      <main
        className={
          legacyShell
            ? 'spa-main min-h-0 min-w-0 flex-1 overflow-y-auto p-2 md:p-4'
            : 'spa-main min-h-0 min-w-0 flex-1 overflow-y-auto p-4 md:p-8'
        }
      >
        <Outlet context={outletContext} />
      </main>
      <AppToastHost />
      <PortalUpdatesHost version={appVersion} />
      {showAcademicConcerns ? <AcademicConcernsHost scope={academicScope} /> : null}
    </div>
  )
}
