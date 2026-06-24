import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  AssignmentCreateHeader,
  FieldLabel,
  FormError,
  FormLoading,
  FormSection,
  inputClass,
} from '../components/assignments/AssignmentCreateLayout'
import {
  QuizQuestionsEditor,
  appendQuizQuestionsToForm,
  createEmptyQuestion,
  type QuizQuestionDraft,
} from '../components/assignments/QuizQuestionsEditor'
import { appendDatetime, appendIfChecked, postAssignmentForm } from '../api/assignmentCreateActions'
import { fetchQuizAssignmentForm, type QuizAssignmentFormMeta } from '../api/assignmentCreateForms'
import { spaRoute } from '../utils/spaRoute'

let questionCounter = 1

function nextQuestionId() {
  questionCounter += 1
  return String(questionCounter)
}

const CATEGORIES = ['', 'Homework', 'Tests', 'Quizzes', 'Projects', 'Labs', 'Participation', 'Other']

export function CreateQuizAssignmentPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const classIdParam = searchParams.get('class_id')
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [meta, setMeta] = useState<QuizAssignmentFormMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const saveActionRef = useRef<'publish' | 'draft'>('publish')

  const [title, setTitle] = useState('')
  const [selectedClassId, setSelectedClassId] = useState<number | ''>('')
  const [description, setDescription] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [quarter, setQuarter] = useState('1')
  const [assignmentContext, setAssignmentContext] = useState('homework')
  const [category, setCategory] = useState('Quizzes')
  const [categoryWeight, setCategoryWeight] = useState('0')
  const [allowExtraCredit, setAllowExtraCredit] = useState(false)
  const [maxExtraCredit, setMaxExtraCredit] = useState('0')
  const [openDate, setOpenDate] = useState('')
  const [closeDate, setCloseDate] = useState('')
  const [timeLimit, setTimeLimit] = useState('')
  const [attempts, setAttempts] = useState('1')
  const [shuffleQuestions, setShuffleQuestions] = useState(false)
  const [showCorrectAnswers, setShowCorrectAnswers] = useState(true)
  const [linkGoogleForm, setLinkGoogleForm] = useState(false)
  const [googleFormUrl, setGoogleFormUrl] = useState('')
  const [allowSaveAndContinue, setAllowSaveAndContinue] = useState(true)
  const [maxSaveAttempts, setMaxSaveAttempts] = useState('10')
  const [saveTimeoutMinutes, setSaveTimeoutMinutes] = useState('30')
  const [questions, setQuestions] = useState<QuizQuestionDraft[]>([createEmptyQuestion('1')])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchQuizAssignmentForm(classId)
      setMeta(data)
      setQuarter(data.current_quarter || '1')
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

  const submitQuiz = async (saveAction: 'publish' | 'draft') => {
    if (!meta) return
    setFormError(null)
    setSubmitting(true)
    saveActionRef.current = saveAction
    try {
      const form = new FormData()
      form.append('quiz_save_action', saveAction)
      form.append('title', title.trim())
      form.append('class_id', String(selectedClassId))
      form.append('description', description.trim())
      if (dueDate) form.append('due_date', dueDate)
      form.append('quarter', quarter)
      form.append('assignment_context', assignmentContext)
      form.append('assignment_category', category)
      form.append('category_weight', categoryWeight)
      appendIfChecked(form, 'allow_extra_credit', allowExtraCredit)
      form.append('max_extra_credit_points', maxExtraCredit)
      appendDatetime(form, 'open_date', openDate)
      appendDatetime(form, 'close_date', closeDate)
      if (timeLimit.trim()) form.append('time_limit', timeLimit)
      form.append('attempts', attempts)
      appendIfChecked(form, 'shuffle_questions', shuffleQuestions)
      appendIfChecked(form, 'show_correct_answers', showCorrectAnswers)
      appendIfChecked(form, 'link_google_form', linkGoogleForm)
      if (linkGoogleForm && googleFormUrl.trim()) form.append('google_form_url', googleFormUrl.trim())
      appendIfChecked(form, 'allow_save_and_continue', allowSaveAndContinue)
      form.append('max_save_attempts', maxSaveAttempts)
      form.append('save_timeout_minutes', saveTimeoutMinutes)

      if (!linkGoogleForm) {
        appendQuizQuestionsToForm(form, questions.filter((q) => q.questionText.trim()))
      }

      const result = await postAssignmentForm(meta.post_url, form)
      if (result.redirect_url) {
        const path = spaRoute(result.redirect_url)
        if (path.startsWith('/management/assignment')) {
          window.location.assign(result.redirect_url)
        } else {
          navigate(path)
        }
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not save quiz')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <FormLoading label="Loading quiz form…" />
  if (error || !meta) return <FormError message={error || 'Could not load form'} backTo={backTo} />

  return (
    <div className="mx-auto max-w-[1100px] px-1 pb-10">
      <AssignmentCreateHeader
        title="Create Quiz Assignment"
        subtitle="Build auto-graded quizzes with multiple question types"
        icon="bi-ui-checks-grid"
        backTo={backTo}
        backLabel="Back to types"
        badge={classBadge}
      />

      <form
        onSubmit={(e) => {
          e.preventDefault()
          void submitQuiz(saveActionRef.current)
        }}
        className="space-y-5"
      >
        <FormSection title="Quiz Information" icon="bi-info-circle" tone="purple">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="title" required>
                Quiz title
              </FieldLabel>
              <input
                id="title"
                className={inputClass('text-base')}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required={saveActionRef.current === 'publish'}
                placeholder="Enter an engaging quiz title…"
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
            <div className="sm:col-span-2">
              <FieldLabel htmlFor="description">Description</FieldLabel>
              <textarea
                id="description"
                className={inputClass()}
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What this quiz covers and any special instructions…"
              />
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
                min="2020-01-01T00:00"
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
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold">
                <input
                  type="checkbox"
                  checked={allowExtraCredit}
                  onChange={(e) => setAllowExtraCredit(e.target.checked)}
                  className="rounded border-slate-300"
                />
                Allow extra credit
              </label>
            </div>
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
              />
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
          </div>
        </FormSection>

        <FormSection title="Quiz Configuration" icon="bi-gear" tone="emerald">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <FieldLabel htmlFor="time_limit">Time limit (minutes)</FieldLabel>
              <input
                id="time_limit"
                type="number"
                min="1"
                max="300"
                className={inputClass()}
                value={timeLimit}
                onChange={(e) => setTimeLimit(e.target.value)}
                placeholder="No limit"
              />
            </div>
            <div>
              <FieldLabel htmlFor="attempts">Max attempts</FieldLabel>
              <input
                id="attempts"
                type="number"
                min="1"
                max="10"
                className={inputClass()}
                value={attempts}
                onChange={(e) => setAttempts(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={shuffleQuestions}
                onChange={(e) => setShuffleQuestions(e.target.checked)}
                className="rounded border-slate-300"
              />
              Shuffle questions
            </label>
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={showCorrectAnswers}
                onChange={(e) => setShowCorrectAnswers(e.target.checked)}
                className="rounded border-slate-300"
              />
              Show correct answers after submission
            </label>
          </div>
          <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={linkGoogleForm}
                onChange={(e) => setLinkGoogleForm(e.target.checked)}
                className="rounded border-slate-300"
              />
              Link to Google Form instead of native questions
            </label>
            {linkGoogleForm ? (
              <div className="mt-3">
                <FieldLabel htmlFor="google_form_url">Google Form URL</FieldLabel>
                <input
                  id="google_form_url"
                  type="url"
                  className={inputClass()}
                  value={googleFormUrl}
                  onChange={(e) => setGoogleFormUrl(e.target.value)}
                  placeholder="https://docs.google.com/forms/d/e/…"
                />
              </div>
            ) : null}
          </div>
          <div className="mt-4 border-t border-slate-200 pt-4">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={allowSaveAndContinue}
                onChange={(e) => setAllowSaveAndContinue(e.target.checked)}
                className="rounded border-slate-300"
              />
              Allow save and continue
            </label>
            {allowSaveAndContinue ? (
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                <div>
                  <FieldLabel htmlFor="max_save_attempts">Max save attempts</FieldLabel>
                  <input
                    id="max_save_attempts"
                    type="number"
                    min="1"
                    className={inputClass()}
                    value={maxSaveAttempts}
                    onChange={(e) => setMaxSaveAttempts(e.target.value)}
                  />
                </div>
                <div>
                  <FieldLabel htmlFor="save_timeout_minutes">Save timeout (minutes)</FieldLabel>
                  <input
                    id="save_timeout_minutes"
                    type="number"
                    min="1"
                    className={inputClass()}
                    value={saveTimeoutMinutes}
                    onChange={(e) => setSaveTimeoutMinutes(e.target.value)}
                  />
                </div>
              </div>
            ) : null}
          </div>
        </FormSection>

        {!linkGoogleForm ? (
          <FormSection title="Questions" icon="bi-list-check">
            <QuizQuestionsEditor
              questions={questions}
              onChange={setQuestions}
              onAdd={() => setQuestions((prev) => [...prev, createEmptyQuestion(nextQuestionId())])}
              onRemove={(id) => setQuestions((prev) => prev.filter((q) => q.id !== id))}
            />
          </FormSection>
        ) : null}

        {formError ? <p className="text-sm font-semibold text-red-700">{formError}</p> : null}

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={submitting}
            onClick={() => void submitQuiz('publish')}
            className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-3 text-sm font-bold text-white shadow-md hover:from-emerald-600 hover:to-teal-700 disabled:opacity-60"
          >
            {submitting && saveActionRef.current === 'publish' ? 'Publishing…' : 'Publish quiz'}
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => void submitQuiz('draft')}
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {submitting && saveActionRef.current === 'draft' ? 'Saving…' : 'Save draft'}
          </button>
          <Link to={backTo} className="rounded-xl px-5 py-3 text-sm font-semibold text-slate-500 hover:text-slate-700">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  )
}
