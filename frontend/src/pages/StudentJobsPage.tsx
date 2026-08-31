import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  addTeamMembers,
  archiveInspection,
  archiveStudentJobsTeam,
  createStudentJobsTeam,
  createTeamDuty,
  resetLunchServiceChecks,
  setLunchServiceCheck,
  updateStudentJobsTeam,
  deleteInspection,
  deleteTeamDuty,
  fetchAllInspectionsForExport,
  fetchInspectionDetail,
  fetchInspectionHistory,
  fetchStudentJobsHub,
  fetchStudentJobsStudents,
  removeTeamMembers,
  saveStudentJobsInspection,
  updateTeamDuty,
  updateTeamMember,
} from '../api/studentJobs'
import { ManagementPageHero, ManagementPageShell } from '../components/layout/ManagementPageShell'
import { ConfirmDialog, Modal, PromptDialog } from '../components/ui/Modal'
import type {
  CleaningBonusFlags,
  CleaningDeductionFlags,
  StudentJobsHubResponse,
  StudentJobsInspectionDetail,
  StudentJobsInspectionHistoryItem,
  StudentJobsInspectionPagination,
  StudentJobsMember,
  StudentJobsStudentOption,
  StudentJobsTeam,
} from '../types/studentJobs'
import { showAppToast } from '../utils/appToast'
import { spaRoute } from '../utils/spaRoute'

const INSPECTIONS_PER_PAGE = 10

const EMPTY_DEDUCTIONS: CleaningDeductionFlags = {}
const EMPTY_BONUSES: CleaningBonusFlags = {}

const WEEKDAY_OPTIONS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
]
const DEFAULT_WORKDAYS = [0, 1, 2, 3, 4]

type TeamDraft = {
  name: string
  team_type: string
  description: string
  days_of_week: number[]
}

const EMPTY_TEAM_DRAFT: TeamDraft = {
  name: '',
  team_type: 'cleaning',
  description: '',
  days_of_week: [...DEFAULT_WORKDAYS],
}

function toggleDay(days: number[], day: number): number[] {
  return days.includes(day)
    ? days.filter((d) => d !== day)
    : [...days, day].sort((a, b) => a - b)
}

/** Teams with every weekday selected are described as working daily. */
function workdaySummary(days: number[]): string {
  if (!days.length || days.length >= WEEKDAY_OPTIONS.length) return 'Every school day'
  return WEEKDAY_OPTIONS.filter((d) => days.includes(d.value))
    .map((d) => d.label)
    .join(', ')
}

function WorkdayPicker({
  days,
  onChange,
  disabled,
}: {
  days: number[]
  onChange: (days: number[]) => void
  disabled?: boolean
}) {
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {WEEKDAY_OPTIONS.map((day) => {
          const on = days.includes(day.value)
          return (
            <button
              key={day.value}
              type="button"
              disabled={disabled}
              aria-pressed={on}
              className={[
                'rounded-xl border px-3 py-1.5 text-sm font-bold',
                on
                  ? 'border-teal-600 bg-teal-600 text-white'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
              ].join(' ')}
              onClick={() => onChange(toggleDay(days, day.value))}
            >
              {day.label}
            </button>
          )
        })}
      </div>
      <p className="mb-0 mt-1.5 text-xs text-hub-muted">
        {days.length ? `Works ${workdaySummary(days)}.` : 'No days picked — counts as every school day.'}
      </p>
    </div>
  )
}

const EMPTY_DUTY_DRAFT = {
  id: null as number | null,
  name: '',
  area: '',
  description: '',
  scoring_type: 'cleaning',
}

const TEAM_TYPE_STYLE: Record<string, { label: string; chip: string; icon: string }> = {
  cleaning: { label: 'Cleaning', chip: 'bg-teal-100 text-teal-800', icon: 'bi-bucket' },
  computer: { label: 'Computer', chip: 'bg-indigo-100 text-indigo-800', icon: 'bi-pc-display' },
  lunch_duty: { label: 'Lunch duty', chip: 'bg-amber-100 text-amber-900', icon: 'bi-cup-straw' },
  experiment_duty: {
    label: 'Experiment duty',
    chip: 'bg-violet-100 text-violet-800',
    icon: 'bi-beaker',
  },
  other: { label: 'Other', chip: 'bg-slate-100 text-slate-700', icon: 'bi-briefcase' },
}

function teamStyle(type: string) {
  return TEAM_TYPE_STYLE[type] || TEAM_TYPE_STYLE.other
}

function scoreTone(score: number) {
  if (score < 60) return { chip: 'bg-red-100 text-red-800', bar: 'bg-red-500', text: 'text-red-700' }
  if (score < 80)
    return { chip: 'bg-amber-100 text-amber-900', bar: 'bg-amber-500', text: 'text-amber-700' }
  return {
    chip: 'bg-emerald-100 text-emerald-800',
    bar: 'bg-emerald-500',
    text: 'text-emerald-700',
  }
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function todayInputValue() {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10)
}

const FIELD_CLASS =
  'w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-semibold text-hub-text focus:border-teal-500 focus:bg-white focus:outline-none'
const LABEL_CLASS = 'mb-1 block text-xs font-bold uppercase tracking-wide text-hub-muted'

function StatTile({
  icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: string
  label: string
  value: string | number
  hint?: string
  tone: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/90 bg-white p-4 shadow-sm">
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${tone}`}>
        <i className={`bi ${icon} text-lg`} aria-hidden />
      </span>
      <div className="min-w-0">
        <div className="text-2xl font-extrabold leading-tight text-hub-text">{value}</div>
        <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">{label}</div>
        {hint ? <div className="text-xs text-hub-muted">{hint}</div> : null}
      </div>
    </div>
  )
}

function Sparkline({ scores }: { scores: number[] }) {
  if (scores.length < 2) {
    return <div className="text-xs text-hub-muted">Not enough inspections to show a trend yet.</div>
  }
  return (
    <div className="flex h-10 items-end gap-1" aria-hidden>
      {scores.map((score, index) => {
        const height = Math.max(8, Math.min(100, score))
        return (
          <div
            key={`${index}-${score}`}
            className={`flex-1 rounded-t ${scoreTone(score).bar}`}
            style={{ height: `${height}%` }}
            title={`${score} points`}
          />
        )
      })}
    </div>
  )
}

function TrendPill({ trend }: { trend: number | null }) {
  if (trend == null || trend === 0) return null
  const up = trend > 0
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold ${
        up ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
      }`}
    >
      <i className={`bi ${up ? 'bi-arrow-up-right' : 'bi-arrow-down-right'}`} aria-hidden />
      {up ? '+' : ''}
      {trend}
    </span>
  )
}

function SectionCard({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-5 py-3.5">
        <div>
          <h2 className="mb-0 font-bold text-hub-text">{title}</h2>
          {subtitle ? <p className="mb-0 text-sm text-hub-muted">{subtitle}</p> : null}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

export function StudentJobsPage() {
  const [data, setData] = useState<StudentJobsHubResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<'teams' | 'inspections' | 'scoring'>('teams')

  // Teams tab
  const [teamQuery, setTeamQuery] = useState('')
  const [teamTypeFilter, setTeamTypeFilter] = useState('all')
  const [detailTeam, setDetailTeam] = useState<StudentJobsTeam | null>(null)

  // Roster
  const [students, setStudents] = useState<StudentJobsStudentOption[]>([])
  const [studentsLoaded, setStudentsLoaded] = useState(false)

  // Duties
  const [dutiesTeam, setDutiesTeam] = useState<StudentJobsTeam | null>(null)
  const [dutyDraft, setDutyDraft] = useState<typeof EMPTY_DUTY_DRAFT | null>(null)

  // Inspection form
  const [inspectionOpen, setInspectionOpen] = useState(false)
  const [inspectionType, setInspectionType] = useState('cleaning')
  const [inspectionTeamId, setInspectionTeamId] = useState<number | null>(null)
  const [inspectionDate, setInspectionDate] = useState(todayInputValue())
  const [inspectorName, setInspectorName] = useState('')
  const [inspectorNotes, setInspectorNotes] = useState('')
  const [deductions, setDeductions] = useState<CleaningDeductionFlags>(EMPTY_DEDUCTIONS)
  const [bonuses, setBonuses] = useState<CleaningBonusFlags>(EMPTY_BONUSES)

  // Create team
  const [createOpen, setCreateOpen] = useState(false)
  const [newTeamName, setNewTeamName] = useState('')
  const [newTeamType, setNewTeamType] = useState('cleaning')
  const [newTeamDescription, setNewTeamDescription] = useState('')
  const [newTeamStudentIds, setNewTeamStudentIds] = useState<number[]>([])
  const [newTeamDays, setNewTeamDays] = useState<number[]>([...DEFAULT_WORKDAYS])

  // Edit team
  const [editTeam, setEditTeam] = useState<StudentJobsTeam | null>(null)
  const [editDraft, setEditDraft] = useState<TeamDraft>(EMPTY_TEAM_DRAFT)

  // Members
  const [membersTeam, setMembersTeam] = useState<StudentJobsTeam | null>(null)
  const [memberQuery, setMemberQuery] = useState('')
  const [memberSelection, setMemberSelection] = useState<number[]>([])
  const [editingMember, setEditingMember] = useState<StudentJobsMember | null>(null)
  const [editingRole, setEditingRole] = useState('')

  // Inspection history
  const [history, setHistory] = useState<StudentJobsInspectionHistoryItem[]>([])
  const [pagination, setPagination] = useState<StudentJobsInspectionPagination | null>(null)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyQuery, setHistoryQuery] = useState('')
  const [historyStatus, setHistoryStatus] = useState<'all' | 'passed' | 'failed'>('all')
  const [historyTeam, setHistoryTeam] = useState<'all' | number>('all')
  const [exporting, setExporting] = useState(false)

  // Detail + confirmations
  const [detail, setDetail] = useState<StudentJobsInspectionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [confirm, setConfirm] = useState<{
    title: string
    body: React.ReactNode
    confirmLabel: string
    action: () => Promise<void>
  } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const payload = await fetchStudentJobsHub()
      setData(payload)
      setHistory(payload.inspection_history)
      setPagination(payload.inspection_pagination)
      setHistoryPage(payload.inspection_pagination?.page || 1)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load student jobs.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const ensureStudents = useCallback(async () => {
    if (studentsLoaded) return
    try {
      setStudents(await fetchStudentJobsStudents())
      setStudentsLoaded(true)
    } catch {
      showAppToast('Could not load the student roster.', 'danger')
    }
  }, [studentsLoaded])

  const loadHistory = useCallback(async (page: number) => {
    setHistoryLoading(true)
    try {
      const result = await fetchInspectionHistory(page, INSPECTIONS_PER_PAGE)
      setHistory(result.items)
      setPagination(result.pagination)
      setHistoryPage(result.pagination.page)
    } catch (e) {
      showAppToast(e instanceof Error ? e.message : 'Could not load inspections.', 'danger')
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  // Keep open modals pointed at the freshly loaded copy of their team.
  useEffect(() => {
    if (!data) return
    const sync = (team: StudentJobsTeam | null) =>
      team ? data.teams.find((candidate) => candidate.id === team.id) || null : null
    setMembersTeam(sync)
    setDutiesTeam(sync)
    setDetailTeam(sync)
  }, [data])

  const inspectionTypes = data?.inspection_types || []
  const activeType = useMemo(
    () => inspectionTypes.find((type) => type.value === inspectionType) || inspectionTypes[0],
    [inspectionTypes, inspectionType],
  )
  const deductionOptions = activeType?.deductions || data?.deduction_options || []
  const bonusOptions = activeType?.bonuses || data?.bonus_options || []
  const startingScore = activeType?.starting_score ?? data?.point_system.starting_points ?? 100
  const passThreshold = activeType?.pass_threshold ?? data?.point_system.redo_threshold ?? 60

  const scorePreview = useMemo(() => {
    let major = 0
    let moderate = 0
    let minor = 0
    for (const option of deductionOptions) {
      if (!deductions[option.key]) continue
      if (option.severity === 'major') major += option.points
      else if (option.severity === 'moderate') moderate += option.points
      else minor += option.points
    }
    const bonus = bonusOptions.reduce(
      (sum, option) => (bonuses[option.key] ? sum + option.points : sum),
      0,
    )
    return {
      major_deductions: major,
      moderate_deductions: moderate,
      minor_deductions: minor,
      bonus_points: bonus,
      final_score: Math.max(0, startingScore - major - moderate - minor + bonus),
    }
  }, [deductionOptions, bonusOptions, deductions, bonuses, startingScore])

  const filteredTeams = useMemo(() => {
    const needle = teamQuery.trim().toLowerCase()
    return (data?.teams || []).filter((team) => {
      if (teamTypeFilter !== 'all' && team.team_type !== teamTypeFilter) return false
      if (!needle) return true
      const haystack = [team.name, team.description, ...team.members.map((m) => m.name)]
        .join(' ')
        .toLowerCase()
      return haystack.includes(needle)
    })
  }, [data?.teams, teamQuery, teamTypeFilter])

  const filteredHistory = useMemo(() => {
    const needle = historyQuery.trim().toLowerCase()
    return history.filter((item) => {
      if (historyTeam !== 'all' && item.team_id !== historyTeam) return false
      if (historyStatus === 'passed' && item.score < 60) return false
      if (historyStatus === 'failed' && item.score >= 60) return false
      if (!needle) return true
      return `${item.team_name} ${item.inspector_name}`.toLowerCase().includes(needle)
    })
  }, [history, historyQuery, historyStatus, historyTeam])

  const passRate = useMemo(() => {
    const total = data?.summary.inspections || 0
    if (!total) return '—'
    return `${Math.round((100 * (data?.summary.passed || 0)) / total)}%`
  }, [data?.summary])

  function openInspection(teamId?: number, type = 'cleaning') {
    setInspectionTeamId(teamId ?? data?.teams[0]?.id ?? null)
    setInspectionType(type)
    setInspectionDate(todayInputValue())
    setInspectorNotes('')
    setDeductions(EMPTY_DEDUCTIONS)
    setBonuses(EMPTY_BONUSES)
    setInspectionOpen(true)
  }

  async function submitInspection() {
    if (!inspectionTeamId) {
      showAppToast('Choose a team to inspect.', 'warning')
      return
    }
    if (!inspectorName.trim()) {
      showAppToast('Enter the inspector name.', 'warning')
      return
    }
    setBusy(true)
    try {
      const result = await saveStudentJobsInspection({
        team_id: inspectionTeamId,
        inspection_type: inspectionType,
        inspection_date: inspectionDate,
        inspector_name: inspectorName.trim(),
        inspector_notes: inspectorNotes.trim(),
        ...deductions,
        ...bonuses,
      })
      if (result.success) {
        showAppToast(result.message || 'Inspection saved.', 'success')
        setInspectionOpen(false)
        await load()
      } else {
        showAppToast('Could not save the inspection.', 'danger')
      }
    } catch (e) {
      showAppToast(e instanceof Error ? e.message : 'Could not save the inspection.', 'danger')
    } finally {
      setBusy(false)
    }
  }

  async function submitCreateTeam() {
    if (!newTeamName.trim()) {
      showAppToast('Team name is required.', 'warning')
      return
    }
    setBusy(true)
    try {
      const result = await createStudentJobsTeam({
        name: newTeamName.trim(),
        description: newTeamDescription.trim(),
        team_type: newTeamType,
        student_ids: newTeamStudentIds,
        days_of_week: newTeamDays,
      })
      if (result.success) {
        showAppToast(result.message || 'Team created.', 'success')
        setCreateOpen(false)
        setNewTeamName('')
        setNewTeamDescription('')
        setNewTeamStudentIds([])
        setNewTeamDays([...DEFAULT_WORKDAYS])
        await load()
      } else {
        showAppToast(result.error || 'Could not create the team.', 'danger')
      }
    } catch (e) {
      showAppToast(e instanceof Error ? e.message : 'Could not create the team.', 'danger')
    } finally {
      setBusy(false)
    }
  }

  function openEditTeam(team: StudentJobsTeam) {
    setEditTeam(team)
    setEditDraft({
      name: team.name,
      team_type: team.team_type,
      description: team.description,
      days_of_week: team.days_of_week?.length ? [...team.days_of_week] : [...DEFAULT_WORKDAYS],
    })
  }

  async function submitEditTeam() {
    if (!editTeam) return
    if (!editDraft.name.trim()) {
      showAppToast('Team name is required.', 'warning')
      return
    }
    const saved = await runAction(() =>
      updateStudentJobsTeam(editTeam.id, {
        name: editDraft.name.trim(),
        description: editDraft.description.trim(),
        team_type: editDraft.team_type,
        days_of_week: editDraft.days_of_week,
      }),
    )
    if (saved) setEditTeam(null)
  }

  async function runAction(fn: () => Promise<{ success: boolean; message?: string; error?: string }>) {
    setBusy(true)
    try {
      const result = await fn()
      if (result.success) {
        showAppToast(result.message || 'Saved.', 'success')
        await load()
        return true
      }
      showAppToast(result.error || 'That did not work.', 'danger')
      return false
    } catch (e) {
      showAppToast(e instanceof Error ? e.message : 'That did not work.', 'danger')
      return false
    } finally {
      setBusy(false)
    }
  }

  async function openDetail(id: number) {
    setDetailLoading(true)
    setDetail(null)
    try {
      const result = await fetchInspectionDetail(id)
      if (result.success) setDetail(result.inspection)
      else showAppToast(result.error || 'Inspection not found.', 'danger')
    } catch (e) {
      showAppToast(e instanceof Error ? e.message : 'Could not load the inspection.', 'danger')
    } finally {
      setDetailLoading(false)
    }
  }

  async function exportCsv() {
    setExporting(true)
    try {
      const result = await fetchAllInspectionsForExport()
      const header = [
        'Date',
        'Team',
        'Score',
        'Status',
        'Inspector',
        'Major',
        'Moderate',
        'Minor',
        'Bonus',
        'Notes',
      ]
      const rows = result.items.map((item) => [
        item.date,
        item.team_name,
        String(item.score),
        item.status,
        item.inspector_name,
        String(item.major_deductions ?? ''),
        String(item.moderate_deductions ?? ''),
        String(item.minor_deductions ?? ''),
        String(item.bonus_points ?? ''),
        (item.inspector_notes || '').replace(/\s+/g, ' '),
      ])
      const csv = [header, ...rows]
        .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
        .join('\n')
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `inspections-${todayInputValue()}.csv`
      link.click()
      URL.revokeObjectURL(url)
      showAppToast(`Exported ${rows.length} inspections.`, 'success')
    } catch (e) {
      showAppToast(e instanceof Error ? e.message : 'Export failed.', 'danger')
    } finally {
      setExporting(false)
    }
  }

  if (loading && !data) {
    return (
      <ManagementPageShell>
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-hub-muted">
          Loading student jobs…
        </div>
      </ManagementPageShell>
    )
  }

  if (error || !data) {
    return (
      <ManagementPageShell>
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
          {error || 'Could not load student jobs.'}
        </div>
      </ManagementPageShell>
    )
  }

  const tabs = [
    { key: 'teams' as const, label: 'Teams', icon: 'bi-people', count: data.teams.length },
    {
      key: 'inspections' as const,
      label: 'Inspections',
      icon: 'bi-clipboard-check',
      count: pagination?.total ?? data.summary.inspections,
    },
    { key: 'scoring' as const, label: 'Scoring guide', icon: 'bi-list-check', count: null },
  ]

  return (
    <ManagementPageShell director={data.is_director}>
      <ManagementPageHero className="!rounded-2xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex gap-3">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/15">
              <i className="bi bi-briefcase text-xl" aria-hidden />
            </span>
            <div>
              <h1 className="mb-1 text-2xl font-extrabold">Student jobs</h1>
              <p className="mb-0 max-w-2xl text-sm text-white/85">
                Build duty teams, run inspections, and track how each crew is performing week to
                week.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to={spaRoute(data.urls.home)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-white/15 px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-white/25"
            >
              <i className="bi bi-arrow-left" aria-hidden />
              Dashboard
            </Link>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-xl bg-white/15 px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-white/25"
              onClick={() => {
                void ensureStudents()
                setCreateOpen(true)
              }}
            >
              <i className="bi bi-plus-lg" aria-hidden />
              New team
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-xl bg-white px-3.5 py-2 text-sm font-bold text-teal-800 transition hover:bg-white/90"
              onClick={() => openInspection()}
            >
              <i className="bi bi-clipboard-check" aria-hidden />
              Conduct inspection
            </button>
          </div>
        </div>
      </ManagementPageHero>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          icon="bi-people-fill"
          label="Active teams"
          value={data.summary.teams}
          tone="bg-teal-100 text-teal-700"
        />
        <StatTile
          icon="bi-person-badge"
          label="Students assigned"
          value={data.summary.members}
          tone="bg-indigo-100 text-indigo-700"
        />
        <StatTile
          icon="bi-clipboard-data"
          label="Inspections"
          value={data.summary.inspections}
          tone="bg-violet-100 text-violet-700"
        />
        <StatTile
          icon="bi-patch-check"
          label="Pass rate"
          value={passRate}
          hint={`${data.summary.passed} passed`}
          tone="bg-emerald-100 text-emerald-700"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button
            key={item.key}
            type="button"
            className={['spa-mgmt-tab', tab === item.key ? 'is-active' : ''].join(' ')}
            onClick={() => setTab(item.key)}
          >
            <i className={`bi ${item.icon} me-1.5`} aria-hidden />
            {item.label}
            {item.count != null ? (
              <span className="ml-1.5 opacity-70">({item.count})</span>
            ) : null}
          </button>
        ))}
      </div>

      {tab === 'teams' ? (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
            <div className="relative min-w-[14rem] flex-1">
              <i
                className="bi bi-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                aria-hidden
              />
              <input
                type="search"
                className={`${FIELD_CLASS} pl-9`}
                placeholder="Search teams or students…"
                value={teamQuery}
                onChange={(e) => setTeamQuery(e.target.value)}
              />
            </div>
            <select
              className={`${FIELD_CLASS} w-auto`}
              value={teamTypeFilter}
              onChange={(e) => setTeamTypeFilter(e.target.value)}
            >
              <option value="all">All types</option>
              {data.team_type_options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {filteredTeams.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
              <i className="bi bi-people text-3xl text-slate-300" aria-hidden />
              <p className="mb-1 mt-2 font-bold text-hub-text">No teams to show</p>
              <p className="mb-0 text-sm text-hub-muted">
                {data.teams.length === 0
                  ? 'Create a team to start assigning students to jobs.'
                  : 'No team matches your search.'}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {filteredTeams.map((team) => {
                const style = teamStyle(team.team_type)
                const tone = scoreTone(team.current_score)
                return (
                  <article
                    key={team.id}
                    className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="mb-0 truncate font-bold text-hub-text">{team.name}</h3>
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold ${style.chip}`}
                          >
                            <i className={`bi ${style.icon}`} aria-hidden />
                            {style.label}
                          </span>
                        </div>
                        <p className="mb-0 text-sm text-hub-muted">
                          {team.members.length} member{team.members.length === 1 ? '' : 's'}
                          {team.stats.last_inspected
                            ? ` · last inspected ${formatDate(team.stats.last_inspected)}`
                            : ' · never inspected'}
                        </p>
                        <p className="mb-0 mt-1 text-xs font-bold uppercase tracking-wide text-teal-800">
                          <i className="bi bi-calendar-week me-1" aria-hidden />
                          {workdaySummary(team.days_of_week || [])}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        <span
                          className={`rounded-full px-3 py-1 text-lg font-extrabold ${tone.chip}`}
                        >
                          {team.current_score}
                        </span>
                        <TrendPill trend={team.stats.trend} />
                      </div>
                    </div>

                    <div className="flex-1 space-y-3 p-5">
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="rounded-xl bg-slate-50 px-2 py-2">
                          <div className="text-lg font-extrabold text-hub-text">
                            {team.stats.average_score ?? '—'}
                          </div>
                          <div className="text-[10px] font-bold uppercase tracking-wide text-hub-muted">
                            Average
                          </div>
                        </div>
                        <div className="rounded-xl bg-slate-50 px-2 py-2">
                          <div className="text-lg font-extrabold text-hub-text">
                            {team.stats.pass_rate != null ? `${team.stats.pass_rate}%` : '—'}
                          </div>
                          <div className="text-[10px] font-bold uppercase tracking-wide text-hub-muted">
                            Pass rate
                          </div>
                        </div>
                        <div className="rounded-xl bg-slate-50 px-2 py-2">
                          <div className="text-lg font-extrabold text-hub-text">
                            {team.stats.inspection_count}
                          </div>
                          <div className="text-[10px] font-bold uppercase tracking-wide text-hub-muted">
                            Inspections
                          </div>
                        </div>
                      </div>

                      <Sparkline scores={team.stats.sparkline} />

                      {team.members.length === 0 ? (
                        <p className="mb-0 rounded-xl border border-dashed border-slate-200 px-3 py-3 text-center text-sm text-hub-muted">
                          No students assigned yet.
                        </p>
                      ) : (
                        <>
                          <p className="mb-0 text-xs font-bold uppercase tracking-wide text-hub-muted">
                            <i className="bi bi-egg-fried me-1" aria-hidden />
                            Lunch turns this week: {team.lunch_served_count} of{' '}
                            {team.members.length} served · click a name to tick it off
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {team.members.map((member) => (
                              <button
                                key={member.member_id}
                                type="button"
                                disabled={busy}
                                aria-pressed={member.served_lunch}
                                title={
                                  member.served_lunch
                                    ? 'Already served this week — click to undo'
                                    : 'Mark as having served lunch this week'
                                }
                                className={[
                                  'rounded-full px-2.5 py-1 text-xs font-semibold',
                                  member.served_lunch
                                    ? 'bg-teal-600 text-white'
                                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
                                ].join(' ')}
                                onClick={() =>
                                  void runAction(() =>
                                    setLunchServiceCheck(member.member_id, !member.served_lunch),
                                  )
                                }
                              >
                                {member.served_lunch ? (
                                  <i className="bi bi-check-lg me-1" aria-hidden />
                                ) : null}
                                {member.name}
                                {member.task_name ? (
                                  <span
                                    className={`ml-1 ${
                                      member.served_lunch ? 'text-teal-100' : 'text-teal-700'
                                    }`}
                                  >
                                    · {member.task_name}
                                  </span>
                                ) : member.role && member.role !== 'Team Member' ? (
                                  <span className="ml-1 text-slate-500">· {member.role}</span>
                                ) : null}
                              </button>
                            ))}
                          </div>
                        </>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 rounded-xl bg-teal-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal-800"
                        onClick={() => openInspection(team.id)}
                      >
                        <i className="bi bi-clipboard-check" aria-hidden />
                        Inspect
                      </button>
                      {team.duties.some((duty) => duty.scoring_type === 'lunch_hall') ? (
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 rounded-xl border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-900 hover:bg-amber-100"
                          onClick={() => openInspection(team.id, 'lunch_hall')}
                        >
                          <i className="bi bi-cup-straw" aria-hidden />
                          Lunch Hall
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-hub-text hover:bg-slate-50"
                        onClick={() => setDutiesTeam(team)}
                      >
                        <i className="bi bi-list-check" aria-hidden />
                        Duties
                        <span className="text-hub-muted">({team.duties.length})</span>
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-hub-text hover:bg-slate-50"
                        onClick={() => openEditTeam(team)}
                      >
                        <i className="bi bi-pencil" aria-hidden />
                        Edit
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-hub-text hover:bg-slate-50"
                        onClick={() => {
                          void ensureStudents()
                          setMembersTeam(team)
                          setMemberSelection([])
                          setMemberQuery('')
                        }}
                      >
                        <i className="bi bi-people" aria-hidden />
                        Members
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-hub-text hover:bg-slate-50"
                        onClick={() => setDetailTeam(team)}
                      >
                        <i className="bi bi-info-circle" aria-hidden />
                        Details
                      </button>
                      <button
                        type="button"
                        className="ml-auto inline-flex items-center gap-1.5 rounded-xl border border-red-200 bg-white px-3 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-50"
                        onClick={() =>
                          setConfirm({
                            title: 'Archive this team?',
                            body: (
                              <>
                                <strong>{team.name}</strong> will be removed from the active list and
                                its members unassigned. Past inspections are kept.
                              </>
                            ),
                            confirmLabel: 'Archive team',
                            action: async () => {
                              await runAction(() => archiveStudentJobsTeam(team.id))
                            },
                          })
                        }
                      >
                        <i className="bi bi-archive" aria-hidden />
                        Archive
                      </button>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </div>
      ) : null}

      {tab === 'inspections' ? (
        <div className="mt-4">
          <SectionCard
            title="Inspection history"
            subtitle={`${pagination?.total ?? 0} recorded inspection${
              (pagination?.total ?? 0) === 1 ? '' : 's'
            }`}
            actions={
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-hub-text hover:bg-slate-50 disabled:opacity-60"
                onClick={() => void exportCsv()}
                disabled={exporting}
              >
                <i className="bi bi-download" aria-hidden />
                {exporting ? 'Exporting…' : 'Export CSV'}
              </button>
            }
          >
            <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 px-5 py-3">
              <div className="relative min-w-[12rem] flex-1">
                <i
                  className="bi bi-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  aria-hidden
                />
                <input
                  type="search"
                  className={`${FIELD_CLASS} pl-9`}
                  placeholder="Search team or inspector…"
                  value={historyQuery}
                  onChange={(e) => setHistoryQuery(e.target.value)}
                />
              </div>
              <select
                className={`${FIELD_CLASS} w-auto`}
                value={String(historyTeam)}
                onChange={(e) =>
                  setHistoryTeam(e.target.value === 'all' ? 'all' : Number(e.target.value))
                }
              >
                <option value="all">All teams</option>
                {data.teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
              <select
                className={`${FIELD_CLASS} w-auto`}
                value={historyStatus}
                onChange={(e) => setHistoryStatus(e.target.value as 'all' | 'passed' | 'failed')}
              >
                <option value="all">All results</option>
                <option value="passed">Passed</option>
                <option value="failed">Needs redo</option>
              </select>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-white text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                    <th className="px-5 py-2.5">Date</th>
                    <th className="px-3 py-2.5">Team</th>
                    <th className="px-3 py-2.5">Score</th>
                    <th className="px-3 py-2.5">Result</th>
                    <th className="px-3 py-2.5">Inspector</th>
                    <th className="px-5 py-2.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {historyLoading ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-10 text-center text-hub-muted">
                        Loading inspections…
                      </td>
                    </tr>
                  ) : filteredHistory.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-10 text-center text-hub-muted">
                        {history.length === 0
                          ? 'No inspections recorded yet.'
                          : 'No inspections match these filters.'}
                      </td>
                    </tr>
                  ) : (
                    filteredHistory.map((item) => {
                      const tone = scoreTone(item.score)
                      const passed = item.score >= 60
                      return (
                        <tr key={item.id} className="border-b border-slate-100 last:border-0">
                          <td className="whitespace-nowrap px-5 py-3 font-semibold text-hub-text">
                            {formatDate(item.date)}
                          </td>
                          <td className="px-3 py-3 text-hub-text">
                            {item.team_name}
                            {item.inspection_type && item.inspection_type !== 'cleaning' ? (
                              <span className="ml-1.5 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-900">
                                {item.inspection_type_label}
                              </span>
                            ) : null}
                          </td>
                          <td className="px-3 py-3">
                            <span
                              className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${tone.chip}`}
                            >
                              {item.score}
                            </span>
                          </td>
                          <td className="px-3 py-3">
                            <span
                              className={`inline-flex items-center gap-1 text-xs font-bold ${
                                passed ? 'text-emerald-700' : 'text-red-700'
                              }`}
                            >
                              <i
                                className={`bi ${passed ? 'bi-check-circle-fill' : 'bi-x-circle-fill'}`}
                                aria-hidden
                              />
                              {passed ? 'Passed' : 'Needs redo'}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-hub-muted">{item.inspector_name}</td>
                          <td className="px-5 py-3">
                            <div className="flex justify-end gap-1">
                              <button
                                type="button"
                                className="rounded-lg px-2 py-1 text-xs font-semibold text-teal-700 hover:bg-teal-50"
                                onClick={() => void openDetail(item.id)}
                              >
                                View
                              </button>
                              <button
                                type="button"
                                className="rounded-lg px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                                onClick={() =>
                                  setConfirm({
                                    title: 'Archive this inspection?',
                                    body: 'It will be removed from the history and will no longer count toward the team score. You can restore it later.',
                                    confirmLabel: 'Archive',
                                    action: async () => {
                                      const ok = await runAction(() => archiveInspection(item.id))
                                      if (ok) await loadHistory(historyPage)
                                    },
                                  })
                                }
                              >
                                Archive
                              </button>
                              <button
                                type="button"
                                className="rounded-lg px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50"
                                onClick={() =>
                                  setConfirm({
                                    title: 'Delete this inspection?',
                                    body: 'This permanently removes the record. Archive it instead if you may need it later.',
                                    confirmLabel: 'Delete',
                                    action: async () => {
                                      const ok = await runAction(() => deleteInspection(item.id))
                                      if (ok) await loadHistory(historyPage)
                                    },
                                  })
                                }
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>

            {pagination && pagination.total_pages > 1 ? (
              <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-5 py-3">
                <button
                  type="button"
                  className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-hub-text hover:bg-slate-50 disabled:opacity-50"
                  onClick={() => void loadHistory(historyPage - 1)}
                  disabled={historyPage <= 1 || historyLoading}
                >
                  Previous
                </button>
                <span className="text-sm text-hub-muted">
                  Page {pagination.page} of {pagination.total_pages}
                </span>
                <button
                  type="button"
                  className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-hub-text hover:bg-slate-50 disabled:opacity-50"
                  onClick={() => void loadHistory(historyPage + 1)}
                  disabled={historyPage >= pagination.total_pages || historyLoading}
                >
                  Next
                </button>
              </div>
            ) : null}
          </SectionCard>
        </div>
      ) : null}

      {tab === 'scoring' ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <SectionCard
            title="How scoring works"
            subtitle={`Every team starts at ${data.point_system.starting_points} points`}
          >
            <div className="space-y-3 p-5 text-sm text-hub-text">
              <p className="mb-0">
                Points come off for each problem found during an inspection and go back on for
                exceptional work. A team scoring below{' '}
                <strong>{data.point_system.redo_threshold}</strong> has to redo the job.
              </p>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-xl font-extrabold text-hub-text">
                    {data.point_system.starting_points}
                  </div>
                  <div className="text-[10px] font-bold uppercase text-hub-muted">Starting</div>
                </div>
                <div className="rounded-xl bg-red-50 p-3">
                  <div className="text-xl font-extrabold text-red-700">
                    {data.point_system.deduction_levels}
                  </div>
                  <div className="text-[10px] font-bold uppercase text-hub-muted">Deductions</div>
                </div>
                <div className="rounded-xl bg-emerald-50 p-3">
                  <div className="text-xl font-extrabold text-emerald-700">
                    +{data.point_system.max_bonus}
                  </div>
                  <div className="text-[10px] font-bold uppercase text-hub-muted">Max bonus</div>
                </div>
              </div>
            </div>
          </SectionCard>

          {inspectionTypes.map((type) => (
            <SectionCard
              key={type.value}
              title={`${type.label} checklist`}
              subtitle={type.description}
            >
              <div className="space-y-4 p-5">
                <div>
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-red-700">
                    Deductions
                  </h3>
                  <ul className="mb-0 list-none space-y-1 p-0">
                    {type.deductions.map((option) => (
                      <li
                        key={option.key}
                        className="flex items-center justify-between gap-3 rounded-lg bg-red-50/60 px-3 py-1.5 text-sm"
                      >
                        <span className="text-hub-text">{option.label}</span>
                        <span className="shrink-0 font-bold text-red-700">−{option.points}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-emerald-700">
                    Bonuses
                  </h3>
                  <ul className="mb-0 list-none space-y-1 p-0">
                    {type.bonuses.map((option) => (
                      <li
                        key={option.key}
                        className="flex items-center justify-between gap-3 rounded-lg bg-emerald-50/60 px-3 py-1.5 text-sm"
                      >
                        <span className="text-hub-text">{option.label}</span>
                        <span className="shrink-0 font-bold text-emerald-700">
                          +{option.points}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </SectionCard>
          ))}

        </div>
      ) : null}

      {/* Conduct inspection */}
      <Modal
        open={inspectionOpen}
        onClose={() => setInspectionOpen(false)}
        title="Conduct inspection"
        subtitle="Mark what you found — the score updates as you go."
        icon="bi-clipboard-check"
        size="xl"
        footer={
          <>
            <div className="mr-auto flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                Final score
              </span>
              <span
                className={`rounded-full px-3 py-1 text-lg font-extrabold ${
                  scoreTone(scorePreview.final_score).chip
                }`}
              >
                {scorePreview.final_score}
              </span>
              {scorePreview.final_score < passThreshold ? (
                <span className="text-xs font-bold text-red-700">Redo required</span>
              ) : null}
            </div>
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              onClick={() => setInspectionOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
              onClick={() => void submitInspection()}
              disabled={busy}
            >
              {busy ? 'Saving…' : 'Save inspection'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          {inspectionTypes.length > 1 ? (
            <div className="flex flex-wrap gap-2">
              {inspectionTypes.map((type) => {
                const active = type.value === inspectionType
                return (
                  <button
                    key={type.value}
                    type="button"
                    className={`flex-1 rounded-xl border px-4 py-2.5 text-left transition ${
                      active
                        ? 'border-teal-600 bg-teal-50'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                    onClick={() => {
                      setInspectionType(type.value)
                      setDeductions(EMPTY_DEDUCTIONS)
                      setBonuses(EMPTY_BONUSES)
                    }}
                  >
                    <span
                      className={`block text-sm font-bold ${
                        active ? 'text-teal-800' : 'text-hub-text'
                      }`}
                    >
                      {type.label}
                    </span>
                    <span className="block text-xs text-hub-muted">{type.description}</span>
                  </button>
                )
              })}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block">
              <span className={LABEL_CLASS}>Team</span>
              <select
                className={FIELD_CLASS}
                value={inspectionTeamId ?? ''}
                onChange={(e) => setInspectionTeamId(Number(e.target.value))}
              >
                <option value="">Select a team…</option>
                {data.teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={LABEL_CLASS}>Date</span>
              <input
                type="date"
                className={FIELD_CLASS}
                value={inspectionDate}
                onChange={(e) => setInspectionDate(e.target.value)}
              />
            </label>
            <label className="block">
              <span className={LABEL_CLASS}>Inspector</span>
              <input
                className={FIELD_CLASS}
                placeholder="Your name"
                value={inspectorName}
                onChange={(e) => setInspectorName(e.target.value)}
              />
            </label>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-xl border border-red-200 bg-red-50/50 p-3">
              <h3 className="mb-2 flex items-center justify-between text-xs font-bold uppercase tracking-wide text-red-800">
                Deductions
                <span>
                  −{scorePreview.major_deductions +
                    scorePreview.moderate_deductions +
                    scorePreview.minor_deductions}
                </span>
              </h3>
              <div className="space-y-1">
                {deductionOptions.map((option) => (
                  <label
                    key={option.key}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-white"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-red-600"
                      checked={deductions[option.key]}
                      onChange={(e) =>
                        setDeductions((prev) => ({ ...prev, [option.key]: e.target.checked }))
                      }
                    />
                    <span className="flex-1 text-hub-text">{option.label}</span>
                    <span className="shrink-0 text-xs font-bold text-red-700">
                      −{option.points}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
                <h3 className="mb-2 flex items-center justify-between text-xs font-bold uppercase tracking-wide text-emerald-800">
                  Bonuses
                  <span>+{scorePreview.bonus_points}</span>
                </h3>
                <div className="space-y-1">
                  {bonusOptions.map((option) => (
                    <label
                      key={option.key}
                      className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-white"
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-300 text-emerald-600"
                        checked={bonuses[option.key]}
                        onChange={(e) =>
                          setBonuses((prev) => ({ ...prev, [option.key]: e.target.checked }))
                        }
                      />
                      <span className="flex-1 text-hub-text">{option.label}</span>
                      <span className="shrink-0 text-xs font-bold text-emerald-700">
                        +{option.points}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <label className="block">
                <span className={LABEL_CLASS}>Notes</span>
                <textarea
                  className={`${FIELD_CLASS} min-h-[6rem]`}
                  placeholder="Anything the team should know for next time…"
                  value={inspectorNotes}
                  onChange={(e) => setInspectorNotes(e.target.value)}
                />
              </label>
            </div>
          </div>
        </div>
      </Modal>

      {/* Create team */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="New team"
        subtitle="Name the crew and pick who starts on it."
        icon="bi-people"
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              onClick={() => setCreateOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
              onClick={() => void submitCreateTeam()}
              disabled={busy}
            >
              {busy ? 'Creating…' : 'Create team'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className={LABEL_CLASS}>Team name</span>
              <input
                className={FIELD_CLASS}
                placeholder="e.g. Team 3"
                value={newTeamName}
                onChange={(e) => setNewTeamName(e.target.value)}
              />
            </label>
            <label className="block">
              <span className={LABEL_CLASS}>Type</span>
              <select
                className={FIELD_CLASS}
                value={newTeamType}
                onChange={(e) => setNewTeamType(e.target.value)}
              >
                {data.team_type_options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block">
            <span className={LABEL_CLASS}>What this team does</span>
            <input
              className={FIELD_CLASS}
              placeholder="e.g. Upstairs classrooms and hallway"
              value={newTeamDescription}
              onChange={(e) => setNewTeamDescription(e.target.value)}
            />
          </label>
          <div>
            <span className={LABEL_CLASS}>Days they work</span>
            <WorkdayPicker days={newTeamDays} onChange={setNewTeamDays} disabled={busy} />
          </div>
          <div>
            <span className={LABEL_CLASS}>
              Starting members ({newTeamStudentIds.length} selected)
            </span>
            <StudentPicker
              students={students}
              selected={newTeamStudentIds}
              onToggle={(id) =>
                setNewTeamStudentIds((prev) =>
                  prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
                )
              }
            />
          </div>
        </div>
      </Modal>

      {/* Edit team */}
      <Modal
        open={!!editTeam}
        onClose={() => setEditTeam(null)}
        title={editTeam ? `Edit ${editTeam.name}` : 'Edit team'}
        subtitle="Rename the team, change what it covers, or set the days it works."
        icon="bi-pencil-square"
        footer={
          <>
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              onClick={() => setEditTeam(null)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
              onClick={() => void submitEditTeam()}
              disabled={busy}
            >
              {busy ? 'Saving…' : 'Save changes'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className={LABEL_CLASS}>Team name</span>
              <input
                className={FIELD_CLASS}
                value={editDraft.name}
                onChange={(e) => setEditDraft((prev) => ({ ...prev, name: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className={LABEL_CLASS}>Type</span>
              <select
                className={FIELD_CLASS}
                value={editDraft.team_type}
                onChange={(e) => setEditDraft((prev) => ({ ...prev, team_type: e.target.value }))}
              >
                {data.team_type_options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block">
            <span className={LABEL_CLASS}>What this team does</span>
            <input
              className={FIELD_CLASS}
              value={editDraft.description}
              onChange={(e) => setEditDraft((prev) => ({ ...prev, description: e.target.value }))}
            />
          </label>
          <div>
            <span className={LABEL_CLASS}>Days they work</span>
            <WorkdayPicker
              days={editDraft.days_of_week}
              onChange={(days) => setEditDraft((prev) => ({ ...prev, days_of_week: days }))}
              disabled={busy}
            />
          </div>
        </div>
      </Modal>

      {/* Manage members */}
      <Modal
        open={!!membersTeam}
        onClose={() => setMembersTeam(null)}
        title={membersTeam ? `${membersTeam.name} — members` : 'Members'}
        subtitle="Add students, change roles, or take someone off the team."
        icon="bi-people"
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              onClick={() => setMembersTeam(null)}
            >
              Done
            </button>
            <button
              type="button"
              className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
              disabled={busy || memberSelection.length === 0 || !membersTeam}
              onClick={async () => {
                if (!membersTeam) return
                const ok = await runAction(() => addTeamMembers(membersTeam.id, memberSelection))
                if (ok) setMemberSelection([])
              }}
            >
              Add {memberSelection.length || ''} student{memberSelection.length === 1 ? '' : 's'}
            </button>
          </>
        }
      >
        {membersTeam ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-teal-200 bg-teal-50 px-3 py-2">
              <p className="mb-0 text-sm font-semibold text-teal-900">
                <i className="bi bi-egg-fried me-1.5" aria-hidden />
                Lunch turns this week: {membersTeam.lunch_served_count} of{' '}
                {membersTeam.members.length} served
              </p>
              <button
                type="button"
                className="rounded-lg border border-teal-300 bg-white px-2.5 py-1 text-xs font-bold text-teal-800 hover:bg-teal-100 disabled:opacity-60"
                disabled={busy || membersTeam.lunch_served_count === 0}
                onClick={() => void runAction(() => resetLunchServiceChecks(membersTeam.id))}
              >
                Clear checks
              </button>
            </div>
            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                On this team ({membersTeam.members.length}) — tick each student once they have served
              </h3>
              {membersTeam.members.length === 0 ? (
                <p className="mb-0 rounded-xl border border-dashed border-slate-200 px-3 py-4 text-center text-sm text-hub-muted">
                  Nobody assigned yet.
                </p>
              ) : (
                <ul className="mb-0 list-none space-y-1 p-0">
                  {membersTeam.members.map((member) => (
                    <li
                      key={member.member_id}
                      className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 px-3 py-2"
                    >
                      <button
                        type="button"
                        disabled={busy}
                        aria-pressed={member.served_lunch}
                        title={
                          member.served_lunch
                            ? 'Served lunch this week — click to undo'
                            : 'Mark as having served lunch this week'
                        }
                        className={[
                          'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-base',
                          member.served_lunch
                            ? 'border-teal-600 bg-teal-600 text-white'
                            : 'border-slate-300 bg-white text-transparent hover:border-teal-400 hover:text-teal-300',
                        ].join(' ')}
                        onClick={() =>
                          void runAction(() =>
                            setLunchServiceCheck(member.member_id, !member.served_lunch),
                          )
                        }
                      >
                        <i className="bi bi-check-lg" aria-hidden />
                      </button>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-semibold text-hub-text">
                          {member.name}
                        </div>
                        <div className="text-xs text-hub-muted">
                          {member.role || 'Team Member'}
                          {member.assignment_description ? ` · ${member.assignment_description}` : ''}
                        </div>
                        <select
                          className="mt-1.5 w-full rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-hub-text focus:border-teal-500 focus:bg-white focus:outline-none"
                          value={member.task_id ?? ''}
                          disabled={busy || membersTeam.duties.length === 0}
                          onChange={(e) => {
                            const value = e.target.value
                            void runAction(() =>
                              updateTeamMember(member.member_id, {
                                task_id: value ? Number(value) : null,
                              }),
                            )
                          }}
                        >
                          <option value="">
                            {membersTeam.duties.length === 0
                              ? 'No duties set up yet'
                              : 'No duty assigned'}
                          </option>
                          {membersTeam.duties.map((duty) => (
                            <option key={duty.id} value={duty.id}>
                              {duty.name}
                              {duty.scoring_type === 'lunch_hall' ? ' (Lunch Hall)' : ''}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <button
                          type="button"
                          className="rounded-lg px-2 py-1 text-xs font-semibold text-teal-700 hover:bg-teal-50"
                          onClick={() => {
                            setEditingMember(member)
                            setEditingRole(member.role || 'Team Member')
                          }}
                        >
                          Edit role
                        </button>
                        <button
                          type="button"
                          className="rounded-lg px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50"
                          onClick={() =>
                            setConfirm({
                              title: 'Remove from team?',
                              body: (
                                <>
                                  <strong>{member.name}</strong> will be taken off{' '}
                                  {membersTeam.name}.
                                </>
                              ),
                              confirmLabel: 'Remove',
                              action: async () => {
                                await runAction(() =>
                                  removeTeamMembers(membersTeam.id, [member.member_id]),
                                )
                              },
                            })
                          }
                        >
                          Remove
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                Add students
              </h3>
              <StudentPicker
                students={students}
                selected={memberSelection}
                query={memberQuery}
                onQueryChange={setMemberQuery}
                excludeIds={membersTeam.members.map((m) => m.id)}
                onToggle={(id) =>
                  setMemberSelection((prev) =>
                    prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
                  )
                }
              />
            </div>
          </div>
        ) : null}
      </Modal>

      {/* Duties */}
      <Modal
        open={!!dutiesTeam}
        onClose={() => {
          setDutiesTeam(null)
          setDutyDraft(null)
        }}
        title={dutiesTeam ? `${dutiesTeam.name} — duties` : 'Duties'}
        subtitle="What this team is responsible for, and who does each part."
        icon="bi-list-check"
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="mr-auto rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              onClick={() => setDutyDraft({ ...EMPTY_DUTY_DRAFT })}
            >
              <i className="bi bi-plus-lg me-1.5" aria-hidden />
              Add duty
            </button>
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              onClick={() => {
                setDutiesTeam(null)
                setDutyDraft(null)
              }}
            >
              Done
            </button>
          </>
        }
      >
        {dutiesTeam ? (
          <div className="space-y-3">
            {dutiesTeam.duties.length === 0 ? (
              <p className="mb-0 rounded-xl border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-hub-muted">
                No duties yet. Add one to describe what this team does.
              </p>
            ) : (
              dutiesTeam.duties.map((duty) => (
                <div key={duty.id} className="rounded-xl border border-slate-200 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold text-hub-text">{duty.name}</span>
                        {duty.area ? (
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                            {duty.area}
                          </span>
                        ) : null}
                        {duty.scoring_type === 'lunch_hall' ? (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-900">
                            Scored separately · Lunch Hall
                          </span>
                        ) : null}
                      </div>
                      {duty.description ? (
                        <p className="mb-0 mt-1 whitespace-pre-wrap text-sm text-hub-muted">
                          {duty.description}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        className="rounded-lg px-2 py-1 text-xs font-semibold text-teal-700 hover:bg-teal-50"
                        onClick={() =>
                          setDutyDraft({
                            id: duty.id,
                            name: duty.name,
                            area: duty.area,
                            description: duty.description,
                            scoring_type: duty.scoring_type,
                          })
                        }
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="rounded-lg px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50"
                        onClick={() =>
                          setConfirm({
                            title: 'Remove this duty?',
                            body: (
                              <>
                                <strong>{duty.name}</strong> will be removed and anyone assigned to
                                it will be left without a duty.
                              </>
                            ),
                            confirmLabel: 'Remove duty',
                            action: async () => {
                              await runAction(() => deleteTeamDuty(duty.id))
                            },
                          })
                        }
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Assigned
                    </span>
                    {duty.assigned.length === 0 ? (
                      <span className="text-xs text-hub-muted">
                        Nobody yet — assign students from the Members tab.
                      </span>
                    ) : (
                      duty.assigned.map((person) => (
                        <span
                          key={person.member_id}
                          className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-semibold text-teal-800"
                        >
                          {person.name}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        ) : null}
      </Modal>

      {/* Add / edit duty */}
      <Modal
        open={!!dutyDraft}
        onClose={() => setDutyDraft(null)}
        title={dutyDraft?.id ? 'Edit duty' : 'Add duty'}
        subtitle={dutiesTeam?.name}
        icon="bi-clipboard-plus"
        footer={
          <>
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              onClick={() => setDutyDraft(null)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
              disabled={busy || !dutyDraft?.name.trim()}
              onClick={async () => {
                if (!dutyDraft || !dutiesTeam) return
                const payload = {
                  name: dutyDraft.name.trim(),
                  area: dutyDraft.area.trim(),
                  description: dutyDraft.description.trim(),
                  scoring_type: dutyDraft.scoring_type,
                }
                const ok = await runAction(() =>
                  dutyDraft.id
                    ? updateTeamDuty(dutyDraft.id, payload)
                    : createTeamDuty(dutiesTeam.id, payload),
                )
                if (ok) setDutyDraft(null)
              }}
            >
              {dutyDraft?.id ? 'Save duty' : 'Add duty'}
            </button>
          </>
        }
      >
        {dutyDraft ? (
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className={LABEL_CLASS}>Duty name</span>
                <input
                  className={FIELD_CLASS}
                  placeholder="e.g. Sweeping Team"
                  value={dutyDraft.name}
                  onChange={(e) => setDutyDraft({ ...dutyDraft, name: e.target.value })}
                />
              </label>
              <label className="block">
                <span className={LABEL_CLASS}>Area</span>
                <input
                  className={FIELD_CLASS}
                  placeholder="e.g. Common Areas"
                  value={dutyDraft.area}
                  onChange={(e) => setDutyDraft({ ...dutyDraft, area: e.target.value })}
                />
              </label>
            </div>
            <label className="block">
              <span className={LABEL_CLASS}>Scored as</span>
              <select
                className={FIELD_CLASS}
                value={dutyDraft.scoring_type}
                onChange={(e) => setDutyDraft({ ...dutyDraft, scoring_type: e.target.value })}
              >
                {inspectionTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-hub-muted">
                Lunch Hall duties are graded on their own checklist instead of the standard cleaning
                one.
              </span>
            </label>
            <label className="block">
              <span className={LABEL_CLASS}>What has to be done</span>
              <textarea
                className={`${FIELD_CLASS} min-h-[8rem]`}
                placeholder={'• Swept top to bottom\n• Trash taken out'}
                value={dutyDraft.description}
                onChange={(e) => setDutyDraft({ ...dutyDraft, description: e.target.value })}
              />
            </label>
          </div>
        ) : null}
      </Modal>

      {/* Team details */}
      <Modal
        open={!!detailTeam}
        onClose={() => setDetailTeam(null)}
        title={detailTeam?.name || 'Team'}
        subtitle={detailTeam ? teamStyle(detailTeam.team_type).label : undefined}
        icon="bi-info-circle"
        size="lg"
      >
        {detailTeam ? (
          <div className="space-y-4 text-sm">
            {detailTeam.description ? (
              <p className="mb-0 text-hub-text">{detailTeam.description}</p>
            ) : null}
            {detailTeam.duties.length > 0 ? (
              <div>
                <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                  Duties
                </h3>
                <ul className="mb-0 list-none space-y-1 p-0">
                  {detailTeam.duties.map((duty) => (
                    <li key={duty.id} className="rounded-lg bg-slate-50 px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-hub-text">{duty.name}</span>
                        {duty.scoring_type === 'lunch_hall' ? (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-900">
                            Scored separately
                          </span>
                        ) : null}
                        {duty.assigned.length > 0 ? (
                          <span className="text-xs text-hub-muted">
                            {duty.assigned.map((p) => p.name).join(', ')}
                          </span>
                        ) : null}
                      </div>
                      {duty.description ? (
                        <p className="mb-0 mt-1 whitespace-pre-wrap text-sm text-hub-muted">
                          {duty.description}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <TeamAreas details={detailTeam.detailed_description} />
            )}
            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                Recent inspections
              </h3>
              {detailTeam.recent_inspections.length === 0 ? (
                <p className="mb-0 text-hub-muted">No inspections yet.</p>
              ) : (
                <ul className="mb-0 list-none space-y-1 p-0">
                  {detailTeam.recent_inspections.map((inspection) => (
                    <li
                      key={inspection.id}
                      className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2"
                    >
                      <span className="text-hub-text">{formatDate(inspection.date)}</span>
                      <span className="text-hub-muted">{inspection.inspector_name}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                          scoreTone(inspection.score).chip
                        }`}
                      >
                        {inspection.score}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ) : null}
      </Modal>

      {/* Inspection detail */}
      <Modal
        open={detailLoading || !!detail}
        onClose={() => {
          setDetail(null)
          setDetailLoading(false)
        }}
        title="Inspection details"
        subtitle={detail ? `${detail.team_name} · ${formatDate(detail.date)}` : undefined}
        icon="bi-clipboard-data"
        size="lg"
      >
        {detailLoading || !detail ? (
          <p className="mb-0 py-6 text-center text-hub-muted">Loading…</p>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-4">
              <span
                className={`rounded-full px-4 py-1.5 text-2xl font-extrabold ${
                  scoreTone(detail.score).chip
                }`}
              >
                {detail.score}
              </span>
              <div className="text-sm">
                <div className="font-bold text-hub-text">{detail.status}</div>
                <div className="text-hub-muted">Inspected by {detail.inspector_name}</div>
              </div>
              <div className="ml-auto grid grid-cols-2 gap-x-4 text-xs text-hub-muted">
                <span>Starting</span>
                <span className="font-bold text-hub-text">{detail.starting_score ?? 100}</span>
                <span>Bonus</span>
                <span className="font-bold text-emerald-700">+{detail.bonus_points ?? 0}</span>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-red-700">
                  Deductions
                </h3>
                {detail.deductions?.length ? (
                  <ul className="mb-0 list-none space-y-1 p-0 text-sm">
                    {detail.deductions.map((label) => (
                      <li key={label} className="rounded-lg bg-red-50 px-3 py-1.5 text-hub-text">
                        {label}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mb-0 text-sm text-hub-muted">None — clean inspection.</p>
                )}
              </div>
              <div>
                <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-emerald-700">
                  Bonuses
                </h3>
                {detail.bonuses?.length ? (
                  <ul className="mb-0 list-none space-y-1 p-0 text-sm">
                    {detail.bonuses.map((label) => (
                      <li key={label} className="rounded-lg bg-emerald-50 px-3 py-1.5 text-hub-text">
                        {label}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mb-0 text-sm text-hub-muted">None awarded.</p>
                )}
              </div>
            </div>

            {detail.inspector_notes ? (
              <div>
                <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-hub-muted">
                  Inspector notes
                </h3>
                <p className="mb-0 whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-hub-text">
                  {detail.inspector_notes}
                </p>
              </div>
            ) : null}
          </div>
        )}
      </Modal>

      <PromptDialog
        open={!!editingMember}
        title="Edit role"
        label={editingMember ? `Role for ${editingMember.name}` : 'Role'}
        value={editingRole}
        placeholder="e.g. Team Captain"
        busy={busy}
        onChange={setEditingRole}
        onCancel={() => setEditingMember(null)}
        onConfirm={async () => {
          if (!editingMember) return
          const ok = await runAction(() =>
            updateTeamMember(editingMember.member_id, { role: editingRole.trim() }),
          )
          if (ok) setEditingMember(null)
        }}
      />

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.title || ''}
        body={confirm?.body}
        confirmLabel={confirm?.confirmLabel}
        busy={busy}
        onCancel={() => setConfirm(null)}
        onConfirm={async () => {
          const pending = confirm
          setConfirm(null)
          await pending?.action()
        }}
      />
    </ManagementPageShell>
  )
}

function StudentPicker({
  students,
  selected,
  onToggle,
  query,
  onQueryChange,
  excludeIds = [],
}: {
  students: StudentJobsStudentOption[]
  selected: number[]
  onToggle: (id: number) => void
  query?: string
  onQueryChange?: (value: string) => void
  excludeIds?: number[]
}) {
  const [localQuery, setLocalQuery] = useState('')
  const value = query ?? localQuery
  const setValue = onQueryChange ?? setLocalQuery

  const excluded = new Set(excludeIds)
  const needle = value.trim().toLowerCase()
  const visible = students.filter((student) => {
    if (excluded.has(student.id)) return false
    if (!needle) return true
    return `${student.first_name} ${student.last_name} ${student.student_id}`
      .toLowerCase()
      .includes(needle)
  })

  return (
    <div className="rounded-xl border border-slate-200">
      <div className="border-b border-slate-200 p-2">
        <input
          type="search"
          className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-teal-500 focus:bg-white focus:outline-none"
          placeholder="Search students…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </div>
      <div className="max-h-56 overflow-y-auto p-2">
        {students.length === 0 ? (
          <p className="mb-0 py-4 text-center text-sm text-hub-muted">Loading students…</p>
        ) : visible.length === 0 ? (
          <p className="mb-0 py-4 text-center text-sm text-hub-muted">No students match.</p>
        ) : (
          visible.map((student) => (
            <label
              key={student.id}
              className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50"
            >
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-teal-600"
                checked={selected.includes(student.id)}
                onChange={() => onToggle(student.id)}
              />
              <span className="flex-1 text-hub-text">
                {student.first_name} {student.last_name}
              </span>
              <span className="shrink-0 text-xs text-hub-muted">{student.student_id}</span>
            </label>
          ))
        )}
      </div>
    </div>
  )
}

export default StudentJobsPage

function TeamAreas({ details }: { details: Record<string, unknown> }) {
  if (!details || typeof details !== 'object') return null

  const description = typeof details.description === 'string' ? details.description : null
  const groups = Object.entries(details).filter(
    ([key, value]) => key !== 'description' && value && typeof value === 'object',
  )

  if (!description && groups.length === 0) return null

  return (
    <div className="space-y-3">
      {description ? <p className="mb-0 text-hub-text">{description}</p> : null}
      {groups.map(([key, value]) => (
        <div key={key}>
          <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-hub-muted">
            {key.replace(/_/g, ' ')}
          </h3>
          <ul className="mb-0 list-none space-y-1 p-0">
            {Object.entries(value as Record<string, unknown>).map(([area, detail]) => (
              <li key={area} className="rounded-lg bg-slate-50 px-3 py-1.5">
                <span className="font-semibold text-hub-text">{area}</span>
                {detail ? <span className="text-hub-muted"> — {String(detail)}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}
