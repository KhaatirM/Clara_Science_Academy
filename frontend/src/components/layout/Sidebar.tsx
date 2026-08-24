import { useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

import { getSidebarNav } from '../../config/appNav'
import {
  isParentShellUser,
  isStudentShellUser,
  isTeacherShellUser,
  isTechShellUser,
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
  onNavigate,
}: {
  item: NavItem
  user: SessionUser
  collapsed: boolean
  isReactActive: boolean
  onNavigate?: () => void
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
          item.reactTo === '/student' ||
          item.reactTo === '/parent' ||
          item.reactTo === '/tech'
        }
        title={collapsed ? label : undefined}
        onClick={onNavigate}
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
      onClick={onNavigate}
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
  isDrawerMode,
}: {
  collapsed: boolean
  onToggle: () => void
  isDrawerMode: boolean
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="spa-sidebar-toggle mb-2 flex h-12 w-full cursor-pointer items-center justify-center text-white shadow-sm transition"
      aria-label={
        isDrawerMode ? 'Close menu' : collapsed ? 'Expand sidebar' : 'Collapse sidebar'
      }
    >
      {isDrawerMode ? (
        <span className="px-3 text-xs font-bold uppercase tracking-wider">Close</span>
      ) : collapsed ? (
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
  const {
    collapsed,
    toggle,
    width,
    spacerWidth,
    isDrawerMode,
    mobileOpen,
    openMobile,
    closeMobile,
    toggleMobile,
  } = useSidebarCollapse()
  const items = getSidebarNav(user)
  const teacherShell = isTeacherShellUser(user)
  const studentShell = isStudentShellUser(user)
  const parentShell = isParentShellUser(user)
  const techShell = isTechShellUser(user)
  const showUsername = !teacherShell && !studentShell && !parentShell && !techShell

  // Auto-close the phone drawer after any route change.
  useEffect(() => {
    if (isDrawerMode) closeMobile()
  }, [location.pathname, isDrawerMode, closeMobile])

  // Escape closes the drawer.
  useEffect(() => {
    if (!isDrawerMode || !mobileOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMobile()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isDrawerMode, mobileOpen, closeMobile])

  // Prevent background scroll while the drawer is open.
  useEffect(() => {
    if (!isDrawerMode || !mobileOpen) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [isDrawerMode, mobileOpen])

  const handleNavigate = isDrawerMode ? closeMobile : undefined
  const railCollapsed = !isDrawerMode && collapsed

  return (
    <>
      {/* Desktop spacer — zero on phone so content uses full width */}
      <div
        aria-hidden
        className="shrink-0 transition-[width] duration-300 ease-in-out"
        style={{ width: spacerWidth }}
      />

      {isDrawerMode && !mobileOpen ? (
        <button
          type="button"
          onClick={openMobile}
          className="spa-sidebar-mobile-open fixed left-3 top-3 z-[1001] flex h-11 w-11 items-center justify-center rounded-xl bg-teal-800 text-white shadow-lg shadow-teal-900/30"
          aria-label="Open menu"
        >
          <span className="flex h-5 w-5 flex-col justify-between" aria-hidden>
            <span className="block h-0.5 rounded bg-white" />
            <span className="block h-0.5 rounded bg-white" />
            <span className="block h-0.5 rounded bg-white" />
          </span>
        </button>
      ) : null}

      {isDrawerMode && mobileOpen ? (
        <button
          type="button"
          className="spa-sidebar-overlay fixed inset-0 z-[999] bg-slate-900/45"
          aria-label="Close menu"
          onClick={closeMobile}
        />
      ) : null}

      <aside
        className={[
          'sidebar spa-sidebar fixed left-0 top-0 z-[1000] flex h-dvh max-h-dvh flex-col overflow-hidden text-white shadow-lg transition-transform duration-300 ease-in-out',
          isDrawerMode
            ? mobileOpen
              ? 'translate-x-0'
              : '-translate-x-full pointer-events-none'
            : 'translate-x-0',
          !isDrawerMode ? 'transition-[width]' : '',
        ].join(' ')}
        style={{ width }}
        aria-hidden={isDrawerMode && !mobileOpen}
      >
        <div className="sidebar-heading spa-sidebar-heading shrink-0 text-white">
          <div className={`px-4 py-4 text-center ${railCollapsed ? 'px-2' : ''}`}>
            {!railCollapsed ? (
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

          <SidebarSchoolClock timezone={schoolTimezone} collapsed={railCollapsed} />

          <SidebarToggle
            collapsed={railCollapsed}
            isDrawerMode={isDrawerMode}
            onToggle={isDrawerMode ? toggleMobile : toggle}
          />
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
              collapsed={railCollapsed}
              onNavigate={handleNavigate}
              isReactActive={Boolean(
                item.reactTo &&
                  (item.reactTo === '/teacher' ||
                  item.reactTo === '/student' ||
                  item.reactTo === '/tech'
                    ? location.pathname === item.reactTo || location.pathname === `${item.reactTo}/`
                    : location.pathname === item.reactTo ||
                      location.pathname.startsWith(`${item.reactTo}/`)),
              )}
            />
          ))}
        </nav>

        <div className={`spa-sidebar-footer shrink-0 ${railCollapsed ? 'p-2' : 'p-3'}`}>
          {user.tech_entry && user.management_entry ? (
            <a
              href="/switch-staff-dashboard"
              title={railCollapsed ? 'Switch dashboard' : undefined}
              onClick={handleNavigate}
              className={[
                'mb-2 flex items-center justify-center gap-2 rounded-xl border border-white/25 bg-white/10 font-semibold text-white transition hover:bg-white/20',
                railCollapsed ? 'px-2 py-2.5 text-base' : 'w-full px-3 py-2.5 text-sm',
              ].join(' ')}
            >
              <i className="bi bi-arrow-left-right" aria-hidden />
              {!railCollapsed ? <span>Switch dashboard</span> : null}
            </a>
          ) : null}
          <a
            href="/logout"
            title={railCollapsed ? 'Logout' : undefined}
            onClick={handleNavigate}
            className={[
              'spa-sidebar-logout flex items-center justify-center gap-2 rounded-xl font-semibold text-white transition',
              railCollapsed ? 'px-2 py-2.5 text-base' : 'w-full px-3 py-2.5 text-sm',
            ].join(' ')}
          >
            <i className="bi bi-box-arrow-right" aria-hidden />
            {!railCollapsed ? <span>Logout</span> : null}
          </a>
        </div>
      </aside>
    </>
  )
}
