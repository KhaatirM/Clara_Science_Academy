import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext, useParams } from 'react-router-dom'
import { fetchClassRoster, mutateRoster } from '../api/classes'
import { ClassWorkflowNav } from '../components/classes/ClassWorkflowNav'
import type { ManagementOutletContext } from '../types/layout'
import type { ClassRosterResponse, ClassTeacherAssignee, StudentRosterEntry } from '../types/classDetail'

function InsightCard({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/90 bg-white p-4 shadow-sm">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-700">
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-xl font-extrabold text-hub-text">{value}</div>
        <div className="text-[0.68rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function TeacherBadge({ teacher, variant }: { teacher: ClassTeacherAssignee; variant: 'primary' | 'substitute' | 'additional' }) {
  const styles = {
    primary: 'border-emerald-300 bg-emerald-50 text-emerald-950',
    substitute: 'border-amber-300 bg-amber-50 text-amber-950',
    additional: 'border-sky-300 bg-sky-50 text-sky-950',
  }
  const roleStyles = {
    primary: 'bg-emerald-600 text-white',
    substitute: 'bg-amber-500 text-amber-950',
    additional: 'bg-sky-500 text-white',
  }
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-semibold ${styles[variant]}`}
    >
      {teacher.display_name}
      <span className={`rounded-full px-2 py-0.5 text-[0.65rem] font-bold uppercase ${roleStyles[variant]}`}>
        {teacher.role}
      </span>
    </span>
  )
}

function formatEmail(email: string | null | undefined) {
  if (!email) return 'No email'
  return email.length > 24 ? `${email.slice(0, 20)}...` : email
}

function EnrolledStudentCard({
  student,
  selected,
  onToggle,
}: {
  student: StudentRosterEntry
  selected: boolean
  onToggle: () => void
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={(e) => {
        if ((e.target as HTMLElement).closest('a')) return
        onToggle()
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onToggle()
        }
      }}
      className={`flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm transition hover:shadow-md ${
        selected ? 'border-teal-500 ring-2 ring-teal-500/20' : 'border-slate-200'
      }`}
    >
      <div className="flex items-start justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-teal-600 to-teal-800 text-sm font-bold text-white">
          {student.initial}
        </span>
        <div className="flex flex-col items-end gap-1">
          {student.has_account ? (
            <span className="text-emerald-600" title="Has account">
              <i className="bi bi-check-circle-fill" aria-hidden />
            </span>
          ) : null}
          {student.grade_level != null ? (
            <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[0.65rem] font-bold text-sky-800">
              {student.grade_level}
            </span>
          ) : null}
        </div>
      </div>
      <div className="flex-1 px-4 py-3">
        <h3 className="mb-2 font-bold text-hub-text">{student.display_name}</h3>
        <div className="space-y-1.5 text-xs text-hub-muted">
          <div className="flex items-center gap-2">
            <i className="bi bi-card-text text-teal-600" aria-hidden />
            <span>{student.student_id || 'No ID'}</span>
          </div>
          <div className="flex items-center gap-2">
            <i className="bi bi-envelope text-sky-600" aria-hidden />
            <span className="truncate">{formatEmail(student.email)}</span>
          </div>
          {student.username ? (
            <div className="flex items-center gap-2">
              <i className="bi bi-person-check text-emerald-600" aria-hidden />
              <span>{student.username}</span>
            </div>
          ) : null}
        </div>
      </div>
      <div className="border-t border-slate-100 p-3">
        <a
          href={student.view_url || `/management/view-student/${student.id}`}
          className="flex w-full items-center justify-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 py-2 text-sm font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
        >
          <i className="bi bi-eye" aria-hidden />
          View
        </a>
      </div>
    </div>
  )
}

function buildRosterStats(data: ClassRosterResponse): ClassRosterResponse['stats'] {
  if (data.stats) return data.stats
  const enrolledList = data.enrolled_students ?? []
  const enrolled = enrolledList.length
  const maxStudents = data.class.max_students ?? 0
  const withAccounts = enrolledList.filter((s) => s.has_account).length
  return {
    enrolled,
    with_accounts: withAccounts,
    capacity_percent: maxStudents ? Math.round((enrolled / maxStudents) * 1000) / 10 : 0,
    max_students: maxStudents,
  }
}

function buildRosterTeachers(data: ClassRosterResponse): ClassRosterResponse['teachers'] {
  return (
    data.teachers ?? {
      primary: null,
      substitute: [],
      additional: [],
    }
  )
}

export function ClassRosterPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const { classId } = useParams()
  const id = Number(classId)
  const isDirector = user.role_canonical === 'Director'
  const [data, setData] = useState<ClassRosterResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [enrolledSearch, setEnrolledSearch] = useState('')
  const [availableSearch, setAvailableSearch] = useState('')
  const [selectedAvailable, setSelectedAvailable] = useState<number[]>([])
  const [selectedEnrolled, setSelectedEnrolled] = useState<number[]>([])

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassRoster(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load roster')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const matchStudent = (student: StudentRosterEntry, term: string) => {
    const q = term.trim().toLowerCase()
    if (!q) return true
    return (
      student.display_name.toLowerCase().includes(q) ||
      (student.student_id || '').toLowerCase().includes(q)
    )
  }

  const available = useMemo(
    () => (data?.available_students || []).filter((s) => matchStudent(s, availableSearch)),
    [data, availableSearch],
  )
  const enrolled = useMemo(
    () => (data?.enrolled_students || []).filter((s) => matchStudent(s, enrolledSearch)),
    [data, enrolledSearch],
  )

  const toggle = (list: number[], setList: (v: number[]) => void, sid: number) => {
    setList(list.includes(sid) ? list.filter((x) => x !== sid) : [...list, sid])
  }

  const runAction = async (action: 'add' | 'remove', ids: number[]) => {
    if (!id || !ids.length) return
    setBusy(true)
    setMessage(null)
    setError(null)
    try {
      const res = await mutateRoster(id, action, ids)
      setMessage(res.message)
      setSelectedAvailable([])
      setSelectedEnrolled([])
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Roster update failed')
    } finally {
      setBusy(false)
    }
  }

  if (!Number.isFinite(id) || id <= 0) {
    return (
      <div className="rounded-3xl bg-gradient-to-br from-rose-50 via-pink-50/60 to-slate-100 p-5 md:p-8">
        <p className="text-sm text-red-800">
          Invalid class link.{' '}
          <Link to="/management/classes" className="font-semibold underline">
            Return to all classes
          </Link>
        </p>
      </div>
    )
  }

  const cls = data?.class
  const stats = data ? buildRosterStats(data) : null
  const teachers = data ? buildRosterTeachers(data) : null
  const canAdminUi = data?.meta?.can_admin_ui ?? false

  return (
    <div
      className={`rounded-3xl p-5 md:p-8 ${
        isDirector
          ? 'bg-gradient-to-br from-violet-50 via-purple-50/70 to-slate-100'
          : 'bg-gradient-to-br from-rose-50 via-pink-50/60 to-slate-100'
      }`}
    >
      <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Enrollment</p>
          <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-hub-text">{cls?.name || 'Class roster'}</h1>
          <p className="mt-2 flex items-center gap-1.5 text-sm text-hub-muted">
            <i className="bi bi-people-fill" aria-hidden />
            {cls ? `${cls.subject} · manage who is in this class` : 'Loading class…'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ClassWorkflowNav classId={id} active="roster" isDirector={isDirector} canAdminUi={canAdminUi} />
        </div>
      </header>

      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {message ? (
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{message}</div>
      ) : null}

      {!loading && !error && !data ? (
        <p className="text-hub-muted">No roster data returned. Restart Flask and hard-refresh the page.</p>
      ) : null}

      {data && stats && teachers ? (
        <>
          <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <InsightCard icon="bi-people-fill" value={stats.enrolled} label="Enrolled" />
            <InsightCard icon="bi-person-check-fill" value={stats.with_accounts} label="With accounts" />
            <InsightCard icon="bi-diagram-3-fill" value={`${stats.capacity_percent}%`} label="Capacity" />
            <InsightCard icon="bi-door-open" value={stats.max_students} label="Max seats" />
          </div>

          <section className="mb-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-teal-100 bg-gradient-to-r from-teal-100/80 to-teal-50/50 px-5 py-4">
              <div className="flex items-start gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-100 text-lg text-teal-800">
                  <i className="bi bi-info-circle" aria-hidden />
                </span>
                <div>
                  <h2 className="text-base font-bold text-hub-text">Class Information</h2>
                  <p className="text-sm text-hub-muted">Complete class details and teacher assignments</p>
                </div>
              </div>
            </div>
            <div className="grid gap-6 p-5 md:grid-cols-2">
              <div className="border-l-[3px] border-rose-400 pl-4">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-emerald-900">
                  <i className="bi bi-building" aria-hidden />
                  Class Details
                </h3>
                <div className="space-y-4 text-sm">
                  {[
                    ['bi-mortarboard', 'Class Name', cls?.name || 'N/A'],
                    ['bi-book', 'Subject', cls?.subject || 'N/A'],
                    ...(cls?.room_number ? [['bi-door-open', 'Room', cls.room_number] as const] : []),
                    ...(cls?.schedule ? [['bi-calendar-event', 'Schedule', cls.schedule] as const] : []),
                    ['bi-people', 'Max Students', String(cls?.max_students ?? stats.max_students)],
                  ].map(([icon, label, value]) => (
                    <div key={label}>
                      <div className="mb-1 flex items-center gap-2 font-semibold text-hub-text">
                        <i className={`bi ${icon} text-teal-600`} aria-hidden />
                        {label}:
                      </div>
                      <div className="text-hub-muted">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="border-l-[3px] border-rose-400 pl-4">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-emerald-900">
                  <i className="bi bi-people" aria-hidden />
                  Assigned Teachers
                </h3>
                <div className="space-y-4 text-sm">
                  <div>
                    <div className="mb-2 flex items-center gap-2 font-semibold text-hub-text">
                      <i className="bi bi-person-fill text-emerald-600" aria-hidden />
                      Primary Teacher:
                    </div>
                    {teachers.primary ? (
                      <TeacherBadge teacher={teachers.primary} variant="primary" />
                    ) : (
                      <span className="inline-flex rounded-full border border-red-200 bg-red-50 px-3 py-1 text-red-800">
                        No primary teacher assigned
                      </span>
                    )}
                  </div>
                  <div>
                    <div className="mb-2 flex items-center gap-2 font-semibold text-hub-text">
                      <i className="bi bi-person-clock text-amber-600" aria-hidden />
                      Substitute Teachers:
                    </div>
                    {(teachers.substitute?.length ?? 0) > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {teachers.substitute.map((t) => (
                          <TeacherBadge key={t.id} teacher={t} variant="substitute" />
                        ))}
                      </div>
                    ) : (
                      <span className="inline-flex rounded-full border border-slate-300 bg-slate-100 px-3 py-1 text-slate-700">
                        N/A
                      </span>
                    )}
                  </div>
                  <div>
                    <div className="mb-2 flex items-center gap-2 font-semibold text-hub-text">
                      <i className="bi bi-people text-sky-600" aria-hidden />
                      Additional Teachers:
                    </div>
                    {(teachers.additional?.length ?? 0) > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {teachers.additional.map((t) => (
                          <TeacherBadge key={t.id} teacher={t} variant="additional" />
                        ))}
                      </div>
                    ) : (
                      <span className="inline-flex rounded-full border border-slate-300 bg-slate-100 px-3 py-1 text-slate-700">
                        None assigned
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <div className="grid gap-4 xl:grid-cols-12 xl:items-start">
            <section className="flex max-h-[40rem] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm xl:col-span-7">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-100 bg-gradient-to-r from-emerald-600 to-teal-700 px-5 py-4 text-white">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20">
                    <i className="bi bi-check-circle-fill" aria-hidden />
                  </span>
                  <div>
                    <h2 className="font-bold">Enrolled Students</h2>
                    <p className="text-sm text-white/85">
                      {enrolled.length} active student{enrolled.length === 1 ? '' : 's'}
                    </p>
                  </div>
                </div>
                <div className="relative min-w-[12rem] flex-1 sm:max-w-xs">
                  <i className="bi bi-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/70" aria-hidden />
                  <input
                    type="search"
                    value={enrolledSearch}
                    onChange={(e) => setEnrolledSearch(e.target.value)}
                    placeholder="Search students..."
                    className="w-full rounded-full border-0 bg-white/15 py-2 pl-9 pr-3 text-sm text-white placeholder:text-white/70 focus:bg-white/25 focus:outline-none focus:ring-2 focus:ring-white/40"
                  />
                </div>
              </div>
              <div className="flex min-h-0 flex-1 flex-col p-4">
                <div className="mb-3 flex shrink-0 flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedEnrolled(enrolled.map((s) => s.id))}
                    className="rounded-full border border-teal-300 bg-white px-3 py-1 text-xs font-semibold text-teal-800 hover:bg-teal-50"
                  >
                    <i className="bi bi-check-all me-1" aria-hidden />
                    Select all
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedEnrolled([])}
                    className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    <i className="bi bi-x me-1" aria-hidden />
                    Clear all
                  </button>
                  <span className="ms-auto text-xs text-hub-muted">{selectedEnrolled.length} selected</span>
                </div>
                {enrolled.length ? (
                  <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                    <div className="grid gap-3 sm:grid-cols-2">
                      {enrolled.map((s) => (
                        <EnrolledStudentCard
                          key={s.id}
                          student={s}
                          selected={selectedEnrolled.includes(s.id)}
                          onToggle={() => toggle(selectedEnrolled, setSelectedEnrolled, s.id)}
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-1 items-center justify-center py-12 text-center">
                    <i className="bi bi-people mb-2 text-3xl text-hub-muted" aria-hidden />
                    <h3 className="font-bold text-hub-text">No Students Enrolled</h3>
                    <p className="text-sm text-hub-muted">Add students from the panel on the right to get started.</p>
                  </div>
                )}
                <button
                  type="button"
                  disabled={busy || !selectedEnrolled.length}
                  onClick={() => void runAction('remove', selectedEnrolled)}
                  className="mt-4 shrink-0 w-full rounded-full border border-red-300 bg-red-50 py-2.5 text-sm font-semibold text-red-800 disabled:opacity-50 sm:w-auto sm:px-6"
                >
                  <i className="bi bi-person-dash me-1" aria-hidden />
                  Remove selected ({selectedEnrolled.length})
                </button>
              </div>
            </section>

            <section className="flex max-h-[40rem] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm xl:col-span-5">
              <div className="border-b border-sky-100 bg-gradient-to-r from-sky-500 to-teal-600 px-5 py-4 text-white">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20">
                    <i className="bi bi-person-plus-fill" aria-hidden />
                  </span>
                  <div>
                    <h2 className="font-bold">Add Students</h2>
                    <p className="text-sm text-white/85">Enroll new students in this class</p>
                  </div>
                </div>
              </div>
              <div className="flex min-h-0 flex-1 flex-col p-4">
                <div className="relative mb-3">
                  <i className="bi bi-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-hub-muted" aria-hidden />
                  <input
                    type="search"
                    value={availableSearch}
                    onChange={(e) => setAvailableSearch(e.target.value)}
                    placeholder="Search available students..."
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                  />
                </div>
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedAvailable(available.map((s) => s.id))}
                    className="rounded-full border border-teal-300 bg-white px-3 py-1 text-xs font-semibold text-teal-800 hover:bg-teal-50"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedAvailable([])}
                    className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Clear All
                  </button>
                  <span className="ms-auto text-xs text-hub-muted">{selectedAvailable.length} selected</span>
                </div>
                <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
                  {available.length ? (
                    available.map((s) => (
                      <label
                        key={s.id}
                        className={`flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition hover:bg-slate-50 ${
                          selectedAvailable.includes(s.id) ? 'border-teal-400 bg-teal-50/50' : 'border-slate-200'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedAvailable.includes(s.id)}
                          onChange={() => toggle(selectedAvailable, setSelectedAvailable, s.id)}
                          className="rounded border-slate-300 text-teal-600"
                        />
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-teal-700 text-xs font-bold text-white">
                          {s.initial}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold text-hub-text">{s.display_name}</span>
                          <span className="mt-0.5 flex flex-wrap gap-2 text-[0.68rem] text-hub-muted">
                            <span>
                              <i className="bi bi-card-text me-1" aria-hidden />
                              {s.student_id || 'No ID'}
                            </span>
                            {s.grade_level != null ? (
                              <span>
                                <i className="bi bi-mortarboard me-1" aria-hidden />
                                Grade {s.grade_level}
                              </span>
                            ) : null}
                          </span>
                        </span>
                      </label>
                    ))
                  ) : (
                    <div className="py-10 text-center text-sm text-hub-muted">
                      <i className="bi bi-check-circle mb-2 block text-2xl text-emerald-600" aria-hidden />
                      All available students are already enrolled in this class.
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  disabled={busy || !selectedAvailable.length}
                  onClick={() => void runAction('add', selectedAvailable)}
                  className="mt-4 shrink-0 w-full rounded-full bg-gradient-to-r from-rose-800 to-teal-800 py-3 text-sm font-bold text-white shadow-sm disabled:opacity-50"
                >
                  <i className="bi bi-plus-circle me-1" aria-hidden />
                  Add {selectedAvailable.length} Student(s)
                </button>
              </div>
            </section>
          </div>

          <div className="mt-4 text-center text-sm text-hub-muted">
            <Link to={`/management/classes/${id}`} className="font-semibold text-teal-700 hover:underline">
              Back to class view
            </Link>
          </div>
        </>
      ) : null}
    </div>
  )
}
