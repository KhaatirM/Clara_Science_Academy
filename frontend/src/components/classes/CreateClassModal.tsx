import { useEffect, useState } from 'react'
import { createClass, fetchClassFormOptions } from '../../api/classes'
import { SUBJECTS } from './ClassSubpageShell'
import type { TeacherOption } from '../../types/classDetail'

const inputClass =
  'w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20'

interface CreateClassModalProps {
  onClose: () => void
  onCreated: (classId: number) => void
}

export function CreateClassModal({ onClose, onCreated }: CreateClassModalProps) {
  const [teachers, setTeachers] = useState<TeacherOption[]>([])
  const [activeYear, setActiveYear] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [subject, setSubject] = useState('')
  const [subjectOther, setSubjectOther] = useState('')
  const [teacherId, setTeacherId] = useState<number | ''>('')
  const [room, setRoom] = useState('')
  const [schedule, setSchedule] = useState('')
  const [maxStudents, setMaxStudents] = useState(30)
  const [description, setDescription] = useState('')
  const [gradeLevels, setGradeLevels] = useState<number[]>([])

  useEffect(() => {
    void fetchClassFormOptions()
      .then((res) => {
        setTeachers(res.teachers)
        setActiveYear(res.active_school_year?.name ?? null)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load form'))
      .finally(() => setLoading(false))
  }, [])

  const resolvedSubject = subject === 'Other' ? subjectOther.trim() : subject

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!teacherId || !resolvedSubject) return
    setSaving(true)
    setError(null)
    try {
      const result = await createClass({
        name: name.trim(),
        subject: resolvedSubject,
        teacher_id: Number(teacherId),
        room_number: room.trim(),
        schedule: schedule.trim(),
        max_students: maxStudents,
        description: description.trim(),
        grade_levels: gradeLevels,
      })
      if (!result.success || !result.class_id) throw new Error(result.message)
      onCreated(result.class_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed')
    } finally {
      setSaving(false)
    }
  }

  const toggleGrade = (g: number) => {
    setGradeLevels((prev) => (prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]))
  }

  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/50 p-4">
      <div className="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl" role="dialog">
        <div className="flex items-center justify-between border-b border-teal-100 bg-gradient-to-r from-teal-700 to-teal-600 px-5 py-4 text-white">
          <h2 className="text-lg font-bold">Create class</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1 hover:bg-white/10" aria-label="Close">
            <i className="bi bi-x-lg" />
          </button>
        </div>
        <form onSubmit={(e) => void onSubmit(e)} className="overflow-y-auto p-5">
          {loading ? <p className="text-hub-muted">Loading…</p> : null}
          {!activeYear ? (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              No active school year — class creation may be blocked.
            </div>
          ) : (
            <p className="mb-4 text-sm text-hub-muted">
              School year: <strong>{activeYear}</strong>
            </p>
          )}
          {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
          <div className="space-y-4">
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
                  <input className={`${inputClass} mt-2`} value={subjectOther} onChange={(e) => setSubjectOther(e.target.value)} required />
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
                  {teachers.map((t) => (
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
                    {g}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-hub-muted">Room</label>
                <input className={inputClass} value={room} onChange={(e) => setRoom(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-hub-muted">Schedule</label>
                <input className={inputClass} value={schedule} onChange={(e) => setSchedule(e.target.value)} />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-hub-muted">Max students</label>
              <input
                type="number"
                min={1}
                max={50}
                className={inputClass}
                value={maxStudents}
                onChange={(e) => setMaxStudents(Number(e.target.value) || 30)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-hub-muted">Description</label>
              <textarea className={inputClass} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>
          <div className="mt-5 flex justify-end gap-2 border-t border-slate-100 pt-4">
            <button type="button" onClick={onClose} className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !activeYear}
              className="rounded-full bg-gradient-to-br from-teal-600 to-teal-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? 'Creating…' : 'Create class'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
