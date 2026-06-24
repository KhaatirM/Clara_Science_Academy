import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { fetchClassEditForm, updateClass } from '../api/classes'
import { ClassEditPanel } from '../components/classes/ClassEditPanel'
import { ClassWorkflowNav } from '../components/classes/ClassWorkflowNav'
import { ScheduleBuilder } from '../components/classes/ScheduleBuilder'
import { SUBJECTS } from '../components/classes/ClassSubpageShell'
import type { ManagementOutletContext } from '../types/layout'
import type { ClassEditResponse, TeacherOption } from '../types/classDetail'

const inputClass =
  'w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20'

const labelClass = 'mb-1 flex items-center gap-1.5 text-xs font-semibold text-hub-text'

function InsightCard({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-white/90 bg-white px-3 py-2.5 shadow-sm">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-50 text-rose-700">
        <i className={`bi ${icon} text-sm`} aria-hidden />
      </span>
      <div>
        <div className="text-lg font-extrabold leading-tight text-hub-text">{value}</div>
        <div className="text-[0.62rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function SummaryRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-slate-100 py-1.5 text-xs last:border-0">
      <dt className="font-semibold text-hub-muted">{label}</dt>
      <dd className="text-right font-medium text-hub-text">{value}</dd>
    </div>
  )
}

function teacherName(teachers: TeacherOption[], id: number | '') {
  if (!id) return 'Not assigned'
  return teachers.find((t) => t.id === id)?.display_name || 'Not assigned'
}

export function ClassEditPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const { classId } = useParams()
  const id = Number(classId)
  const navigate = useNavigate()
  const isDirector = user.role_canonical === 'Director'

  const [data, setData] = useState<ClassEditResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [subject, setSubject] = useState('')
  const [subjectOther, setSubjectOther] = useState('')
  const [teacherId, setTeacherId] = useState<number | ''>('')
  const [room, setRoom] = useState('')
  const [schedule, setSchedule] = useState('')
  const [maxStudents, setMaxStudents] = useState(30)
  const [description, setDescription] = useState('')
  const [termType, setTermType] = useState('full_year')
  const [termValue, setTermValue] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [gradeLevels, setGradeLevels] = useState<number[]>([])
  const [gradeSearch, setGradeSearch] = useState('')
  const [substituteIds, setSubstituteIds] = useState<number[]>([])
  const [additionalIds, setAdditionalIds] = useState<number[]>([])
  const [assistant1, setAssistant1] = useState<number | ''>('')
  const [assistant2, setAssistant2] = useState<number | ''>('')

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetchClassEditForm(id)
      setData(res)
      setName(res.class.name)
      const subj = res.class.subject
      if (SUBJECTS.includes(subj)) {
        setSubject(subj)
        setSubjectOther('')
      } else {
        setSubject('Other')
        setSubjectOther(subj)
      }
      setTeacherId(res.class.teacher.id ?? '')
      setRoom(res.class.room_number || '')
      setSchedule(res.class.schedule || '')
      setMaxStudents(res.class.max_students ?? 30)
      setDescription(res.class.description || '')
      setTermType(res.class.term_type || 'full_year')
      setTermValue(res.class.term_value || '')
      setIsActive(res.form.is_active)
      setGradeLevels(res.class.grade_levels || [])
      setSubstituteIds(res.form.substitute_teacher_ids)
      setAdditionalIds(res.form.additional_teacher_ids)
      const aids = res.form.student_assistant_ids || []
      setAssistant1(aids[0] ?? '')
      setAssistant2(aids[1] ?? '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load class')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const resolvedSubject = subject === 'Other' ? subjectOther.trim() : subject
  const enrolledCount = data?.stats?.students ?? data?.enrolled_students?.length ?? 0

  const visibleGrades = useMemo(() => {
    const q = gradeSearch.trim().toLowerCase()
    return Array.from({ length: 12 }, (_, i) => i + 1).filter((g) => !q || `grade ${g}`.includes(q))
  }, [gradeSearch])

  const gradeDisplay =
    gradeLevels.length === 0
      ? 'None'
      : gradeLevels.length <= 4
        ? gradeLevels.join(', ')
        : `${gradeLevels.length} selected`

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !teacherId || !resolvedSubject) return
    setSaving(true)
    setError(null)
    const assistantIds = [assistant1, assistant2].filter((x): x is number => typeof x === 'number')
    try {
      const result = await updateClass(id, {
        name: name.trim(),
        subject: resolvedSubject,
        teacher_id: Number(teacherId),
        room_number: room.trim(),
        schedule: schedule.trim(),
        max_students: maxStudents,
        description: description.trim(),
        is_active: isActive,
        grade_levels: gradeLevels,
        substitute_teacher_ids: substituteIds,
        additional_teacher_ids: additionalIds,
        term_type: termType,
        term_value: termType === 'full_year' ? null : termValue || null,
        student_assistant_ids: assistantIds,
      })
      setMessage(result.message)
      setTimeout(() => navigate(`/management/classes/${id}`), 800)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const toggleGrade = (g: number) => {
    setGradeLevels((prev) => (prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g].sort((a, b) => a - b)))
  }

  const onMultiSelect = (setter: (v: number[]) => void, e: React.ChangeEvent<HTMLSelectElement>) => {
    setter(Array.from(e.target.selectedOptions, (o) => Number(o.value)))
  }

  if (!Number.isFinite(id) || id <= 0) return null

  return (
    <div
      className={`rounded-3xl p-5 md:p-6 ${
        isDirector
          ? 'bg-gradient-to-br from-violet-50 via-purple-50/70 to-slate-100'
          : 'bg-gradient-to-br from-rose-50 via-pink-50/60 to-slate-100'
      }`}
    >
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Class management</p>
          <h1 className="mt-0.5 text-2xl font-extrabold tracking-tight text-hub-text">{name || 'Edit class'}</h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-hub-muted">
            <i className="bi bi-mortarboard" aria-hidden />
            {name || 'Class'} · {resolvedSubject || 'No subject'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ClassWorkflowNav
            classId={id}
            active="edit"
            isDirector={isDirector}
            canAdminUi={data?.meta.can_admin_ui ?? false}
          />
        </div>
      </header>

      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div> : null}
      {message ? (
        <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900">{message}</div>
      ) : null}

      {data ? (
        <>
          <div className="mb-4 grid gap-2 sm:grid-cols-3">
            <InsightCard icon="bi-people-fill" value={enrolledCount} label="Enrolled" />
            <InsightCard icon="bi-person-lines-fill" value={maxStudents} label="Max capacity" />
            <InsightCard icon="bi-list-ol" value={gradeLevels.length} label="Grade levels set" />
          </div>

          <form onSubmit={(e) => void onSave(e)} className="grid gap-4 xl:grid-cols-3 xl:items-start">
            <div className="space-y-3 xl:col-span-2">
              <ClassEditPanel icon="bi-info-circle-fill" title="Basic information">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <label className={labelClass}>
                      <i className="bi bi-mortarboard text-teal-600" aria-hidden />
                      Class name <span className="text-red-500">*</span>
                    </label>
                    <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
                  </div>
                  <div>
                    <label className={labelClass}>
                      <i className="bi bi-book text-teal-600" aria-hidden />
                      Subject <span className="text-red-500">*</span>
                    </label>
                    <select className={inputClass} value={subject} onChange={(e) => setSubject(e.target.value)} required>
                      <option value="">Select subject</option>
                      {SUBJECTS.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    {subject === 'Other' ? (
                      <input
                        className={`${inputClass} mt-2`}
                        value={subjectOther}
                        onChange={(e) => setSubjectOther(e.target.value)}
                        placeholder="Type subject"
                        required
                      />
                    ) : null}
                  </div>
                  <div>
                    <label className={labelClass}>
                      <i className="bi bi-door-open text-teal-600" aria-hidden />
                      Room number
                    </label>
                    <input
                      className={inputClass}
                      value={room}
                      onChange={(e) => setRoom(e.target.value)}
                      placeholder="e.g., Room 101"
                    />
                  </div>
                  <div>
                    <label className={labelClass}>
                      <i className="bi bi-people-fill text-teal-600" aria-hidden />
                      Maximum students
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      className={inputClass}
                      value={maxStudents}
                      onChange={(e) => setMaxStudents(Number(e.target.value) || 30)}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className={labelClass}>
                      <i className="bi bi-clock text-teal-600" aria-hidden />
                      Weekly schedule
                    </label>
                    <ScheduleBuilder key={`${id}-${loading ? 'loading' : 'ready'}`} value={schedule} onChange={setSchedule} />
                  </div>
                  <div>
                    <label className={labelClass}>
                      <i className="bi bi-calendar4-range text-teal-600" aria-hidden />
                      Class term
                    </label>
                    <select className={inputClass} value={termType} onChange={(e) => setTermType(e.target.value)}>
                      <option value="full_year">Full year (all quarters)</option>
                      <option value="semester">Semester (S1 or S2)</option>
                      <option value="quarter">Single quarter (Q1–Q4)</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelClass}>
                      <i className="bi bi-calendar2-week text-teal-600" aria-hidden />
                      Term value
                    </label>
                    <select
                      className={inputClass}
                      value={termValue}
                      onChange={(e) => setTermValue(e.target.value)}
                      disabled={termType === 'full_year'}
                    >
                      <option value="">—</option>
                      <option value="S1">S1 (Q1 + Q2)</option>
                      <option value="S2">S2 (Q3 + Q4)</option>
                      <option value="Q1">Q1 only</option>
                      <option value="Q2">Q2 only</option>
                      <option value="Q3">Q3 only</option>
                      <option value="Q4">Q4 only</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2">
                    <label className={labelClass}>
                      <i className="bi bi-file-text text-teal-600" aria-hidden />
                      Description
                    </label>
                    <textarea
                      className={inputClass}
                      rows={2}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Optional description of the class..."
                    />
                  </div>
                </div>
              </ClassEditPanel>

              <ClassEditPanel icon="bi-people-fill" title="Teacher assignment">
                <div className="space-y-3">
                  <div>
                    <label className={labelClass}>
                      <i className="bi bi-person-fill text-teal-600" aria-hidden />
                      Primary teacher <span className="text-red-500">*</span>
                    </label>
                    <select
                      className={inputClass}
                      value={teacherId}
                      onChange={(e) => setTeacherId(e.target.value ? Number(e.target.value) : '')}
                      required
                    >
                      <option value="">Select a primary teacher…</option>
                      {data.teachers.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.display_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className={labelClass}>
                        <i className="bi bi-person-clock text-amber-600" aria-hidden />
                        Substitute teachers
                      </label>
                      <select
                        multiple
                        size={4}
                        className={`${inputClass} min-h-[6.5rem]`}
                        value={substituteIds.map(String)}
                        onChange={(e) => onMultiSelect(setSubstituteIds, e)}
                      >
                        {data.teachers.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.display_name}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1 text-[0.65rem] text-hub-muted">Ctrl/Cmd + click for multiple</p>
                    </div>
                    <div>
                      <label className={labelClass}>
                        <i className="bi bi-people text-sky-600" aria-hidden />
                        Additional teachers
                      </label>
                      <select
                        multiple
                        size={4}
                        className={`${inputClass} min-h-[6.5rem]`}
                        value={additionalIds.map(String)}
                        onChange={(e) => onMultiSelect(setAdditionalIds, e)}
                      >
                        {data.teachers.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.display_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              </ClassEditPanel>

              <ClassEditPanel icon="bi-mortarboard-fill" title="Grade levels">
                <div className="mb-2">
                  <input
                    type="search"
                    value={gradeSearch}
                    onChange={(e) => setGradeSearch(e.target.value)}
                    placeholder="Search grade levels…"
                    className={inputClass}
                  />
                </div>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setGradeLevels(Array.from({ length: 12 }, (_, i) => i + 1))}
                    className="rounded-full border border-teal-300 bg-white px-2.5 py-0.5 text-xs font-semibold text-teal-800"
                  >
                    Select all
                  </button>
                  <button
                    type="button"
                    onClick={() => setGradeLevels([])}
                    className="rounded-full border border-slate-300 bg-white px-2.5 py-0.5 text-xs font-semibold text-slate-700"
                  >
                    Clear all
                  </button>
                  <span className="ms-auto text-xs text-hub-muted">{gradeLevels.length} of 12 selected</span>
                </div>
                <div className="flex max-h-28 flex-wrap gap-1.5 overflow-y-auto">
                  {visibleGrades.map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => toggleGrade(g)}
                      className={[
                        'rounded-full px-2.5 py-1 text-xs font-semibold transition',
                        gradeLevels.includes(g) ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
                      ].join(' ')}
                    >
                      Grade {g}
                    </button>
                  ))}
                </div>
              </ClassEditPanel>

              {data.can_manage_assistants ? (
                <ClassEditPanel icon="bi-person-badge-fill" title="Student assistants">
                  <p className="mb-3 text-xs text-hub-muted">
                    Up to {data.max_assistants_per_class} per class. Each student may assist at most{' '}
                    <strong>2 classes</strong>.
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {([1, 2] as const).map((slot, idx) => (
                      <div key={slot}>
                        <label className={labelClass}>
                          <i className="bi bi-person-plus text-rose-600" aria-hidden />
                          Assistant {slot}
                        </label>
                        <select
                          className={inputClass}
                          value={idx === 0 ? assistant1 : assistant2}
                          onChange={(e) =>
                            (idx === 0 ? setAssistant1 : setAssistant2)(e.target.value ? Number(e.target.value) : '')
                          }
                        >
                          <option value="">— None —</option>
                          {data.eligible_assistants.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.display_name}
                              {s.grade_level != null ? ` (Grade ${s.grade_level})` : ''}
                              {s.student_id ? ` — ${s.student_id}` : ''}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                </ClassEditPanel>
              ) : null}

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => navigate(`/management/classes/${id}`)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
                >
                  <i className="bi bi-x-circle" aria-hidden />
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-rose-800 to-teal-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  <i className="bi bi-check-circle" aria-hidden />
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            </div>

            <aside className="space-y-3 xl:sticky xl:top-4">
              <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 bg-slate-50/80 px-4 py-2.5">
                  <h2 className="flex items-center gap-2 text-sm font-bold text-hub-text">
                    <i className="bi bi-info-circle-fill text-teal-600" aria-hidden />
                    Current configuration
                  </h2>
                </div>
                <dl className="px-4 py-2">
                  <p className="mb-1 text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">Class details</p>
                  <SummaryRow label="Name" value={name || '—'} />
                  <SummaryRow label="Subject" value={resolvedSubject || 'Not set'} />
                  <SummaryRow label="Room" value={room.trim() || 'Not set'} />
                  <SummaryRow label="Schedule" value={schedule.trim() || 'Not set'} />
                  <SummaryRow label="Max students" value={maxStudents} />
                </dl>
                <dl className="border-t border-slate-100 px-4 py-2">
                  <p className="mb-1 text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">Teachers</p>
                  <SummaryRow label="Primary" value={teacherName(data.teachers, teacherId)} />
                  <SummaryRow
                    label="Substitutes"
                    value={substituteIds.length ? `${substituteIds.length} assigned` : 'None'}
                  />
                  <SummaryRow
                    label="Additional"
                    value={additionalIds.length ? `${additionalIds.length} assigned` : 'None'}
                  />
                </dl>
                <dl className="border-t border-slate-100 px-4 py-2">
                  <p className="mb-1 text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">Other</p>
                  <SummaryRow label="Grade levels" value={gradeDisplay} />
                  <SummaryRow label="School year" value={data.class.school_year_name || 'Not set'} />
                </dl>
              </section>

              <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50/80 px-4 py-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-100 text-sm text-teal-800">
                    <i className="bi bi-toggle-on" aria-hidden />
                  </span>
                  <h2 className="text-sm font-bold text-hub-text">Class status</h2>
                </div>
                <div className="p-4">
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-600"
                      checked={isActive}
                      onChange={(e) => setIsActive(e.target.checked)}
                    />
                    <span>
                      <span className="block text-sm font-bold text-hub-text">Class is active</span>
                      <span className="mt-0.5 block text-xs text-hub-muted">
                        When active, this class is available for enrollment and assignments.
                      </span>
                    </span>
                  </label>
                  <div className="mt-3">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold ${
                        isActive ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {isActive ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </section>

              <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-900">
                <i className="bi bi-exclamation-triangle-fill me-1" aria-hidden />
                <strong>Note:</strong> Changes affect all assignments and student records for this class.
              </div>

              <div className="grid gap-2">
                <Link
                  to={`/management/classes/${id}/roster`}
                  className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:border-teal-400"
                >
                  <i className="bi bi-people" aria-hidden />
                  Manage roster
                </Link>
                <Link
                  to={`/management/classes/${id}/grades`}
                  className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:border-teal-400"
                >
                  <i className="bi bi-clipboard-data" aria-hidden />
                  Grades & assignments
                </Link>
              </div>
            </aside>
          </form>
        </>
      ) : null}
    </div>
  )
}
