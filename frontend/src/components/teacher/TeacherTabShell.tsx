import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ManagementPageShell } from '../layout/ManagementPageShell'
import type { TeacherTabStat } from '../../types/teacherTabs'

type TeacherTabShellProps = {
  eyebrow: string
  title: string
  subtitle: ReactNode
  stats: TeacherTabStat[]
  loading?: boolean
  error?: string | null
  children?: ReactNode
}

const STAT_TONE_CLASS: Record<NonNullable<TeacherTabStat['tone']>, string> = {
  classes: 'mgmt-home-stat--classes',
  students: 'mgmt-home-stat--students',
  assignments: 'mgmt-home-stat--assignments',
  notifications: 'mgmt-home-stat--notifications',
}

export function TeacherTabShell({
  eyebrow,
  title,
  subtitle,
  stats,
  loading,
  error,
  children,
}: TeacherTabShellProps) {
  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          <header className="mgmt-home-hero">
            <div>
              <p className="mgmt-home-eyebrow">{eyebrow}</p>
              <h1 className="mgmt-home-title">{title}</h1>
              <p className="mgmt-home-date">{subtitle}</p>
            </div>
            <div className="mgmt-home-hero-actions">
              <span className="mgmt-home-role-badge mgmt-home-role-badge--admin">
                <i className="bi bi-mortarboard-fill me-1" aria-hidden />
                Teacher
              </span>
              <Link to="/teacher" className="mgmt-home-switch-link">
                <i className="bi bi-grid me-1" aria-hidden />
                Home
              </Link>
            </div>
          </header>

          {loading ? (
            <div className="p-5 text-center text-muted">Loading…</div>
          ) : error ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : (
            <>
              <div className="mgmt-home-stats">
                {stats.map((stat) => (
                  <article
                    key={stat.label}
                    className={`mgmt-home-stat ${STAT_TONE_CLASS[stat.tone || 'classes']}`}
                  >
                    <div className="mgmt-home-stat-icon">
                      <i className={`bi ${stat.icon}`} aria-hidden />
                    </div>
                    <p className="mgmt-home-stat-number">{stat.value}</p>
                    <p className="mgmt-home-stat-label">{stat.label}</p>
                  </article>
                ))}
              </div>
              {children}
            </>
          )}
        </div>
      </div>
    </ManagementPageShell>
  )
}
