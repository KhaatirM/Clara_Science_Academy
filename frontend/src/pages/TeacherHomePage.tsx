import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { fetchTeacherDashboardHome } from '../api/teacherDashboard'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { ManagementOutletContext } from '../types/layout'
import type { TeacherDashboardFeedItem, TeacherDashboardHomeResponse } from '../types/teacherDashboard'

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

function activityIcon(type: string) {
  switch (type) {
    case 'submission':
      return 'bi-file-earmark-check-fill'
    case 'grade':
      return 'bi-star-fill'
    case 'assignment':
      return 'bi-journal-plus'
    default:
      return 'bi-circle-fill'
  }
}

function activityIconClass(type: string) {
  switch (type) {
    case 'submission':
      return 'mgmt-home-feed-icon--submission'
    case 'grade':
      return 'mgmt-home-feed-icon--grade'
    case 'assignment':
      return 'mgmt-home-feed-icon--assignment'
    default:
      return ''
  }
}

const QUICK_ACTIONS = [
  { to: '/teacher/classes', icon: 'bi-house-door-fill', label: 'My Classes' },
  { to: '/teacher/assignments-and-grades', icon: 'bi-journal-check', label: 'Assignments & Grades' },
  { to: '/teacher/attendance', icon: 'bi-calendar-check-fill', label: 'Attendance' },
  { to: '/teacher/students', icon: 'bi-people-fill', label: 'Students' },
] as const

export function TeacherHomePage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const [data, setData] = useState<TeacherDashboardHomeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchTeacherDashboardHome()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading ? (
            <div className="p-5 text-center text-muted">Loading dashboard…</div>
          ) : error || !data ? (
            <div className="alert alert-danger m-3">{error || 'Could not load dashboard'}</div>
          ) : (
            <TeacherHomeBody data={data} username={user.username} />
          )}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function TeacherHomeBody({
  data,
  username,
}: {
  data: TeacherDashboardHomeResponse
  username: string
}) {
  const st = data.stats
  const ms = data.monthly_stats
  const ws = data.weekly_stats

  return (
    <>
      <header className="mgmt-home-hero">
        <div>
          <p className="mgmt-home-eyebrow">Teacher portal</p>
          <h1 className="mgmt-home-title">Welcome back, {data.profile.display_name || username}</h1>
          <p className="mgmt-home-date">
            <i className="bi bi-calendar3" aria-hidden />
            {data.home_display_date}
          </p>
        </div>
        <div className="mgmt-home-hero-actions">
          <span className="mgmt-home-role-badge mgmt-home-role-badge--admin">
            <i className="bi bi-mortarboard-fill" aria-hidden /> Teacher
          </span>
          {data.is_admin ? (
            <span className="mgmt-home-role-badge mgmt-home-role-badge--director">
              <i className="bi bi-shield-fill" aria-hidden /> Admin view
            </span>
          ) : null}
        </div>
      </header>

      {!data.has_active_school_year ? (
        <div className="school-year-closed-banner" role="status">
          <span className="school-year-closed-banner__icon" aria-hidden>
            <i className="bi bi-calendar-x" />
          </span>
          <div>
            <p className="school-year-closed-banner__title">School year closed</p>
            <p className="school-year-closed-banner__text mb-0">
              There is no active school year. Live statistics are hidden until a new year is started.
            </p>
            {data.latest_school_year_label ? (
              <p className="school-year-closed-banner__meta mb-0">
                Most recent year: {data.latest_school_year_label}
              </p>
            ) : null}
          </div>
        </div>
      ) : (
          <div className="mgmt-home-stats">
            <article className="mgmt-home-stat mgmt-home-stat--classes">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-house-door-fill" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number">{st.classes}</p>
              <p className="mgmt-home-stat-label">My classes</p>
              <p className="mgmt-home-stat-meta">Assigned this year</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--students">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-people-fill" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number">{st.students}</p>
              <p className="mgmt-home-stat-label">Students</p>
              <p className="mgmt-home-stat-meta">Across your classes</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--assignments">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-journal-text" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number">{st.active_assignments}</p>
              <p className="mgmt-home-stat-label">Active assignments</p>
              <p className="mgmt-home-stat-meta">
                {ws.due_assignments} due this week · {ms.grades_entered} graded this month
              </p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--notifications">
              <div className="mgmt-home-stat-icon">
                <i className="bi bi-bell-fill" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number">{st.notifications}</p>
              <p className="mgmt-home-stat-label">Notifications</p>
              <p className="mgmt-home-stat-meta">In your inbox</p>
            </article>
          </div>
      )}

      <div className="mgmt-home-main-grid">
        <aside className="mgmt-home-profile">
          <div className="mgmt-home-profile-top">
            <div className="mgmt-home-avatar mgmt-home-avatar--admin">{data.profile.initials}</div>
            <div>
              <h2 className="mgmt-home-profile-name">{data.profile.display_name}</h2>
              <p className="mgmt-home-profile-role">{data.profile.role}</p>
            </div>
          </div>
          {data.profile.email ? (
            <div className="mgmt-home-profile-detail">
              <i className="bi bi-envelope" aria-hidden />
              <span>{data.profile.email}</span>
            </div>
          ) : null}
          {data.profile.phone ? (
            <div className="mgmt-home-profile-detail">
              <i className="bi bi-telephone" aria-hidden />
              <span>{data.profile.phone}</span>
            </div>
          ) : null}
          <div className="mgmt-home-profile-detail">
            <i className="bi bi-house-door" aria-hidden />
            <span>{data.profile.class_count} assigned classes</span>
          </div>
        </aside>

        <section className="mgmt-home-actions-panel" aria-labelledby="teacherHomeQuickActions">
          <h2 id="teacherHomeQuickActions" className="mgmt-home-section-title">
            <i className="bi bi-lightning-charge-fill" aria-hidden /> Quick actions
          </h2>
          <div className="mgmt-home-action-grid mgmt-home-action-grid--teacher">
            {QUICK_ACTIONS.map((action) => (
              <Link key={action.to} to={action.to} className="mgmt-home-action">
                <i className={`bi ${action.icon}`} aria-hidden />
                <span>{action.label}</span>
              </Link>
            ))}
          </div>
        </section>
      </div>

      <div className="mgmt-home-feeds">
        <FeedSection
          id="teacherHomeNotifications"
          title="Notifications"
          count={data.notifications.length}
          emptyIcon="bi-bell-slash"
          emptyText="No new notifications at this time."
          items={data.notifications}
          mode="notification"
        />
        <FeedSection
          id="teacherHomeActivity"
          title="Recent activity"
          emptyIcon="bi-clock-history"
          emptyText="No recent activity yet. Create assignments or grade student work to see updates here."
          items={data.recent_activity}
          mode="activity"
        />
      </div>
    </>
  )
}

function FeedSection({
  id,
  title,
  count,
  emptyIcon,
  emptyText,
  items,
  mode,
}: {
  id: string
  title: string
  count?: number
  emptyIcon: string
  emptyText: string
  items: TeacherDashboardFeedItem[]
  mode: 'notification' | 'activity'
}) {
  return (
    <section className="mgmt-home-feed" aria-labelledby={id}>
      <div className="mgmt-home-feed-header">
        <h2 id={id} className="mgmt-home-feed-title">
          <i className={`bi ${mode === 'notification' ? 'bi-bell-fill' : 'bi-activity'}`} aria-hidden />{' '}
          {title}
          {count && count > 0 ? <span className="mgmt-home-feed-count">{count}</span> : null}
        </h2>
      </div>
      <div className="mgmt-home-feed-list">
        {items.length === 0 ? (
          <div className="mgmt-home-empty">
            <i className={`bi ${emptyIcon}`} aria-hidden />
            <p>{emptyText}</p>
          </div>
        ) : mode === 'notification' ? (
          items.slice(0, 5).map((n) => (
            <article
              key={`${n.type}-${n.title}-${n.timestamp}`}
              className={`mgmt-home-feed-item${n.is_read ? '' : ' opacity-100'}`}
            >
              <div className={`mgmt-home-feed-icon ${activityIconClass(n.type)}`}>
                <i className="bi bi-bell-fill" aria-hidden />
              </div>
              <div className="mgmt-home-feed-body">
                <h3 className="mgmt-home-feed-item-title">{n.title}</h3>
                <p className="mgmt-home-feed-item-text">{n.message}</p>
                <time className="mgmt-home-feed-time">{formatFeedTime(n.timestamp)}</time>
                {n.link ? (
                  <a href={n.link} className="mgmt-home-feed-link">
                    View
                  </a>
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <div className="mgmt-home-timeline">
            {items.slice(0, 5).map((a) => (
              <article key={`${a.type}-${a.title}-${a.timestamp}`} className="mgmt-home-timeline-item">
                <span className="mgmt-home-timeline-dot" aria-hidden />
                <h3 className="mgmt-home-timeline-item-title">
                  <i className={`bi ${activityIcon(a.type)} me-1`} aria-hidden />
                  {a.title}
                </h3>
                <p className="mgmt-home-timeline-item-text">{a.description}</p>
                <time className="mgmt-home-feed-time">{formatFeedTime(a.timestamp)}</time>
                {a.link ? (
                  <a href={a.link} className="mgmt-home-feed-link">
                    View details
                  </a>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
