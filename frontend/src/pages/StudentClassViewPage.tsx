import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchStudentClassDetail } from '../api/studentClasses'
import { ClassSyllabusModal } from '../components/classes/ClassSyllabusModal'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import { GRADE_TONES, gradeToneFromLetter } from '../utils/gradeDisplay'
import type {
  StudentClassDetailAnnouncement,
  StudentClassDetailAssignment,
  StudentClassDetailResponse,
} from '../types/studentClassView'

function statusLabel(status: string) {
  const s = (status || '').trim()
  if (!s) return '—'
  if (s === 'Un-Submitted') return 'To do'
  if (s === 'Submitted or Awaiting Grade') return 'Submitted'
  if (s === 'submitted_in_person') return 'Graded (in person)'
  if (s === 'completed') return 'Completed'
  if (s === 'Past Due') return 'Past due'
  if (s === 'Extended') return 'Extended'
  if (s === 'Voided') return 'Voided'
  return s.replace(/_/g, ' ')
}

function statusTone(status: string) {
  const s = (status || '').toLowerCase()
  if (s === 'completed' || s === 'submitted_in_person') return 'bg-emerald-100 text-emerald-800'
  if (s === 'un-submitted' || s === 'extended') return 'bg-amber-100 text-amber-900'
  if (s === 'past due') return 'bg-rose-100 text-rose-800'
  if (s === 'submitted or awaiting grade') return 'bg-teal-100 text-teal-900'
  if (s === 'voided') return 'bg-slate-200 text-slate-600'
  return 'bg-slate-100 text-slate-700'
}

function typeTone(type: string) {
  const t = (type || '').toLowerCase()
  if (t === 'quiz') return 'bg-violet-100 text-violet-800'
  if (t === 'discussion') return 'bg-sky-100 text-sky-800'
  return 'bg-slate-100 text-slate-700'
}

function gpaTone(gpa: number) {
  if (gpa >= 3.5) return 'from-emerald-600 to-teal-500'
  if (gpa >= 3.0) return 'from-teal-600 to-cyan-500'
  if (gpa >= 2.0) return 'from-amber-500 to-orange-500'
  return 'from-rose-500 to-red-500'
}

export function StudentClassViewPage() {
  const { classId } = useParams<{ classId: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<StudentClassDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syllabusOpen, setSyllabusOpen] = useState(false)

  useEffect(() => {
    if (!classId) {
      setError('Missing class id')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    void fetchStudentClassDetail(classId)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load class'))
      .finally(() => setLoading(false))
  }, [classId])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading class…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <>
              <StudentClassViewBody
                data={data}
                onNavigate={navigate}
                onOpenSyllabus={() => setSyllabusOpen(true)}
              />
              {data.links.syllabus ? (
                <ClassSyllabusModal
                  open={syllabusOpen}
                  classId={data.class.id}
                  onClose={() => setSyllabusOpen(false)}
                />
              ) : null}
            </>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function StudentClassViewBody({
  data,
  onNavigate,
  onOpenSyllabus,
}: {
  data: StudentClassDetailResponse
  onNavigate: (to: string) => void
  onOpenSyllabus: () => void
}) {
  const { class: cls, teacher, stats, group, roster, announcements, assignments, links } = data

  const openAssignment = (a: StudentClassDetailAssignment) => {
    if (!a.primary_url) return
    const to = a.primary_url.replace(/^\/app/, '')
    onNavigate(to)
  }

  return (
    <>
      <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-3xl">
              <i className="bi bi-journal-bookmark-fill" aria-hidden />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
                Student portal
              </p>
              <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{cls.name}</h1>
              <p className="mb-0 mt-1 text-sm text-teal-50/95">
                <i className="bi bi-book me-1" aria-hidden />
                {cls.subject} · {cls.grade_levels_display}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {links.assistant ? (
              <a
                href={links.assistant}
                className="inline-flex items-center rounded-full border border-amber-200/60 bg-amber-400/95 px-4 py-2 text-sm font-bold text-amber-950 hover:bg-amber-300"
              >
                <i className="bi bi-person-badge me-1" aria-hidden />
                Assistant
              </a>
            ) : null}
            <Link
              to={`/student/assignments?class_id=${cls.id}`}
              className="inline-flex items-center rounded-full border border-white/30 bg-white/15 px-4 py-2 text-sm font-semibold text-white hover:bg-white/25"
            >
              <i className="bi bi-journal-text me-1" aria-hidden />
              Assignments
            </Link>
            {links.class_notes ? (
              <Link
                to={links.class_notes.replace(/^\/app/, '')}
                className="inline-flex items-center rounded-full border border-white/30 bg-white/15 px-4 py-2 text-sm font-semibold text-white hover:bg-white/25"
              >
                <i className="bi bi-journal-bookmark me-1" aria-hidden />
                Class notes
              </Link>
            ) : null}
            {links.syllabus ? (
              <button
                type="button"
                onClick={onOpenSyllabus}
                className="inline-flex items-center rounded-full border border-white/30 bg-white/15 px-4 py-2 text-sm font-semibold text-white hover:bg-white/25"
              >
                <i className="bi bi-journal-richtext me-1" aria-hidden />
                Syllabus
              </button>
            ) : null}
            <Link
              to="/student/classes"
              className="inline-flex items-center rounded-full bg-white px-4 py-2 text-sm font-bold text-teal-900 hover:bg-teal-50"
            >
              <i className="bi bi-arrow-left me-1" aria-hidden />
              Back to classes
            </Link>
          </div>
        </div>
      </header>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon="bi-info-circle"
          label="Subject"
          value={cls.subject}
          hint={cls.grade_levels_display}
          tone="from-teal-700 to-emerald-600"
        />
        <StatCard
          icon="bi-person-badge"
          label="Teacher"
          value={teacher?.name || 'Not assigned'}
          hint={teacher?.position || '—'}
          tone="from-emerald-600 to-teal-500"
        />
        <StatCard
          icon="bi-people"
          label="Students"
          value={String(stats.student_count)}
          hint="Enrolled"
          tone="from-cyan-600 to-sky-500"
        />
        <StatCard
          icon="bi-graph-up"
          label="Your GPA"
          value={stats.class_gpa.toFixed(2)}
          hint={stats.graded_count ? `${stats.graded_count} graded` : 'No grades yet'}
          tone={gpaTone(stats.class_gpa)}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-4">
          {teacher ? (
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="bg-gradient-to-r from-emerald-600 to-teal-500 px-4 py-3 text-white">
                <h2 className="mb-0 text-sm font-bold uppercase tracking-wide">
                  <i className="bi bi-person-circle me-2" aria-hidden />
                  Teacher
                </h2>
              </div>
              <div className="p-4 text-center">
                <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-3xl text-white">
                  <i className="bi bi-person-circle" aria-hidden />
                </div>
                <h3 className="mb-0 text-lg font-bold text-hub-text">{teacher.name}</h3>
                <p className="mb-3 text-sm text-hub-muted">{teacher.position}</p>
                <div className="space-y-2 text-left text-sm">
                  <p className="mb-0 flex items-start gap-2">
                    <i className="bi bi-envelope text-teal-700 mt-0.5" aria-hidden />
                    {teacher.email ? (
                      <a href={`mailto:${teacher.email}`} className="text-hub-text hover:text-teal-800">
                        {teacher.email}
                      </a>
                    ) : (
                      <span className="text-hub-muted">Email not available</span>
                    )}
                  </p>
                  <p className="mb-0 flex items-start gap-2">
                    <i className="bi bi-telephone text-teal-700 mt-0.5" aria-hidden />
                    {teacher.phone ? (
                      <a href={`tel:${teacher.phone}`} className="text-hub-text hover:text-teal-800">
                        {teacher.phone}
                      </a>
                    ) : (
                      <span className="text-hub-muted">Phone not available</span>
                    )}
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-gradient-to-r from-teal-700 to-cyan-600 px-4 py-3 text-white">
              <h2 className="mb-0 text-sm font-bold uppercase tracking-wide">
                <i className="bi bi-people-fill me-2" aria-hidden />
                Your group
              </h2>
            </div>
            <div className="p-4">
              {group ? (
                <>
                  <p className="mb-3 text-base font-bold text-hub-text">{group.name}</p>
                  <ul className="mb-0 space-y-2">
                    {group.members.map((m) => (
                      <li
                        key={m.id}
                        className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
                      >
                        <span className="font-medium text-hub-text">{m.name}</span>
                        {m.is_you ? (
                          <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs font-bold text-teal-800">
                            You
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="mb-0 text-sm text-hub-muted">You are not in a group for this class.</p>
              )}
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-gradient-to-r from-cyan-600 to-sky-500 px-4 py-3 text-white">
              <h2 className="mb-0 text-sm font-bold uppercase tracking-wide">
                <i className="bi bi-people me-2" aria-hidden />
                Class roster ({roster.length})
              </h2>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {roster.length ? (
                <ul className="mb-0 divide-y divide-slate-100">
                  {roster.map((s) => (
                    <li key={s.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal-600 to-emerald-500 text-white">
                        <i className="bi bi-person" aria-hidden />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="mb-0 truncate text-sm font-semibold text-hub-text">
                          {s.name}
                          {s.is_you ? (
                            <span className="ms-2 rounded-full bg-teal-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-teal-800">
                              You
                            </span>
                          ) : null}
                        </p>
                        {s.email ? (
                          <p className="mb-0 truncate text-xs text-hub-muted">{s.email}</p>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="p-4 text-sm text-hub-muted">No students enrolled.</p>
              )}
            </div>
          </section>
        </div>

        <div className="space-y-4 lg:col-span-8">
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-gradient-to-r from-teal-800 to-teal-600 px-4 py-3 text-white">
              <h2 className="mb-0 text-sm font-bold uppercase tracking-wide">
                <i className="bi bi-megaphone me-2" aria-hidden />
                Recent announcements
              </h2>
            </div>
            <div className="p-4">
              {announcements.length ? (
                <ul className="mb-0 space-y-3">
                  {announcements.map((a) => (
                    <AnnouncementRow key={a.id} item={a} />
                  ))}
                </ul>
              ) : (
                <p className="mb-0 text-sm text-hub-muted">No announcements yet.</p>
              )}
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 bg-gradient-to-r from-emerald-700 to-teal-600 px-4 py-3 text-white">
              <h2 className="mb-0 text-sm font-bold uppercase tracking-wide">
                <i className="bi bi-clipboard-check me-2" aria-hidden />
                Recent assignments
              </h2>
              <Link
                to={`/student/assignments?class_id=${cls.id}`}
                className="rounded-full bg-white/20 px-3 py-1 text-xs font-bold text-white hover:bg-white/30"
              >
                View all
              </Link>
            </div>
            <div className="p-4">
              {assignments.length ? (
                <ul className="mb-0 space-y-3">
                  {assignments.map((a) => (
                    <li
                      key={a.id}
                      className="rounded-2xl border border-slate-100 bg-slate-50/80 p-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="mb-1 flex flex-wrap gap-1.5">
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${typeTone(a.assignment_type)}`}
                            >
                              {a.type_label}
                            </span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${statusTone(a.status)}`}
                            >
                              {statusLabel(a.status)}
                            </span>
                            {a.letter_grade ? (
                              <span
                                className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${GRADE_TONES[gradeToneFromLetter(a.letter_grade)].solid}`}
                              >
                                {a.letter_grade}
                              </span>
                            ) : null}
                          </div>
                          <p className="mb-0.5 text-sm font-bold text-hub-text">{a.title}</p>
                          {a.due_display ? (
                            <p className="mb-0 text-xs text-hub-muted">
                              <i className="bi bi-calendar-event me-1" aria-hidden />
                              Due {a.due_display}
                            </p>
                          ) : null}
                        </div>
                        {a.primary_url ? (
                          <button
                            type="button"
                            onClick={() => openAssignment(a)}
                            className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-teal-800"
                          >
                            Open
                          </button>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mb-0 text-sm text-hub-muted">No assignments in this class yet.</p>
              )}
            </div>
          </section>
        </div>
      </div>
    </>
  )
}

function StatCard({
  icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: string
  label: string
  value: string
  hint: string
  tone: string
}) {
  return (
    <div
      className={`rounded-2xl bg-gradient-to-br ${tone} px-4 py-5 text-center text-white shadow-sm`}
    >
      <i className={`bi ${icon} mb-2 text-2xl opacity-90`} aria-hidden />
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-white/85">{label}</p>
      <p className="mb-0 text-xl font-bold leading-tight">{value}</p>
      <p className="mb-0 mt-1 text-xs text-white/85">{hint}</p>
    </div>
  )
}

function AnnouncementRow({ item }: { item: StudentClassDetailAnnouncement }) {
  return (
    <li className="rounded-2xl border border-slate-100 bg-slate-50/80 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="mb-1 text-sm font-bold text-hub-text">{item.title}</h3>
        {item.timestamp_display ? (
          <span className="text-[11px] font-medium text-hub-muted">{item.timestamp_display}</span>
        ) : null}
      </div>
      <p className="mb-0 whitespace-pre-wrap text-sm text-hub-muted">{item.message}</p>
    </li>
  )
}
