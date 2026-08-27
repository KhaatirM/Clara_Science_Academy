import { useEffect, useState } from 'react'
import { fetchTeacherSchedule } from '../api/teacherTabs'
import { BellScheduleGrid } from '../components/schedule/BellScheduleGrid'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'
import type { TeacherScheduleResponse } from '../types/teacherTabs'

export function TeacherSchedulePage() {
  const [data, setData] = useState<TeacherScheduleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchTeacherSchedule()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load schedule'))
      .finally(() => setLoading(false))
  }, [])

  const stats = data
    ? [
        { icon: 'bi-calendar-day', value: data.stats.today_blocks, label: 'Today', tone: 'classes' as const },
        { icon: 'bi-calendar-week', value: data.stats.total_blocks, label: 'Weekly blocks', tone: 'assignments' as const },
        { icon: 'bi-calendar-range', value: data.stats.active_days, label: 'Active days', tone: 'students' as const },
        { icon: 'bi-house-door', value: data.stats.unique_classes, label: 'Classes', tone: 'notifications' as const },
      ]
    : []

  return (
    <TeacherTabShell
      eyebrow="Schedule"
      title="My schedule"
      subtitle={
        <>
          <i className="bi bi-calendar-week me-1" aria-hidden />
          {data?.today_display || 'Weekly class schedule'}
        </>
      }
      stats={stats}
      loading={loading}
      error={error}
    >
      {data?.bell_grid ? (
        <BellScheduleGrid
          grid={data.bell_grid}
          pdfUrl={data.links?.pdf || '/api/spa/teacher/schedule.pdf'}
          showTeacher={false}
          compactListDays={data.days}
        />
      ) : data ? (
        <div className="teacher-schedule-wrap">
          <div className="teacher-schedule-days">
            {data.days.map((day) => (
              <section
                key={day.day_index}
                className={`teacher-schedule-day${day.is_today ? ' teacher-schedule-day--today' : ''}`}
              >
                <h2 className="teacher-schedule-day__title">{day.day_name}</h2>
                {day.blocks.length === 0 ? (
                  <p className="teacher-schedule-day__empty">No classes scheduled</p>
                ) : (
                  <ul className="teacher-schedule-day__list">
                    {day.blocks.map((block) => (
                      <li
                        key={`${block.class_id}-${block.time_str}`}
                        className={`teacher-schedule-block${
                          block.is_now ? ' teacher-schedule-block--now' : ''
                        }${block.is_upcoming ? ' teacher-schedule-block--upcoming' : ''}`}
                      >
                        <div className="teacher-schedule-block__time">{block.time_str}</div>
                        <div className="teacher-schedule-block__main">
                          <strong>{block.class_name}</strong>
                          <span>
                            {block.subject} · Room {block.room} · {block.student_count ?? 0} students
                          </span>
                        </div>
                        <a href={block.links.view_class} className="teacher-schedule-block__link">
                          View
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ))}
          </div>
        </div>
      ) : null}
    </TeacherTabShell>
  )
}
