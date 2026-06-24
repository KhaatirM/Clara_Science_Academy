import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  AssignmentCreateHeader,
  FieldLabel,
  FormError,
  FormLoading,
  FormSection,
  inputClass,
} from '../components/assignments/AssignmentCreateLayout'
import { appendIfChecked, postAssignmentForm } from '../api/assignmentCreateActions'
import { fetchDiscussionAssignmentForm, type DiscussionAssignmentFormMeta } from '../api/assignmentCreateForms'
import { spaRoute } from '../utils/spaRoute'

export function CreateDiscussionAssignmentPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const classIdParam = searchParams.get('class_id')
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [meta, setMeta] = useState<DiscussionAssignmentFormMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [selectedClassId, setSelectedClassId] = useState<number | ''>('')
  const [discussionPrompt, setDiscussionPrompt] = useState('')
  const [description, setDescription] = useState('')
  const [minInitialPosts, setMinInitialPosts] = useState('1')
  const [minReplies, setMinReplies] = useState('2')
  const [requirePeerResponse, setRequirePeerResponse] = useState(true)
  const [allowStudentThreads, setAllowStudentThreads] = useState(true)
  const [allowStudentEditPosts, setAllowStudentEditPosts] = useState(false)
  const [totalPoints, setTotalPoints] = useState('100')
  const [quarter, setQuarter] = useState('1')
  const [assignmentContext, setAssignmentContext] = useState('homework')
  const [dueDate, setDueDate] = useState('')
  const [openDate, setOpenDate] = useState('')
  const [closeDate, setCloseDate] = useState('')
  const [useRubric, setUseRubric] = useState(false)
  const [rubricCriteria, setRubricCriteria] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDiscussionAssignmentForm(classId)
      setMeta(data)
      setQuarter(data.current_quarter || '1')
      setMinInitialPosts(String(data.defaults.min_initial_posts))
      setMinReplies(String(data.defaults.min_replies))
      setTotalPoints(String(data.defaults.total_points))
      if (data.preselected_class) {
        setSelectedClassId(data.preselected_class.id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load form')
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    void load()
  }, [load])

  const backTo = spaRoute(meta?.type_selector_url || '/management/assignments/create')
  const classBadge = meta?.preselected_class
    ? `${meta.preselected_class.name}${meta.preselected_class.subject ? ` · ${meta.preselected_class.subject}` : ''}`
    : null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!meta) return
    setFormError(null)
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('title', title.trim())
      form.append('class_id', String(selectedClassId))
      form.append('discussion_prompt', discussionPrompt.trim())
      form.append('description', description.trim())
      form.append('min_initial_posts', minInitialPosts)
      form.append('min_replies', minReplies)
      appendIfChecked(form, 'require_peer_response', requirePeerResponse)
      appendIfChecked(form, 'allow_student_threads', allowStudentThreads)
      appendIfChecked(form, 'allow_student_edit_posts', allowStudentEditPosts)
      form.append('total_points', totalPoints)
      form.append('quarter', quarter)
      form.append('assignment_context', assignmentContext)
      form.append('due_date', dueDate)
      form.append('open_date', openDate)
      form.append('close_date', closeDate)
      appendIfChecked(form, 'use_rubric', useRubric)
      if (useRubric) form.append('rubric_criteria', rubricCriteria.trim())

      const result = await postAssignmentForm(meta.post_url, form)
      if (result.redirect_url) {
        navigate(spaRoute(result.redirect_url))
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not create discussion')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <FormLoading label="Loading discussion form…" />
  if (error || !meta) return <FormError message={error || 'Could not load form'} backTo={backTo} />

  return (
    <div className="mx-auto max-w-[1100px] px-1 pb-10">
      <AssignmentCreateHeader
        title="Create Discussion Assignment"
        subtitle="Foster critical thinking through structured academic discussions"
        icon="bi-chat-dots"
        backTo={backTo}
        backLabel="Back to types"
        badge={classBadge}
      />

      <form onSubmit={(e) => void handleSubmit(e)} className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-5">
          <FormSection title="Discussion Topic & Instructions" icon="bi-chat-quote" tone="info">
            <div className="space-y-4">
              <div>
                <FieldLabel htmlFor="title" required>
                  Assignment title
                </FieldLabel>
                <input
                  id="title"
                  className={inputClass('text-base')}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder="e.g., Climate Change: Causes and Solutions"
                />
              </div>
              <div>
                <FieldLabel htmlFor="class_id" required>
                  Class
                </FieldLabel>
                <select
                  id="class_id"
                  className={inputClass('text-base')}
                  value={selectedClassId}
                  onChange={(e) => setSelectedClassId(e.target.value ? Number(e.target.value) : '')}
                  required
                  disabled={Boolean(meta.preselected_class)}
                >
                  <option value="">Choose a class…</option>
                  {meta.classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                      {c.subject ? ` – ${c.subject}` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="discussion_prompt" required>
                  Discussion prompt
                </FieldLabel>
                <textarea
                  id="discussion_prompt"
                  className={inputClass()}
                  rows={4}
                  value={discussionPrompt}
                  onChange={(e) => setDiscussionPrompt(e.target.value)}
                  required
                  placeholder="Enter the main question or topic for discussion…"
                />
              </div>
              <div>
                <FieldLabel htmlFor="description">Instructions & guidelines</FieldLabel>
                <textarea
                  id="description"
                  className={inputClass()}
                  rows={5}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Expectations for quality, length, citations…"
                />
              </div>
            </div>
          </FormSection>

          <FormSection title="Participation Requirements" icon="bi-people">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="min_initial_posts" required>
                  Minimum initial posts
                </FieldLabel>
                <input
                  id="min_initial_posts"
                  type="number"
                  min="1"
                  max="10"
                  className={inputClass()}
                  value={minInitialPosts}
                  onChange={(e) => setMinInitialPosts(e.target.value)}
                  required
                />
              </div>
              <div>
                <FieldLabel htmlFor="min_replies" required>
                  Minimum replies
                </FieldLabel>
                <input
                  id="min_replies"
                  type="number"
                  min="0"
                  max="20"
                  className={inputClass()}
                  value={minReplies}
                  onChange={(e) => setMinReplies(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={requirePeerResponse}
                  onChange={(e) => setRequirePeerResponse(e.target.checked)}
                  className="mt-1 rounded border-slate-300"
                />
                <span>
                  <strong>Require students to respond to peer posts</strong>
                  <span className="block text-xs text-slate-500">Students must reply to classmates</span>
                </span>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={allowStudentThreads}
                  onChange={(e) => setAllowStudentThreads(e.target.checked)}
                  className="mt-1 rounded border-slate-300"
                />
                <span>
                  <strong>Allow students to create new discussion threads</strong>
                </span>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={allowStudentEditPosts}
                  onChange={(e) => setAllowStudentEditPosts(e.target.checked)}
                  className="mt-1 rounded border-slate-300"
                />
                <span>
                  <strong>Allow students to edit their posts</strong>
                </span>
              </label>
            </div>
          </FormSection>

          <FormSection title="Assignment Settings" icon="bi-gear" tone="success">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="total_points" required>
                  Total points
                </FieldLabel>
                <input
                  id="total_points"
                  type="number"
                  min="1"
                  step="0.1"
                  className={inputClass()}
                  value={totalPoints}
                  onChange={(e) => setTotalPoints(e.target.value)}
                  required
                />
              </div>
              <div>
                <FieldLabel htmlFor="quarter" required>
                  Quarter
                </FieldLabel>
                <select id="quarter" className={inputClass()} value={quarter} onChange={(e) => setQuarter(e.target.value)}>
                  <option value="1">Quarter 1</option>
                  <option value="2">Quarter 2</option>
                  <option value="3">Quarter 3</option>
                  <option value="4">Quarter 4</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="assignment_context">Context</FieldLabel>
                <select
                  id="assignment_context"
                  className={inputClass()}
                  value={assignmentContext}
                  onChange={(e) => setAssignmentContext(e.target.value)}
                >
                  <option value="homework">Homework</option>
                  <option value="in-class">In-class</option>
                </select>
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
                <FieldLabel htmlFor="open_date" required>
                  Open date
                </FieldLabel>
                <input
                  id="open_date"
                  type="datetime-local"
                  className={inputClass()}
                  value={openDate}
                  onChange={(e) => setOpenDate(e.target.value)}
                  required
                  min="2020-01-01T00:00"
                />
              </div>
              <div>
                <FieldLabel htmlFor="close_date" required>
                  Close date
                </FieldLabel>
                <input
                  id="close_date"
                  type="datetime-local"
                  className={inputClass()}
                  value={closeDate}
                  onChange={(e) => setCloseDate(e.target.value)}
                  required
                  min="2020-01-01T00:00"
                />
              </div>
            </div>
          </FormSection>

          <FormSection title="Grading & Rubric (Optional)" icon="bi-clipboard-check" tone="warning">
            <label className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={useRubric}
                onChange={(e) => setUseRubric(e.target.checked)}
                className="rounded border-slate-300"
              />
              Use rubric-based grading
            </label>
            {useRubric ? (
              <div>
                <FieldLabel htmlFor="rubric_criteria">Rubric criteria</FieldLabel>
                <textarea
                  id="rubric_criteria"
                  className={inputClass()}
                  rows={6}
                  value={rubricCriteria}
                  onChange={(e) => setRubricCriteria(e.target.value)}
                  placeholder="One criterion per line with point values in parentheses…"
                />
              </div>
            ) : null}
          </FormSection>

          {formError ? <p className="text-sm font-semibold text-red-700">{formError}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-cyan-600 px-4 py-3 text-sm font-bold text-white hover:bg-cyan-700 disabled:opacity-60 lg:hidden"
          >
            {submitting ? 'Creating…' : 'Create discussion assignment'}
          </button>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-2 text-sm font-bold text-slate-800">Discussion tips</h3>
            <ul className="space-y-2 text-xs text-slate-600">
              <li>Open-ended prompts work best for deeper dialogue.</li>
              <li>Set minimum replies to encourage peer engagement.</li>
              <li>Use rubrics when grading quality, not just participation.</li>
            </ul>
          </div>
          <div className="hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:block">
            <button
              type="submit"
              disabled={submitting}
              className="mb-3 w-full rounded-xl bg-cyan-600 px-4 py-3 text-sm font-bold text-white hover:bg-cyan-700 disabled:opacity-60"
            >
              {submitting ? 'Creating…' : 'Create discussion assignment'}
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
