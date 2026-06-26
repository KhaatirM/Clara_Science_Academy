import { Outlet } from 'react-router-dom'
import type { ManagementOutletContext } from '../../types/layout'
import type { SchoolTimezone, SessionUser } from '../../types/session'
import { useLegacyMgmtShell } from '../../hooks/useLegacyStyles'
import { Sidebar } from './Sidebar'

interface AppLayoutProps {
  user: SessionUser
  schoolTimezone: SchoolTimezone | null
}

export function AppLayout({ user, schoolTimezone }: AppLayoutProps) {
  const legacyShell = useLegacyMgmtShell()
  const outletContext: ManagementOutletContext = { user, schoolTimezone }

  return (
    <div className="flex h-dvh w-full overflow-hidden">
      <Sidebar user={user} schoolTimezone={schoolTimezone} />
      <main
        className={
          legacyShell
            ? 'min-h-0 min-w-0 flex-1 overflow-y-auto bg-[#f8f9fa] p-2 md:p-4'
            : 'min-h-0 min-w-0 flex-1 overflow-y-auto bg-slate-100 p-4 md:p-8'
        }
      >
        <Outlet context={outletContext} />
      </main>
    </div>
  )
}
