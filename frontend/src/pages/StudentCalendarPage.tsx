import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchStudentCalendar } from '../api/studentTabs'
import { CalendarLegend } from '../components/calendar/CalendarLegend'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { StudentCalendarResponse } from '../types/studentTabs'
import { calendarEventClass } from '../utils/calendarEventColors'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

function eventTone(type: string) {
  const t = (type || '').toLowerCase()
  if (t.includes('holiday')) return 'bg-rose-100 text-rose-800'
  if (t.includes('break')) return 'bg-amber-100 text-amber-900'
  if (t.includes('quarter') || t.includes('semester') || t.includes('school_year')) {
    return 'bg-teal-100 text-teal-900'
  }
  if (t.includes('teacher') || t.includes('professional') || t.includes('pd')) {
    return 'bg-violet-100 text-violet-800'
  }
  return 'bg-sky-100 text-sky-800'
}

export function StudentCalendarPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const month = Number(searchParams.get('month')) || new Date().getMonth() + 1
  const year = Number(searchParams.get('year')) || new Date().getFullYear()

  const [data, setData] = useState<StudentCalendarResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchStudentCalendar(month, year))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load calendar')
    } finally {
      setLoading(false)
    }
  }, [month, year])

  useEffect(() => {
    void load()
  }, [load])

  function goMonth(next: { month: number; year: number }) {
    setSearchParams({ month: String(next.month), year: String(next.year) })
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading calendar…</div>
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
                    <h1 className="text-2xl font-bold tracking-tight md:text-3xl">School calendar</h1>
                    <p className="mb-0 mt-1 text-sm text-teal-50/95">
                      Academic dates and school events · read only
                    </p>
                  </div>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
                    <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-100">Month</p>
                    <p className="mb-0 text-lg font-bold">
                      {data.month_name} {data.year}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
                    <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-100">Events</p>
                    <p className="mb-0 text-lg font-bold">{data.events_this_month}</p>
                  </div>
                  <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
                    <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-100">
                      School year
                    </p>
                    <p className="mb-0 text-lg font-bold">{data.active_school_year?.name || 'N/A'}</p>
                  </div>
                </div>
              </header>

              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
                  <button
                    type="button"
                    onClick={() => goMonth(data.prev_month)}
                    className="rounded-full border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    <i className="bi bi-chevron-left me-1" aria-hidden />
                    Previous
                  </button>
                  <h2 className="mb-0 text-lg font-bold text-hub-text">
                    {data.month_name} {data.year}
                  </h2>
                  <button
                    type="button"
                    onClick={() => goMonth(data.next_month)}
                    className="rounded-full border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Next
                    <i className="bi bi-chevron-right ms-1" aria-hidden />
                  </button>
                </div>

                <div className="grid grid-cols-7 gap-1.5 p-3 sm:gap-2">
                  {WEEKDAYS.map((label) => (
                    <div
                      key={label}
                      className="rounded-lg bg-slate-100 px-1 py-2 text-center text-[11px] font-bold uppercase tracking-wide text-hub-muted"
                    >
                      {label}
                    </div>
                  ))}
                  {data.weeks.flatMap((week, wi) =>
                    week.map((day, di) => (
                      <div
                        key={`${wi}-${di}`}
                        className={[
                          'min-h-[5.5rem] rounded-xl border p-1.5 sm:min-h-[6.5rem] sm:p-2',
                          day.is_current_month
                            ? 'border-slate-200 bg-white'
                            : 'border-transparent bg-slate-50/70 text-slate-400',
                          day.is_today ? 'border-teal-400 ring-2 ring-teal-200' : '',
                        ]
                          .filter(Boolean)
                          .join(' ')}
                      >
                        {day.day_num ? (
                          <div
                            className={`mb-1 text-xs font-bold ${
                              day.is_today ? 'text-teal-800' : 'text-hub-text'
                            }`}
                          >
                            {day.day_num}
                          </div>
                        ) : null}
                        <ul className="mb-0 space-y-1">
                          {day.events.slice(0, 3).map((event, idx) => (
                            <li
                              key={`${event.title}-${idx}`}
                              className={`truncate rounded px-1 py-0.5 text-[10px] font-semibold leading-tight ${eventTone(event.type)} ${calendarEventClass(event.type)}`}
                              title={event.description || event.title}
                            >
                              {event.title}
                            </li>
                          ))}
                          {day.events.length > 3 ? (
                            <li className="text-[10px] font-semibold text-hub-muted">
                              +{day.events.length - 3} more
                            </li>
                          ) : null}
                        </ul>
                      </div>
                    )),
                  )}
                </div>
              </div>

              <CalendarLegend className="mt-4" />
            </>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}
