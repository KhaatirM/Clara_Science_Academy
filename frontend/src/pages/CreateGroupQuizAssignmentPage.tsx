import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
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
  appendGroupQuizQuestionsToForm,
  createEmptyQuestion,
  type QuizQuestionDraft,
} from '../components/assignments/QuizQuestionsEditor'
import { appendIfChecked, postAssignmentForm } from '../api/assignmentCreateActions'
import {
  fetchClassGroups,
  fetchGroupQuizForm,
  type ClassGroupBrief,
  type GroupQuizFormMeta,
} from '../api/groupCreateForms'
import { spaRoute } from '../utils/spaRoute'

let questionCounter = 1
function nextQuestionId() {
  questionCounter += 1
  return String(questionCounter)
}

function quarterOptionValue(q: string): string {
  if (q === '1') return 'Q1'
  if (q === '2') return 'Q2'
  if (q === '3') return 'Q3'
  if (q === '4') return 'Q4'
  if (q.startsWith('Q')) return q
  return 'Q1'
}

export function CreateGroupQuizAssignmentPage() {
  const navigate = useNavigate()
  const { classId: classIdParam } = useParams()
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [meta, setMeta] = useState<GroupQuizFormMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [groups, setGroups] = useState<ClassGroupBrief[]>([])
  const [groupsLoading, setGroupsLoading] = useState(false)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [timeLimit, setTimeLimit] = useState('30')
  const [passingScore, setPassingScore] = useState('70')
  const [shuffleQuestions, setShuffleQuestions] = useState(false)
  const [showCorrectAnswers, setShowCorrectAnswers] = useState(false)
  const [allowSaveAndContinue, setAllowSaveAndContinue] = useState(true)
  const [groupSizeMin, setGroupSizeMin] = useState('2')
  const [groupSizeMax, setGroupSizeMax] = useState('')
  const [groupSelection, setGroupSelection] = useState<'all' | 'specific'>('all')
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([])
  const [dueDate, setDueDate] = useState('')
  const [quarter, setQuarter] = useState('Q1')
  const [semester, setSemester] = useState('')
  const [academicPeriodId, setAcademicPeriodId] = useState('')
  const [questions, setQuestions] = useState<QuizQuestionDraft[]>([createEmptyQuestion('1')])

  const load = useCallback(async () => {
    if (!classId) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGroupQuizForm(classId)
      setMeta(data)
      setQuarter(quarterOptionValue(data.current_quarter || '1'))
      setAllowSaveAndContinue(data.defaults.allow_save_and_continue)
      setTimeLimit(String(data.defaults.time_limit_minutes))
      setPassingScore(String(data.defaults.passing_score))
      setGroupSizeMin(String(data.defaults.group_size_min))
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)
      tomorrow.setHours(23, 59, 0, 0)
      setDueDate(tomorrow.toISOString().slice(0, 16))
      setGroupsLoading(true)
      try {
        setGroups(await fetchClassGroups(data.groups_api_url))
      } finally {
        setGroupsLoading(false)
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

  const backTo = spaRoute(meta?.back_url || `/management/assignments/create/group/${classId ?? ''}`)
  const classBadge = meta?.class
    ? `${meta.class.name}${meta.class.subject ? ` · ${meta.class.subject}` : ''}`
    : null

  const questionStats = useMemo(() => {
    const valid = questions.filter((q) => q.questionText.trim())
    const points = valid.reduce((sum, q) => sum + (parseFloat(q.points) || 0), 0)
    return { count: valid.length, points }
  }, [questions])

  const toggleGroup = (id: number) => {
    setSelectedGroupIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!meta || !classId) return
    const validQuestions = questions.filter((q) => q.questionText.trim())
    if (validQuestions.length === 0) {
      setFormError('Add at least one question before creating the group quiz.')
      return
    }
    setFormError(null)
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('title', title.trim())
      form.append('description', description.trim())
      form.append('due_date', dueDate)
      form.append('quarter', quarter)
      if (semester) form.append('semester', semester)
      if (academicPeriodId) form.append('academic_period_id', academicPeriodId)
      form.append('time_limit', timeLimit || '0')
      form.append('passing_score', passingScore)
      appendIfChecked(form, 'shuffle_questions', shuffleQuestions)
      appendIfChecked(form, 'show_correct_answers', showCorrectAnswers)
      appendIfChecked(form, 'allow_save_and_continue', allowSaveAndContinue)
      form.append('group_size_min', groupSizeMin)
      if (groupSizeMax.trim()) form.append('group_size_max', groupSizeMax)
      form.append('collaboration_type', 'group')
      form.append('group_selection', groupSelection)
      if (groupSelection === 'specific') {
        selectedGroupIds.forEach((id) => form.append('selected_groups', String(id)))
      }
      appendGroupQuizQuestionsToForm(form, validQuestions)

      const result = await postAssignmentForm(meta.post_url, form)
      if (result.redirect_url) {
        navigate(spaRoute(result.redirect_url))
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not create group quiz')
    } finally {
      setSubmitting(false)
    }
  }

  if (!classId) {
    return <FormError message="Invalid class" backTo="/management/assignments/create/group" />
  }
  if (loading) return <FormLoading label="Loading group quiz form…" />
  if (error || !meta) return <FormError message={error || 'Could not load form'} backTo={backTo} />

  return (
    <div className="mx-auto max-w-[1280px] px-1 pb-10">
      <AssignmentCreateHeader
        title="Create Group Quiz"
        subtitle="One shared quiz per team — students collaborate on answers and any member can submit"
        icon="bi-ui-checks-grid"
        backTo={backTo}
        backLabel="Back to group types"
        badge={classBadge}
      />

      <form onSubmit={(e) => void handleSubmit(e)} className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-5">
          <FormSection title="Quiz Information" icon="bi-info-circle" tone="purple">
            <div className="space-y-4">
              <div>
                <FieldLabel htmlFor="title" required>
                  Quiz title
                </FieldLabel>
                <input
                  id="title"
                  className={inputClass('text-base')}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>
              <div>
                <FieldLabel htmlFor="description">Description & instructions</FieldLabel>
                <textarea
                  id="description"
                  className={inputClass()}
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Explain that the group shares one quiz attempt and can save progress together…"
                />
              </div>
            </div>
          </FormSection>

          <FormSection title="Collaborative Quiz Settings" icon="bi-gear" tone="emerald">
            <p className="mb-4 text-sm text-slate-600">
              Groups work on one shared attempt. Enable save & continue so teams can return and pick up where they left off.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="time_limit">Time limit (minutes, 0 = none)</FieldLabel>
                <input
                  id="time_limit"
                  type="number"
                  min="0"
                  max="300"
                  className={inputClass()}
                  value={timeLimit}
                  onChange={(e) => setTimeLimit(e.target.value)}
                />
              </div>
              <div>
                <FieldLabel htmlFor="passing_score">Passing score (%)</FieldLabel>
                <input
                  id="passing_score"
                  type="number"
                  min="0"
                  max="100"
                  className={inputClass()}
                  value={passingScore}
                  onChange={(e) => setPassingScore(e.target.value)}
                />
              </div>
            </div>
            <div className="mt-4 space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold">
                <input
                  type="checkbox"
                  checked={allowSaveAndContinue}
                  onChange={(e) => setAllowSaveAndContinue(e.target.checked)}
                  className="rounded border-slate-300"
                />
                Allow save & continue (recommended for group quizzes)
              </label>
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
                Show correct answers after submit
              </label>
            </div>
          </FormSection>

          <FormSection title="Group Settings" icon="bi-people" tone="warning">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="group_size_min">Min group size</FieldLabel>
                <input
                  id="group_size_min"
                  type="number"
                  min="1"
                  className={inputClass()}
                  value={groupSizeMin}
                  onChange={(e) => setGroupSizeMin(e.target.value)}
                />
              </div>
              <div>
                <FieldLabel htmlFor="group_size_max">Max group size</FieldLabel>
                <input
                  id="group_size_max"
                  type="number"
                  min="1"
                  className={inputClass()}
                  value={groupSizeMax}
                  onChange={(e) => setGroupSizeMax(e.target.value)}
                  placeholder="Unlimited"
                />
              </div>
            </div>
          </FormSection>

          <FormSection title="Target Groups" icon="bi-check2-square">
            <div className="space-y-3">
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="group_selection"
                  checked={groupSelection === 'all'}
                  onChange={() => setGroupSelection('all')}
                  className="mt-1"
                />
                <span>
                  <strong>All groups</strong>
                </span>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="group_selection"
                  checked={groupSelection === 'specific'}
                  onChange={() => setGroupSelection('specific')}
                  className="mt-1"
                />
                <span>
                  <strong>Specific groups only</strong>
                </span>
              </label>
              {groupSelection === 'specific' ? (
                <div className="rounded-lg border border-slate-200 p-3">
                  {groupsLoading ? (
                    <p className="text-sm text-slate-500">Loading groups…</p>
                  ) : groups.length === 0 ? (
                    <p className="text-sm text-slate-500">No groups in this class yet.</p>
                  ) : (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {groups.map((g) => (
                        <label
                          key={g.id}
                          className={`flex cursor-pointer items-center gap-2 rounded-lg border p-3 text-sm ${
                            selectedGroupIds.includes(g.id) ? 'border-violet-400 bg-violet-50' : 'border-slate-200'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedGroupIds.includes(g.id)}
                            onChange={() => toggleGroup(g.id)}
                          />
                          <span>
                            <strong>{g.name}</strong>
                            <span className="block text-xs text-slate-500">{g.member_count} members</span>
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </FormSection>

          <FormSection title="Schedule" icon="bi-calendar-event">
            <div className="grid gap-4 sm:grid-cols-2">
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
                <select id="quarter" className={inputClass()} value={quarter} onChange={(e) => setQuarter(e.target.value)}>
                  <option value="Q1">Quarter 1</option>
                  <option value="Q2">Quarter 2</option>
                  <option value="Q3">Quarter 3</option>
                  <option value="Q4">Quarter 4</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="semester">Semester</FieldLabel>
                <select id="semester" className={inputClass()} value={semester} onChange={(e) => setSemester(e.target.value)}>
                  <option value="">Optional</option>
                  <option value="S1">Semester 1</option>
                  <option value="S2">Semester 2</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="academic_period_id">Academic period</FieldLabel>
                <select
                  id="academic_period_id"
                  className={inputClass()}
                  value={academicPeriodId}
                  onChange={(e) => setAcademicPeriodId(e.target.value)}
                >
                  <option value="">Optional</option>
                  {meta.academic_periods.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </FormSection>

          <FormSection title="Questions" icon="bi-list-check">
            <QuizQuestionsEditor
              questions={questions}
              onChange={setQuestions}
              onAdd={() => setQuestions((prev) => [...prev, createEmptyQuestion(nextQuestionId())])}
              onRemove={(id) => setQuestions((prev) => prev.filter((q) => q.id !== id))}
            />
          </FormSection>

          {formError ? <p className="text-sm font-semibold text-red-700">{formError}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-60 lg:hidden"
          >
            {submitting ? 'Creating…' : 'Create group quiz'}
          </button>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-800">Quiz stats</h3>
            <dl className="mt-2 grid grid-cols-2 gap-2 text-center text-sm">
              <div className="rounded-lg bg-violet-50 py-2">
                <dt className="text-xs text-slate-500">Questions</dt>
                <dd className="text-xl font-bold text-violet-700">{questionStats.count}</dd>
              </div>
              <div className="rounded-lg bg-emerald-50 py-2">
                <dt className="text-xs text-slate-500">Points</dt>
                <dd className="text-xl font-bold text-emerald-700">{questionStats.points}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-800">Group quiz tips</h3>
            <ul className="mt-2 space-y-2 text-xs text-slate-600">
              <li>One submitted attempt counts for the whole group.</li>
              <li>All members see the same questions and shared answers.</li>
              <li>Leave save & continue on so teams can work across sessions.</li>
            </ul>
          </div>
          <div className="hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:block">
            <button
              type="submit"
              disabled={submitting}
              className="mb-3 w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-60"
            >
              {submitting ? 'Creating…' : 'Create group quiz'}
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
