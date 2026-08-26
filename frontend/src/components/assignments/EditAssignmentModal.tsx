import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchAssignmentEditForm,
  saveAssignmentEdit,
  type AssignmentEditForm,
} from '../../api/assignmentWorkspace'

const CATEGORIES = ['', 'Homework', 'Tests', 'Quizzes', 'Projects', 'Classwork', 'Participation', 'Extra Credit', 'Other']
const STATUSES = ['Active', 'Inactive', 'Upcoming', 'Voided']

function isoToDatetimeLocal(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function inputClass() {
  return 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-hub-text'
}

function FieldLabel({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-xs font-bold uppercase tracking-wide text-hub-muted">
      {children}
    </label>
  )
}

export function EditAssignmentModal({
  open,
  assignmentId,
  isGroup,
  onClose,
  onSaved,
}: {
  open: boolean
  assignmentId: number
  isGroup: boolean
  onClose: () => void
  onSaved: (message: string) => void
}) {
  const [form, setForm] = useState<AssignmentEditForm | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newFiles, setNewFiles] = useState<File[]>([])
  const [removeIds, setRemoveIds] = useState<number[]>([])
  const [clearGroupAttachment, setClearGroupAttachment] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAssignmentEditForm(assignmentId, isGroup)
      setForm({
        ...data,
        due_date: isoToDatetimeLocal(data.due_date) || data.due_date || '',
        open_date: data.open_date ? isoToDatetimeLocal(data.open_date) : '',
        close_date: data.close_date ? isoToDatetimeLocal(data.close_date) : '',
        status_override_until: data.status_override_until
          ? isoToDatetimeLocal(data.status_override_until)
          : '',
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load assignment')
    } finally {
      setLoading(false)
    }
  }, [assignmentId, isGroup])

  useEffect(() => {
    if (open) void load()
    else {
      setForm(null)
      setError(null)
      setNewFiles([])
      setRemoveIds([])
      setClearGroupAttachment(false)
    }
  }, [open, load])

  if (!open) return null

  const typeLabel = (form?.assignment_type || 'assignment').replace(/_/g, ' ')
  const isPdfLike =
    !form?.assignment_type ||
    ['pdf', 'pdf_paper', 'paper'].includes(String(form.assignment_type).toLowerCase())

  async function handleSave() {
    if (!form) return
    setSaving(true)
    setError(null)
    try {
      const body: Record<string, unknown> = {
        title: form.title,
        description: form.description,
        due_date: form.due_date,
        open_date: form.open_date || null,
        close_date: form.close_date || null,
        quarter: form.quarter,
        status: form.status,
        assignment_context: form.assignment_context,
        assignment_category: form.assignment_category || '',
        category_weight: form.category_weight ?? 0,
        total_points: form.total_points,
        allow_extra_credit: form.allow_extra_credit,
        max_extra_credit_points: form.max_extra_credit_points ?? 0,
        late_penalty_enabled: form.late_penalty_enabled,
        late_penalty_per_day: form.late_penalty_per_day ?? 0,
        late_penalty_max_days: form.late_penalty_max_days ?? 0,
        status_revert_enabled: form.status_revert_enabled,
        status_override_until: form.status_override_until || null,
      }
      if (form.allow_individual != null) body.allow_individual = form.allow_individual
      if (form.quiz) body.quiz = form.quiz
      if (form.discussion) body.discussion = form.discussion

      const removeAttachmentIds = isGroup
        ? clearGroupAttachment
          ? [-1]
          : []
        : removeIds

      const result = await saveAssignmentEdit(
        assignmentId,
        isGroup,
        body,
        'management',
        isPdfLike ? newFiles : [],
        removeAttachmentIds,
      )
      if (!result.success) throw new Error(result.message)
      onSaved(result.message || 'Assignment updated.')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  function patch(patch: Partial<AssignmentEditForm>) {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  function toggleRemove(id: number | null) {
    if (id == null) return
    setRemoveIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  function onPickFiles(list: FileList | null) {
    if (!list?.length) return
    setNewFiles((prev) => [...prev, ...Array.from(list)])
  }

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/45 p-4" role="dialog" aria-modal>
      <div className="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
        <div className="flex items-start justify-between bg-gradient-to-r from-amber-600 to-orange-700 px-5 py-4 text-white">
          <div>
            <h2 className="text-lg font-bold">Edit assignment</h2>
            <p className="text-sm text-white/85">
              {form?.class_name || 'Loading…'} · {typeLabel}
            </p>
          </div>
          <button type="button" onClick={onClose} className="rounded-full p-1 hover:bg-white/15" aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {loading ? <p className="text-hub-muted">Loading assignment…</p> : null}
          {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}

          {form ? (
            <div className="space-y-4">
              <div>
                <FieldLabel htmlFor="edit-title">Title</FieldLabel>
                <input
                  id="edit-title"
                  value={form.title}
                  onChange={(e) => patch({ title: e.target.value })}
                  className={inputClass()}
                  required
                />
              </div>

              <div>
                <FieldLabel htmlFor="edit-description">Description</FieldLabel>
                <textarea
                  id="edit-description"
                  rows={4}
                  value={form.description}
                  onChange={(e) => patch({ description: e.target.value })}
                  className={inputClass()}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <FieldLabel htmlFor="edit-due">Due date</FieldLabel>
                  <input
                    id="edit-due"
                    type="datetime-local"
                    value={form.due_date}
                    onChange={(e) => patch({ due_date: e.target.value })}
                    className={inputClass()}
                  />
                </div>
                <div>
                  <FieldLabel htmlFor="edit-quarter">Quarter</FieldLabel>
                  <select
                    id="edit-quarter"
                    value={form.quarter}
                    onChange={(e) => patch({ quarter: e.target.value })}
                    className={inputClass()}
                  >
                    {['1', '2', '3', '4'].map((q) => (
                      <option key={q} value={q}>
                        Quarter {q}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <FieldLabel htmlFor="edit-status">Status</FieldLabel>
                  <select
                    id="edit-status"
                    value={form.status}
                    onChange={(e) => patch({ status: e.target.value })}
                    className={inputClass()}
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <FieldLabel htmlFor="edit-context">Context</FieldLabel>
                  <select
                    id="edit-context"
                    value={form.assignment_context}
                    onChange={(e) => patch({ assignment_context: e.target.value })}
                    className={inputClass()}
                  >
                    <option value="homework">Homework</option>
                    <option value="in-class">In-class</option>
                  </select>
                </div>
                <div>
                  <FieldLabel htmlFor="edit-points">Total points</FieldLabel>
                  <input
                    id="edit-points"
                    type="number"
                    min={1}
                    step="0.1"
                    value={form.total_points}
                    onChange={(e) => patch({ total_points: Number(e.target.value) })}
                    className={inputClass()}
                  />
                </div>
                <div>
                  <FieldLabel htmlFor="edit-category">Category</FieldLabel>
                  <select
                    id="edit-category"
                    value={form.assignment_category || ''}
                    onChange={(e) => patch({ assignment_category: e.target.value })}
                    className={inputClass()}
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c || 'none'} value={c}>
                        {c || 'None'}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {isPdfLike ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Documents</p>
                  {(form.attachments || []).length > 0 ? (
                    <ul className="space-y-2 text-sm text-hub-text">
                      {form.attachments!.map((a, idx) => (
                        <li key={a.id ?? `legacy-${idx}`} className="flex items-center gap-2">
                          <i className="bi bi-paperclip text-teal-700" aria-hidden />
                          <span className="min-w-0 flex-1 truncate">{a.name}</span>
                          {isGroup ? (
                            <label className="flex shrink-0 items-center gap-1 text-xs text-red-700">
                              <input
                                type="checkbox"
                                checked={clearGroupAttachment}
                                onChange={(e) => setClearGroupAttachment(e.target.checked)}
                              />
                              Remove
                            </label>
                          ) : a.id != null ? (
                            <label className="flex shrink-0 items-center gap-1 text-xs text-red-700">
                              <input
                                type="checkbox"
                                checked={removeIds.includes(a.id)}
                                onChange={() => toggleRemove(a.id)}
                              />
                              Remove
                            </label>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-hub-muted">No documents yet.</p>
                  )}
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple={!isGroup}
                      className="sr-only"
                      accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.xls,.xlsx,.ppt,.pptx"
                      onChange={(e) => {
                        onPickFiles(e.target.files)
                        e.target.value = ''
                      }}
                    />
                    <button
                      type="button"
                      className="rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {isGroup ? 'Add or replace document' : 'Add documents'}
                    </button>
                    <p className="mt-1 text-xs text-hub-muted">
                      New files are saved when you click Save changes.
                    </p>
                  </div>
                  {newFiles.length > 0 ? (
                    <ul className="space-y-1 text-sm">
                      {newFiles.map((f, index) => (
                        <li
                          key={`${f.name}-${f.size}-${f.lastModified}`}
                          className="flex items-center gap-2 text-emerald-900"
                        >
                          <i className="bi bi-file-earmark-plus" aria-hidden />
                          <span className="min-w-0 flex-1 truncate">{f.name}</span>
                          <button
                            type="button"
                            className="text-xs text-slate-600 underline"
                            onClick={() => setNewFiles((prev) => prev.filter((_, i) => i !== index))}
                          >
                            Undo
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}

              {form.assignment_type === 'quiz' && form.quiz ? (
                <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-4 space-y-3">
                  <p className="text-sm font-bold text-violet-950">Quiz settings</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <FieldLabel htmlFor="edit-time-limit">Time limit (minutes)</FieldLabel>
                      <input
                        id="edit-time-limit"
                        type="number"
                        min={0}
                        placeholder="Unlimited"
                        value={form.quiz.time_limit_minutes ?? ''}
                        onChange={(e) =>
                          patch({
                            quiz: {
                              ...form.quiz!,
                              time_limit_minutes: e.target.value ? Number(e.target.value) : null,
                            },
                          })
                        }
                        className={inputClass()}
                      />
                    </div>
                    <div>
                      <FieldLabel htmlFor="edit-attempts">Max attempts</FieldLabel>
                      <input
                        id="edit-attempts"
                        type="number"
                        min={1}
                        value={form.quiz.max_attempts}
                        onChange={(e) =>
                          patch({ quiz: { ...form.quiz!, max_attempts: Number(e.target.value) || 1 } })
                        }
                        className={inputClass()}
                      />
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={form.quiz.shuffle_questions}
                      onChange={(e) =>
                        patch({ quiz: { ...form.quiz!, shuffle_questions: e.target.checked } })
                      }
                    />
                    Shuffle questions
                    <span className="mt-0.5 block text-xs font-normal text-slate-500">
                      Within each section
                    </span>
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={form.quiz.show_correct_answers}
                      onChange={(e) =>
                        patch({ quiz: { ...form.quiz!, show_correct_answers: e.target.checked } })
                      }
                    />
                    Show correct answers after submission
                  </label>
                </div>
              ) : null}

              {form.assignment_type === 'discussion' && form.discussion ? (
                <label className="flex items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm">
                  <input
                    type="checkbox"
                    checked={form.discussion.allow_student_edit_posts}
                    onChange={(e) =>
                      patch({ discussion: { allow_student_edit_posts: e.target.checked } })
                    }
                  />
                  Allow students to edit their posts
                </label>
              ) : null}

              {isGroup ? (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(form.allow_individual)}
                    onChange={(e) => patch({ allow_individual: e.target.checked })}
                  />
                  Allow individual submissions
                </label>
              ) : null}

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={Boolean(form.allow_extra_credit)}
                  onChange={(e) => patch({ allow_extra_credit: e.target.checked })}
                />
                Allow extra credit
              </label>
            </div>
          ) : null}
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 bg-slate-50 px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving || loading || !form}
            onClick={() => void handleSave()}
            className="rounded-full bg-amber-600 px-5 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
