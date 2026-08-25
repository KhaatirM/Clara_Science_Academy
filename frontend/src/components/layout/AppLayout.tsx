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
import { IdleSessionGuard } from '../session/IdleSessionGuard'
import { ForcePasswordChangeHost } from '../session/ForcePasswordChangeHost'
import { Sidebar } from './Sidebar'

interface AppLayoutProps {
  user: SessionUser
  schoolTimezone: SchoolTimezone | null
  appVersion?: AppVersionInfo | null
  idleTimeoutMinutes?: number
  onSessionRefresh?: () => Promise<void> | void
}

export function AppLayout({
  user,
  schoolTimezone,
  appVersion,
  idleTimeoutMinutes = 30,
  onSessionRefresh,
}: AppLayoutProps) {
  const legacyShell = useLegacyMgmtShell()
  const outletContext: ManagementOutletContext = { user, schoolTimezone }
  const showAcademicConcerns =
    isManagementShellUser(user) || isTeacherShellUser(user)
  const academicScope = isTeacherShellUser(user) ? 'teacher' : 'management'

  return (
    <div className="flex h-dvh w-full overflow-hidden">
      <IdleSessionGuard timeoutMinutes={idleTimeoutMinutes} />
      <Sidebar user={user} schoolTimezone={schoolTimezone} />
      <main
        className={
          legacyShell
            ? 'spa-main min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto p-2 pt-14 min-[576px]:p-2 min-[576px]:pt-2 md:p-4 md:pt-4'
            : 'spa-main min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto p-2 pt-14 min-[576px]:p-3 min-[576px]:pt-3 md:p-6 md:pt-6 lg:p-8 lg:pt-8'
        }
      >
        <Outlet context={outletContext} />
      </main>
      <AppToastHost />
      <PortalUpdatesHost version={appVersion} />
      {showAcademicConcerns ? <AcademicConcernsHost scope={academicScope} /> : null}
      <ForcePasswordChangeHost
        user={user}
        onChanged={async () => {
          await onSessionRefresh?.()
        }}
      />
    </div>
  )
}
