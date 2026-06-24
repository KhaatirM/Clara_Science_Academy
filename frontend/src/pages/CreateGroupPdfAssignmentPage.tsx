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
import { appendDatetime, appendIfChecked, postAssignmentForm } from '../api/assignmentCreateActions'
import {
  fetchClassGroups,
  fetchGroupPdfForm,
  type ClassGroupBrief,
  type GroupPdfFormMeta,
} from '../api/groupCreateForms'
import { spaRoute } from '../utils/spaRoute'

const CATEGORIES = ['', 'Homework', 'Tests', 'Quizzes', 'Projects', 'Classwork', 'Participation', 'Extra Credit']

function quarterOptionValue(q: string): string {
  if (q === '1') return 'Q1'
  if (q === '2') return 'Q2'
  if (q === '3') return 'Q3'
  if (q === '4') return 'Q4'
  if (q.startsWith('Q')) return q
  return 'Q1'
}

export function CreateGroupPdfAssignmentPage() {
  const navigate = useNavigate()
  const { classId: classIdParam } = useParams()
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [meta, setMeta] = useState<GroupPdfFormMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [groups, setGroups] = useState<ClassGroupBrief[]>([])
  const [groupsLoading, setGroupsLoading] = useState(false)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assignmentStatus, setAssignmentStatus] = useState('Active')
  const [category, setCategory] = useState('')
  const [quarter, setQuarter] = useState('Q1')
  const [semester, setSemester] = useState('')
  const [openDate, setOpenDate] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [closeDate, setCloseDate] = useState('')
  const [academicPeriodId, setAcademicPeriodId] = useState('')
  const [categoryWeight, setCategoryWeight] = useState('0')
  const [totalPoints, setTotalPoints] = useState('100')
  const [gradeScalePreset, setGradeScalePreset] = useState('')
  const [allowExtraCredit, setAllowExtraCredit] = useState(false)
  const [maxExtraCredit, setMaxExtraCredit] = useState('0')
  const [latePenaltyEnabled, setLatePenaltyEnabled] = useState(false)
  const [latePenaltyPerDay, setLatePenaltyPerDay] = useState('10')
  const [latePenaltyMaxDays, setLatePenaltyMaxDays] = useState('0')
  const [groupSizeMin, setGroupSizeMin] = useState('2')
  const [groupSizeMax, setGroupSizeMax] = useState('')
  const [collaborationType, setCollaborationType] = useState('group')
  const [allowIndividual, setAllowIndividual] = useState(false)
  const [groupSelection, setGroupSelection] = useState<'all' | 'specific'>('all')
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([])
  const [attachment, setAttachment] = useState<File | null>(null)

  const load = useCallback(async () => {
    if (!classId) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGroupPdfForm(classId)
      setMeta(data)
      setQuarter(quarterOptionValue(data.current_quarter || '1'))
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

  const toggleGroup = (id: number) => {
    setSelectedGroupIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!meta || !classId) return
    setFormError(null)
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('class_id', String(classId))
      form.append('title', title.trim())
      form.append('description', description.trim())
      form.append('assignment_status', assignmentStatus)
      form.append('assignment_category', category)
      form.append('quarter', quarter)
      if (semester) form.append('semester', semester)
      appendDatetime(form, 'open_date', openDate)
      form.append('due_date', dueDate)
      appendDatetime(form, 'close_date', closeDate)
      if (academicPeriodId) form.append('academic_period_id', academicPeriodId)
      form.append('category_weight', categoryWeight)
      form.append('total_points', totalPoints)
      if (gradeScalePreset) form.append('grade_scale_preset', gradeScalePreset)
      appendIfChecked(form, 'allow_extra_credit', allowExtraCredit)
      form.append('max_extra_credit_points', maxExtraCredit)
      appendIfChecked(form, 'late_penalty_enabled', latePenaltyEnabled)
      form.append('late_penalty_per_day', latePenaltyPerDay)
      form.append('late_penalty_max_days', latePenaltyMaxDays)
      form.append('group_size_min', groupSizeMin)
      if (groupSizeMax.trim()) form.append('group_size_max', groupSizeMax)
      form.append('collaboration_type', collaborationType)
      appendIfChecked(form, 'allow_individual', allowIndividual)
      form.append('group_selection', groupSelection)
      if (groupSelection === 'specific') {
        selectedGroupIds.forEach((id) => form.append('selected_groups', String(id)))
      }
      if (attachment) form.append('attachment', attachment)

      const result = await postAssignmentForm(meta.post_url, form)
      if (result.redirect_url) {
        navigate(spaRoute(result.redirect_url))
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not create group assignment')
    } finally {
      setSubmitting(false)
    }
  }

  if (!classId) {
    return <FormError message="Invalid class" backTo="/management/assignments/create/group" />
  }
  if (loading) return <FormLoading label="Loading group PDF form…" />
  if (error || !meta) return <FormError message={error || 'Could not load form'} backTo={backTo} />

  return (
    <div className="mx-auto max-w-[1280px] px-1 pb-10">
      <AssignmentCreateHeader
        title="Create Group PDF/Paper Assignment"
        subtitle="Collaborative file submission — one student submits for the team"
        icon="bi-file-earmark-text"
        backTo={backTo}
        backLabel="Back to group types"
        badge={classBadge}
      />

      <form onSubmit={(e) => void handleSubmit(e)} className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-5">
          <FormSection title="Assignment Details" icon="bi-pencil-square" tone="purple">
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
                />
              </div>
              <div>
                <FieldLabel htmlFor="description">Description & instructions</FieldLabel>
                <textarea
                  id="description"
                  className={inputClass()}
                  rows={5}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>
          </FormSection>

          <FormSection title="Assignment Settings" icon="bi-gear" tone="info">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="assignment_status" required>
                  Status
                </FieldLabel>
                <select
                  id="assignment_status"
                  className={inputClass()}
                  value={assignmentStatus}
                  onChange={(e) => setAssignmentStatus(e.target.value)}
                >
                  <option value="Active">Active — visible to students</option>
                  <option value="Inactive">Inactive — hidden</option>
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
                      {c || 'Select category (optional)'}
                    </option>
                  ))}
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
                <FieldLabel htmlFor="grade_scale_preset">Grade scale preset</FieldLabel>
                <select
                  id="grade_scale_preset"
                  className={inputClass()}
                  value={gradeScalePreset}
                  onChange={(e) => setGradeScalePreset(e.target.value)}
                >
                  <option value="">Default</option>
                  <option value="standard">Standard (A=93)</option>
                  <option value="strict">Strict (A=93, higher B/C cutoffs)</option>
                  <option value="lenient">Lenient (A=88)</option>
                </select>
              </div>
            </div>
          </FormSection>

          <FormSection title="Schedule & Academic Period" icon="bi-calendar-event">
            <div className="grid gap-4 sm:grid-cols-2">
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

          <FormSection title="Group Configuration" icon="bi-people" tone="emerald">
            <div className="grid gap-4 sm:grid-cols-3">
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
              <div>
                <FieldLabel htmlFor="collaboration_type">Collaboration type</FieldLabel>
                <select
                  id="collaboration_type"
                  className={inputClass()}
                  value={collaborationType}
                  onChange={(e) => setCollaborationType(e.target.value)}
                >
                  <option value="group">Group work only</option>
                  <option value="individual">Individual work only</option>
                  <option value="both">Allow both</option>
                </select>
              </div>
            </div>
            <label className="mt-4 flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={allowIndividual}
                onChange={(e) => setAllowIndividual(e.target.checked)}
                className="rounded border-slate-300"
              />
              Allow individual submissions
            </label>
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
                  <span className="block text-xs text-slate-500">Every group in this class receives the assignment</span>
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
                  <strong>Specific groups</strong>
                  <span className="block text-xs text-slate-500">Choose which groups get this assignment</span>
                </span>
              </label>
              {groupSelection === 'specific' ? (
                <div className="mt-2 rounded-lg border border-slate-200 p-3">
                  {groupsLoading ? (
                    <p className="text-sm text-slate-500">Loading groups…</p>
                  ) : groups.length === 0 ? (
                    <p className="text-sm text-slate-500">No groups found for this class.</p>
                  ) : (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {groups.map((g) => (
                        <label
                          key={g.id}
                          className={`flex cursor-pointer items-center gap-2 rounded-lg border p-3 text-sm ${
                            selectedGroupIds.includes(g.id)
                              ? 'border-violet-400 bg-violet-50'
                              : 'border-slate-200'
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

          <FormSection title="Attachment" icon="bi-paperclip" tone="success">
            <input
              type="file"
              className="text-sm"
              accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.xls,.xlsx,.ppt,.pptx"
              onChange={(e) => setAttachment(e.target.files?.[0] ?? null)}
            />
            {attachment ? <p className="mt-2 text-sm text-slate-600">{attachment.name}</p> : null}
          </FormSection>

          {formError ? <p className="text-sm font-semibold text-red-700">{formError}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-pink-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-60 lg:hidden"
          >
            {submitting ? 'Creating…' : 'Create group assignment'}
          </button>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-slate-600 px-4 py-2 text-sm font-bold text-white">
              <i className="bi bi-lightbulb me-2" aria-hidden />
              Tips
            </div>
            <ul className="space-y-2 p-4 text-xs text-slate-600">
              <li>One student submits on behalf of the whole group.</li>
              <li>Use specific groups when only some teams should receive the work.</li>
              <li>Membership is snapshotted at creation time.</li>
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
          <div className="hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:block">
            <button
              type="submit"
              disabled={submitting}
              className="mb-3 w-full rounded-xl bg-gradient-to-r from-violet-600 to-pink-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-60"
            >
              {submitting ? 'Creating…' : 'Create group assignment'}
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
