import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { googleClassroomAction } from '../api/classes'
import { fetchTeacherClasses } from '../api/teacherClasses'
import { LinkGoogleClassroomModal } from '../components/classes/LinkGoogleClassroomModal'
import { TeacherClassCard } from '../components/teacher/TeacherClassCard'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { TeacherClassesResponse } from '../types/teacherClasses'

export function TeacherClassesPage() {
  const [data, setData] = useState<TeacherClassesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [linkGoogle, setLinkGoogle] = useState<{ id: number; name: string } | null>(null)
  const [googleBusyId, setGoogleBusyId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTeacherClasses())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load classes')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const runGoogle = async (classId: number, action: 'create' | 'unlink') => {
    setGoogleBusyId(classId)
    try {
      const res = await googleClassroomAction(classId, action, undefined, 'teacher')
      if (!res.success) throw new Error(res.message)
      await load()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Google Classroom action failed')
    } finally {
      setGoogleBusyId(null)
    }
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading classes…</div>
          ) : error || !data ? (
            <div className="alert alert-danger m-3">{error || 'Could not load classes'}</div>
          ) : (
            <TeacherClassesBody
              data={data}
              googleBusyId={googleBusyId}
              onLinkGoogle={(id, name) => setLinkGoogle({ id, name })}
              onCreateGoogle={(id) => void runGoogle(id, 'create')}
              onUnlinkGoogle={(id) => void runGoogle(id, 'unlink')}
            />
          )}
        </div>
      </div>
      {linkGoogle ? (
        <LinkGoogleClassroomModal
          classId={linkGoogle.id}
          className={linkGoogle.name}
          scope="teacher"
          onClose={() => setLinkGoogle(null)}
          onLinked={() => void load()}
        />
      ) : null}
    </ManagementPageShell>
  )
}

function TeacherClassesBody({
  data,
  googleBusyId,
  onLinkGoogle,
  onCreateGoogle,
  onUnlinkGoogle,
}: {
  data: TeacherClassesResponse
  googleBusyId: number | null
  onLinkGoogle: (classId: number, className: string) => void
  onCreateGoogle: (classId: number) => void
  onUnlinkGoogle: (classId: number) => void
}) {
  const st = data.stats

  return (
    <>
      <header className="mgmt-home-hero">
        <div>
          <p className="mgmt-home-eyebrow">Teaching</p>
          <h1 className="mgmt-home-title">My classes</h1>
          <p className="mgmt-home-date">
            <i className="bi bi-house-door me-1" aria-hidden />
            Classes you teach
            {data.meta?.active_school_year_name ? ` for ${data.meta.active_school_year_name}` : ''}
          </p>
        </div>
        <div className="mgmt-home-hero-actions">
          <span className="mgmt-home-role-badge mgmt-home-role-badge--admin">
            <i className="bi bi-mortarboard-fill me-1" aria-hidden />
            Teacher
          </span>
          <Link to="/teacher" className="mgmt-home-switch-link">
            <i className="bi bi-grid me-1" aria-hidden />
            Home
          </Link>
        </div>
      </header>

      <div className="mgmt-home-stats">
        <article className="mgmt-home-stat mgmt-home-stat--classes">
          <div className="mgmt-home-stat-icon">
            <i className="bi bi-house-door-fill" aria-hidden />
          </div>
          <p className="mgmt-home-stat-number">{st.total_classes}</p>
          <p className="mgmt-home-stat-label">Classes</p>
        </article>
        <article className="mgmt-home-stat mgmt-home-stat--students">
          <div className="mgmt-home-stat-icon">
            <i className="bi bi-people-fill" aria-hidden />
          </div>
          <p className="mgmt-home-stat-number">{st.total_enrollments}</p>
          <p className="mgmt-home-stat-label">Students</p>
        </article>
        <article className="mgmt-home-stat mgmt-home-stat--notifications">
          <div className="mgmt-home-stat-icon">
            <i className="bi bi-google" aria-hidden />
          </div>
          <p className="mgmt-home-stat-number">{st.linked_classrooms}</p>
          <p className="mgmt-home-stat-label">Linked</p>
        </article>
        <article className="mgmt-home-stat mgmt-home-stat--assignments">
          <div className="mgmt-home-stat-icon">
            <i className="bi bi-journal-check" aria-hidden />
          </div>
          <p className="mgmt-home-stat-number">{st.total_assignments}</p>
          <p className="mgmt-home-stat-label">Assignments</p>
        </article>
      </div>

      {data.items.length === 0 ? (
        <div className="teacher-classes-empty">
          <i className="bi bi-inbox" aria-hidden />
          <h2>No classes found</h2>
          <p>
            {data.meta?.has_active_school_year
              ? 'You have no classes in the active school year.'
              : 'There is no active school year, or you are not assigned to any classes.'}
          </p>
        </div>
      ) : (
        <div className="teacher-classes-grid">
          {data.items.map((item) => (
            <TeacherClassCard
              key={item.id}
              item={item}
              googleBusy={googleBusyId === item.id}
              onLinkGoogle={onLinkGoogle}
              onCreateGoogle={onCreateGoogle}
              onUnlinkGoogle={onUnlinkGoogle}
            />
          ))}
        </div>
      )}
    </>
  )
}
