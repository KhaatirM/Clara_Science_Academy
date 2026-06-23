import { Link } from 'react-router-dom'
import type { StaffListItem } from '../../types/staff'

interface StaffCardProps {
  staff: StaffListItem
  roleBadgeClass: (bootstrapClass: string) => string
  statusClasses: (tone: StaffListItem['status_tone']) => string
  onView: (id: number) => void
  onRemove: (staff: StaffListItem) => void
}

export function StaffCard({
  staff,
  roleBadgeClass,
  statusClasses,
  onView,
  onRemove,
}: StaffCardProps) {
  const departments = staff.department
    ? staff.department.split(',').map((d) => d.trim()).filter(Boolean)
    : []

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-md transition hover:-translate-y-1 hover:shadow-lg">
      <div className="flex items-center gap-4 bg-gradient-to-br from-emerald-400 to-cyan-300 px-5 py-5">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white text-xl text-emerald-500">
          {staff.image_url ? (
            <img src={staff.image_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <i className="bi bi-person-fill" aria-hidden />
          )}
        </div>
        <div className="min-w-0">
          <h3 className="truncate text-lg font-bold text-white">{staff.display_name}</h3>
          <p className="text-sm text-white/90">ID: {staff.staff_id || 'N/A'}</p>
        </div>
      </div>

      <div className="space-y-3 p-5 text-sm text-hub-text">
        <div className="flex flex-wrap items-center gap-1">
          <i className="bi bi-person-badge text-hub-muted" aria-hidden />
          <span className="text-hub-muted">Role:</span>
          {staff.role_badges.map((b) => (
            <span
              key={b.label}
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${roleBadgeClass(b.class)}`}
            >
              {b.label}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <i className="bi bi-building text-hub-muted" aria-hidden />
          <span className="text-hub-muted">Dept:</span>
          {departments.length ? (
            departments.slice(0, 2).map((d) => (
              <span key={d} className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">
                {d}
              </span>
            ))
          ) : (
            <span>N/A</span>
          )}
        </div>
        <div className="flex items-center gap-2 truncate">
          <i className="bi bi-envelope shrink-0 text-hub-muted" aria-hidden />
          <span className="truncate">{staff.email || 'N/A'}</span>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <i className="bi bi-calendar-check text-hub-muted" aria-hidden />
          <span className="text-hub-muted">Type:</span>
          {staff.employment_type ? (
            <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
              {staff.employment_type}
            </span>
          ) : (
            <span>N/A</span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <i className="bi bi-shield-check text-hub-muted" aria-hidden />
          <span className="text-hub-muted">Status:</span>
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusClasses(staff.status_tone)}`}>
            {staff.status_display}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-slate-100 px-5 py-4">
        <button
          type="button"
          onClick={() => onView(staff.id)}
          className="inline-flex items-center gap-1 rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
        >
          <i className="bi bi-eye" aria-hidden />
          View
        </button>
        <Link
          to={`/management/teachers/${staff.id}/edit`}
          className="inline-flex items-center gap-1 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-300 px-3 py-1.5 text-xs font-semibold text-white"
        >
          <i className="bi bi-pencil" aria-hidden />
          Edit
        </Link>
        <button
          type="button"
          onClick={() => onRemove(staff)}
          className="inline-flex items-center gap-1 rounded-lg bg-gradient-to-br from-pink-400 to-rose-500 px-3 py-1.5 text-xs font-semibold text-white"
        >
          <i className="bi bi-trash" aria-hidden />
          Remove
        </button>
      </div>
    </article>
  )
}
