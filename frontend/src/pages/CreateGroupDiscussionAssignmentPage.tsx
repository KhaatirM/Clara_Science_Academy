import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AssignmentCreateHeader,
  FieldLabel,
  FormError,
  FormLoading,
  FormSection,
  inputClass,
} from '../components/assignments/AssignmentCreateLayout'
import { appendIfChecked, postAssignmentForm } from '../api/assignmentCreateActions'
import {
  fetchClassGroups,
  fetchGroupDiscussionForm,
  type ClassGroupBrief,
  type GroupDiscussionFormMeta,
} from '../api/groupCreateForms'
import { spaRoute } from '../utils/spaRoute'
import { assignmentCreateRoutePrefix, useAssignmentCreateScope } from '../utils/assignmentCreateScope'

type DiscussionPrompt = {
  key: string
  text: string
  promptType: string
  responseLength: string
}

function quarterOptionValue(q: string): string {
  if (q === '1') return 'Q1'
  if (q === '2') return 'Q2'
  if (q === '3') return 'Q3'
  if (q === '4') return 'Q4'
  if (q.startsWith('Q')) return q
  return 'Q1'
}

let promptCounter = 0
function newPrompt(): DiscussionPrompt {
  promptCounter += 1
  return { key: String(promptCounter), text: '', promptType: 'open', responseLength: 'medium' }
}

export function CreateGroupDiscussionAssignmentPage() {
  const navigate = useNavigate()
  const scope = useAssignmentCreateScope()
  const { classId: classIdParam } = useParams()
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [meta, setMeta] = useState<GroupDiscussionFormMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [groups, setGroups] = useState<ClassGroupBrief[]>([])
  const [groupsLoading, setGroupsLoading] = useState(false)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [prompts, setPrompts] = useState<DiscussionPrompt[]>([newPrompt()])
  const [minPosts, setMinPosts] = useState('2')
  const [minWords, setMinWords] = useState('100')
  const [maxPosts, setMaxPosts] = useState('10')
  const [allowReplies, setAllowReplies] = useState(true)
  const [requireCitations, setRequireCitations] = useState(false)
  const [anonymousPosts, setAnonymousPosts] = useState(false)
  const [moderatePosts, setModeratePosts] = useState(false)
  const [groupSizeMin, setGroupSizeMin] = useState('2')
  const [groupSizeMax, setGroupSizeMax] = useState('')
  const [collaborationType, setCollaborationType] = useState('group')
  const [allowIndividual, setAllowIndividual] = useState(false)
  const [groupSelection, setGroupSelection] = useState<'all' | 'specific'>('all')
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([])
  const [quarter, setQuarter] = useState('Q1')
  const [semester, setSemester] = useState('')
  const [academicPeriodId, setAcademicPeriodId] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [assignmentContext, setAssignmentContext] = useState('homework')

  const load = useCallback(async () => {
    if (!classId) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGroupDiscussionForm(classId, scope)
      setMeta(data)
      setQuarter(quarterOptionValue(data.current_quarter || '1'))
      setMinPosts(String(data.defaults.min_posts))
      setMinWords(String(data.defaults.min_words))
      setMaxPosts(String(data.defaults.max_posts))
      setGroupSizeMin(String(data.defaults.group_size_min))
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
  }, [classId, scope])

  useEffect(() => {
    void load()
  }, [load])

  const backTo = spaRoute(meta?.back_url || `${assignmentCreateRoutePrefix(scope)}/group/${classId ?? ''}`)
  const classBadge = meta?.class
    ? `${meta.class.name}${meta.class.subject ? ` · ${meta.class.subject}` : ''}`
    : null

  const toggleGroup = (id: number) => {
    setSelectedGroupIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const updatePrompt = (key: string, patch: Partial<DiscussionPrompt>) => {
    setPrompts((prev) => prev.map((p) => (p.key === key ? { ...p, ...patch } : p)))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!meta || !classId) return
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
      form.append('assignment_context', assignmentContext)
      form.append('min_posts', minPosts)
      form.append('min_words', minWords)
      form.append('max_posts', maxPosts)
      appendIfChecked(form, 'allow_replies', allowReplies)
      appendIfChecked(form, 'require_citations', requireCitations)
      appendIfChecked(form, 'anonymous_posts', anonymousPosts)
      appendIfChecked(form, 'moderate_posts', moderatePosts)
      form.append('group_size_min', groupSizeMin)
      if (groupSizeMax.trim()) form.append('group_size_max', groupSizeMax)
      form.append('collaboration_type', collaborationType)
      appendIfChecked(form, 'allow_individual', allowIndividual)
      form.append('group_selection', groupSelection)
      if (groupSelection === 'specific') {
        selectedGroupIds.forEach((gid) => form.append('selected_groups', String(gid)))
      }
      for (const p of prompts) {
        if (!p.text.trim()) continue
        form.append(`prompt_text_${p.key}`, p.text.trim())
        form.append(`prompt_type_${p.key}`, p.promptType)
        form.append(`response_length_${p.key}`, p.responseLength)
      }

      const result = await postAssignmentForm(meta.post_url, form)
      if (result.redirect_url) {
        navigate(spaRoute(result.redirect_url))
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not create group discussion')
    } finally {
      setSubmitting(false)
    }
  }

  if (!classId) {
    return <FormError message="Invalid class" backTo={`${assignmentCreateRoutePrefix(scope)}/group`} />
  }
  if (loading) return <FormLoading label="Loading group discussion form…" />
  if (error || !meta) return <FormError message={error || 'Could not load form'} backTo={backTo} />

  return (
    <div className="mx-auto max-w-[1280px] px-1 pb-10">
      <AssignmentCreateHeader
        title="Create Group Discussion Assignment"
        subtitle="Structured prompts and collaborative participation for student teams"
        icon="bi-chat-dots"
        backTo={backTo}
        backLabel="Back to group types"
        badge={classBadge}
      />

      <form onSubmit={(e) => void handleSubmit(e)} className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-5">
          <FormSection title="Discussion information" icon="bi-info-circle" tone="info">
            <div className="space-y-4">
              <div>
                <FieldLabel htmlFor="title" required>
                  Title
                </FieldLabel>
                <input
                  id="title"
                  className={inputClass('text-base')}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder="e.g., Climate change: causes and solutions"
                />
              </div>
              <div>
                <FieldLabel htmlFor="description">Description & guidelines</FieldLabel>
                <textarea
                  id="description"
                  className={inputClass()}
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Background, participation rules, and learning goals…"
                />
              </div>
            </div>
          </FormSection>

          <FormSection title="Discussion prompts" icon="bi-question-circle" tone="purple">
            <div className="space-y-3">
              {prompts.map((p, idx) => (
                <div key={p.key} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Prompt {idx + 1}
                    </span>
                    {prompts.length > 1 ? (
                      <button
                        type="button"
                        className="text-xs font-semibold text-red-700"
                        onClick={() => setPrompts((prev) => prev.filter((x) => x.key !== p.key))}
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>
                  <textarea
                    className={inputClass()}
                    rows={2}
                    value={p.text}
                    onChange={(e) => updatePrompt(p.key, { text: e.target.value })}
                    placeholder="Enter an open-ended discussion question…"
                  />
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <select
                      className={inputClass()}
                      value={p.promptType}
                      onChange={(e) => updatePrompt(p.key, { promptType: e.target.value })}
                    >
                      <option value="open">Open-ended</option>
                      <option value="debate">Debate</option>
                      <option value="analysis">Analysis</option>
                    </select>
                    <select
                      className={inputClass()}
                      value={p.responseLength}
                      onChange={(e) => updatePrompt(p.key, { responseLength: e.target.value })}
                    >
                      <option value="short">Short response</option>
                      <option value="medium">Medium response</option>
                      <option value="long">Long response</option>
                    </select>
                  </div>
                </div>
              ))}
              <button
                type="button"
                onClick={() => setPrompts((prev) => [...prev, newPrompt()])}
                className="rounded-full border border-teal-300 px-3 py-1.5 text-sm font-semibold text-teal-800 hover:bg-teal-50"
              >
                <i className="bi bi-plus-circle me-1" aria-hidden />
                Add prompt
              </button>
            </div>
          </FormSection>

          <FormSection title="Participation requirements" icon="bi-chat-square-text" tone="success">
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <FieldLabel htmlFor="min_posts">Minimum posts (per group)</FieldLabel>
                <input
                  id="min_posts"
                  type="number"
                  min={1}
                  className={inputClass()}
                  value={minPosts}
                  onChange={(e) => setMinPosts(e.target.value)}
                />
              </div>
              <div>
                <FieldLabel htmlFor="min_words">Minimum words (per post)</FieldLabel>
                <input
                  id="min_words"
                  type="number"
                  min={10}
                  className={inputClass()}
                  value={minWords}
                  onChange={(e) => setMinWords(e.target.value)}
                />
              </div>
              <div>
                <FieldLabel htmlFor="max_posts">Maximum posts</FieldLabel>
                <input
                  id="max_posts"
                  type="number"
                  min={1}
                  className={inputClass()}
                  value={maxPosts}
                  onChange={(e) => setMaxPosts(e.target.value)}
                />
              </div>
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={allowReplies} onChange={(e) => setAllowReplies(e.target.checked)} />
                Allow group replies
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={requireCitations}
                  onChange={(e) => setRequireCitations(e.target.checked)}
                />
                Require citations
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={anonymousPosts}
                  onChange={(e) => setAnonymousPosts(e.target.checked)}
                />
                Allow anonymous posts
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={moderatePosts} onChange={(e) => setModeratePosts(e.target.checked)} />
                Moderate posts before publishing
              </label>
            </div>
          </FormSection>

          <FormSection title="Group settings" icon="bi-people" tone="warning">
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <FieldLabel htmlFor="group_size_min">Minimum group size</FieldLabel>
                <input
                  id="group_size_min"
                  type="number"
                  min={1}
                  className={inputClass()}
                  value={groupSizeMin}
                  onChange={(e) => setGroupSizeMin(e.target.value)}
                />
              </div>
              <div>
                <FieldLabel htmlFor="group_size_max">Maximum group size</FieldLabel>
                <input
                  id="group_size_max"
                  type="number"
                  min={2}
                  placeholder="Unlimited"
                  className={inputClass()}
                  value={groupSizeMax}
                  onChange={(e) => setGroupSizeMax(e.target.value)}
                />
              </div>
              <div>
                <FieldLabel htmlFor="collaboration_type">Collaboration</FieldLabel>
                <select
                  id="collaboration_type"
                  className={inputClass()}
                  value={collaborationType}
                  onChange={(e) => setCollaborationType(e.target.value)}
                >
                  <option value="group">Group work only</option>
                  <option value="individual">Individual only</option>
                  <option value="both">Group or individual</option>
                </select>
              </div>
            </div>
            <label className="mt-3 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={allowIndividual}
                onChange={(e) => setAllowIndividual(e.target.checked)}
              />
              Allow individual participation alongside groups
            </label>
          </FormSection>

          <FormSection title="Schedule & grading period" icon="bi-calendar" tone="primary">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="due_date" required>
                  Due date & time
                </FieldLabel>
                <input
                  id="due_date"
                  type="datetime-local"
                  className={inputClass()}
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  required
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
                  <option value="Q1">Quarter 1</option>
                  <option value="Q2">Quarter 2</option>
                  <option value="Q3">Quarter 3</option>
                  <option value="Q4">Quarter 4</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor="semester">Semester</FieldLabel>
                <select
                  id="semester"
                  className={inputClass()}
                  value={semester}
                  onChange={(e) => setSemester(e.target.value)}
                >
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
                      {p.period_type ? ` (${p.period_type})` : ''}
                    </option>
                  ))}
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
            </div>
          </FormSection>

          <FormSection title="Assign to groups" icon="bi-people-fill" tone="emerald">
            {groupsLoading ? (
              <p className="text-sm text-hub-muted">Loading groups…</p>
            ) : groups.length ? (
              <>
                <div className="mb-3 flex gap-3 text-sm">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      checked={groupSelection === 'all'}
                      onChange={() => setGroupSelection('all')}
                    />
                    All groups
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      checked={groupSelection === 'specific'}
                      onChange={() => setGroupSelection('specific')}
                    />
                    Specific groups
                  </label>
                </div>
                {groupSelection === 'specific' ? (
                  <div className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-3">
                    {groups.map((g) => (
                      <label key={g.id} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={selectedGroupIds.includes(g.id)}
                          onChange={() => toggleGroup(g.id)}
                        />
                        {g.name} ({g.member_count} members)
                      </label>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-hub-muted">This assignment will apply to all active groups in the class.</p>
                )}
              </>
            ) : (
              <p className="text-sm text-hub-muted">
                No groups in this class yet.{' '}
                <Link to={`/management/classes/${classId}/groups`} className="font-semibold text-teal-700 hover:underline">
                  Create groups
                </Link>{' '}
                first, or the assignment will apply when groups are added.
              </p>
            )}
          </FormSection>

          {formError ? <p className="text-sm text-red-700">{formError}</p> : null}

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-full bg-cyan-700 px-5 py-2.5 text-sm font-bold text-white hover:bg-cyan-800 disabled:opacity-60"
            >
              {submitting ? 'Creating…' : 'Create discussion assignment'}
            </button>
            <Link to={backTo} className="rounded-full border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700">
              Cancel
            </Link>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-950">
            <h3 className="font-bold">Tips</h3>
            <ul className="mt-2 list-disc space-y-1 ps-4 text-cyan-900">
              <li>Use open-ended prompts that invite debate.</li>
              <li>Set realistic minimum word counts per post.</li>
              <li>Groups participate as a team — track collaboration in submissions.</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm">
            <div className="flex justify-between">
              <span className="text-hub-muted">Prompts</span>
              <strong>{prompts.filter((p) => p.text.trim()).length}</strong>
            </div>
            <div className="mt-1 flex justify-between">
              <span className="text-hub-muted">Min posts / group</span>
              <strong>{minPosts}</strong>
            </div>
          </div>
        </aside>
      </form>
    </div>
  )
}
