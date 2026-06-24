import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  AssignmentCreateHeader,
  FieldLabel,
  FormError,
  FormLoading,
  FormSection,
  inputClass,
} from '../components/assignments/AssignmentCreateLayout'
import { appendDatetime, appendIfChecked, postAssignmentForm } from '../api/assignmentCreateActions'
import { fetchPdfAssignmentForm, type PdfAssignmentFormMeta } from '../api/assignmentCreateForms'
import { spaRoute } from '../utils/spaRoute'

const CATEGORIES = ['', 'Homework', 'Tests', 'Quizzes', 'Projects', 'Labs', 'Participation', 'Other']

export function CreatePdfAssignmentPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const contextParam = searchParams.get('context') === 'in-class' ? 'in-class' : 'homework'
  const classIdParam = searchParams.get('class_id')
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [meta, setMeta] = useState<PdfAssignmentFormMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [classIds, setClassIds] = useState<number[]>([])
  const [dueDate, setDueDate] = useState('')
  const [quarter, setQuarter] = useState('')
  const [openDate, setOpenDate] = useState('')
  const [closeDate, setCloseDate] = useState('')
  const [status, setStatus] = useState('Active')
  const [assignmentContext, setAssignmentContext] = useState<'homework' | 'in-class'>(contextParam)
  const [totalPoints, setTotalPoints] = useState('100')
  const [category, setCategory] = useState('')
  const [categoryWeight, setCategoryWeight] = useState('0')
  const [allowExtraCredit, setAllowExtraCredit] = useState(false)
  const [maxExtraCredit, setMaxExtraCredit] = useState('0')
  const [latePenaltyEnabled, setLatePenaltyEnabled] = useState(false)
  const [latePenaltyPerDay, setLatePenaltyPerDay] = useState('0')
  const [latePenaltyMaxDays, setLatePenaltyMaxDays] = useState('0')
  const [files, setFiles] = useState<File[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPdfAssignmentForm(contextParam, classId)
      setMeta(data)
      setQuarter(data.current_quarter || '1')
      setAssignmentContext(data.context)
      if (data.preselected_class) {
        setClassIds([data.preselected_class.id])
      }
      if (data.default_due_date) {
        setDueDate(data.default_due_date)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load form')
    } finally {
      setLoading(false)
    }
  }, [classId, contextParam])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!meta) return
    if (assignmentContext === 'in-class' && meta.in_class_due_date) {
      setDueDate(meta.in_class_due_date)
    }
  }, [assignmentContext, meta])

  const lockedClass = Boolean(meta?.preselected_class)
  const backTo = spaRoute(meta?.type_selector_url || '/management/assignments/create')
  const classBadge = meta?.preselected_class
    ? `${meta.preselected_class.name}${meta.preselected_class.subject ? ` · ${meta.preselected_class.subject}` : ''}`
    : null

  const previewHtml = useMemo(() => {
    const cls =
      meta?.preselected_class?.name ||
      meta?.classes
        .filter((c) => classIds.includes(c.id))
        .map((c) => c.name)
        .join(', ') ||
      '—'
    return (
      <div className="space-y-2 text-sm">
        <p className="font-bold text-slate-800">{title || 'Untitled assignment'}</p>
        <p className="whitespace-pre-wrap text-slate-600">{description || 'No description yet.'}</p>
        <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-xs text-slate-500">
          <dt>Class</dt>
          <dd>{cls}</dd>
          <dt>Due</dt>
          <dd>{dueDate ? dueDate.replace('T', ' ') : '—'}</dd>
          <dt>Points</dt>
          <dd>{totalPoints}</dd>
          <dt>Context</dt>
          <dd>{assignmentContext === 'in-class' ? 'In-class' : 'Homework'}</dd>
          {files.length > 0 ? (
            <>
              <dt>Files</dt>
              <dd>{files.length} attached</dd>
            </>
          ) : null}
        </dl>
      </div>
    )
  }, [assignmentContext, classIds, description, dueDate, files.length, meta, title, totalPoints])

  const toggleClass = (id: number) => {
    setClassIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const onFileChange = (list: FileList | null) => {
    if (!list) return
    setFiles(Array.from(list))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!meta) return
    setFormError(null)
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('title', title.trim())
      form.append('description', description.trim())
      if (lockedClass && meta.preselected_class) {
        form.append('class_id', String(meta.preselected_class.id))
      } else {
        classIds.forEach((id) => form.append('class_ids', String(id)))
      }
      form.append('due_date', dueDate)
      form.append('quarter', quarter)
      appendDatetime(form, 'open_date', openDate)
      appendDatetime(form, 'close_date', closeDate)
      form.append('status', status)
      form.append('assignment_context', assignmentContext)
      form.append('total_points', totalPoints)
      form.append('assignment_category', category)
      form.append('category_weight', categoryWeight)
      appendIfChecked(form, 'allow_extra_credit', allowExtraCredit)
      form.append('max_extra_credit_points', maxExtraCredit)
      appendIfChecked(form, 'late_penalty_enabled', latePenaltyEnabled)
      form.append('late_penalty_per_day', latePenaltyPerDay)
      form.append('late_penalty_max_days', latePenaltyMaxDays)
      files.forEach((file) => form.append('assignment_files', file))

      const result = await postAssignmentForm(meta.post_url, form)
      if (result.redirect_url) {
        navigate(spaRoute(result.redirect_url))
      } else if (meta.back_url) {
        navigate(spaRoute(meta.back_url))
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not create assignment')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <FormLoading label="Loading PDF assignment form…" />
  if (error || !meta) return <FormError message={error || 'Could not load form'} backTo={backTo} />

  return (
    <div className="mx-auto max-w-[1280px] px-1 pb-10">
      <AssignmentCreateHeader
        title="Create PDF/Paper Assignment"
        subtitle="Upload documents and set due dates for student file submissions"
        icon="bi-file-earmark-text"
        backTo={backTo}
        backLabel="Back to types"
        badge={classBadge}
      />

      <form onSubmit={(e) => void handleSubmit(e)} className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <FormSection title="Assignment Information" icon="bi-info-circle">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <FieldLabel htmlFor="title" required>
                  Assignment title
                </FieldLabel>
                <input
                  id="title"
                  className={inputClass()}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder="Enter a clear, descriptive title…"
                />
              </div>
              <div className="sm:col-span-2">
                <FieldLabel htmlFor="description" required>
                  Description
                </FieldLabel>
                <textarea
                  id="description"
                  className={inputClass()}
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  placeholder="Instructions, objectives, and requirements…"
                />
              </div>
              <div>
                <FieldLabel required>{lockedClass ? 'Class' : 'Classes'}</FieldLabel>
                {lockedClass && meta.preselected_class ? (
                  <select className={inputClass()} disabled value={meta.preselected_class.id}>
                    <option value={meta.preselected_class.id}>
                      {meta.preselected_class.name}
                      {meta.preselected_class.subject ? ` – ${meta.preselected_class.subject}` : ''}
                    </option>
                  </select>
                ) : (
                  <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-slate-200 p-3">
                    {meta.classes.map((c) => (
                      <label key={c.id} className="flex cursor-pointer items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={classIds.includes(c.id)}
                          onChange={() => toggleClass(c.id)}
                          className="rounded border-slate-300"
                        />
                        <span>
                          {c.name}
                          {c.subject ? ` – ${c.subject}` : ''}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <FieldLabel htmlFor="due_date" required>
                  Due date
                </FieldLabel>
                <input
                  id="due_date"
                  type="datetime-local"
                  className={inputClass()}
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  required
                  min="2020-01-01T00:00"
                />
              </div>
              <div>
                <FieldLabel htmlFor="quarter" required>
                  Quarter
                </FieldLabel>
                <select
                  id="quarter"
                  className={inputClass()}
                  value={quarter}
                  onChange={(e) => setQuarter(e.target.value)}
                  required
                >
                  <option value="1">Quarter 1</option>
                  <option value="2">Quarter 2</option>
                  <option value="3">Quarter 3</option>
                  <option value="4">Quarter 4</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="open_date">Open date</FieldLabel>
                <input
                  id="open_date"
                  type="datetime-local"
                  className={inputClass()}
                  value={openDate}
                  onChange={(e) => setOpenDate(e.target.value)}
                  min="2020-01-01T00:00"
                />
              </div>
              <div>
                <FieldLabel htmlFor="close_date">Close date</FieldLabel>
                <input
                  id="close_date"
                  type="datetime-local"
                  className={inputClass()}
                  value={closeDate}
                  onChange={(e) => setCloseDate(e.target.value)}
                  min="2020-01-01T00:00"
                />
              </div>
              <div>
                <FieldLabel htmlFor="status" required>
                  Status
                </FieldLabel>
                <select id="status" className={inputClass()} value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                  <option value="Voided">Voided</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="assignment_context" required>
                  Context
                </FieldLabel>
                <select
                  id="assignment_context"
                  className={inputClass()}
                  value={assignmentContext}
                  onChange={(e) => setAssignmentContext(e.target.value as 'homework' | 'in-class')}
                >
                  <option value="homework">Homework</option>
                  <option value="in-class">In-class</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="total_points" required>
                  Total points
                </FieldLabel>
                <input
                  id="total_points"
                  type="number"
                  min="0.1"
                  step="0.1"
                  className={inputClass()}
                  value={totalPoints}
                  onChange={(e) => setTotalPoints(e.target.value)}
                  required
                />
              </div>
              <div>
                <FieldLabel htmlFor="assignment_category">Category</FieldLabel>
                <select
                  id="assignment_category"
                  className={inputClass()}
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c || 'none'} value={c}>
                      {c || 'None (Uncategorized)'}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="category_weight">Category weight (%)</FieldLabel>
                <input
                  id="category_weight"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  className={inputClass()}
                  value={categoryWeight}
                  onChange={(e) => setCategoryWeight(e.target.value)}
                />
              </div>
            </div>
          </FormSection>

          <FormSection title="Assignment Files" icon="bi-cloud-upload" tone="success">
            <div
              className="cursor-pointer rounded-xl border-2 border-dashed border-emerald-300 bg-emerald-50/50 p-6 text-center"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                onFileChange(e.dataTransfer.files)
              }}
            >
              <i className="bi bi-cloud-upload mb-2 block text-3xl text-emerald-600" aria-hidden />
              <p className="font-semibold text-slate-700">Click or drag files here</p>
              <p className="mt-1 text-xs text-slate-500">PDF, Word, images, and more — up to 16 MB each</p>
              <input
                type="file"
                multiple
                className="mt-3 text-sm"
                accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.xls,.xlsx,.ppt,.pptx"
                onChange={(e) => onFileChange(e.target.files)}
              />
            </div>
            {files.length > 0 ? (
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                {files.map((f) => (
                  <li key={`${f.name}-${f.size}`} className="flex items-center gap-2">
                    <i className="bi bi-file-earmark text-emerald-600" aria-hidden />
                    {f.name}
                  </li>
                ))}
              </ul>
            ) : null}
          </FormSection>

          {formError ? <p className="text-sm font-semibold text-red-700">{formError}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-bold text-white shadow-md hover:from-indigo-700 hover:to-violet-700 disabled:opacity-60 lg:hidden"
          >
            {submitting ? 'Creating…' : 'Create assignment'}
          </button>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-cyan-600 px-4 py-2 text-sm font-bold text-white">
              <i className="bi bi-eye me-2" aria-hidden />
              Live preview
            </div>
            <div className="p-4">{previewHtml}</div>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-slate-600 px-4 py-2 text-sm font-bold text-white">
              <i className="bi bi-lightbulb me-2" aria-hidden />
              Tips
            </div>
            <ul className="space-y-3 p-4 text-xs text-slate-600">
              <li>Write step-by-step instructions so students know exactly what to submit.</li>
              <li>In-class assignments default due today at 4:00 PM Eastern.</li>
              <li>Attach rubrics or exemplars when helpful.</li>
            </ul>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-cyan-600 px-4 py-2 text-sm font-bold text-white">
              <i className="bi bi-gear me-2" aria-hidden />
              Advanced grading
            </div>
            <div className="space-y-4 p-4">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={allowExtraCredit}
                  onChange={(e) => setAllowExtraCredit(e.target.checked)}
                  className="rounded border-slate-300"
                />
                Allow extra credit
              </label>
              <div>
                <FieldLabel htmlFor="max_extra_credit">Max extra credit points</FieldLabel>
                <input
                  id="max_extra_credit"
                  type="number"
                  min="0"
                  step="0.1"
                  className={inputClass()}
                  value={maxExtraCredit}
                  onChange={(e) => setMaxExtraCredit(e.target.value)}
                  disabled={!allowExtraCredit}
                />
              </div>
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={latePenaltyEnabled}
                  onChange={(e) => setLatePenaltyEnabled(e.target.checked)}
                  className="rounded border-slate-300"
                />
                Enable late penalty
              </label>
              <div className="space-y-3">
                <div>
                  <FieldLabel htmlFor="late_penalty_per_day">Penalty per day (%)</FieldLabel>
                  <input
                    id="late_penalty_per_day"
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    className={inputClass()}
                    value={latePenaltyPerDay}
                    onChange={(e) => setLatePenaltyPerDay(e.target.value)}
                    disabled={!latePenaltyEnabled}
                  />
                </div>
                <div>
                  <FieldLabel htmlFor="late_penalty_max_days">Max days (0 = unlimited)</FieldLabel>
                  <input
                    id="late_penalty_max_days"
                    type="number"
                    min="0"
                    className={inputClass()}
                    value={latePenaltyMaxDays}
                    onChange={(e) => setLatePenaltyMaxDays(e.target.value)}
                    disabled={!latePenaltyEnabled}
                  />
                </div>
              </div>
            </div>
          </div>
          <div className="hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:block">
            <button
              type="submit"
              disabled={submitting}
              className="mb-3 w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-bold text-white shadow-md hover:from-indigo-700 hover:to-violet-700 disabled:opacity-60"
            >
              {submitting ? 'Creating…' : 'Create assignment'}
            </button>
            <Link to={backTo} className="block text-center text-sm font-semibold text-slate-500 hover:text-slate-700">
              Cancel
            </Link>
          </div>
        </aside>
      </form>
    </div>
  )
}
