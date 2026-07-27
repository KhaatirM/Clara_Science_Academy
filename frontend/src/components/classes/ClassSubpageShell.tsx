import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

const SUBJECTS = [
  'Mathematics',
  'Science',
  'English',
  'History',
  'Art',
  'Physical Education',
  'Other',
]

export function ClassSubpageShell({
  eyebrow,
  title,
  subtitle,
  children,
  actions,
}: {
  eyebrow: string
  title: string
  subtitle?: string
  children: ReactNode
  actions?: React.ReactNode
}) {
  return (
    <div className="rounded-3xl bg-gradient-to-br from-emerald-50 via-teal-50/70 to-slate-100 p-5 md:p-8">
      <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">{eyebrow}</p>
          <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-hub-text">{title}</h1>
          {subtitle ? <p className="mt-2 text-sm text-hub-muted">{subtitle}</p> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {actions}
          <Link
            to="/management/classes"
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
          >
            <i className="bi bi-grid" aria-hidden />
            All classes
          </Link>
        </div>
      </header>
      {children}
    </div>
  )
}

export { SUBJECTS }
