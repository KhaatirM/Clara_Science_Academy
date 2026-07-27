import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  createDeadlineReminder,
  fetchDeadlineReminderCreateForm,
  fetchDeadlineReminderEditForm,
  fetchStudentsNeedingReminder,
  updateDeadlineReminder,
} from '../../api/deadlineReminders'
import type { DeadlineReminderFormMeta, StudentNeedingReminder } from '../../types/classTools'

type Props = {
  classId: number
  reminderId?: number
  onSaved: () => void
  onCancel: () => void
  scope?: 'management' | 'teacher'
}

const inputClass =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-hub-text focus:border-pink-500 focus:outline-none focus:ring-1 focus:ring-pink-500'

export function DeadlineReminderFormPanel({
  classId,
  reminderId,
  onSaved,
  onCancel,
  scope = 'management',
}: Props) {
  const isEdit = reminderId != null
  const [meta, setMeta] = useState<DeadlineReminderFormMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [reminderType, setReminderType] = useState('assignment')
  const [reminderFrequency, setReminderFrequency] = useState('once')
  const [reminderTitle, setReminderTitle] = useState('')
  const [reminderMessage, setReminderMessage] = useState('')
  const [reminderDate, setReminderDate] = useState('')
  const [assignmentId, setAssignmentId] = useState('')
  const [groupAssignmentId, setGroupAssignmentId] = useState('')
  const [selectedStudentIds, setSelectedStudentIds] = useState<number[]>([])
  const [assignmentStudents, setAssignmentStudents] = useState<StudentNeedingReminder[]>([])
  const [studentsLoading, setStudentsLoading] = useState(false)

  const loadForm = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = isEdit
        ? await fetchDeadlineReminderEditForm(classId, reminderId!, scope)
        : await fetchDeadlineReminderCreateForm(classId, scope)
      setMeta(data)
      const r = data.reminder
      if (r) {
        setReminderType(r.reminder_type)
        setReminderFrequency(r.reminder_frequency)
        setReminderTitle(r.reminder_title)
        setReminderMessage(r.reminder_message)
        setReminderDate(r.reminder_date)
        setAssignmentId(r.assignment_id ? String(r.assignment_id) : '')
        setGroupAssignmentId(r.group_assignment_id ? String(r.group_assignment_id) : '')
        setSelectedStudentIds(r.selected_student_ids || [])
      } else {
        setReminderType(data.defaults.reminder_type)
        setReminderFrequency(data.defaults.reminder_frequency)
        setReminderDate(data.defaults.reminder_date)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load form')
    } finally {
      setLoading(false)
    }
  }, [classId, isEdit, reminderId, scope])

  useEffect(() => {
    void loadForm()
  }, [loadForm])

  const showAssignmentSection = reminderType === 'assignment' || reminderType === 'group_assignment'
  const showStudentSelection = reminderType === 'assignment' || reminderType === 'general'

  const studentOptions = useMemo(() => {
    if (reminderType === 'assignment' && assignmentId) {
      return assignmentStudents
    }
    return (meta?.students || []).map((s) => ({
      id: s.id,
      display_name: s.display_name,
      status: 'not_submitted' as const,
    }))
  }, [assignmentStudents, assignmentId, meta?.students, reminderType])

  useEffect(() => {
    if (reminderType !== 'assignment' || !assignmentId) {
      setAssignmentStudents([])
      return
    }
    let cancelled = false
    setStudentsLoading(true)
    void fetchStudentsNeedingReminder(Number(assignmentId))
      .then((res) => {
        if (!cancelled) setAssignmentStudents(res.students)
      })
      .catch(() => {
        if (!cancelled) setAssignmentStudents([])
      })
      .finally(() => {
        if (!cancelled) setStudentsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [assignmentId, reminderType])

  const toggleStudent = (id: number) => {
    setSelectedStudentIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const selectAllStudents = () => setSelectedStudentIds(studentOptions.map((s) => s.id))
  const deselectAllStudents = () => setSelectedStudentIds([])

  const applyTemplate = (type: 'assignment' | 'group' | 'general') => {
    if (type === 'assignment') {
      setReminderType('assignment')
      setReminderTitle('Assignment Deadline Reminder')
      setReminderMessage(
        'This is a friendly reminder that your assignment is due soon. Please make sure to submit your work on time.\n\nIf you have any questions or need assistance, please do not hesitate to reach out.',
      )
    } else if (type === 'group') {
      setReminderType('group_assignment')
      setReminderTitle('Group Assignment Deadline Reminder')
      setReminderMessage(
        'This is a reminder about your upcoming group assignment deadline. Please coordinate with your group members to ensure everyone contributes and the assignment is submitted on time.',
      )
    } else {
      setReminderType('general')
      setReminderTitle('Important Class Reminder')
      setReminderMessage(
        'This is a reminder about an important upcoming event or deadline in our class. Please make sure you are prepared.',
      )
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    const body = {
      reminder_type: reminderType,
      reminder_frequency: reminderFrequency,
      reminder_title: reminderTitle.trim(),
      reminder_message: reminderMessage.trim(),
      reminder_date: reminderDate,
      assignment_id: assignmentId || null,
      group_assignment_id: groupAssignmentId || null,
      selected_student_ids: selectedStudentIds,
    }
    try {
      if (isEdit) {
        await updateDeadlineReminder(classId, reminderId!, body, scope)
      } else {
        await createDeadlineReminder(classId, body, scope)
      }
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save reminder')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-hub-muted">Loading form…</p>
  }

  if (!meta) {
    return <p className="text-sm text-red-700">{error || 'Could not load form'}</p>
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-bold text-hub-text">
          {isEdit ? 'Edit reminder' : 'Create reminder'}
        </h3>
        <button
          type="button"
          onClick={onCancel}
          className="text-sm font-semibold text-hub-muted hover:text-hub-text"
        >
          <i className="bi bi-arrow-left me-1" aria-hidden />
          Back to list
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
        <div className="space-y-4">
          <section className="rounded-xl border border-slate-200 p-4">
            <h4 className="mb-3 text-sm font-bold text-pink-700">Basic information</h4>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold text-hub-muted">Type</label>
                <select
                  className={inputClass}
                  value={reminderType}
                  onChange={(e) => setReminderType(e.target.value)}
                  required
                >
                  <option value="assignment">Assignment reminder</option>
                  <option value="group_assignment">Group assignment reminder</option>
                  <option value="general">General class reminder</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-hub-muted">Frequency</label>
                <select
                  className={inputClass}
                  value={reminderFrequency}
                  onChange={(e) => setReminderFrequency(e.target.value)}
                  required
                >
                  <option value="once">Once</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
            </div>
          </section>

          {showAssignmentSection ? (
            <section className="rounded-xl border border-slate-200 p-4">
              <h4 className="mb-3 text-sm font-bold text-pink-700">Assignment selection</h4>
              <div className="grid gap-3 sm:grid-cols-2">
                {reminderType === 'assignment' ? (
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-hub-muted">
                      Regular assignment
                    </label>
                    <select
                      className={inputClass}
                      value={assignmentId}
                      onChange={(e) => setAssignmentId(e.target.value)}
                      required
                    >
                      <option value="">Select an assignment…</option>
                      {meta.assignments.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.title}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-hub-muted">
                      Group assignment
                    </label>
                    <select
                      className={inputClass}
                      value={groupAssignmentId}
                      onChange={(e) => setGroupAssignmentId(e.target.value)}
                      required
                    >
                      <option value="">Select a group assignment…</option>
                      {meta.group_assignments.map((ga) => (
                        <option key={ga.id} value={ga.id}>
                          {ga.title}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </section>
          ) : null}

          <section className="rounded-xl border border-slate-200 p-4">
            <h4 className="mb-3 text-sm font-bold text-pink-700">Reminder content</h4>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-semibold text-hub-muted">Title</label>
                <input
                  className={inputClass}
                  value={reminderTitle}
                  onChange={(e) => setReminderTitle(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-hub-muted">Message</label>
                <textarea
                  className={inputClass}
                  rows={5}
                  value={reminderMessage}
                  onChange={(e) => setReminderMessage(e.target.value)}
                  required
                />
              </div>
            </div>
          </section>

          {showStudentSelection ? (
            <section className="rounded-xl border border-slate-200 p-4">
              <h4 className="mb-2 text-sm font-bold text-pink-700">Student selection</h4>
              <p className="mb-3 text-xs text-hub-muted">
                Leave all unchecked to send to every student in the class. Use smart filter for
                assignment reminders to target students who still need to submit.
              </p>
              <div className="mb-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={selectAllStudents}
                  className="rounded-full border border-slate-300 px-2.5 py-1 text-xs font-semibold"
                >
                  Select all
                </button>
                <button
                  type="button"
                  onClick={deselectAllStudents}
                  className="rounded-full border border-slate-300 px-2.5 py-1 text-xs font-semibold"
                >
                  Deselect all
                </button>
                {reminderType === 'assignment' && assignmentId ? (
                  <button
                    type="button"
                    onClick={selectAllStudents}
                    className="rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800"
                  >
                    Smart filter
                  </button>
                ) : null}
                <span className="self-center text-xs text-hub-muted">
                  Selected: {selectedStudentIds.length}
                </span>
              </div>
              {studentsLoading ? (
                <p className="text-sm text-hub-muted">Loading students…</p>
              ) : studentOptions.length ? (
                <div className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
                  {studentOptions.map((s) => (
                    <label key={s.id} className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-slate-50">
                      <input
                        type="checkbox"
                        checked={selectedStudentIds.includes(s.id)}
                        onChange={() => toggleStudent(s.id)}
                      />
                      <span className="flex-1">{s.display_name}</span>
                      {'status' in s && s.status === 'not_submitted' ? (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-[0.65rem] font-bold text-red-800">
                          Not submitted
                        </span>
                      ) : null}
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-hub-muted">
                  {reminderType === 'assignment' && !assignmentId
                    ? 'Select an assignment to load students.'
                    : 'No students need reminders for this selection.'}
                </p>
              )}
            </section>
          ) : null}

          <section className="rounded-xl border border-slate-200 p-4">
            <h4 className="mb-3 text-sm font-bold text-pink-700">Schedule</h4>
            <div>
              <label className="mb-1 block text-xs font-semibold text-hub-muted">
                Reminder date &amp; time
              </label>
              <input
                type="datetime-local"
                className={inputClass}
                value={reminderDate}
                onChange={(e) => setReminderDate(e.target.value)}
                required
              />
            </div>
          </section>

          {error ? <p className="text-sm text-red-700">{error}</p> : null}

          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-full bg-pink-600 px-4 py-2 text-sm font-bold text-white hover:bg-pink-700 disabled:opacity-60"
            >
              {submitting ? 'Saving…' : isEdit ? 'Update reminder' : 'Create reminder'}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>

        <aside className="space-y-3">
          <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-3 text-sm">
            <h5 className="font-bold text-cyan-900">Quick templates</h5>
            <div className="mt-2 grid gap-2">
              <button
                type="button"
                onClick={() => applyTemplate('assignment')}
                className="rounded-lg border border-cyan-300 bg-white px-2 py-1.5 text-left text-xs font-semibold"
              >
                Assignment template
              </button>
              <button
                type="button"
                onClick={() => applyTemplate('group')}
                className="rounded-lg border border-cyan-300 bg-white px-2 py-1.5 text-left text-xs font-semibold"
              >
                Group assignment template
              </button>
              <button
                type="button"
                onClick={() => applyTemplate('general')}
                className="rounded-lg border border-cyan-300 bg-white px-2 py-1.5 text-left text-xs font-semibold"
              >
                General template
              </button>
            </div>
          </div>
          {isEdit && meta.reminder ? (
            <div className="rounded-xl border border-slate-200 p-3 text-sm">
              <div className="text-hub-muted">Status</div>
              <div className="font-semibold">{meta.reminder.is_active ? 'Active' : 'Inactive'}</div>
              {meta.reminder.last_sent ? (
                <>
                  <div className="mt-2 text-hub-muted">Last sent</div>
                  <div>{new Date(meta.reminder.last_sent).toLocaleString()}</div>
                </>
              ) : null}
            </div>
          ) : null}
        </aside>
      </div>
    </form>
  )
}
