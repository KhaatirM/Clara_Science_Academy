import { useNavigate } from 'react-router-dom'
import type { SessionUser } from '../../types/session'
import { canStaffAdminUi } from '../../utils/staffAccess'

export type StaffPageMode = 'manage' | 'roster'

interface StaffPageHeaderProps {
  user: SessionUser
  mode: StaffPageMode
}

export function StaffPageHeader({ user, mode }: StaffPageHeaderProps) {
  const navigate = useNavigate()
  const isDirector = user.role_canonical === 'Director'
  const showAdminUi = canStaffAdminUi(user)
  const showRosterPills = showAdminUi && user.management_entry
  const accent = isDirector
    ? {
        badge: 'bg-gradient-to-br from-violet-100 to-violet-200 text-violet-800 border-violet-200',
        primary: 'from-violet-600 to-violet-800 shadow-violet-500/25',
        pillActive: 'bg-violet-100 text-violet-800',
      }
    : {
        badge: 'bg-gradient-to-br from-teal-100 to-emerald-200 text-teal-900 border-teal-200',
        primary: 'from-teal-600 to-teal-800 shadow-teal-500/25',
        pillActive: 'bg-teal-100 text-teal-900',
      }

  const pillClass = (active: boolean) =>
    [
      'inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[0.82rem] font-semibold transition',
      active ? accent.pillActive : 'text-slate-600 hover:bg-slate-50',
    ].join(' ')

  const goManage = () => {
    navigate('/management/teachers')
  }

  const goRoster = () => {
    navigate('/management/teachers/roster')
  }

  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">
          People operations
        </p>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-hub-text">
          Teachers &amp; staff
        </h1>
        <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-hub-muted">
          {mode === 'roster' ? (
            <>
              <i className="bi bi-archive" aria-hidden />
              Browse payroll roster and inactive records
            </>
          ) : (
            <>
              <i className="bi bi-briefcase" aria-hidden />
              Search, add, and maintain active staff records
            </>
          )}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {isDirector ? (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-[0.82rem] font-bold ${accent.badge}`}
          >
            <i className="bi bi-award-fill" aria-hidden />
            Director
          </span>
        ) : user.management_entry ? (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-[0.82rem] font-bold ${accent.badge}`}
          >
            <i className="bi bi-shield-fill" aria-hidden />
            Administrator
          </span>
        ) : null}

        {showRosterPills ? (
          <div className="inline-flex flex-wrap gap-1 rounded-full border border-slate-200 bg-white p-1">
            <button type="button" onClick={goManage} className={pillClass(mode === 'manage')}>
              <i className="bi bi-sliders" aria-hidden />
              Manage
            </button>
            <button type="button" onClick={goRoster} className={pillClass(mode === 'roster')}>
              <i className="bi bi-people" aria-hidden />
              Roster
            </button>
          </div>
        ) : null}

        {mode === 'manage' ? (
          <button
            type="button"
            onClick={() => navigate('/management/teachers/new')}
            className={`inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br px-3.5 py-2 text-[0.82rem] font-semibold text-white shadow-md ${accent.primary}`}
          >
            <i className="bi bi-plus-circle" aria-hidden />
            Add staff
          </button>
        ) : null}

        <button
          type="button"
          onClick={() => navigate('/management')}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 transition hover:border-teal-600 hover:text-teal-800"
        >
          <i className="bi bi-house-door" aria-hidden />
          Dashboard
        </button>
      </div>
    </header>
  )
}
