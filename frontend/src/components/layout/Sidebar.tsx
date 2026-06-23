import { NavLink, useLocation } from 'react-router-dom'

import {
  MANAGEMENT_NAV,
  hasNavAccess,
  navItemHref,
  navItemLabel,
  type NavItem,
} from '../../config/managementNav'
import { useSidebarCollapse } from '../../hooks/useSidebarCollapse'
import type { SchoolTimezone, SessionUser } from '../../types/session'
import { SidebarSchoolClock } from './SidebarSchoolClock'

interface SidebarProps {
  user: SessionUser
  schoolTimezone: SchoolTimezone | null
}

function NavRow({
  item,
  user,
  collapsed,
  isReactActive,
}: {
  item: NavItem
  user: SessionUser
  collapsed: boolean
  isReactActive: boolean
}) {
  const label = navItemLabel(item, user)
  const baseClass = [
    'flex items-center rounded-xl text-sm font-medium transition',
    collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5',
  ].join(' ')
  const activeClass = 'bg-white/15 text-white shadow-sm ring-1 ring-inset ring-white/20'
  const idleClass = 'text-white/85 hover:bg-white/10 hover:text-white'

  if (item.reactTo) {
    return (
      <NavLink
        to={item.reactTo}
        end={item.reactTo === '/management'}
        title={collapsed ? label : undefined}
        className={({ isActive }) =>
          [baseClass, isActive || isReactActive ? activeClass : idleClass].join(' ')
        }
      >
        <i className={`bi ${item.icon} ${collapsed ? 'text-lg' : 'text-base'}`} aria-hidden />
        {!collapsed ? <span className="flex-1">{label}</span> : null}
      </NavLink>
    )
  }

  return (
    <a
      href={navItemHref(item)}
      title={collapsed ? label : undefined}
      className={[baseClass, idleClass].join(' ')}
    >
      <i className={`bi ${item.icon} ${collapsed ? 'text-lg' : 'text-base'}`} aria-hidden />
      {!collapsed ? <span className="flex-1">{label}</span> : null}
    </a>
  )
}

function SidebarToggle({
  collapsed,
  onToggle,
}: {
  collapsed: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="mb-2 flex h-12 w-full cursor-pointer items-center justify-center border-b border-sky-500/60 bg-gradient-to-r from-slate-800 to-slate-700 text-white shadow-sm transition hover:from-slate-700 hover:to-slate-600"
      aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
    >
      {collapsed ? (
        <span className="flex h-10 w-full flex-col justify-between px-3 py-2" aria-hidden>
          <span className="block h-1 rounded bg-white/90" />
          <span className="block h-1 rounded bg-white/90" />
          <span className="block h-1 rounded bg-white/90" />
        </span>
      ) : (
        <span className="px-3 text-xs font-bold uppercase tracking-wider">Collapse</span>
      )}
    </button>
  )
}

export function Sidebar({ user, schoolTimezone }: SidebarProps) {
  const location = useLocation()
  const { collapsed, toggle, width } = useSidebarCollapse()
  const items = MANAGEMENT_NAV.filter((item) => hasNavAccess(user, item))

  return (
    <>
      <div
        aria-hidden
        className="shrink-0 transition-[width] duration-300 ease-in-out"
        style={{ width }}
      />
      <aside
        className="fixed left-0 top-0 z-[1000] flex h-dvh max-h-dvh flex-col overflow-hidden border-r border-slate-700 bg-slate-900 text-white shadow-lg transition-[width] duration-300 ease-in-out"
        style={{ width }}
      >
        <div className="shrink-0 border-b border-indigo-100/80 bg-slate-900 text-white">
          <div className={`px-4 py-4 text-center ${collapsed ? 'px-2' : ''}`}>
            {!collapsed ? (
              <>
                <h2 className="truncate text-lg font-bold">{user.sidebar_title}</h2>
                <p className="mt-0.5 truncate text-sm text-white/70">{user.username}</p>
              </>
            ) : (
              <p className="text-[0.65rem] font-bold uppercase tracking-wide text-white/70">
                CSA
              </p>
            )}
          </div>

          <SidebarSchoolClock timezone={schoolTimezone} collapsed={collapsed} />

          <SidebarToggle collapsed={collapsed} onToggle={toggle} />
        </div>

        <nav
          className="min-h-0 flex-1 space-y-1 overflow-y-auto overflow-x-hidden p-3"
          aria-label="Main"
        >
          {items.map((item) => (
            <NavRow
              key={item.id}
              item={item}
              user={user}
              collapsed={collapsed}
              isReactActive={Boolean(item.reactTo && location.pathname === item.reactTo)}
            />
          ))}
        </nav>

        <div className={`shrink-0 border-t border-slate-700 bg-slate-900 ${collapsed ? 'p-2' : 'p-3'}`}>
          <a
            href="/logout"
            title={collapsed ? 'Logout' : undefined}
            className={[
              'flex items-center justify-center gap-2 rounded-xl bg-red-600 font-semibold text-white transition hover:bg-red-700',
              collapsed ? 'px-2 py-2.5 text-base' : 'w-full px-3 py-2.5 text-sm',
            ].join(' ')}
          >
            <i className="bi bi-box-arrow-right" aria-hidden />
            {!collapsed ? <span>Logout</span> : null}
          </a>
        </div>
      </aside>
    </>
  )
}
