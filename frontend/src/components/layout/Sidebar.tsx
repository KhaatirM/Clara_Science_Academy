import { NavLink, useLocation } from 'react-router-dom'

import { getSidebarNav } from '../../config/appNav'
import {
  isStudentShellUser,
  isTeacherShellUser,
  navItemHref,
  navItemLabel,
  type NavItem,
} from '../../config/navTypes'
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
    'spa-sidebar-nav-link flex items-center rounded-xl text-sm font-medium transition',
    collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5',
  ].join(' ')
  const activeClass = 'is-active text-white shadow-sm'
  const idleClass = 'text-white/85 hover:text-white'

  if (item.reactTo) {
    return (
      <NavLink
        to={item.reactTo}
        end={
          item.reactTo === '/management' ||
          item.reactTo === '/teacher' ||
          item.reactTo === '/student'
        }
        title={collapsed ? label : undefined}
        className={({ isActive }) =>
          [baseClass, isActive || isReactActive ? activeClass : idleClass].join(' ')
        }
      >
        <i className={`bi ${item.icon} ${collapsed ? 'text-lg' : 'text-base'}`} aria-hidden />
        {!collapsed ? <span className="flex-1 leading-snug">{label}</span> : null}
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
      className="spa-sidebar-toggle mb-2 flex h-12 w-full cursor-pointer items-center justify-center text-white shadow-sm transition"
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
  const items = getSidebarNav(user)
  const teacherShell = isTeacherShellUser(user)
  const studentShell = isStudentShellUser(user)
  const showUsername = !teacherShell && !studentShell

  return (
    <>
      <div
        aria-hidden
        className="shrink-0 transition-[width] duration-300 ease-in-out"
        style={{ width }}
      />
      <aside
        className="sidebar spa-sidebar fixed left-0 top-0 z-[1000] flex h-dvh max-h-dvh flex-col overflow-hidden text-white shadow-lg transition-[width] duration-300 ease-in-out"
        style={{ width }}
      >
        <div className="sidebar-heading spa-sidebar-heading shrink-0 text-white">
          <div className={`px-4 py-4 text-center ${collapsed ? 'px-2' : ''}`}>
            {!collapsed ? (
              <>
                <h2 className="truncate text-lg font-bold">{user.sidebar_title}</h2>
                {!showUsername ? null : (
                  <p className="mt-0.5 truncate text-sm text-white/70">{user.username}</p>
                )}
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
          className="spa-sidebar-nav min-h-0 flex-1 space-y-1 overflow-y-auto overflow-x-hidden p-3"
          aria-label="Main"
        >
          {items.map((item) => (
            <NavRow
              key={item.id}
              item={item}
              user={user}
              collapsed={collapsed}
              isReactActive={Boolean(
                item.reactTo &&
                  (item.reactTo === '/teacher' || item.reactTo === '/student'
                    ? location.pathname === item.reactTo || location.pathname === `${item.reactTo}/`
                    : location.pathname === item.reactTo ||
                      location.pathname.startsWith(`${item.reactTo}/`)),
              )}
            />
          ))}
        </nav>

        <div className={`spa-sidebar-footer shrink-0 ${collapsed ? 'p-2' : 'p-3'}`}>
          <a
            href="/logout"
            title={collapsed ? 'Logout' : undefined}
            className={[
              'spa-sidebar-logout flex items-center justify-center gap-2 rounded-xl font-semibold text-white transition',
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
