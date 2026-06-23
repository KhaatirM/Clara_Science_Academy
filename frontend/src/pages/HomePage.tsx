import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { fetchDashboardHome } from '../api/dashboard'
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

function ActionTile({
  icon,
  label,
  href,
  react,
  highlight,
  badge,
}: {
  icon: string
  label: string
  href: string
  react?: boolean
  highlight?: boolean
  badge?: number
}) {
  const className = [
    'relative flex flex-col items-center justify-center gap-1.5 rounded-[14px] border px-2 py-3.5 text-center text-[0.78rem] font-semibold leading-tight text-slate-700 transition hover:-translate-y-px',
    highlight
      ? 'border-amber-300/60 bg-gradient-to-br from-amber-50 to-amber-100/80 hover:border-amber-400/60'
      : 'border-slate-200 bg-slate-50 hover:border-teal-600/35 hover:bg-teal-50/80 hover:text-teal-800',
  ].join(' ')

  const inner = (
    <>
      <i
        className={`bi ${icon} text-xl ${highlight ? 'text-amber-700' : 'text-teal-700'}`}
        aria-hidden
      />
      <span>{label}</span>
      {badge ? (
        <span className="absolute right-1.5 top-1.5 flex h-[1.1rem] min-w-[1.1rem] items-center justify-center rounded-full bg-red-600 px-1 text-[0.65rem] font-bold text-white">
          {badge}
        </span>
      ) : null}
    </>
  )

  if (react) {
    return (
      <Link to={href} className={className}>
        {inner}
      </Link>
    )
  }
  return (
    <a href={href} className={className}>
      {inner}
    </a>
  )
}

function InsightCard({
  icon,
  value,
  label,
  href,
  alert,
}: {
  icon: string
  value: string | number
  label: string
  href?: string
  alert?: boolean
}) {
  const body = (
    <div
      className={[
        'flex items-start gap-3 rounded-2xl border p-4 shadow-sm',
        alert ? 'border-amber-300 bg-gradient-to-br from-amber-50 to-white' : 'border-white/90 bg-white/95',
      ].join(' ')}
    >
      <span
        className={[
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-base',
          alert ? 'bg-amber-100 text-amber-700' : 'bg-teal-100 text-teal-800',
        ].join(' ')}
      >
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-lg font-extrabold text-hub-text">{value}</div>
        <div className="text-[0.72rem] font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
  if (href) {
    return (
      <a href={href} className="block no-underline">
        {body}
      </a>
    )
  }
  return body
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

  if (loading) {
    return (
      <div className="rounded-3xl bg-white/90 p-8 text-center text-hub-muted shadow-lg">
        Loading dashboard…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-3xl border border-red-200 bg-red-50 p-8 text-center text-red-800 shadow-lg">
        {error || 'Could not load dashboard'}
      </div>
    )
  }

  const shellClass = isDirector
    ? 'bg-gradient-to-br from-violet-50 via-violet-50/80 to-indigo-100'
    : 'bg-gradient-to-br from-emerald-50 via-teal-50/80 to-cyan-50'

  const ms = data.monthly_stats
  const ws = data.weekly_stats
  const st = data.stats
  const pendingExt = data.pending_extension_count
  const atRisk = data.at_risk_count

  return (
    <div className={`rounded-3xl p-5 md:p-8 ${shellClass}`}>
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">
            School management
          </p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-hub-text">
            Welcome back, {data.profile.display_name}
          </h1>
          <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-hub-muted">
            <i className="bi bi-calendar3" aria-hidden />
            {data.home_display_date}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isDirector ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-gradient-to-br from-violet-100 to-violet-200 px-3.5 py-2 text-[0.82rem] font-bold text-violet-800">
              <i className="bi bi-award-fill" aria-hidden />
              Director
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-gradient-to-br from-teal-100 to-emerald-200 px-3.5 py-2 text-[0.82rem] font-bold text-teal-900">
              <i className="bi bi-shield-fill" aria-hidden />
              Administrator
            </span>
          )}
          {data.dual_dashboard_staff ? (
            <a
              href="/switch-staff-dashboard"
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 hover:border-teal-600 hover:text-teal-800"
            >
              <i className="bi bi-arrow-left-right" aria-hidden />
              Switch dashboard
            </a>
          ) : null}
        </div>
      </header>

      {!data.has_active_school_year ? (
        <div className="mb-6 flex gap-4 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-sm">
          <i className="bi bi-calendar-x text-2xl text-slate-500" aria-hidden />
          <div>
            <p className="font-bold text-hub-text">School year closed</p>
            <p className="text-sm text-hub-muted">
              There is no active school year. Live statistics and coursework summaries are hidden
              until a new year is started.
            </p>
            {data.latest_school_year_label ? (
              <p className="mt-1 text-sm text-hub-muted">
                Most recent year: {data.latest_school_year_label}
              </p>
            ) : null}
          </div>
        </div>
      ) : (
        <>
          <div className="mb-5 grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
            <InsightCard icon="bi-calendar-week" value={ws.due_assignments} label="Due this week" />
            <InsightCard icon="bi-check2-circle" value={`${ms.attendance_rate}%`} label="Attendance rate" />
            <InsightCard icon="bi-graph-up" value={`${ms.average_grade}%`} label="Avg. grade score" />
            <InsightCard icon="bi-person-plus" value={ms.new_students} label="New enrollments" />
            <InsightCard
              icon="bi-clock-history"
              value={pendingExt}
              label="Pending extensions"
              href={pendingExt > 0 ? '/management/extension-requests' : undefined}
              alert={pendingExt > 0}
            />
            <InsightCard
              icon={atRisk > 0 ? 'bi-exclamation-triangle' : 'bi-shield-check'}
              value={atRisk}
              label="Academic concerns"
              href={atRisk > 0 ? '/management/assignments-and-grades' : undefined}
              alert={atRisk > 0}
            />
          </div>

          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard tone="students" icon="bi-people-fill" value={st.students} label="Students" meta="Enrolled in the system" />
            <StatCard tone="staff" icon="bi-person-badge-fill" value={st.teachers} label="Teachers & staff" meta="Active staff records" />
            <StatCard tone="classes" icon="bi-mortarboard-fill" value={st.classes} label="Classes" meta="Across all grade levels" />
            <StatCard
              tone="assignments"
              icon="bi-journal-check"
              value={st.active_assignments}
              label="Active assignments"
              meta={`${st.assignments} total in system`}
            />
          </div>
        </>
      )}

      <div className="mb-5 grid gap-4 lg:grid-cols-[minmax(260px,320px)_1fr] lg:items-start">
        <aside className="rounded-[20px] border border-white/90 bg-white/95 p-5 shadow-[0_4px_6px_rgba(15,23,42,0.04),0_18px_40px_rgba(15,23,42,0.08)]">
          <div className="mb-4 flex items-center gap-4 border-b border-slate-200 pb-4">
            <div
              className={[
                'flex h-[3.25rem] w-[3.25rem] shrink-0 items-center justify-center rounded-[14px] text-[1.35rem]',
                isDirector
                  ? 'bg-gradient-to-br from-violet-100 to-violet-300 text-violet-800'
                  : 'bg-gradient-to-br from-teal-100 to-teal-300 text-teal-800',
              ].join(' ')}
            >
              <i className={`bi ${isDirector ? 'bi-award-fill' : 'bi-person-badge-fill'}`} aria-hidden />
            </div>
            <div>
              <h2 className="text-[1.05rem] font-bold text-hub-text">{data.profile.display_name}</h2>
              <p className="text-[0.82rem] text-hub-muted">{data.profile.role}</p>
            </div>
          </div>
          <div className="space-y-2.5 text-[0.88rem] leading-snug text-slate-600">
            <p className="flex items-start gap-2">
              <i className="bi bi-person-vcard mt-0.5 text-teal-700" aria-hidden />
              <span>ID: {data.profile.staff_id}</span>
            </p>
            <p className="flex items-start gap-2">
              <i className="bi bi-envelope mt-0.5 text-teal-700" aria-hidden />
              <span>{data.profile.email || 'None'}</span>
            </p>
            <p className="flex items-start gap-2">
              <i className="bi bi-building mt-0.5 text-teal-700" aria-hidden />
              <span>Clara Science Academy — School operations</span>
            </p>
          </div>
        </aside>

        <section className="rounded-[20px] border border-white/90 bg-white/95 px-5 pb-4 pt-5 shadow-[0_4px_6px_rgba(15,23,42,0.04),0_18px_40px_rgba(15,23,42,0.08)]">
          <h2 className="mb-4 flex items-center gap-1.5 text-[0.95rem] font-bold text-hub-text">
            <i className="bi bi-lightning-fill text-teal-700" aria-hidden />
            Quick actions
          </h2>
          <div className="space-y-4">
            <ActionGroup label="People">
              <ActionTile icon="bi-person-plus-fill" label="Add student" href="/management/add-student" />
              <ActionTile icon="bi-person-badge" label="Add staff" href="/management/teachers/new" react />
              <ActionTile icon="bi-people" label="Students" href="/management/students" react />
              <ActionTile icon="bi-heart-fill" label="Family Portal" href="/management/parents" react />
              <ActionTile icon="bi-person-workspace" label="Teachers & staff" href="/management/teachers" react />
            </ActionGroup>
            <ActionGroup label="Academics">
              <ActionTile icon="bi-plus-circle" label="Add class" href="/management/classes?open=create" react />
              <ActionTile icon="bi-mortarboard" label="Classes" href="/management/classes" react />
              <ActionTile icon="bi-journal-plus" label="Add assignment" href="/management/assignment/type-selector" />
              <ActionTile icon="bi-clipboard-data" label="Grades & assignments" href="/management/assignments-and-grades" />
              <ActionTile icon="bi-file-earmark-text" label="Report cards" href="/management/generate-report-card-form" />
              <ActionTile icon="bi-collection" label="View report cards" href="/management/report-cards" />
            </ActionGroup>
            <ActionGroup label="Operations">
              <ActionTile icon="bi-calendar-check" label="Attendance" href="/management/unified-attendance" />
              <ActionTile
                icon="bi-clock-history"
                label="Extensions"
                href="/management/extension-requests"
                highlight={pendingExt > 0}
                badge={pendingExt > 0 ? pendingExt : undefined}
              />
            </ActionGroup>
          </div>
        </section>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <FeedPanel
          title="Notifications"
          icon="bi-bell-fill"
          emptyIcon="bi-bell-slash"
          emptyText="No new notifications"
          items={data.notifications.map((n) => ({
            type: n.type,
            title: n.title,
            text: n.message || '',
            timestamp: n.timestamp,
            link: n.link,
          }))}
        />
        <FeedPanel
          title="Recent activity"
          icon="bi-activity"
          emptyIcon="bi-inbox"
          emptyText="No recent activity"
          items={data.recent_activity.map((a) => ({
            type: a.type,
            title: a.title,
            text: a.description || '',
            timestamp: a.timestamp,
            link: a.link,
          }))}
          timeline
        />
      </div>
    </div>
  )
}

function ActionGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-[0.7rem] font-bold uppercase tracking-[0.08em] text-slate-400">{label}</p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">{children}</div>
    </div>
  )
}

function StatCard({
  tone,
  icon,
  value,
  label,
  meta,
}: {
  tone: 'students' | 'staff' | 'classes' | 'assignments'
  icon: string
  value: number
  label: string
  meta: string
}) {
  const accent =
    tone === 'students'
      ? 'from-blue-500/20'
      : tone === 'staff'
        ? 'from-violet-500/20'
        : tone === 'classes'
          ? 'from-teal-500/20'
          : 'from-amber-500/20'

  return (
    <article className={`relative overflow-hidden rounded-2xl border border-white/90 bg-white/95 p-5 shadow-lg`}>
      <div className={`pointer-events-none absolute right-0 top-0 h-20 w-20 rounded-bl-full bg-gradient-to-br ${accent} to-transparent opacity-60`} />
      <i className={`bi ${icon} text-2xl text-teal-700`} aria-hidden />
      <p className="mt-3 text-3xl font-extrabold text-hub-text">{value}</p>
      <p className="font-semibold text-hub-text">{label}</p>
      <p className="text-sm text-hub-muted">{meta}</p>
    </article>
  )
}

function FeedPanel({
  title,
  icon,
  emptyIcon,
  emptyText,
  items,
  timeline,
}: {
  title: string
  icon: string
  emptyIcon: string
  emptyText: string
  items: { type: string; title: string; text: string; timestamp: string | null; link: string | null }[]
  timeline?: boolean
}) {
  return (
    <section className="rounded-2xl border border-white/90 bg-white/95 p-5 shadow-lg">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-bold text-hub-text">
          <i className={`bi ${icon}`} aria-hidden />
          {title}
          {items.length ? (
            <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs font-bold text-teal-800">
              {items.length}
            </span>
          ) : null}
        </h2>
        <span className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Last 7 days</span>
      </div>
      {items.length === 0 ? (
        <div className="py-10 text-center text-hub-muted">
          <i className={`bi ${emptyIcon} mb-2 block text-3xl`} aria-hidden />
          <p>{emptyText}</p>
        </div>
      ) : timeline ? (
        <div className="space-y-4 border-l-2 border-teal-100 pl-4">
          {items.map((item) => (
            <article key={`${item.type}-${item.title}-${item.timestamp}`} className="relative">
              <span className="absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full bg-teal-500" aria-hidden />
              <h3 className="font-semibold text-hub-text">{item.title}</h3>
              <p className="text-sm text-hub-muted">{item.text}</p>
              <time className="text-xs text-hub-muted">{formatFeedTime(item.timestamp)}</time>
              {item.link ? (
                <a href={item.link} className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-teal-700 hover:underline">
                  View <i className="bi bi-arrow-right-short" aria-hidden />
                </a>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={`${item.type}-${item.title}-${item.timestamp}`} className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
              <h3 className="font-semibold text-hub-text">{item.title}</h3>
              <p className="text-sm text-hub-muted">{item.text}</p>
              <time className="text-xs text-hub-muted">{formatFeedTime(item.timestamp)}</time>
              {item.link ? (
                <a href={item.link} className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-teal-700 hover:underline">
                  View details <i className="bi bi-arrow-right-short" aria-hidden />
                </a>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
