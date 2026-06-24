import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { fetchClassDetail } from '../api/classes'
import { ClassManagementPanel } from '../components/classes/ClassManagementPanel'
import { ClassSubpageShell } from '../components/classes/ClassSubpageShell'
import { ClassWorkflowNav } from '../components/classes/ClassWorkflowNav'
import type { ManagementOutletContext } from '../types/layout'
import type { ClassDetailResponse, ClassManagementLinks, StudentBrief } from '../types/classDetail'

function DetailRow({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-slate-200 border-l-[3px] border-l-teal-500 bg-slate-50 px-3 py-2.5 text-sm">
      <i className={`bi ${icon} mt-0.5 shrink-0 text-teal-600`} aria-hidden />
      <span className="text-hub-muted">
        <strong className="text-hub-text">{label}:</strong> {value}
      </span>
    </div>
  )
}

function PanelHeader({ icon, title, subtitle }: { icon: string; title: string; subtitle: string }) {
  return (
    <div className="border-b border-teal-100 bg-gradient-to-r from-teal-100/80 to-teal-50/50 px-5 py-4">
      <div className="flex items-start gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-100 text-lg text-teal-800">
          <i className={`bi ${icon}`} aria-hidden />
        </span>
        <div>
          <h2 className="text-base font-bold text-hub-text">{title}</h2>
          <p className="text-sm text-hub-muted">{subtitle}</p>
        </div>
      </div>
    </div>
  )
}

function StudentRow({ student }: { student: StudentBrief }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5">
      {student.photo_url ? (
        <img src={student.photo_url} alt="" className="h-10 w-10 rounded-full object-cover" />
      ) : (
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-600 text-sm font-bold text-white">
          {student.initial}
        </span>
      )}
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-hub-text">{student.display_name}</div>
        <div className="text-xs text-hub-muted">
          ID: {student.student_id || 'N/A'}
          {student.grade_level != null ? ` · Grade: ${student.grade_level}` : ''}
        </div>
      </div>
    </div>
  )
}

export function ClassViewPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const { classId } = useParams()
  const id = Number(classId)
  const navigate = useNavigate()
  const isDirector = user.role_canonical === 'Director'
  const [data, setData] = useState<ClassDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassDetail(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load class')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  if (!Number.isFinite(id) || id <= 0) {
    return (
      <ClassSubpageShell eyebrow="Class overview" title="Class">
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Invalid class link. Return to{' '}
          <Link to="/management/classes" className="font-semibold underline">
            all classes
          </Link>
          .
        </div>
      </ClassSubpageShell>
    )
  }

  const pendingAssistantCount = data?.pending_assistant_count ?? 0
  const features = data?.features ?? { grade1_standards: false, grade3_standards: false }
  const links: Partial<ClassManagementLinks> = data?.links ?? {}

  const cls = data?.class

  return (
    <ClassSubpageShell
      eyebrow="Class overview"
      title={cls?.name || 'Class'}
      subtitle={cls ? `${cls.subject} · ${cls.grade_levels_display || 'All grades'}` : undefined}
      actions={
        cls && data ? (
          <ClassWorkflowNav
            classId={id}
            active="view"
            isDirector={isDirector}
            canAdminUi={data.meta.can_admin_ui}
          />
        ) : null
      }
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {data && cls ? (
        <>
          <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [data.stats.students, 'Students', 'bi-people-fill'],
              [data.stats.assignments, 'Assignments', 'bi-journal-text'],
              [data.stats.teacher_count, 'Teacher', 'bi-person-badge'],
              [data.stats.grade_levels_display, 'Grades', 'bi-mortarboard'],
            ].map(([value, label, icon]) => (
              <div key={String(label)} className="rounded-2xl border border-white/90 bg-white p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
                    <i className={`bi ${icon}`} aria-hidden />
                  </span>
                  <div>
                    <div className="text-xl font-extrabold text-hub-text">{value}</div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {pendingAssistantCount > 0 && links.assistant_approvals ? (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <span>
                <i className="bi bi-stars me-1 text-amber-600" aria-hidden />
                <strong>{pendingAssistantCount}</strong> student-assistant proposal(s) need approval.
              </span>
              <a
                href={links.assistant_approvals}
                className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                Review & approve
              </a>
            </div>
          ) : null}

          {links.assistant_approvals ? (
            <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm text-hub-muted">
              <a
                href={links.assistant_approvals}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
              >
                <i className="bi bi-patch-check-fill" aria-hidden />
                Assistant approvals
              </a>
              <span>When a student assistant proposes an assignment, review it here.</span>
            </div>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-3">
            <section className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <PanelHeader
                icon="bi-people-fill"
                title="Enrolled Students"
                subtitle={`${data.enrolled_students.length} Students`}
              />
              <div className="max-h-[32rem] flex-1 overflow-y-auto p-4">
                {data.enrolled_students.length ? (
                  <div className="space-y-2">
                    {data.enrolled_students.map((s) => (
                      <StudentRow key={s.id} student={s} />
                    ))}
                  </div>
                ) : (
                  <p className="py-8 text-center text-sm text-hub-muted">No students are currently enrolled in this class.</p>
                )}
              </div>
            </section>

            <section className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <PanelHeader icon="bi-info-circle" title="Class Information" subtitle="Complete Details" />
              <div className="space-y-2 p-4">
                <DetailRow icon="bi-book" label="Subject" value={cls.subject || 'N/A'} />
                <DetailRow icon="bi-mortarboard" label="Grade Levels" value={cls.grade_levels_display || 'N/A'} />
                <DetailRow icon="bi-door-open" label="Room" value={cls.room_display || cls.room_number || 'N/A'} />
                <DetailRow icon="bi-calendar-event" label="Schedule" value={cls.schedule_display || cls.schedule || 'TBD'} />
                <DetailRow icon="bi-calendar3" label="School Year" value={cls.school_year_name || 'N/A'} />
                <DetailRow icon="bi-person" label="Teacher" value={data.teacher.display_name} />
                <DetailRow icon="bi-envelope" label="Teacher Email" value={data.teacher.email || 'N/A'} />
                <DetailRow icon="bi-telephone" label="Teacher Phone" value={data.teacher.phone || 'N/A'} />
              </div>
            </section>

            <ClassManagementPanel links={links} features={features} canAdminUi={data.meta.can_admin_ui} />
          </div>

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => navigate(`/management/classes/${id}/roster`)}
              className="text-sm font-semibold text-teal-700 hover:underline"
            >
              Manage roster
            </button>
          </div>
        </>
      ) : null}
    </ClassSubpageShell>
  )
}
