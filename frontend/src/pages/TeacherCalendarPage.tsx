import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchTeacherCalendar } from '../api/teacherTabs'
import { CalendarLegend } from '../components/calendar/CalendarLegend'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'
import type { TeacherCalendarResponse } from '../types/teacherTabs'
import { calendarEventClass } from '../utils/calendarEventColors'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

export function TeacherCalendarPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const month = Number(searchParams.get('month')) || new Date().getMonth() + 1
  const year = Number(searchParams.get('year')) || new Date().getFullYear()

  const [data, setData] = useState<TeacherCalendarResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTeacherCalendar(month, year))
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

  const stats = data
    ? [
        { icon: 'bi-calendar3', value: data.month_name, label: 'Month', tone: 'classes' as const },
        { icon: 'bi-calendar-event', value: data.events_this_month, label: 'Events', tone: 'assignments' as const },
        {
          icon: 'bi-mortarboard',
          value: data.active_school_year?.name || 'N/A',
          label: 'School year',
          tone: 'students' as const,
        },
        { icon: 'bi-eye', value: 'View', label: 'Read only', tone: 'notifications' as const },
      ]
    : []

  return (
    <TeacherTabShell
      eyebrow="Calendar"
      title="School calendar"
      subtitle={
        <>
          <i className="bi bi-calendar-event me-1" aria-hidden />
          Academic dates and school events
        </>
      }
      stats={stats}
      loading={loading}
      error={error}
    >
      {data ? (
        <div className="teacher-calendar">
          <div className="teacher-calendar__toolbar">
            <button
              type="button"
              className="teacher-calendar__nav"
              onClick={() => goMonth(data.prev_month)}
            >
              <i className="bi bi-chevron-left" aria-hidden />
              Previous
            </button>
            <h2 className="teacher-calendar__month">
              {data.month_name} {data.year}
            </h2>
            <button
              type="button"
              className="teacher-calendar__nav"
              onClick={() => goMonth(data.next_month)}
            >
              Next
              <i className="bi bi-chevron-right" aria-hidden />
            </button>
          </div>

          <div className="teacher-calendar__grid">
            {WEEKDAYS.map((label) => (
              <div key={label} className="teacher-calendar__weekday">
                {label}
              </div>
            ))}
            {data.weeks.flatMap((week, wi) =>
              week.map((day, di) => (
                <div
                  key={`${wi}-${di}`}
                  className={[
                    'teacher-calendar__day',
                    day.is_current_month ? '' : 'teacher-calendar__day--muted',
                    day.is_today ? 'teacher-calendar__day--today' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {day.day_num ? <div className="teacher-calendar__day-num">{day.day_num}</div> : null}
                  <ul className="teacher-calendar__events">
                    {day.events.slice(0, 3).map((event, idx) => (
                      <li
                        key={`${event.title}-${idx}`}
                        className={`teacher-calendar__event ${calendarEventClass(event.type)}`}
                        title={event.description || event.title}
                      >
                        {event.title}
                      </li>
                    ))}
                    {day.events.length > 3 ? (
                      <li className="teacher-calendar__more">+{day.events.length - 3} more</li>
                    ) : null}
                  </ul>
                </div>
              )),
            )}
          </div>

          <CalendarLegend className="mt-4" />
        </div>
      ) : null}
    </TeacherTabShell>
  )
}
