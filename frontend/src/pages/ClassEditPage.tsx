import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchClassEditForm, updateClass } from '../api/classes'
import { ClassSubpageShell, SUBJECTS } from '../components/classes/ClassSubpageShell'
import type { ClassEditResponse } from '../types/classDetail'

const inputClass =
  'w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20'

export function ClassEditPage() {
  const { classId } = useParams()
  const id = Number(classId)
  const navigate = useNavigate()
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
  const [isActive, setIsActive] = useState(true)
  const [gradeLevels, setGradeLevels] = useState<number[]>([])
  const [substituteIds, setSubstituteIds] = useState<number[]>([])
  const [additionalIds, setAdditionalIds] = useState<number[]>([])

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
      } else {
        setSubject('Other')
        setSubjectOther(subj)
      }
      setTeacherId(res.class.teacher.id ?? '')
      setRoom(res.class.room_number || '')
      setSchedule(res.class.schedule || '')
      setMaxStudents(res.class.max_students ?? 30)
      setDescription(res.class.description || '')
      setIsActive(res.form.is_active)
      setGradeLevels(res.class.grade_levels || [])
      setSubstituteIds(res.form.substitute_teacher_ids)
      setAdditionalIds(res.form.additional_teacher_ids)
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

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !teacherId || !resolvedSubject) return
    setSaving(true)
    setError(null)
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

  if (!id) return null

  return (
    <ClassSubpageShell eyebrow="Edit class" title={name || 'Class'} subtitle="Update class details and staff.">
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {message ? <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{message}</div> : null}
      {data ? (
        <form onSubmit={(e) => void onSave(e)} className="max-w-3xl space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <label className="mb-1 block text-sm font-medium text-hub-muted">Class name</label>
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-hub-muted">Subject</label>
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
              <label className="mb-1 block text-sm font-medium text-hub-muted">Primary teacher</label>
              <select
                className={inputClass}
                value={teacherId}
                onChange={(e) => setTeacherId(e.target.value ? Number(e.target.value) : '')}
                required
              >
                <option value="">Select teacher</option>
                {data.teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.display_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium text-hub-muted">Grade levels</p>
            <div className="flex flex-wrap gap-2">
              {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => toggleGrade(g)}
                  className={[
                    'rounded-full px-3 py-1 text-xs font-semibold',
                    gradeLevels.includes(g) ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-700',
                  ].join(' ')}
                >
                  Grade {g}
                </button>
              ))}
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-hub-muted">Room</label>
              <input className={inputClass} value={room} onChange={(e) => setRoom(e.target.value)} />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-sm font-medium text-hub-muted">Schedule</label>
              <input className={inputClass} value={schedule} onChange={(e) => setSchedule(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-hub-muted">Description</label>
            <textarea className={inputClass} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm font-medium text-hub-text">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Class is active
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-full bg-gradient-to-br from-teal-600 to-teal-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {saving ? 'Saving…' : 'Save changes'}
            </button>
            <button
              type="button"
              onClick={() => navigate(`/management/classes/${id}`)}
              className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}
    </ClassSubpageShell>
  )
}
