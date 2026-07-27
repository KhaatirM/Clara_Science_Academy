import { useEffect, useMemo, useState } from 'react'
import { fetchTeacherStudents } from '../api/teacherTabs'
import { TeacherTabShell } from '../components/teacher/TeacherTabShell'
import type { TeacherStudentsResponse } from '../types/teacherTabs'

export function TeacherStudentsPage() {
  const [data, setData] = useState<TeacherStudentsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    void fetchTeacherStudents()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load students'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    if (!q) return data.items
    return data.items.filter((student) => {
      const haystack = [
        student.full_name,
        student.student_id,
        student.email,
        student.grade_label,
        ...student.class_names,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return haystack.includes(q)
    })
  }, [data, search])

  const stats = data
    ? [
        { icon: 'bi-people-fill', value: data.stats.total_students, label: 'Students', tone: 'students' as const },
        { icon: 'bi-house-door-fill', value: data.stats.total_classes, label: 'Classes', tone: 'classes' as const },
        { icon: 'bi-mortarboard', value: data.stats.grade_levels, label: 'Grade levels', tone: 'assignments' as const },
        { icon: 'bi-envelope', value: data.stats.with_email, label: 'With email', tone: 'notifications' as const },
      ]
    : []

  const yearLabel = data?.meta?.active_school_year_name

  return (
    <TeacherTabShell
      eyebrow="Roster"
      title="My students"
      subtitle={
        <>
          <i className="bi bi-people me-1" aria-hidden />
          Students enrolled in your classes
          {yearLabel ? ` for ${yearLabel}` : ''}
        </>
      }
      stats={stats}
      loading={loading}
      error={error}
    >
      {data && !data.meta.has_active_school_year ? (
        <div className="teacher-classes-empty">
          <i className="bi bi-calendar-x" aria-hidden />
          <h2>No active school year</h2>
          <p>Student rosters are shown for the active school year only.</p>
        </div>
      ) : null}

      {data && data.meta.has_active_school_year && data.items.length > 0 ? (
        <div className="mb-4">
          <label className="sr-only" htmlFor="teacher-student-search">
            Search students
          </label>
          <div className="relative max-w-md">
            <i
              className="bi bi-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              aria-hidden
            />
            <input
              id="teacher-student-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, ID, email, or class…"
              className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm shadow-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-200"
            />
          </div>
        </div>
      ) : null}

      {data && data.meta.has_active_school_year && data.items.length === 0 ? (
        <div className="teacher-classes-empty">
          <i className="bi bi-person-x" aria-hidden />
          <h2>No students found</h2>
          <p>No students are enrolled in your active-year classes yet.</p>
        </div>
      ) : null}

      {data && data.meta.has_active_school_year && filtered.length === 0 && data.items.length > 0 ? (
        <div className="teacher-classes-empty">
          <i className="bi bi-search" aria-hidden />
          <h2>No matches</h2>
          <p>Try a different search term.</p>
        </div>
      ) : null}

      {data && filtered.length > 0 ? (
        <div className="teacher-students-grid">
          {filtered.map((student) => (
            <article key={student.id} className="teacher-student-card">
              <div className="teacher-student-card__header">
                <img src={student.photo_url} alt="" className="teacher-student-card__photo" />
                <div className="min-w-0">
                  <h3 className="teacher-student-card__name">{student.full_name}</h3>
                  <p className="teacher-student-card__id">
                    ID: {student.student_id || student.state_id || 'N/A'}
                  </p>
                </div>
              </div>
              <div className="teacher-student-card__body">
                <div className="teacher-student-card__row">
                  <span>Grade</span>
                  <strong>{student.grade_label}</strong>
                </div>
                <div className="teacher-student-card__row">
                  <span>DOB</span>
                  <strong>{student.date_of_birth_display || 'N/A'}</strong>
                </div>
                <div className="teacher-student-card__row">
                  <span>Email</span>
                  <strong>{student.email || 'N/A'}</strong>
                </div>
                {student.class_names.length > 0 ? (
                  <div className="teacher-student-card__classes">
                    <span className="teacher-student-card__classes-label">Classes</span>
                    <div className="teacher-student-card__class-list">
                      {student.class_names.map((name) => (
                        <span key={name} className="teacher-student-card__class-chip">
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="teacher-student-card__actions">
                <a href={student.links.grades} className="teacher-class-card__btn teacher-class-card__btn--assignment">
                  <i className="bi bi-journal-check" aria-hidden />
                  Grades
                </a>
                <a href={student.links.attendance} className="teacher-class-card__btn teacher-class-card__btn--attendance">
                  <i className="bi bi-calendar-check" aria-hidden />
                  Attendance
                </a>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </TeacherTabShell>
  )
}
