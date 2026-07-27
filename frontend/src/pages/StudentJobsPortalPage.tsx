import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchStudentJobsHub } from '../api/studentTabs'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { StudentJobsHubResponse, StudentJobsTeam } from '../types/studentJobs'
import { scoreBadgeClass } from '../utils/studentJobsScoring'

function formatDate(value: string) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function teamTypeLabel(type: string) {
  const t = (type || '').toLowerCase()
  if (t === 'cleaning') return 'Cleaning'
  if (t === 'computer') return 'Computer'
  if (t === 'lunch_duty') return 'Lunch duty'
  if (t === 'experiment_duty') return 'Experiment duty'
  return 'Team'
}

export function StudentJobsPortalPage() {
  const [data, setData] = useState<(StudentJobsHubResponse & { can_manage?: boolean }) | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchStudentJobsHub())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load student jobs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const filtered = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    if (!q) return data.teams
    return data.teams.filter((t) => {
      const hay = `${t.name} ${t.description} ${t.team_type} ${t.members.map((m) => m.name).join(' ')}`.toLowerCase()
      return hay.includes(q)
    })
  }, [data, query])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading student jobs…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <>
              <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
                    Student portal
                  </p>
                  <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Student jobs</h1>
                  <p className="mb-0 mt-1 text-sm text-teal-50/95">
                    Cleaning crews, computer teams, and other campus jobs · view only
                  </p>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <HeroStat label="Teams" value={data.summary.teams} />
                  <HeroStat label="Members" value={data.summary.members} />
                  <HeroStat label="Inspections" value={data.summary.inspections} />
                  <HeroStat label="Passed" value={data.summary.passed} />
                </div>
              </header>

              <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-hub-muted">
                  Point system
                </h2>
                <p className="mb-0 text-sm text-hub-text">
                  Teams start at <strong>{data.point_system.starting_points}</strong> points each week.
                  Scores under <strong>{data.point_system.redo_threshold}</strong> require a redo.
                  Deductions: {data.point_system.deduction_levels}. Max bonus:{' '}
                  {data.point_system.max_bonus}.
                </p>
              </div>

              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="mb-0 text-lg font-bold text-hub-text">Teams</h2>
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search teams…"
                  className="w-full max-w-xs rounded-full border border-slate-300 px-4 py-2 text-sm"
                />
              </div>

              {filtered.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-5 py-10 text-center text-sm text-hub-muted">
                  No teams match your search.
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {filtered.map((team) => (
                    <TeamCard
                      key={team.id}
                      team={team}
                      open={Boolean(expanded[team.id])}
                      onToggle={() =>
                        setExpanded((prev) => ({ ...prev, [team.id]: !prev[team.id] }))
                      }
                    />
                  ))}
                </div>
              )}

              <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-4 py-3">
                  <h2 className="mb-0 text-base font-bold text-hub-text">Recent inspections</h2>
                </div>
                <div className="p-4">
                  {data.inspection_history.length ? (
                    <ul className="mb-0 space-y-2">
                      {data.inspection_history.map((item) => (
                        <li
                          key={item.id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5 text-sm"
                        >
                          <div>
                            <p className="mb-0 font-semibold text-hub-text">{item.team_name}</p>
                            <p className="mb-0 text-xs text-hub-muted">
                              {formatDate(item.date)} · {item.inspector_name}
                            </p>
                          </div>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${scoreBadgeClass(item.score)}`}>
                            {item.score} · {item.status}
                          </span>
                        </li>
                      ))}
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
    </ManagementPageShell>
  )
}

function HeroStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-100">{label}</p>
      <p className="mb-0 text-2xl font-bold">{value}</p>
    </div>
  )
}

function TeamCard({
  team,
  open,
  onToggle,
}: {
  team: StudentJobsTeam
  open: boolean
  onToggle: () => void
}) {
  return (
    <article className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="bg-gradient-to-r from-teal-700 to-emerald-600 px-4 py-3 text-white">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="mb-0 text-[10px] font-bold uppercase tracking-wide text-teal-100">
              {teamTypeLabel(team.team_type)}
            </p>
            <h3 className="mb-0 truncate text-base font-bold">{team.name}</h3>
          </div>
          <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${scoreBadgeClass(team.current_score)}`}>
            {team.current_score}
          </span>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        {team.description ? <p className="mb-0 text-sm text-hub-muted">{team.description}</p> : null}
        <div>
          <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-hub-muted">
            Members ({team.members.length})
          </p>
          {team.members.length ? (
            <ul className="mb-0 space-y-1">
              {team.members.slice(0, open ? undefined : 4).map((m) => (
                <li key={m.member_id} className="text-sm text-hub-text">
                  <strong>{m.name}</strong>
                  {m.role ? <span className="text-hub-muted"> · {m.role}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mb-0 text-sm text-hub-muted">No members listed</p>
          )}
          {team.members.length > 4 ? (
            <button
              type="button"
              onClick={onToggle}
              className="mt-2 text-xs font-bold text-teal-800 hover:underline"
            >
              {open ? 'Show less' : `Show all ${team.members.length}`}
            </button>
          ) : null}
        </div>
        {team.recent_inspections.length ? (
          <div>
            <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-hub-muted">
              Latest inspection
            </p>
            <p className="mb-0 text-sm text-hub-text">
              {formatDate(team.recent_inspections[0].date)} · score{' '}
              <strong>{team.recent_inspections[0].score}</strong>
            </p>
          </div>
        ) : null}
      </div>
    </article>
  )
}
