import { useCallback, useEffect, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  deleteStudentGoal,
  fetchStudentDashboardHome,
  setStudentGoal,
} from '../api/studentDashboard'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { ManagementOutletContext } from '../types/layout'
import type {
  StudentAnnouncement,
  StudentDashboardHomeResponse,
  StudentGoalRow,
} from '../types/studentDashboard'

export function StudentHomePage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const [data, setData] = useState<StudentDashboardHomeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<StudentAnnouncement | null>(null)
  const [showAllAnnouncements, setShowAllAnnouncements] = useState(false)
  const [selectedNotification, setSelectedNotification] = useState<{
    title: string
    message: string
    meta?: string
  } | null>(null)
  const [goalDrafts, setGoalDrafts] = useState<Record<number, string>>({})
  const [goalBusy, setGoalBusy] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchStudentDashboardHome())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const previewAnnouncements = useMemo(() => (data?.announcements || []).slice(0, 8), [data])

  const onSetGoal = async (row: StudentGoalRow) => {
    const raw = goalDrafts[row.class_id]
    const target = Number(raw)
    if (!Number.isFinite(target) || target < 0 || target > 100) {
      window.alert('Enter a target grade between 0 and 100.')
      return
    }
    setGoalBusy(row.class_id)
    setMessage(null)
    try {
      const res = await setStudentGoal(row.class_id, target)
      setMessage(res.message)
      await load()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Could not set goal')
    } finally {
      setGoalBusy(null)
    }
  }

  const onDeleteGoal = async (row: StudentGoalRow) => {
    if (!row.goal_id || !window.confirm('Delete this goal?')) return
    setGoalBusy(row.class_id)
    setMessage(null)
    try {
      const res = await deleteStudentGoal(row.goal_id)
      setMessage(res.message)
      await load()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Could not delete goal')
    } finally {
      setGoalBusy(null)
    }
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading dashboard…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <StudentHomeBody
              data={data}
              username={user.username}
              message={message}
              previewAnnouncements={previewAnnouncements}
              goalDrafts={goalDrafts}
              goalBusy={goalBusy}
              onGoalDraft={(classId, value) =>
                setGoalDrafts((prev) => ({ ...prev, [classId]: value }))
              }
              onSetGoal={(row) => void onSetGoal(row)}
              onDeleteGoal={(row) => void onDeleteGoal(row)}
              onOpenAnnouncement={setSelectedAnnouncement}
              onOpenAllAnnouncements={() => setShowAllAnnouncements(true)}
              onOpenNotificationDetail={setSelectedNotification}
            />
          ) : null}
        </div>
      </div>

      {selectedAnnouncement ? (
        <AnnouncementModal
          announcement={selectedAnnouncement}
          onClose={() => setSelectedAnnouncement(null)}
        />
      ) : null}
      {selectedNotification ? (
        <NotificationDetailModal
          title={selectedNotification.title}
          message={selectedNotification.message}
          meta={selectedNotification.meta}
          onClose={() => setSelectedNotification(null)}
        />
      ) : null}
      {showAllAnnouncements && data ? (
        <AllAnnouncementsModal
          announcements={data.announcements}
          onSelect={(a) => {
            setShowAllAnnouncements(false)
            setSelectedAnnouncement(a)
          }}
          onClose={() => setShowAllAnnouncements(false)}
        />
      ) : null}
    </ManagementPageShell>
  )
}

function StudentHomeBody({
  data,
  username,
  message,
  previewAnnouncements,
  goalDrafts,
  goalBusy,
  onGoalDraft,
  onSetGoal,
  onDeleteGoal,
  onOpenAnnouncement,
  onOpenAllAnnouncements,
  onOpenNotificationDetail,
}: {
  data: StudentDashboardHomeResponse
  username: string
  message: string | null
  previewAnnouncements: StudentAnnouncement[]
  goalDrafts: Record<number, string>
  goalBusy: number | null
  onGoalDraft: (classId: number, value: string) => void
  onSetGoal: (row: StudentGoalRow) => void
  onDeleteGoal: (row: StudentGoalRow) => void
  onOpenAnnouncement: (a: StudentAnnouncement) => void
  onOpenAllAnnouncements: () => void
  onOpenNotificationDetail: (detail: {
    title: string
    message: string
    meta?: string
  }) => void
}) {
  const st = data.stats
  const firstName = data.profile.first_name || username
  const hasUpNext =
    data.failing_classes.length > 0 || data.up_next_items.length > 0

  return (
    <>
      <header className="mgmt-home-hero">
        <div>
          <p className="mgmt-home-eyebrow">Student portal</p>
          <h1 className="mgmt-home-title">Welcome back, {firstName}!</h1>
          <p className="mgmt-home-date">
            <i className="bi bi-calendar3 me-1" aria-hidden />
            {data.home_display_date}
          </p>
        </div>
        <div className="mgmt-home-hero-actions">
          <span className="mgmt-home-role-badge mgmt-home-role-badge--admin">
            <i className="bi bi-mortarboard-fill me-1" aria-hidden />
            Student
          </span>
        </div>
      </header>

      {message ? (
        <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {message}
        </div>
      ) : null}

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
        <>
          {data.assistant_classes.length > 0 ? (
            <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-bold text-hub-text">Student assistant</h2>
                  <p className="mb-0 text-sm text-hub-muted">
                    You can take attendance and enter grades for{' '}
                    <strong>{data.assistant_classes.length}</strong>{' '}
                    class{data.assistant_classes.length === 1 ? '' : 'es'}.
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {data.assistant_classes.map((c) => (
                      <a
                        key={c.id}
                        href={c.url}
                        className="rounded-full border border-teal-300 bg-white px-3 py-1 text-xs font-semibold text-teal-800"
                      >
                        {c.name}
                      </a>
                    ))}
                  </div>
                </div>
                <a
                  href={data.links.assistant_console}
                  className="rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                >
                  Open assistant console
                </a>
              </div>
            </div>
          ) : null}

          <div className="mgmt-home-stats mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <article className="mgmt-home-stat mgmt-home-stat--assignments rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mgmt-home-stat-icon mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800">
                <i className="bi bi-graph-up" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number text-2xl font-extrabold text-hub-text">{st.gpa.toFixed(2)}</p>
              <p className="mgmt-home-stat-label text-xs font-semibold uppercase tracking-wide text-hub-muted">Current GPA</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--classes rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mgmt-home-stat-icon mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
                <i className="bi bi-house-door-fill" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number text-2xl font-extrabold text-hub-text">{st.class_count}</p>
              <p className="mgmt-home-stat-label text-xs font-semibold uppercase tracking-wide text-hub-muted">Classes</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--students rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mgmt-home-stat-icon mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-800">
                <i className="bi bi-calendar-event" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number text-2xl font-extrabold text-hub-text">{st.upcoming_count}</p>
              <p className="mgmt-home-stat-label text-xs font-semibold uppercase tracking-wide text-hub-muted">Due soon</p>
            </article>
            <article className="mgmt-home-stat mgmt-home-stat--notifications rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mgmt-home-stat-icon mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-violet-800">
                <i className="bi bi-mortarboard-fill" aria-hidden />
              </div>
              <p className="mgmt-home-stat-number text-2xl font-extrabold text-hub-text">{st.grade_display}</p>
              <p className="mgmt-home-stat-label text-xs font-semibold uppercase tracking-wide text-hub-muted">Grade level</p>
            </article>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm xl:col-span-1">
              <div className="border-b border-slate-100 px-4 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">Profile</h2>
              </div>
              <div className="space-y-3 p-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-12 w-12 items-center justify-center rounded-full bg-teal-100 text-xl text-teal-800">
                    <i className="bi bi-person-fill" aria-hidden />
                  </span>
                  <div>
                    <div className="font-bold text-hub-text">{data.profile.display_name}</div>
                    <div className="text-sm text-hub-muted">
                      ID: {data.profile.state_id || 'N/A'}
                    </div>
                  </div>
                </div>
                <p className="mb-0 text-sm text-hub-muted">
                  <i className="bi bi-mortarboard me-2" aria-hidden />
                  Grade {data.profile.grade_display}
                </p>
                <p className="mb-0 text-sm text-hub-muted">
                  <i className="bi bi-calendar3 me-2" aria-hidden />
                  {data.profile.dob || 'N/A'}
                </p>
                <p className="mb-0 text-sm text-hub-muted">
                  <i className="bi bi-envelope me-2" aria-hidden />
                  {data.profile.email || 'N/A'}
                </p>
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm xl:col-span-2">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">
                  <i className="bi bi-megaphone-fill me-2" aria-hidden />
                  Announcements
                </h2>
                <button
                  type="button"
                  onClick={onOpenAllAnnouncements}
                  className="text-sm font-semibold text-teal-700 hover:underline"
                >
                  View all
                </button>
              </div>
              <div className="max-h-[22rem] space-y-2 overflow-y-auto p-4">
                {previewAnnouncements.length ? (
                  previewAnnouncements.map((a) => {
                    const isLong = (a.message || '').length > 120
                    return (
                      <div
                        key={a.id}
                        className={`w-full rounded-xl border px-3 py-3 text-left ${
                          a.is_important
                            ? 'border-amber-200 bg-amber-50'
                            : 'border-slate-100 bg-slate-50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <h3 className="text-sm font-bold text-hub-text">{a.title}</h3>
                          <small className="shrink-0 text-hub-muted">{a.timestamp_display}</small>
                        </div>
                        <p className="mb-2 mt-1 text-sm text-hub-muted">{a.preview}</p>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-700">
                            {a.audience_label}
                          </span>
                          {a.is_important ? (
                            <span className="rounded-full bg-amber-200 px-2 py-0.5 text-xs font-bold text-amber-900">
                              Important
                            </span>
                          ) : null}
                          {isLong ? (
                            <button
                              type="button"
                              onClick={() => onOpenAnnouncement(a)}
                              className="text-xs font-semibold text-teal-700 hover:underline"
                            >
                              View more
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => onOpenAnnouncement(a)}
                              className="text-xs font-semibold text-teal-700 hover:underline"
                            >
                              View
                            </button>
                          )}
                        </div>
                      </div>
                    )
                  })
                ) : (
                  <p className="mb-0 py-6 text-center text-sm text-hub-muted">No announcements yet.</p>
                )}
              </div>
            </section>
          </div>

          {hasUpNext ? (
            <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div className="flex items-center gap-2">
                  <i className="bi bi-lightning-charge-fill text-amber-500" aria-hidden />
                  <h2 className="mb-0 text-base font-bold text-hub-text">Up Next</h2>
                </div>
                <a href={data.links.assignments} className="text-sm font-semibold text-teal-700 hover:underline">
                  View all
                </a>
              </div>
              <div className="space-y-2 px-4 py-3">
                {data.failing_classes.map((item) => (
                  <a
                    key={`fail-${item.class_id}`}
                    href={item.url}
                    className="flex items-center justify-between gap-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-hub-text hover:border-red-200"
                  >
                    <span className="font-semibold">{item.class_name}</span>
                    <span className="rounded-full bg-red-600 px-2 py-0.5 text-xs font-bold text-white">
                      {item.average}%
                    </span>
                  </a>
                ))}
                {data.up_next_items.slice(0, 3).map((item) => (
                  <a
                    key={`up-${item.assignment_id}-${item.urgency}`}
                    href={item.url}
                    className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-hub-text hover:border-teal-200"
                  >
                    <span className="font-semibold">{item.title}</span>
                    <UrgencyBadge item={item} />
                  </a>
                ))}
              </div>
            </section>
          ) : null}

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-4 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">
                  <i className="bi bi-target me-2" aria-hidden />
                  Academic goals
                </h2>
              </div>
              <div className="space-y-4 p-4">
                {data.goals.length ? (
                  data.goals.map((row) => (
                    <div key={row.class_id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                      <h3 className="text-sm font-bold text-hub-text">{row.class_name}</h3>
                      <div className="mt-1 flex justify-between text-xs text-hub-muted">
                        <span>Current: {row.current_grade.toFixed(1)}%</span>
                        {row.target_grade != null ? (
                          <span>Goal: {row.target_grade.toFixed(1)}%</span>
                        ) : null}
                      </div>
                      {row.target_grade != null ? (
                        <>
                          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                            <div
                              className={`h-full ${
                                (row.progress_pct || 0) >= 100
                                  ? 'bg-emerald-500'
                                  : (row.progress_pct || 0) >= 80
                                    ? 'bg-amber-400'
                                    : 'bg-red-400'
                              }`}
                              style={{ width: `${Math.min(row.progress_pct || 0, 100)}%` }}
                            />
                          </div>
                          <button
                            type="button"
                            disabled={goalBusy === row.class_id}
                            onClick={() => onDeleteGoal(row)}
                            className="mt-2 rounded-lg border border-red-200 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                          >
                            Remove goal
                          </button>
                        </>
                      ) : (
                        <div className="mt-2 flex gap-2">
                          <input
                            type="number"
                            min={0}
                            max={100}
                            step={0.1}
                            placeholder="Target %"
                            value={goalDrafts[row.class_id] || ''}
                            onChange={(e) => onGoalDraft(row.class_id, e.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                          />
                          <button
                            type="button"
                            disabled={goalBusy === row.class_id}
                            onClick={() => onSetGoal(row)}
                            className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                          >
                            Set
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="mb-0 text-sm text-hub-muted">You are not yet enrolled in any classes.</p>
                )}
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-4 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">
                  <i className="bi bi-calendar-event me-2" aria-hidden />
                  Upcoming assignments
                </h2>
              </div>
              <div className="space-y-2 p-4">
                {data.upcoming_assignments.length ? (
                  data.upcoming_assignments.map((a) => (
                    <a
                      key={a.id}
                      href={a.url}
                      className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 hover:border-teal-200"
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-100 text-teal-800">
                        <i className="bi bi-journal-text" aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-semibold text-hub-text">{a.title}</div>
                        <div className="truncate text-xs text-hub-muted">{a.class_name}</div>
                      </div>
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-900">
                        Due: {a.due_display}
                      </span>
                    </a>
                  ))
                ) : (
                  <p className="mb-0 py-4 text-center text-sm text-hub-muted">No upcoming assignments</p>
                )}
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-4 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">
                  <i className="bi bi-bell-fill me-2" aria-hidden />
                  Notifications
                </h2>
              </div>
              <div className="space-y-3 p-4">
                {data.notifications.length ? (
                  data.notifications.map((n) => {
                    const preview = n.preview || n.message
                    const isLong = Boolean(n.is_long || (n.message && n.message.length > 120))
                    return (
                      <div key={n.id} className="border-l-2 border-teal-400 pl-3">
                        <div className="text-sm font-semibold text-hub-text">{n.title}</div>
                        <p className="mb-1 text-sm text-hub-muted">{preview}</p>
                        <div className="flex flex-wrap items-center gap-2">
                          <small className="text-hub-muted">{n.timestamp_display}</small>
                          {isLong ? (
                            <button
                              type="button"
                              className="text-xs font-semibold text-teal-700 hover:underline"
                              onClick={() =>
                                onOpenNotificationDetail({
                                  title: n.title,
                                  message: n.message,
                                  meta: n.timestamp_display,
                                })
                              }
                            >
                              View more
                            </button>
                          ) : null}
                        </div>
                      </div>
                    )
                  })
                ) : data.past_due_assignments.length ? (
                  data.past_due_assignments.map((a) => (
                    <a key={a.id} href={a.url} className="block border-l-2 border-red-400 pl-3">
                      <div className="text-sm font-semibold text-hub-text">Past Due: {a.title}</div>
                      <p className="mb-1 text-sm text-hub-muted">{a.class_name}</p>
                      <small className="text-hub-muted">Due: {a.due_display}</small>
                    </a>
                  ))
                ) : (
                  <p className="mb-0 py-4 text-center text-sm text-hub-muted">No notifications</p>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </>
  )
}

function UrgencyBadge({
  item,
}: {
  item: { urgency: string; days_offset: number }
}) {
  if (item.urgency === 'overdue') {
    return (
      <span className="rounded-full bg-red-600 px-2 py-0.5 text-xs font-bold text-white">
        {item.days_offset}d overdue
      </span>
    )
  }
  if (item.urgency === 'due_today') {
    return (
      <span className="rounded-full bg-amber-500 px-2 py-0.5 text-xs font-bold text-white">Today</span>
    )
  }
  return (
    <span className="rounded-full bg-sky-600 px-2 py-0.5 text-xs font-bold text-white">
      {item.days_offset}d
    </span>
  )
}

function AnnouncementModal({
  announcement,
  onClose,
}: {
  announcement: StudentAnnouncement
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl" role="dialog">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-hub-text">{announcement.title}</h2>
          <p className="text-sm text-hub-muted">
            {announcement.audience_label}
            {announcement.timestamp_full ? ` · ${announcement.timestamp_full}` : ''}
          </p>
        </div>
        <div className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap px-5 py-4 text-sm text-hub-text">
          {announcement.message}
        </div>
        <div className="border-t border-slate-100 px-5 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

function NotificationDetailModal({
  title,
  message,
  meta,
  onClose,
}: {
  title: string
  message: string
  meta?: string
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl" role="dialog">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-hub-text">{title}</h2>
          {meta ? <p className="text-sm text-hub-muted">{meta}</p> : null}
        </div>
        <div className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap px-5 py-4 text-sm text-hub-text">
          {message}
        </div>
        <div className="border-t border-slate-100 px-5 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

function AllAnnouncementsModal({
  announcements,
  onSelect,
  onClose,
}: {
  announcements: StudentAnnouncement[]
  onSelect: (a: StudentAnnouncement) => void
  onClose: () => void
}) {
  const [search, setSearch] = useState('')
  const [audience, setAudience] = useState('all')
  const [importantOnly, setImportantOnly] = useState(false)

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return announcements.filter((a) => {
      if (importantOnly && !a.is_important) return false
      if (audience === 'schoolwide' && !a.is_schoolwide) return false
      if (audience.startsWith('class-')) {
        const id = Number(audience.slice(6))
        if (a.class_id !== id) return false
      }
      if (!q) return true
      return (
        a.title.toLowerCase().includes(q) ||
        a.message.toLowerCase().includes(q) ||
        a.audience_label.toLowerCase().includes(q)
      )
    })
  }, [announcements, audience, importantOnly, search])

  const classOptions = useMemo(() => {
    const map = new Map<number, string>()
    for (const a of announcements) {
      if (a.class_id && !a.is_schoolwide) map.set(a.class_id, a.audience_label)
    }
    return [...map.entries()]
  }, [announcements])

  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/50 p-4">
      <div className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-2xl bg-white shadow-2xl" role="dialog">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-hub-text">Announcements</h2>
          <p className="text-sm text-hub-muted">Class updates and school-wide messages</p>
        </div>
        <div className="grid gap-3 border-b border-slate-100 px-5 py-3 sm:grid-cols-3">
          <select
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="all">All announcements</option>
            <option value="schoolwide">Entire student assembly</option>
            {classOptions.map(([id, name]) => (
              <option key={id} value={`class-${id}`}>
                {name}
              </option>
            ))}
          </select>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search title or message…"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-1"
          />
          <label className="flex items-center gap-2 text-sm text-hub-muted">
            <input
              type="checkbox"
              checked={importantOnly}
              onChange={(e) => setImportantOnly(e.target.checked)}
            />
            Important only
          </label>
        </div>
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
          {filtered.length ? (
            filtered.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => onSelect(a)}
                className="w-full rounded-xl border border-slate-100 bg-slate-50 px-3 py-3 text-left hover:border-teal-200"
              >
                <div className="flex justify-between gap-2">
                  <span className="text-sm font-bold text-hub-text">{a.title}</span>
                  <small className="text-hub-muted">{a.timestamp_display}</small>
                </div>
                <p className="mb-0 mt-1 text-sm text-hub-muted">{a.preview}</p>
                {(a.message || '').length > 120 ? (
                  <span className="mt-1 inline-block text-xs font-semibold text-teal-700">View more</span>
                ) : null}
              </button>
            ))
          ) : (
            <p className="py-8 text-center text-sm text-hub-muted">No matches</p>
          )}
        </div>
        <div className="border-t border-slate-100 px-5 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
