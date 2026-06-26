import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  addTeamMembers,
  fetchInspectionDetail,
  fetchStudentJobsHub,
  fetchStudentJobsStudents,
  removeTeamMembers,
  saveStudentJobsInspection,
  updateTeamMember,
} from '../api/studentJobs'
import type { StudentJobsHubResponse, StudentJobsTeam } from '../types/studentJobs'
import {
  calculateCleaningInspectionScore,
  scoreBadgeClass,
  type CleaningBonuses,
  type CleaningDeductions,
} from '../utils/studentJobsScoring'
import { spaRoute } from '../utils/spaRoute'

const EMPTY_DEDUCTIONS: CleaningDeductions = {
  bathroom_not_restocked: false,
  trash_can_left_full: false,
  floor_not_swept: false,
  materials_left_out: false,
  tables_missed: false,
  classroom_trash_full: false,
  bathroom_floor_poor: false,
  not_finished_on_time: false,
  small_debris_left: false,
  trash_spilled: false,
  dispensers_half_filled: false,
}

const EMPTY_BONUSES: CleaningBonuses = {
  exceptional_finish: false,
  speed_efficiency: false,
  going_above_beyond: false,
  teamwork_award: false,
}

function localDateInputValue(d = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function TeamDescription({ team }: { team: StudentJobsTeam }) {
  const details = team.detailed_description
  if (details.description && typeof details.description === 'string') {
    return <p className="whitespace-pre-wrap text-sm text-hub-muted">{details.description}</p>
  }
  const classrooms = details.classrooms as Record<string, string> | undefined
  const commonAreas = details.common_areas as Record<string, string> | undefined
  return (
    <div className="space-y-3 text-sm text-hub-muted">
      {classrooms
        ? Object.entries(classrooms).map(([name, text]) => (
            <div key={name}>
              <div className="font-semibold text-hub-text">{name}</div>
              <p className="whitespace-pre-wrap">{text}</p>
            </div>
          ))
        : null}
      {commonAreas
        ? Object.entries(commonAreas).map(([name, text]) => (
            <div key={name}>
              <div className="font-semibold text-hub-text">{name}</div>
              <p className="whitespace-pre-wrap">{text}</p>
            </div>
          ))
        : null}
    </div>
  )
}

export default function StudentJobsPage() {
  const [data, setData] = useState<StudentJobsHubResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [expandedTeamId, setExpandedTeamId] = useState<number | null>(null)
  const [inspectionOpen, setInspectionOpen] = useState(false)
  const [addMembersTeamId, setAddMembersTeamId] = useState<number | null>(null)
  const [students, setStudents] = useState<Array<{ id: number; label: string }>>([])
  const [selectedStudentIds, setSelectedStudentIds] = useState<number[]>([])
  const [busy, setBusy] = useState(false)

  const [inspectionTeamId, setInspectionTeamId] = useState<number | ''>('')
  const [inspectionDate, setInspectionDate] = useState(localDateInputValue())
  const [inspectorName, setInspectorName] = useState('')
  const [inspectorNotes, setInspectorNotes] = useState('')
  const [deductions, setDeductions] = useState<CleaningDeductions>(EMPTY_DEDUCTIONS)
  const [bonuses, setBonuses] = useState<CleaningBonuses>(EMPTY_BONUSES)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchStudentJobsHub())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load student jobs.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const scorePreview = useMemo(
    () => calculateCleaningInspectionScore(deductions, bonuses),
    [deductions, bonuses],
  )

  async function openAddMembers(teamId: number) {
    setAddMembersTeamId(teamId)
    setSelectedStudentIds([])
    try {
      const roster = await fetchStudentJobsStudents()
      setStudents(
        roster.map((student) => ({
          id: student.id,
          label: `${student.first_name} ${student.last_name}`.trim(),
        })),
      )
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not load students.')
    }
  }

  async function handleAddMembers() {
    if (!addMembersTeamId || !selectedStudentIds.length) return
    setBusy(true)
    try {
      const result = await addTeamMembers(addMembersTeamId, selectedStudentIds)
      setMessage(result.message || 'Members added.')
      setAddMembersTeamId(null)
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not add members.')
    } finally {
      setBusy(false)
    }
  }

  async function handleRemoveMember(teamId: number, memberId: number) {
    if (!window.confirm('Remove this team member?')) return
    setBusy(true)
    try {
      await removeTeamMembers(teamId, [memberId])
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not remove member.')
    } finally {
      setBusy(false)
    }
  }

  async function handleEditMember(memberId: number, role: string) {
    const nextRole = window.prompt('Member role', role)
    if (nextRole === null) return
    setBusy(true)
    try {
      await updateTeamMember(memberId, { role: nextRole })
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not update member.')
    } finally {
      setBusy(false)
    }
  }

  async function handleSubmitInspection(event: React.FormEvent) {
    event.preventDefault()
    if (!inspectionTeamId || !inspectorName.trim()) return
    setBusy(true)
    try {
      const result = await saveStudentJobsInspection({
        team_id: Number(inspectionTeamId),
        inspection_date: inspectionDate,
        inspector_name: inspectorName.trim(),
        inspector_notes: inspectorNotes,
        ...scorePreview,
        ...deductions,
        ...bonuses,
      })
      setMessage(result.message || 'Inspection submitted.')
      setInspectionOpen(false)
      setDeductions(EMPTY_DEDUCTIONS)
      setBonuses(EMPTY_BONUSES)
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not submit inspection.')
    } finally {
      setBusy(false)
    }
  }

  async function viewInspection(inspectionId: number) {
    try {
      const result = await fetchInspectionDetail(inspectionId)
      const inspection = result.inspection
      window.alert(
        `Team: ${inspection.team_name}\nScore: ${inspection.score}\nInspector: ${inspection.inspector_name}\nNotes: ${inspection.inspector_notes || '—'}`,
      )
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not load inspection.')
    }
  }

  if (loading && !data) {
    return <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted">Loading student jobs…</div>
  }

  if (error || !data) {
    return <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">{error || 'Could not load student jobs.'}</div>
  }

  const shellClass = data.is_director
    ? 'bg-gradient-to-br from-violet-50 via-[#f0ecf5] to-[#e8e4f0]'
    : 'bg-gradient-to-br from-emerald-50 via-[#e8f0ec] to-[#dce8e4]'

  return (
    <div className={`rounded-3xl p-5 shadow-sm md:p-6 ${shellClass}`}>
      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Student jobs</p>
          <h1 className="mt-1 text-2xl font-bold text-hub-text">Student jobs</h1>
          <p className="mt-2 text-sm text-hub-muted">
            <i className="bi bi-briefcase-fill mr-1 text-emerald-700" aria-hidden />
            Cleaning crews, inspections, and team management
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to={spaRoute(data.urls.home)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text"
          >
            <i className="bi bi-house-door" aria-hidden />
            Dashboard
          </Link>
          <button
            type="button"
            onClick={() => setInspectionOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
          >
            <i className="bi bi-clipboard-check" aria-hidden />
            Conduct inspection
          </button>
        </div>
      </header>

      {message ? (
        <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">{message}</div>
      ) : null}

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Teams', data.summary.teams],
          ['Members', data.summary.members],
          ['Inspections', data.summary.inspections],
          ['Passed', data.summary.passed],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-white/80 bg-white/95 p-4 shadow-sm">
            <div className="text-xl font-bold text-hub-text">{value}</div>
            <div className="text-sm text-hub-muted">{label}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
        <h2 className="font-bold text-emerald-900">Cleaning crew point system</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-4 text-center text-sm">
          <div>
            <div className="text-lg font-bold text-hub-text">{data.point_system.starting_points}</div>
            <div className="text-hub-muted">Starting points</div>
          </div>
          <div>
            <div className="text-lg font-bold text-hub-text">{data.point_system.redo_threshold}</div>
            <div className="text-hub-muted">Re-do threshold</div>
          </div>
          <div>
            <div className="text-lg font-bold text-hub-text">+{data.point_system.max_bonus}</div>
            <div className="text-hub-muted">Max bonus</div>
          </div>
          <div>
            <div className="text-lg font-bold text-hub-text">{data.point_system.deduction_levels}</div>
            <div className="text-hub-muted">Deduction levels</div>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {data.teams.map((team) => (
          <section key={team.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4">
              <div>
                <h3 className="font-bold text-hub-text">{team.name}</h3>
                <p className="text-sm text-hub-muted">{team.members.length} members · {team.team_type}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-sm font-bold ${scoreBadgeClass(team.current_score)}`}>
                {team.current_score} pts
              </span>
            </div>
            <div className="p-5">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setExpandedTeamId((id) => (id === team.id ? null : team.id))}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold"
                >
                  {expandedTeamId === team.id ? 'Hide details' : 'View details'}
                </button>
                <button
                  type="button"
                  onClick={() => void openAddMembers(team.id)}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold"
                >
                  Add members
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setInspectionTeamId(team.id)
                    setInspectionOpen(true)
                  }}
                  className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white"
                >
                  Inspect team
                </button>
              </div>

              {expandedTeamId === team.id ? (
                <div className="mt-4 space-y-4">
                  <TeamDescription team={team} />
                  <div>
                    <h4 className="text-sm font-bold text-hub-text">Members</h4>
                    <ul className="mt-2 space-y-2">
                      {team.members.map((member) => (
                        <li
                          key={member.member_id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 px-3 py-2 text-sm"
                        >
                          <div>
                            <div className="font-semibold text-hub-text">{member.name}</div>
                            <div className="text-hub-muted">{member.role || 'Team member'}</div>
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => void handleEditMember(member.member_id, member.role)}
                              className="text-xs font-semibold text-violet-700"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleRemoveMember(team.id, member.member_id)}
                              className="text-xs font-semibold text-red-700"
                            >
                              Remove
                            </button>
                          </div>
                        </li>
                      ))}
                      {!team.members.length ? (
                        <li className="text-sm text-hub-muted">No members assigned yet.</li>
                      ) : null}
                    </ul>
                  </div>
                </div>
              ) : null}
            </div>
          </section>
        ))}
      </div>

      <section className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
          <h2 className="font-bold text-hub-text">Recent inspection history</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-hub-muted">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Inspector</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.inspection_history.map((item) => (
                <tr key={item.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">{item.date}</td>
                  <td className="px-4 py-3">{item.team_name}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-1 text-xs font-bold ${scoreBadgeClass(item.score)}`}>
                      {item.score}
                    </span>
                  </td>
                  <td className="px-4 py-3">{item.status}</td>
                  <td className="px-4 py-3">{item.inspector_name}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => void viewInspection(item.id)}
                      className="text-xs font-semibold text-violet-700"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {inspectionOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={(e) => void handleSubmitInspection(e)}
            className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl"
          >
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-bold text-hub-text">Conduct inspection</h2>
              <button type="button" onClick={() => setInspectionOpen(false)} className="text-hub-muted">
                <i className="bi bi-x-lg" aria-hidden />
              </button>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-sm text-hub-muted">
                Team
                <select
                  required
                  value={inspectionTeamId}
                  onChange={(e) => setInspectionTeamId(e.target.value ? Number(e.target.value) : '')}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="">Choose a team…</option>
                  {data.teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-hub-muted">
                Date
                <input
                  type="date"
                  required
                  value={inspectionDate}
                  onChange={(e) => setInspectionDate(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <label className="text-sm text-hub-muted sm:col-span-2">
                Inspector name
                <input
                  required
                  value={inspectorName}
                  onChange={(e) => setInspectorName(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
            </div>

            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4">
              <h3 className="font-bold text-red-900">Cleanup deductions</h3>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(deductions).map(([key, value]) => (
                  <label key={key} className="flex items-center gap-2 text-sm text-hub-text">
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={(e) =>
                        setDeductions((prev) => ({ ...prev, [key]: e.target.checked }))
                      }
                    />
                    {key.replace(/_/g, ' ')}
                  </label>
                ))}
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
              <h3 className="font-bold text-emerald-900">Bonuses</h3>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(bonuses).map(([key, value]) => (
                  <label key={key} className="flex items-center gap-2 text-sm text-hub-text">
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={(e) => setBonuses((prev) => ({ ...prev, [key]: e.target.checked }))}
                    />
                    {key.replace(/_/g, ' ')}
                  </label>
                ))}
              </div>
            </div>

            <label className="mt-4 block text-sm text-hub-muted">
              Notes
              <textarea
                rows={3}
                value={inspectorNotes}
                onChange={(e) => setInspectorNotes(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              />
            </label>

            <div className="mt-4 flex items-center justify-between gap-3">
              <span className={`rounded-full px-3 py-1 text-sm font-bold ${scoreBadgeClass(scorePreview.final_score)}`}>
                Live score: {scorePreview.final_score}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setInspectionOpen(false)}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  Submit inspection
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}

      {addMembersTeamId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl">
            <h2 className="text-lg font-bold text-hub-text">Add team members</h2>
            <div className="mt-4 max-h-72 overflow-y-auto space-y-2">
              {students.map((student) => (
                <label key={student.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedStudentIds.includes(student.id)}
                    onChange={(e) =>
                      setSelectedStudentIds((ids) =>
                        e.target.checked ? [...ids, student.id] : ids.filter((id) => id !== student.id),
                      )
                    }
                  />
                  {student.label}
                </label>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAddMembersTeamId(null)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy || !selectedStudentIds.length}
                onClick={() => void handleAddMembers()}
                className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                Add selected
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
