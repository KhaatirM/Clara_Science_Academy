import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchAssignmentEditForm,
  saveAssignmentEdit,
  type AssignmentEditForm,
} from '../../api/assignmentWorkspace'
import { isPdfPaperAssignmentType } from '../../utils/assignmentTypes'
import { isoToSchoolDatetimeLocal } from '../../utils/schoolTimezone'

/** Same options as create PDF/paper (+ Classwork for older records). */
const CATEGORIES = [
  '',
  'Homework',
  'Tests',
  'Quizzes',
  'Projects',
  'Labs',
  'Classwork',
  'Participation',
  'Extra Credit',
  'Other',
]
const STATUSES = ['Active', 'Inactive', 'Upcoming', 'Voided']

function normalizeQuarter(raw: string | null | undefined): string {
  const q = String(raw || '1').trim().toUpperCase()
  if (q === 'Q1' || q === '1') return '1'
  if (q === 'Q2' || q === '2') return '2'
  if (q === 'Q3' || q === '3') return '3'
  if (q === 'Q4' || q === '4') return '4'
  return '1'
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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [form, setForm] = useState<AssignmentEditForm | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newFiles, setNewFiles] = useState<File[]>([])
  const [removeIds, setRemoveIds] = useState<number[]>([])
  const [clearGroupAttachment, setClearGroupAttachment] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAssignmentEditForm(assignmentId, isGroup, 'management')
      const category = data.assignment_category || ''
      setForm({
        ...data,
        title: data.title || '',
        description: data.description || '',
        due_date: isoToSchoolDatetimeLocal(data.due_date) || '',
        open_date: isoToSchoolDatetimeLocal(data.open_date) || '',
        close_date: isoToSchoolDatetimeLocal(data.close_date) || '',
        quarter: normalizeQuarter(data.quarter),
        status: data.status || 'Active',
        assignment_context: data.assignment_context || 'homework',
        assignment_category: CATEGORIES.includes(category) ? category : category,
        category_weight: data.category_weight ?? 0,
        total_points: data.total_points ?? 100,
        allow_extra_credit: Boolean(data.allow_extra_credit),
        max_extra_credit_points: data.max_extra_credit_points ?? 0,
        late_penalty_enabled: Boolean(data.late_penalty_enabled),
        late_penalty_per_day: data.late_penalty_per_day ?? 0,
        late_penalty_max_days: data.late_penalty_max_days ?? 0,
        status_override_until: isoToSchoolDatetimeLocal(data.status_override_until) || '',
        attachments: data.attachments || [],
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
  const isPdfLike = isPdfPaperAssignmentType(form?.assignment_type)

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
    const picked = Array.from(list)
    setNewFiles((prev) => {
      const next = [...prev]
      for (const file of picked) {
        const exists = next.some(
          (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified,
        )
        if (!exists) next.push(file)
      }
      return next
    })
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
                    min="2020-01-01T00:00"
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
                  <FieldLabel htmlFor="edit-open">Open date</FieldLabel>
                  <input
                    id="edit-open"
                    type="datetime-local"
                    value={form.open_date || ''}
                    onChange={(e) => patch({ open_date: e.target.value })}
                    className={inputClass()}
                    min="2020-01-01T00:00"
                  />
                </div>
                <div>
                  <FieldLabel htmlFor="edit-close">Close date</FieldLabel>
                  <input
                    id="edit-close"
                    type="datetime-local"
                    value={form.close_date || ''}
                    onChange={(e) => patch({ close_date: e.target.value })}
                    className={inputClass()}
                    min="2020-01-01T00:00"
                  />
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
                    min={0.1}
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
                        {c || 'None (Uncategorized)'}
                      </option>
                    ))}
                    {form.assignment_category && !CATEGORIES.includes(form.assignment_category) ? (
                      <option value={form.assignment_category}>{form.assignment_category}</option>
                    ) : null}
                  </select>
                </div>
                <div>
                  <FieldLabel htmlFor="edit-category-weight">Category weight (%)</FieldLabel>
                  <input
                    id="edit-category-weight"
                    type="number"
                    min={0}
                    max={100}
                    step="0.1"
                    value={form.category_weight ?? 0}
                    onChange={(e) => patch({ category_weight: Number(e.target.value) })}
                    className={inputClass()}
                  />
                </div>
              </div>

              {isPdfLike ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Documents</p>
                  {newFiles.length > 0 ? (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50/80 p-2">
                      <p className="mb-2 text-xs font-semibold text-emerald-900">
                        Ready to attach ({newFiles.length})
                      </p>
                      <ul className="space-y-1 text-sm">
                        {newFiles.map((f, index) => (
                          <li
                            key={`${f.name}-${f.size}-${f.lastModified}`}
                            className="flex items-center gap-2 text-emerald-900"
                          >
                            <i className="bi bi-file-earmark-plus shrink-0" aria-hidden />
                            <span className="min-w-0 flex-1 truncate">{f.name}</span>
                            <button
                              type="button"
                              className="shrink-0 text-xs text-slate-600 underline"
                              onClick={() => setNewFiles((prev) => prev.filter((_, i) => i !== index))}
                            >
                              Remove
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
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
                      className="hidden"
                      accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.xls,.xlsx,.ppt,.pptx"
                      onChange={(e) => onPickFiles(e.target.files)}
                    />
                    <button
                      type="button"
                      className="inline-flex rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-50"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {isGroup ? 'Add or replace document' : 'Add documents'}
                    </button>
                    <p className="mt-1 text-xs text-hub-muted">
                      Selected files appear above. They are uploaded when you click Save changes.
                    </p>
                  </div>
                </div>
              ) : null}

              <div className="rounded-xl border border-slate-200 bg-white p-3 space-y-3">
                <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Advanced grading</p>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(form.allow_extra_credit)}
                    onChange={(e) => patch({ allow_extra_credit: e.target.checked })}
                  />
                  Allow extra credit
                </label>
                <div>
                  <FieldLabel htmlFor="edit-max-extra">Max extra credit points</FieldLabel>
                  <input
                    id="edit-max-extra"
                    type="number"
                    min={0}
                    step="0.1"
                    value={form.max_extra_credit_points ?? 0}
                    onChange={(e) => patch({ max_extra_credit_points: Number(e.target.value) })}
                    className={inputClass()}
                    disabled={!form.allow_extra_credit}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(form.late_penalty_enabled)}
                    onChange={(e) => patch({ late_penalty_enabled: e.target.checked })}
                  />
                  Enable late penalty
                </label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <FieldLabel htmlFor="edit-late-per-day">Penalty per day (%)</FieldLabel>
                    <input
                      id="edit-late-per-day"
                      type="number"
                      min={0}
                      max={100}
                      step="0.1"
                      value={form.late_penalty_per_day ?? 0}
                      onChange={(e) => patch({ late_penalty_per_day: Number(e.target.value) })}
                      className={inputClass()}
                      disabled={!form.late_penalty_enabled}
                    />
                  </div>
                  <div>
                    <FieldLabel htmlFor="edit-late-max-days">Max days (0 = unlimited)</FieldLabel>
                    <input
                      id="edit-late-max-days"
                      type="number"
                      min={0}
                      value={form.late_penalty_max_days ?? 0}
                      onChange={(e) => patch({ late_penalty_max_days: Number(e.target.value) })}
                      className={inputClass()}
                      disabled={!form.late_penalty_enabled}
                    />
                  </div>
                </div>
              </div>

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
