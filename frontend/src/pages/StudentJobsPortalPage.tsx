import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchStudentJobsHub } from '../api/studentTabs'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import { Modal } from '../components/ui/Modal'
import type { StudentJobsHubResponse, StudentJobsTeam } from '../types/studentJobs'

type PortalPayload = StudentJobsHubResponse & {
  can_manage?: boolean
  my_student_id?: number | null
  my_team_ids?: number[]
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
  other: { label: 'Team', chip: 'bg-slate-100 text-slate-700', icon: 'bi-briefcase' },
}

function teamStyle(type: string) {
  return TEAM_TYPE_STYLE[(type || '').toLowerCase()] || TEAM_TYPE_STYLE.other
}

function scoreTone(score: number) {
  if (score < 60) return { chip: 'bg-red-100 text-red-800', bar: 'bg-red-500' }
  if (score < 80) return { chip: 'bg-amber-100 text-amber-900', bar: 'bg-amber-500' }
  return { chip: 'bg-emerald-100 text-emerald-800', bar: 'bg-emerald-500' }
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function HeroStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-100">{label}</p>
      <p className="mb-0 text-2xl font-bold">{value}</p>
    </div>
  )
}

function Sparkline({ scores }: { scores: number[] }) {
  if (scores.length < 2) return null
  return (
    <div className="flex h-8 items-end gap-1" aria-hidden>
      {scores.map((score, index) => (
        <div
          key={`${index}-${score}`}
          className={`flex-1 rounded-t ${scoreTone(score).bar}`}
          style={{ height: `${Math.max(8, Math.min(100, score))}%` }}
        />
      ))}
    </div>
  )
}

function TeamCard({
  team,
  isMine,
  onOpen,
}: {
  team: StudentJobsTeam
  isMine: boolean
  onOpen: () => void
}) {
  const style = teamStyle(team.team_type)
  const tone = scoreTone(team.current_score)
  const visibleMembers = team.members.slice(0, 5)
  const overflow = team.members.length - visibleMembers.length

  return (
    <article
      className={`flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm transition hover:shadow-md ${
        isMine ? 'border-teal-400 ring-2 ring-teal-200' : 'border-slate-200'
      }`}
    >
      <div className="flex items-start justify-between gap-2 border-b border-slate-200 bg-slate-50 px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${style.chip}`}
            >
              <i className={`bi ${style.icon}`} aria-hidden />
              {style.label}
            </span>
            {isMine ? (
              <span className="rounded-full bg-teal-600 px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                Your team
              </span>
            ) : null}
          </div>
          <h3 className="mb-0 mt-1 truncate text-base font-bold text-hub-text">{team.name}</h3>
        </div>
        <span className={`shrink-0 rounded-full px-3 py-1 text-lg font-extrabold ${tone.chip}`}>
          {team.current_score}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        {team.description ? (
          <p className="mb-0 text-sm text-hub-muted">{team.description}</p>
        ) : null}

        <Sparkline scores={team.stats.sparkline} />

        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-xl bg-slate-50 px-2 py-1.5">
            <div className="text-sm font-extrabold text-hub-text">
              {team.stats.average_score ?? '—'}
            </div>
            <div className="text-[10px] font-bold uppercase text-hub-muted">Average</div>
          </div>
          <div className="rounded-xl bg-slate-50 px-2 py-1.5">
            <div className="text-sm font-extrabold text-hub-text">
              {team.stats.pass_rate != null ? `${team.stats.pass_rate}%` : '—'}
            </div>
            <div className="text-[10px] font-bold uppercase text-hub-muted">Passed</div>
          </div>
          <div className="rounded-xl bg-slate-50 px-2 py-1.5">
            <div className="text-sm font-extrabold text-hub-text">
              {team.stats.inspection_count}
            </div>
            <div className="text-[10px] font-bold uppercase text-hub-muted">Checks</div>
          </div>
        </div>

        {team.members.length === 0 ? (
          <p className="mb-0 text-sm text-hub-muted">No members listed.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {visibleMembers.map((member) => (
              <span
                key={member.member_id}
                className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700"
              >
                {member.name}
              </span>
            ))}
            {overflow > 0 ? (
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
                +{overflow} more
              </span>
            ) : null}
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={onOpen}
        className="border-t border-slate-200 px-4 py-2.5 text-sm font-bold text-teal-800 transition hover:bg-teal-50"
      >
        View team
      </button>
    </article>
  )
}

export function StudentJobsPortalPage() {
  const [data, setData] = useState<PortalPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [openTeam, setOpenTeam] = useState<StudentJobsTeam | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData((await fetchStudentJobsHub()) as PortalPayload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load student jobs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const myTeamIds = useMemo(() => new Set(data?.my_team_ids || []), [data?.my_team_ids])

  const sortedTeams = useMemo(() => {
    if (!data) return []
    const needle = query.trim().toLowerCase()
    const matches = data.teams.filter((team) => {
      if (!needle) return true
      return `${team.name} ${team.description} ${team.members.map((m) => m.name).join(' ')}`
        .toLowerCase()
        .includes(needle)
    })
    // Your own teams first, then the rest alphabetically.
    return [...matches].sort((a, b) => {
      const mine = Number(myTeamIds.has(b.id)) - Number(myTeamIds.has(a.id))
      return mine !== 0 ? mine : a.name.localeCompare(b.name)
    })
  }, [data, query, myTeamIds])

  const passRate = useMemo(() => {
    const total = data?.summary.inspections || 0
    if (!total) return '—'
    return `${Math.round((100 * (data?.summary.passed || 0)) / total)}%`
  }, [data?.summary])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-hub-muted">
              Loading student jobs…
            </div>
          ) : error && !data ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
              {error}
            </div>
          ) : data ? (
            <>
              <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
                  Student portal
                </p>
                <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Student jobs</h1>
                <p className="mb-0 mt-1 text-sm text-teal-50/95">
                  {myTeamIds.size > 0
                    ? 'Your crew is highlighted below — check your score and see who you are working with.'
                    : 'Cleaning crews, computer teams, and other campus jobs.'}
                </p>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <HeroStat label="Teams" value={data.summary.teams} />
                  <HeroStat label="Students" value={data.summary.members} />
                  <HeroStat label="Inspections" value={data.summary.inspections} />
                  <HeroStat label="Pass rate" value={passRate} />
                </div>
              </header>

              <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                  How scoring works
                </h2>
                <p className="mb-0 text-sm text-hub-text">
                  Every team starts the week at{' '}
                  <strong>{data.point_system.starting_points}</strong> points. Inspectors take points
                  off for problems ({data.point_system.deduction_levels}) and add up to{' '}
                  <strong>+{data.point_system.max_bonus}</strong> for great work. Below{' '}
                  <strong>{data.point_system.redo_threshold}</strong> means the job has to be redone.
                </p>
              </div>

              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="mb-0 text-lg font-bold text-hub-text">Teams</h2>
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search teams or students…"
                  className="w-full max-w-xs rounded-full border border-slate-300 px-4 py-2 text-sm focus:border-teal-500 focus:outline-none"
                />
              </div>

              {sortedTeams.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-12 text-center">
                  <i className="bi bi-people text-3xl text-slate-300" aria-hidden />
                  <p className="mb-0 mt-2 text-sm text-hub-muted">No teams match your search.</p>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {sortedTeams.map((team) => (
                    <TeamCard
                      key={team.id}
                      team={team}
                      isMine={myTeamIds.has(team.id)}
                      onOpen={() => setOpenTeam(team)}
                    />
                  ))}
                </div>
              )}

              <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-200 bg-slate-50 px-5 py-3">
                  <h2 className="mb-0 font-bold text-hub-text">Recent inspections</h2>
                  <p className="mb-0 text-sm text-hub-muted">The latest results across all teams</p>
                </div>
                <div className="p-4">
                  {data.inspection_history.length ? (
                    <ul className="mb-0 list-none space-y-2 p-0">
                      {data.inspection_history.map((item) => {
                        const passed = item.score >= 60
                        return (
                          <li
                            key={item.id}
                            className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2.5 text-sm ${
                              myTeamIds.has(item.team_id)
                                ? 'border-teal-200 bg-teal-50/60'
                                : 'border-slate-100 bg-slate-50'
                            }`}
                          >
                            <div>
                              <p className="mb-0 font-semibold text-hub-text">{item.team_name}</p>
                              <p className="mb-0 text-xs text-hub-muted">
                                {formatDate(item.date)} · {item.inspector_name}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <span
                                className={`inline-flex items-center gap-1 text-xs font-bold ${
                                  passed ? 'text-emerald-700' : 'text-red-700'
                                }`}
                              >
                                <i
                                  className={`bi ${
                                    passed ? 'bi-check-circle-fill' : 'bi-x-circle-fill'
                                  }`}
                                  aria-hidden
                                />
                                {passed ? 'Passed' : 'Redo'}
                              </span>
                              <span
                                className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                                  scoreTone(item.score).chip
                                }`}
                              >
                                {item.score}
                              </span>
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  ) : (
                    <p className="mb-0 text-sm text-hub-muted">No inspections yet.</p>
                  )}
                </div>
              </section>
            </>
          ) : null}
        </div>
      </div>

      <Modal
        open={!!openTeam}
        onClose={() => setOpenTeam(null)}
        title={openTeam?.name || 'Team'}
        subtitle={openTeam ? teamStyle(openTeam.team_type).label : undefined}
        icon="bi-people"
        size="lg"
      >
        {openTeam ? (
          <div className="space-y-4 text-sm">
            {openTeam.description ? (
              <p className="mb-0 text-hub-text">{openTeam.description}</p>
            ) : null}

            <div className="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-4">
              <span
                className={`rounded-full px-4 py-1.5 text-2xl font-extrabold ${
                  scoreTone(openTeam.current_score).chip
                }`}
              >
                {openTeam.current_score}
              </span>
              <div>
                <div className="font-bold text-hub-text">Current score</div>
                <div className="text-hub-muted">
                  {openTeam.stats.last_inspected
                    ? `Last inspected ${formatDate(openTeam.stats.last_inspected)}`
                    : 'Not inspected yet'}
                </div>
              </div>
            </div>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                Members ({openTeam.members.length})
              </h3>
              {openTeam.members.length === 0 ? (
                <p className="mb-0 text-hub-muted">No members listed.</p>
              ) : (
                <ul className="mb-0 list-none space-y-1 p-0">
                  {openTeam.members.map((member) => (
                    <li
                      key={member.member_id}
                      className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-1.5"
                    >
                      <span className="font-semibold text-hub-text">{member.name}</span>
                      <span className="text-xs text-hub-muted">
                        {member.role || 'Team Member'}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                Recent inspections
              </h3>
              {openTeam.recent_inspections.length === 0 ? (
                <p className="mb-0 text-hub-muted">No inspections yet.</p>
              ) : (
                <ul className="mb-0 list-none space-y-1 p-0">
                  {openTeam.recent_inspections.map((inspection) => (
                    <li
                      key={inspection.id}
                      className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-1.5"
                    >
                      <span className="text-hub-text">{formatDate(inspection.date)}</span>
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
    </ManagementPageShell>
  )
}

export default StudentJobsPortalPage
