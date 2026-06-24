import { Link } from 'react-router-dom'

export type ClassWorkflowPage = 'view' | 'roster' | 'grades' | 'edit'

export function ClassWorkflowNav({
  classId,
  active,
  isDirector,
  canAdminUi,
}: {
  classId: number
  active: ClassWorkflowPage
  isDirector: boolean
  canAdminUi: boolean
}) {
  const ghost =
    'inline-flex items-center gap-1.5 rounded-full border border-slate-300/80 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 shadow-sm hover:border-teal-500 hover:text-teal-800'

  return (
    <>
      {isDirector ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2.5 py-1 text-xs font-bold text-violet-900">
          <i className="bi bi-award-fill" aria-hidden />
          Director
        </span>
      ) : canAdminUi ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-1 text-xs font-bold text-teal-900">
          <i className="bi bi-shield-fill" aria-hidden />
          Administrator
        </span>
      ) : null}
      {active !== 'roster' ? (
        <Link to={`/management/classes/${classId}/roster`} className={ghost}>
          <i className="bi bi-people" aria-hidden />
          Roster
        </Link>
      ) : null}
      {active !== 'grades' ? (
        <Link to={`/management/classes/${classId}/grades`} className={ghost}>
          <i className="bi bi-graph-up" aria-hidden />
          Grades
        </Link>
      ) : null}
      {canAdminUi && active !== 'edit' ? (
        <Link to={`/management/classes/${classId}/edit`} className={ghost}>
          <i className="bi bi-pencil" aria-hidden />
          Edit
        </Link>
      ) : null}
      {active !== 'view' ? (
        <Link to={`/management/classes/${classId}`} className={ghost}>
          <i className="bi bi-building" aria-hidden />
          Class view
        </Link>
      ) : null}
      <Link
        to="/management/classes"
        className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br from-rose-800 to-teal-900 px-3.5 py-2 text-[0.82rem] font-semibold text-white shadow-sm hover:brightness-105"
      >
        <i className="bi bi-grid" aria-hidden />
        All classes
      </Link>
    </>
  )
}
