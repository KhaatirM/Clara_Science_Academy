import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchStudentSchedule } from '../api/studentTabs'
import { BellScheduleGrid } from '../components/schedule/BellScheduleGrid'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { StudentScheduleResponse } from '../types/studentTabs'

function spaPath(href: string) {
  return href.replace(/^\/app/, '') || '/'
}

export function StudentSchedulePage() {
  const navigate = useNavigate()
  const [data, setData] = useState<StudentScheduleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchStudentSchedule()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load schedule'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading schedule…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <>
              <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
                      Student portal
                    </p>
                    <h1 className="text-2xl font-bold tracking-tight md:text-3xl">My schedule</h1>
                    <p className="mb-0 mt-1 text-sm text-teal-50/95">{data.today_display}</p>
                  </div>
                  <Link
                    to="/student/calendar"
                    className="inline-flex items-center rounded-full bg-white px-4 py-2 text-sm font-bold text-teal-900 hover:bg-teal-50"
                  >
                    <i className="bi bi-calendar-event me-1" aria-hidden />
                    School calendar
                  </Link>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Stat label="Today" value={data.stats.today_blocks} icon="bi-calendar-day" />
                  <Stat label="Weekly blocks" value={data.stats.total_blocks} icon="bi-calendar-week" />
                  <Stat label="Active days" value={data.stats.active_days} icon="bi-calendar-range" />
                  <Stat label="Classes" value={data.stats.unique_classes} icon="bi-journal-bookmark" />
                </div>
              </header>

              {data.bell_grid ? (
                <BellScheduleGrid
                  grid={data.bell_grid}
                  pdfUrl={data.links.pdf || '/api/spa/student/schedule.pdf'}
                  showTeacher
                  compactListDays={data.days}
                  onOpenClass={(href) => navigate(spaPath(href))}
                />
              ) : data.stats.total_blocks === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-5 py-10 text-center">
                  <i className="bi bi-calendar-x mb-2 text-3xl text-hub-muted" aria-hidden />
                  <p className="mb-0 font-semibold text-hub-text">No class times scheduled yet</p>
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {data.days.map((day) => (
                    <section
                      key={day.day_index}
                      className={`overflow-hidden rounded-2xl border bg-white shadow-sm ${
                        day.is_today ? 'border-teal-400 ring-2 ring-teal-200' : 'border-slate-200'
                      }`}
                    >
                      <div
                        className={`px-4 py-3 ${
                          day.is_today
                            ? 'bg-gradient-to-r from-teal-700 to-emerald-600 text-white'
                            : 'bg-slate-50 text-hub-text'
                        }`}
                      >
                        <h2 className="mb-0 text-sm font-bold uppercase tracking-wide">
                          {day.day_name}
                          {day.is_today ? ' · Today' : ''}
                        </h2>
                      </div>
                      <div className="p-3">
                        {day.blocks.length === 0 ? (
                          <p className="mb-0 px-1 py-3 text-sm text-hub-muted">No classes</p>
                        ) : (
                          <ul className="mb-0 space-y-2">
                            {day.blocks.map((block) => (
                              <li
                                key={`${block.class_id}-${block.time_str}`}
                                className={`rounded-xl border px-3 py-2.5 ${
                                  block.is_now
                                    ? 'border-emerald-300 bg-emerald-50'
                                    : block.is_upcoming
                                      ? 'border-sky-200 bg-sky-50'
                                      : 'border-slate-100 bg-slate-50'
                                }`}
                              >
                                <p className="mb-0.5 text-xs font-bold text-teal-800">{block.time_str}</p>
                                <p className="mb-0.5 text-sm font-bold text-hub-text">{block.class_name}</p>
                                <p className="mb-2 text-xs text-hub-muted">
                                  {block.subject} · Room {block.room} · {block.teacher_name}
                                </p>
                                <Link
                                  to={spaPath(block.links.view_class)}
                                  className="text-xs font-bold text-teal-800 hover:underline"
                                >
                                  Open class
                                </Link>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </section>
                  ))}
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function Stat({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="rounded-2xl bg-white/15 px-4 py-3 backdrop-blur-sm">
      <div className="flex items-center gap-2 text-teal-100">
        <i className={`bi ${icon}`} aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
      </div>
      <p className="mb-0 mt-1 text-2xl font-bold tabular-nums">{value}</p>
    </div>
  )
}
