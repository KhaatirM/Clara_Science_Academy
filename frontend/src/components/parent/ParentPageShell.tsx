import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import { ManagementPageShell } from '../layout/ManagementPageShell'
import { ParentChildPicker } from './ParentChildPicker'
import type { ParentChildBrief } from '../../types/parentPortal'

export function ParentPageShell({
  title,
  subtitle,
  childrenList,
  activeChildId,
  onSelectChild,
  childBusy,
  actions,
  children,
}: {
  title: string
  subtitle?: string
  childrenList: ParentChildBrief[]
  activeChildId: number | null
  onSelectChild?: (studentId: number) => void
  childBusy?: boolean
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <header className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-hub-muted">
                Family portal
              </p>
              <h1 className="mb-0 text-2xl font-bold text-slate-900 md:text-3xl">{title}</h1>
              {subtitle ? <p className="mb-0 mt-1 text-sm text-hub-muted">{subtitle}</p> : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {onSelectChild ? (
                <ParentChildPicker
                  children={childrenList}
                  activeChildId={activeChildId}
                  busy={childBusy}
                  onSelect={onSelectChild}
                />
              ) : null}
              {actions}
            </div>
          </header>
          {children}
        </div>
      </div>
    </ManagementPageShell>
  )
}

export function ParentEmptyChildren() {
  return (
    <section className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center shadow-sm">
      <i className="bi bi-people mb-3 block text-3xl text-slate-400" aria-hidden />
      <p className="mb-1 text-base font-semibold text-slate-800">No linked children yet</p>
      <p className="mb-0 text-sm text-hub-muted">
        Ask the school office to link your account to your student&apos;s record.
      </p>
    </section>
  )
}

export function ParentQuickLinks() {
  const links = [
    { to: '/parent/grades', icon: 'bi-card-checklist', label: 'Grades' },
    { to: '/parent/attendance', icon: 'bi-clipboard-check', label: 'Attendance' },
    { to: '/parent/classes', icon: 'bi-journal-bookmark', label: 'Classes' },
    { to: '/parent/report-cards', icon: 'bi-file-earmark-pdf', label: 'Report cards' },
  ]
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {links.map((link) => (
        <Link
          key={link.to}
          to={link.to}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-teal-300 bg-white px-3 py-2.5 text-sm font-semibold text-teal-800 hover:border-teal-500 hover:bg-teal-50"
        >
          <i className={`bi ${link.icon}`} aria-hidden />
          {link.label}
        </Link>
      ))}
    </div>
  )
}
