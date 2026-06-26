import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { fetchDashboardHome } from '../api/dashboard'
import { LegacyMgmtScope } from '../components/legacy/LegacyMgmtScope'
import {
  homeActionsForGroup,
  type HomeActionGroup,
  type HomeQuickAction,
} from '../config/homeQuickActions'
import type { ManagementOutletContext } from '../types/layout'
import type { DashboardHomeResponse } from '../types/dashboard'

function formatFeedTime(value: string | null | undefined) {
  if (!value) return 'Recently'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return 'Recently'
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function notificationIconClass(type: string) {
  switch (type) {
    case 'grade':
      return 'mgmt-home-feed-icon--grade'
    case 'assignment':
      return 'mgmt-home-feed-icon--assignment'
    case 'attendance':
      return 'mgmt-home-feed-icon--attendance'
    case 'submission':
      return 'mgmt-home-feed-icon--submission'
    case 'extension_request':
      return 'mgmt-home-feed-icon--extension'
    case 'alert':
    case 'warning':
      return 'mgmt-home-feed-icon--alert'
    default:
      return ''
  }
}

function notificationIcon(type: string) {
  switch (type) {
    case 'grade':
      return 'bi-clipboard-check-fill'
    case 'assignment':
      return 'bi-journal-plus-fill'
    case 'attendance':
      return 'bi-calendar-check-fill'
    case 'submission':
      return 'bi-file-earmark-check-fill'
    case 'extension_request':
      return 'bi-clock-history'
    case 'alert':
    case 'warning':
      return 'bi-exclamation-triangle-fill'
    default:
      return 'bi-bell-fill'
  }
}

function activityIcon(type: string) {
  switch (type) {
    case 'grade':
      return 'bi-clipboard-check text-success'
    case 'assignment':
      return 'bi-journal-plus text-primary'
    case 'submission':
      return 'bi-file-earmark-check text-warning'
    case 'extension_request':
      return 'bi-clock-history text-info'
    default:
      return 'bi-circle-fill text-secondary'
  }
}

export function HomePage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const isDirector = user.role_canonical === 'Director'
  const [data, setData] = useState<DashboardHomeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchDashboardHome()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <LegacyMgmtScope>
      <div className="mgmt-home container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading ? (
            <div className="p-5 text-center text-muted">Loading dashboard…</div>
          ) : error || !data ? (
            <div className="alert alert-danger m-3">{error || 'Could not load dashboard'}</div>
          ) : (
            <HomeDashboardBody data={data} user={user} isDirector={isDirector} />
          )}
        </div>
      </div>
    </LegacyMgmtScope>
  )
}

function HomeDashboardBody({
  data,
  user,
  isDirector,
}: {
  data: DashboardHomeResponse
  user: ManagementOutletContext['user']
  isDirector: boolean
}) {
  const ms = data.monthly_stats
  const ws = data.weekly_stats
  const st = data.stats
  const pendingExt = data.pending_extension_count
  const atRisk = data.at_risk_count

  return (
    <>
      <header className="mgmt-home-hero">
        <div>
          <p className="mgmt-home-eyebrow">School management</p>
          <h1 className="mgmt-home-title">Welcome back, {data.profile.display_name}</h1>
          <p className="mgmt-home-date">
            <i className="bi bi-calendar3" aria-hidden="true" />
            {data.home_display_date}
          </p>
        </div>
        <div className="mgmt-home-hero-actions">
          {isDirector ? (
            <span className="mgmt-home-role-badge mgmt-home-role-badge--director">
              <i className="bi bi-award-fill" aria-hidden="true" /> Director
            </span>
          ) : (
            <span className="mgmt-home-role-badge mgmt-home-role-badge--admin">
              <i className="bi bi-shield-fill" aria-hidden="true" /> Administrator
            </span>
          )}
          {data.dual_dashboard_staff ? (
            <a href="/switch-staff-dashboard" className="mgmt-home-switch-link">
              <i className="bi bi-arrow-left-right" aria-hidden="true" /> Switch dashboard
            </a>
          ) : null}
        </div>
      </header>

      {!data.has_active_school_year ? (
        <div className="school-year-closed-banner" role="status">
          <span className="school-year-closed-banner__icon" aria-hidden="true">
            <i className="bi bi-calendar-x" />
          </span>
          <div>
            <p className="school-year-closed-banner__title">School year closed</p>
            <p className="school-year-closed-banner__text mb-0">
              There is no active school year. Live statistics and coursework summaries are hidden
              until a new year is started.
            </p>
            {data.latest_school_year_label ? (
              <p className="school-year-closed-banner__meta mb-0">
                Most recent year: {data.latest_school_year_label}
              </p>
            ) : null}
          </div>
        </div>
      ) : (
        <>
          <div className="mgmt-home-insights" role="list">
            <InsightChip icon="bi-calendar-week" value={ws.due_assignments} label="Due this week" />
            <InsightChip icon="bi-check2-circle" value={`${ms.attendance_rate}%`} label="Attendance rate" />
            <InsightChip icon="bi-graph-up" value={`${ms.average_grade}%`} label="Avg. grade score" />
            <InsightChip icon="bi-person-plus" value={ms.new_students} label="New enrollments" />
            {pendingExt > 0 ? (
              <Link
                to="/management/extensions"
                className="mgmt-home-insight mgmt-home-insight--alert text-decoration-none"
                role="listitem"
              >
                <span className="mgmt-home-insight-icon">
                  <i className="bi bi-clock-history" aria-hidden="true" />
                </span>
                <div>
                  <div className="mgmt-home-insight-value">{pendingExt}</div>
                  <div className="mgmt-home-insight-label">Pending extensions</div>
                </div>
              </Link>
            ) : (
              <InsightChip icon="bi-clock-history" value={0} label="Pending extensions" />
            )}
            {atRisk > 0 ? (
              <Link
                to="/management/assignments"
                className="mgmt-home-insight mgmt-home-insight--alert text-decoration-none"
                role="listitem"
              >
                <span className="mgmt-home-insight-icon">
                  <i className="bi bi-exclamation-triangle" aria-hidden="true" />
                </span>
                <div>
                  <div className="mgmt-home-insight-value">{atRisk}</div>
                  <div className="mgmt-home-insight-label">Academic concerns</div>
                </div>
              </Link>
            ) : (
              <InsightChip icon="bi-shield-check" value={0} label="Academic concerns" />
            )}
          </div>

          <div className="mgmt-home-stats">
            <article className="mgmt-home-stat mgmt-home-stat--students">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-people-fill" aria-hidden="true" />
              </div>
              <p className="mgmt-home-stat-number">{st.students}</p>
              <p className="mgmt-home-stat-label">Students</p>
              <p className="mgmt-home-stat-meta">Enrolled in the system</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--staff">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-person-badge-fill" aria-hidden="true" />
              </div>
              <p className="mgmt-home-stat-number">{st.teachers}</p>
              <p className="mgmt-home-stat-label">Teachers &amp; staff</p>
              <p className="mgmt-home-stat-meta">Active staff records</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--classes">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-mortarboard-fill" aria-hidden="true" />
              </div>
              <p className="mgmt-home-stat-number">{st.classes}</p>
              <p className="mgmt-home-stat-label">Classes</p>
              <p className="mgmt-home-stat-meta">Across all grade levels</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--assignments">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-journal-check" aria-hidden="true" />
              </div>
              <p className="mgmt-home-stat-number">{st.active_assignments}</p>
              <p className="mgmt-home-stat-label">Active assignments</p>
              <p className="mgmt-home-stat-meta">{st.assignments} total in system</p>
            </article>
          </div>
        </>
      )}

      <div className="mgmt-home-main-grid">
        <aside className="mgmt-home-profile">
          <div className="mgmt-home-profile-top">
            <div
              className={`mgmt-home-avatar ${isDirector ? 'mgmt-home-avatar--director' : 'mgmt-home-avatar--admin'}`}
              aria-hidden="true"
            >
              <i className={`bi ${isDirector ? 'bi-award-fill' : 'bi-person-badge-fill'}`} />
            </div>
            <div>
              <h2 className="mgmt-home-profile-name">{data.profile.display_name}</h2>
              <p className="mgmt-home-profile-role">{data.profile.role}</p>
            </div>
          </div>
          <div className="mgmt-home-profile-detail">
            <i className="bi bi-person-vcard" aria-hidden="true" />
            <span>ID: {data.profile.staff_id}</span>
          </div>
          <div className="mgmt-home-profile-detail">
            <i className="bi bi-envelope" aria-hidden="true" />
            <span>{data.profile.email || 'None'}</span>
          </div>
          <div className="mgmt-home-profile-detail">
            <i className="bi bi-building" aria-hidden="true" />
            <span>Clara Science Academy — School operations</span>
          </div>
        </aside>

        <section className="mgmt-home-actions-panel" aria-labelledby="mgmtHomeQuickActions">
          <h2 id="mgmtHomeQuickActions" className="mgmt-home-section-title">
            <i className="bi bi-lightning-fill" aria-hidden="true" /> Quick actions
          </h2>
          <div className="mgmt-home-action-groups">
            <ActionGroup user={user} group="people" label="People" pendingExt={pendingExt} />
            <ActionGroup user={user} group="academics" label="Academics" pendingExt={pendingExt} />
            <ActionGroup user={user} group="operations" label="Operations" pendingExt={pendingExt} />
          </div>
        </section>
      </div>

      <div className="mgmt-home-feeds">
        <section className="mgmt-home-feed" aria-labelledby="mgmtHomeNotifications">
          <div className="mgmt-home-feed-header">
            <h2 id="mgmtHomeNotifications" className="mgmt-home-feed-title">
              <i className="bi bi-bell-fill" aria-hidden="true" />
              Notifications
              {data.notifications.length ? (
                <span className="mgmt-home-feed-count">{data.notifications.length}</span>
              ) : null}
            </h2>
            <span className="mgmt-home-feed-meta">Last 7 days</span>
          </div>
          <div className="mgmt-home-feed-list">
            {data.notifications.length === 0 ? (
              <div className="mgmt-home-empty">
                <i className="bi bi-bell-slash" aria-hidden="true" />
                <p>No new notifications</p>
              </div>
            ) : (
              data.notifications.map((n) => (
                <article key={`${n.type}-${n.title}-${n.timestamp}`} className="mgmt-home-feed-item">
                  <div className={`mgmt-home-feed-icon ${notificationIconClass(n.type)}`}>
                    <i className={`bi ${notificationIcon(n.type)}`} aria-hidden="true" />
                  </div>
                  <div className="mgmt-home-feed-body">
                    <h3 className="mgmt-home-feed-item-title">{n.title}</h3>
                    <p className="mgmt-home-feed-item-text">{n.message}</p>
                    <time className="mgmt-home-feed-time">{formatFeedTime(n.timestamp)}</time>
                    {n.link ? (
                      <a href={n.link} className="mgmt-home-feed-link">
                        View details <i className="bi bi-arrow-right-short" aria-hidden="true" />
                      </a>
                    ) : null}
                  </div>
                </article>
              ))
            )}
          </div>
        </section>

        <section className="mgmt-home-feed" aria-labelledby="mgmtHomeActivity">
          <div className="mgmt-home-feed-header">
            <h2 id="mgmtHomeActivity" className="mgmt-home-feed-title">
              <i className="bi bi-activity" aria-hidden="true" />
              Recent activity
            </h2>
            <span className="mgmt-home-feed-meta">Last 7 days</span>
          </div>
          <div className="mgmt-home-feed-list">
            {data.recent_activity.length === 0 ? (
              <div className="mgmt-home-empty">
                <i className="bi bi-inbox" aria-hidden="true" />
                <p>No recent activity</p>
              </div>
            ) : (
              <div className="mgmt-home-timeline">
                {data.recent_activity.map((a) => (
                  <article key={`${a.type}-${a.title}-${a.timestamp}`} className="mgmt-home-timeline-item">
                    <span className="mgmt-home-timeline-dot" aria-hidden="true" />
                    <h3 className="mgmt-home-timeline-item-title">
                      <i className={`bi ${activityIcon(a.type)} me-1`} aria-hidden="true" />
                      {a.title}
                    </h3>
                    <p className="mgmt-home-timeline-item-text">{a.description}</p>
                    <time className="mgmt-home-feed-time">{formatFeedTime(a.timestamp)}</time>
                    {a.link ? (
                      <a href={a.link} className="mgmt-home-feed-link">
                        View <i className="bi bi-arrow-right-short" aria-hidden="true" />
                      </a>
                    ) : null}
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </>
  )
}

function InsightChip({
  icon,
  value,
  label,
}: {
  icon: string
  value: string | number
  label: string
}) {
  return (
    <div className="mgmt-home-insight" role="listitem">
      <span className="mgmt-home-insight-icon">
        <i className={`bi ${icon}`} aria-hidden="true" />
      </span>
      <div>
        <div className="mgmt-home-insight-value">{value}</div>
        <div className="mgmt-home-insight-label">{label}</div>
      </div>
    </div>
  )
}

function ActionGroup({
  user,
  group,
  label,
  pendingExt,
}: {
  user: ManagementOutletContext['user']
  group: HomeActionGroup
  label: string
  pendingExt: number
}) {
  const actions = homeActionsForGroup(user, group)
  if (!actions.length) return null

  return (
    <div>
      <p className="mgmt-home-action-group-label">{label}</p>
      <div className="mgmt-home-action-grid">
        {actions.map((action) => (
          <HomeActionTile
            key={action.id}
            action={action}
            highlight={action.id === 'extensions' && pendingExt > 0}
            badge={action.id === 'extensions' && pendingExt > 0 ? pendingExt : undefined}
          />
        ))}
      </div>
    </div>
  )
}

function HomeActionTile({
  action,
  highlight,
  badge,
}: {
  action: HomeQuickAction
  highlight?: boolean
  badge?: number
}) {
  const className = `mgmt-home-action${highlight ? ' mgmt-home-action--highlight' : ''}`
  const inner = (
    <>
      <i className={`bi ${action.icon}`} aria-hidden="true" />
      <span>{action.label}</span>
    </>
  )

  if (badge) {
    return (
      <span className="mgmt-home-action-wrap">
        {action.reactTo ? (
          <Link to={action.reactTo} className={className}>
            {inner}
          </Link>
        ) : (
          <a href={action.legacyHref} className={className}>
            {inner}
          </a>
        )}
        <span className="mgmt-home-action-badge">{badge}</span>
      </span>
    )
  }

  if (action.reactTo) {
    return (
      <Link to={action.reactTo} className={className}>
        {inner}
      </Link>
    )
  }

  return (
    <a href={action.legacyHref} className={className}>
      {inner}
    </a>
  )
}
