import { Link } from 'react-router-dom'
import { googleClassroomAction, removeClass } from '../../api/classes'
import type { ClassListItem } from '../../types/classes'

interface ClassCardProps {
  item: ClassListItem
  canAdminUi: boolean
  canCreate: boolean
  accentClass?: string
  onLinkGoogle: (classId: number, className: string) => void
  onChanged: () => void
}

export function ClassCard({
  item,
  canAdminUi,
  canCreate,
  accentClass = 'teal',
  onLinkGoogle,
  onChanged,
}: ClassCardProps) {
  const accent =
    accentClass === 'violet'
      ? {
          header: 'from-violet-100/80 to-violet-50/50 border-violet-100',
          icon: 'bg-violet-100 text-violet-800',
          detail: 'border-violet-500 text-violet-600',
          action: 'border-violet-300 text-violet-800 hover:border-violet-500 hover:bg-violet-50',
        }
      : {
          header: 'from-teal-100/80 to-teal-50/50 border-teal-100',
          icon: 'bg-teal-100 text-teal-800',
          detail: 'border-teal-500 text-teal-600',
          action: 'border-teal-300 text-teal-800 hover:border-teal-500 hover:bg-teal-50',
        }

  const runGoogle = async (action: 'create' | 'unlink') => {
    if (action === 'unlink' && !window.confirm('Unlink this class from Google Classroom?')) return
    try {
      const res = await googleClassroomAction(item.id, action)
      if (!res.success) {
        if (res.settings_url) {
          window.alert(`${res.message}\n\nOpen Settings to connect your Google account.`)
          window.location.href = res.settings_url
          return
        }
        throw new Error(res.message)
      }
      window.alert(res.message)
      onChanged()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Google Classroom action failed')
    }
  }

  const onRemove = async () => {
    if (!window.confirm(`Remove "${item.name}"? This cannot be undone.`)) return
    try {
      const res = await removeClass(item.id)
      window.alert(res.message)
      onChanged()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Could not remove class')
    }
  }

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md">
      <div className={`border-b px-5 py-4 bg-gradient-to-r ${accent.header}`}>
        <div className="flex items-start gap-3">
          <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-lg ${accent.icon}`}>
            <i className="bi bi-book-fill" aria-hidden />
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-base font-bold text-hub-text">{item.name}</h3>
            <p className="text-sm text-hub-muted">{item.subject}</p>
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4 text-sm">
        <div className={`flex items-center gap-2 rounded-lg border border-slate-200 border-l-[3px] bg-slate-50 px-3 py-2 ${accent.detail}`}>
          <i className="bi bi-mortarboard shrink-0" aria-hidden />
          <span className="text-hub-muted">
            Grade: <strong className="text-hub-text">{item.grade_levels_display}</strong>
          </span>
        </div>
        <div className={`flex items-center gap-2 rounded-lg border border-slate-200 border-l-[3px] bg-slate-50 px-3 py-2 ${accent.detail}`}>
          <i className="bi bi-person-badge shrink-0" aria-hidden />
          <span className="text-hub-muted">
            Teacher: <strong className="text-hub-text">{item.teacher.display_name}</strong>
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${accent.icon}`}>
              <i className="bi bi-people-fill text-sm" aria-hidden />
            </span>
            <div>
              <div className="text-lg font-extrabold leading-tight text-hub-text">{item.enrollment_count}</div>
              <div className="text-[0.65rem] font-semibold uppercase tracking-wide text-hub-muted">Students</div>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${accent.icon}`}>
              <i className="bi bi-journal-check text-sm" aria-hidden />
            </span>
            <div>
              <div className="text-lg font-extrabold leading-tight text-hub-text">{item.assignment_count}</div>
              <div className="text-[0.65rem] font-semibold uppercase tracking-wide text-hub-muted">Assignments</div>
            </div>
          </div>
        </div>
        {item.room_number ? (
          <div className={`flex items-center gap-2 rounded-lg border border-slate-200 border-l-[3px] bg-slate-50 px-3 py-2 ${accent.detail}`}>
            <i className="bi bi-door-open shrink-0" aria-hidden />
            <span className="text-hub-muted">
              Room: <strong className="text-hub-text">{item.room_number}</strong>
            </span>
          </div>
        ) : null}
        {item.schedule ? (
          <div className={`flex items-center gap-2 rounded-lg border border-slate-200 border-l-[3px] bg-slate-50 px-3 py-2 ${accent.detail}`}>
            <i className="bi bi-clock shrink-0" aria-hidden />
            <strong className="text-hub-text">{item.schedule}</strong>
          </div>
        ) : null}
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <i className="bi bi-google me-1 text-hub-muted" aria-hidden />
          {item.google_classroom_linked ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
              <i className="bi bi-check-circle-fill" aria-hidden />
              Google Classroom linked
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
              <i className="bi bi-exclamation-circle-fill" aria-hidden />
              Not linked
            </span>
          )}
        </div>
      </div>

      <div className="mt-auto border-t border-slate-200 bg-slate-50 px-4 py-3">
        <div className="grid grid-cols-2 gap-2">
          <Link
            to={`/management/classes/${item.id}`}
            className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
          >
            <i className="bi bi-eye" aria-hidden />
            View
          </Link>
          {canAdminUi ? (
            <Link
              to={`/management/classes/${item.id}/edit`}
              className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
            >
              <i className="bi bi-pencil" aria-hidden />
              Edit
            </Link>
          ) : null}
          <Link
            to={`/management/classes/${item.id}/roster`}
            className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
          >
            <i className="bi bi-people" aria-hidden />
            Roster
          </Link>
          <Link
            to={`/management/classes/${item.id}/grades`}
            className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
          >
            <i className="bi bi-clipboard-data" aria-hidden />
            Grades
          </Link>
          {canAdminUi && item.google_classroom_linked && item.google_classroom_id ? (
            <>
              <a
                href={`https://classroom.google.com/c/${item.google_classroom_id}`}
                target="_blank"
                rel="noreferrer"
                className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
              >
                <i className="bi bi-google" aria-hidden />
                Open
              </a>
              <button
                type="button"
                onClick={() => void runGoogle('unlink')}
                className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
              >
                <i className="bi bi-link-45deg" aria-hidden />
                Unlink
              </button>
            </>
          ) : canAdminUi ? (
            <>
              <button
                type="button"
                onClick={() => onLinkGoogle(item.id, item.name)}
                className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
              >
                <i className="bi bi-link-45deg" aria-hidden />
                Link
              </button>
              <button
                type="button"
                onClick={() => void runGoogle('create')}
                className={`inline-flex items-center justify-center gap-1 rounded-full border bg-white px-2 py-2 text-xs font-semibold ${accent.action}`}
              >
                <i className="bi bi-plus-circle-fill" aria-hidden />
                Create
              </button>
            </>
          ) : null}
          {canCreate ? (
            <button
              type="button"
              onClick={() => void onRemove()}
              className="col-span-2 inline-flex items-center justify-center gap-1 rounded-full border border-red-300 bg-red-50 px-2 py-2 text-xs font-semibold text-red-800 hover:bg-red-100"
            >
              <i className="bi bi-trash" aria-hidden />
              Remove class
            </button>
          ) : null}
        </div>
      </div>
    </article>
  )
}
