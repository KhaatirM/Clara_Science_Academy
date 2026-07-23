import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchTeacherAttendanceHub } from '../api/teacherTabs'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'
import type { TeacherAttendanceResponse } from '../types/teacherTabs'

export function TeacherAttendancePage() {
  const [data, setData] = useState<TeacherAttendanceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchTeacherAttendanceHub()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load attendance'))
      .finally(() => setLoading(false))
  }, [])

  const stats = data
    ? [
        { icon: 'bi-house-door-fill', value: data.stats.total_classes, label: 'Classes', tone: 'classes' as const },
        { icon: 'bi-check-circle', value: data.stats.completed_today, label: 'Done today', tone: 'assignments' as const },
        { icon: 'bi-clock', value: data.stats.pending_today, label: 'Pending', tone: 'notifications' as const },
        { icon: 'bi-calendar3', value: data.today_display.split(',')[0], label: 'Today', tone: 'students' as const },
      ]
    : []

  return (
    <TeacherTabShell
      eyebrow="Attendance"
      title="Attendance hub"
      subtitle={
        <>
          <i className="bi bi-clipboard-check me-1" aria-hidden />
          {data?.today_display ? `Today: ${data.today_display}` : 'Take and review class-period attendance'}
        </>
      }
      stats={stats}
      loading={loading}
      error={error}
    >
      {data && data.items.length === 0 ? (
        <div className="teacher-classes-empty">
          <i className="bi bi-calendar-x" aria-hidden />
          <h2>No classes found</h2>
          <p>You are not assigned to any classes yet.</p>
        </div>
      ) : null}
      {data && data.items.length > 0 ? (
        <div className="teacher-classes-grid">
          {data.items.map((item) => (
            <article key={item.id} className="teacher-class-card">
              <div className="teacher-class-card__header">
                <h3 className="teacher-class-card__title">{item.name}</h3>
                <span className="teacher-class-card__grade">{item.grade_levels_display}</span>
              </div>
              <div className="teacher-class-card__body">
                <div className="teacher-class-card__google">
                  <span className="teacher-class-card__google-label">
                    <i className="bi bi-people-fill" aria-hidden />
                    {item.enrollment_count} students
                  </span>
                  {item.attendance_taken_today ? (
                    <span className="teacher-class-card__badge teacher-class-card__badge--ok">
                      <i className="bi bi-check-circle-fill" aria-hidden />
                      Taken today
                    </span>
                  ) : (
                    <span className="teacher-class-card__badge teacher-class-card__badge--warn">
                      <i className="bi bi-clock" aria-hidden />
                      Pending
                    </span>
                  )}
                </div>
                <div className="teacher-class-card__actions teacher-class-card__actions--pair">
                  <Link to={item.links.take.replace(/^\/app/, '')} className="teacher-class-card__btn teacher-class-card__btn--attendance">
                    <i className="bi bi-calendar-check" aria-hidden />
                    Take attendance
                  </Link>
                  <Link to={item.links.records.replace(/^\/app/, '')} className="teacher-class-card__btn teacher-class-card__btn--view">
                    <i className="bi bi-list-check" aria-hidden />
                    Records
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </TeacherTabShell>
  )
}
