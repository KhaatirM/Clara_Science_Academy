import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { TeacherClassItem } from '../../types/teacherClasses'
import { spaRoute } from '../../utils/spaRoute'

const META_ICONS: Record<string, string> = {
  teacher: 'bg-pink-100 text-pink-700',
  subject: 'bg-blue-100 text-blue-700',
  students: 'bg-emerald-100 text-emerald-700',
  schedule: 'bg-amber-100 text-amber-700',
}

function MetaItem({
  kind,
  icon,
  label,
  children,
}: {
  kind: keyof typeof META_ICONS
  icon: string
  label: string
  children: ReactNode
}) {
  return (
    <div className="teacher-class-card__meta-item">
      <span className={`teacher-class-card__meta-icon ${META_ICONS[kind]}`}>
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div className="min-w-0">
        <div className="teacher-class-card__meta-label">{label}</div>
        <div className="teacher-class-card__meta-value">{children}</div>
      </div>
    </div>
  )
}

function SpaLink({
  href,
  className,
  children,
}: {
  href: string
  className: string
  children: ReactNode
}) {
  if (!href || href === 'spa') return null
  if (href.startsWith('http')) {
    return (
      <a href={href} className={className} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    )
  }
  return (
    <Link to={spaRoute(href)} className={className}>
      {children}
    </Link>
  )
}

export function TeacherClassCard({
  item,
  onLinkGoogle,
  onCreateGoogle,
  onUnlinkGoogle,
  googleBusy,
}: {
  item: TeacherClassItem
  onLinkGoogle: (classId: number, className: string) => void
  onCreateGoogle: (classId: number) => void
  onUnlinkGoogle: (classId: number) => void
  googleBusy?: boolean
}) {
  const gradeLabel = item.grade_levels_display || 'N/A'
  const busy = Boolean(googleBusy)

  return (
    <article className="teacher-class-card">
      <div className="teacher-class-card__header">
        <h3 className="teacher-class-card__title">{item.name}</h3>
        <span className="teacher-class-card__grade">{gradeLabel}</span>
      </div>

      <div className="teacher-class-card__body">
        <div className="teacher-class-card__meta">
          <MetaItem kind="teacher" icon="bi-person-fill" label="Teacher">
            {item.teacher_display}
          </MetaItem>
          <MetaItem kind="subject" icon="bi-book-fill" label="Subject">
            {item.subject}
          </MetaItem>
          <MetaItem kind="students" icon="bi-people-fill" label="Students">
            {item.enrollment_count} {item.enrollment_count === 1 ? 'Student' : 'Students'}
          </MetaItem>
          <MetaItem kind="schedule" icon="bi-clock-fill" label="Schedule">
            {item.schedule || 'N/A'}
          </MetaItem>
        </div>

        {item.show_google_integration ? (
          <>
            {item.google_group_email ? (
              <a className="teacher-class-card__mail" href={`mailto:${item.google_group_email}`}>
                {item.google_group_email}
              </a>
            ) : null}
            <div
              className={`teacher-class-card__google${
                item.google_classroom_linked ? ' teacher-class-card__google--linked' : ''
              }`}
            >
              <span className="teacher-class-card__google-label">
                <i className="bi bi-google" aria-hidden />
                Classroom
              </span>
              {item.google_classroom_linked ? (
                <span className="teacher-class-card__badge teacher-class-card__badge--ok">
                  <i className="bi bi-check-circle-fill" aria-hidden />
                  Linked
                </span>
              ) : (
                <span className="teacher-class-card__badge teacher-class-card__badge--warn">
                  <i className="bi bi-exclamation-circle-fill" aria-hidden />
                  Not linked
                </span>
              )}
            </div>
          </>
        ) : null}

        <div className="teacher-class-card__actions">
          <Link
            to={`/teacher/classes/${item.id}`}
            className="teacher-class-card__btn teacher-class-card__btn--view"
          >
            <i className="bi bi-eye-fill" aria-hidden />
            View Class
          </Link>
          <SpaLink href={item.links.attendance} className="teacher-class-card__btn teacher-class-card__btn--attendance">
            <i className="bi bi-calendar-check" aria-hidden />
            Attendance
          </SpaLink>
          <SpaLink href={item.links.assignment} className="teacher-class-card__btn teacher-class-card__btn--assignment">
            <i className="bi bi-plus-circle-fill" aria-hidden />
            Assignment
          </SpaLink>
        </div>

        {item.features.grade1_standards && item.links.grade1_standards ? (
          <div className="teacher-class-card__actions teacher-class-card__actions--pair">
            <SpaLink
              href={item.links.grade1_standards}
              className="teacher-class-card__btn teacher-class-card__btn--standards"
            >
              <i className="bi bi-check2-square" aria-hidden />
              1st Grade Standards
            </SpaLink>
          </div>
        ) : null}
        {item.features.grade3_standards && item.links.grade3_standards ? (
          <div className="teacher-class-card__actions teacher-class-card__actions--pair">
            <SpaLink
              href={item.links.grade3_standards}
              className="teacher-class-card__btn teacher-class-card__btn--standards"
            >
              <i className="bi bi-check2-square" aria-hidden />
              3rd Grade Standards
            </SpaLink>
          </div>
        ) : null}

        {item.show_google_integration ? (
          <div className="teacher-class-card__actions teacher-class-card__actions--pair">
            {item.google_classroom_linked && item.links.open_google ? (
              <>
                <a
                  href={item.links.open_google}
                  className="teacher-class-card__btn teacher-class-card__btn--google-open"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <i className="bi bi-google" aria-hidden />
                  Open
                </a>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onUnlinkGoogle(item.id)}
                  className="teacher-class-card__btn teacher-class-card__btn--google-unlink"
                >
                  <i className="bi bi-link-45deg" aria-hidden />
                  Unlink
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onLinkGoogle(item.id, item.name)}
                  className="teacher-class-card__btn teacher-class-card__btn--google-link"
                >
                  <i className="bi bi-link-45deg" aria-hidden />
                  Link Existing
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onCreateGoogle(item.id)}
                  className="teacher-class-card__btn teacher-class-card__btn--google-create"
                >
                  <i className="bi bi-plus-circle-fill" aria-hidden />
                  Create New
                </button>
              </>
            )}
          </div>
        ) : null}
      </div>
    </article>
  )
}
