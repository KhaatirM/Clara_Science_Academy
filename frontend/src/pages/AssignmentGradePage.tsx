import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import {
  fetchGroupAssignmentGrade,
  fetchIndividualAssignmentGrade,
  saveGroupAssignmentGrades,
  saveIndividualStudentGrade,
  type AssignmentGradeResponse,
  type GradeStudentRow,
} from '../api/assignmentWorkspace'

type RowDraft = {
  score: string
  comment: string
  submission_type: string
  submission_notes_type: string
  submission_notes: string
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function rowKey(row: GradeStudentRow) {
  return `${row.group_id ?? 0}-${row.student.id}`
}

function draftFromRow(row: GradeStudentRow): RowDraft {
  const score = row.grade.score
  return {
    score: score != null && score > 0 ? String(score) : '',
    comment: row.grade.comment || '',
    submission_type: row.submission?.submission_type || row.submission_type || 'not_submitted',
    submission_notes_type: 'On-Time',
    submission_notes: row.submission?.submission_notes || row.submission_notes || '',
  }
}

export function AssignmentGradePage() {
  const { classId, assignmentId } = useParams()
  const location = useLocation()
  const isGroup = location.pathname.includes('/group/')
  const [data, setData] = useState<AssignmentGradeResponse | null>(null)
  const [drafts, setDrafts] = useState<Record<string, RowDraft>>({})
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [rowStatus, setRowStatus] = useState<Record<string, 'saved' | 'error'>>({})

  const load = useCallback(async () => {
    if (!assignmentId) return
    setLoading(true)
    setError(null)
    try {
      const payload = isGroup
        ? await fetchGroupAssignmentGrade(Number(assignmentId))
        : await fetchIndividualAssignmentGrade(Number(assignmentId))
      if (
        payload.legacy_only ||
        payload.legacy_reason === 'quiz_open_ended_grade'
      ) {
        if (payload.legacy_grade_url) {
          window.location.assign(payload.legacy_grade_url)
          return
        }
      }
      if (!payload.students && !payload.groups) {
        throw new Error('This assignment must be graded in the legacy interface.')
      }
      setData(payload)
      const next: Record<string, RowDraft> = {}
      if (payload.students) {
        for (const row of payload.students) {
          next[String(row.student.id)] = draftFromRow(row)
        }
      }
      if (payload.groups) {
        for (const group of payload.groups) {
          for (const row of group.members) {
            next[rowKey(row)] = draftFromRow(row)
          }
        }
      }
      setDrafts(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load gradebook')
    } finally {
      setLoading(false)
    }
  }, [assignmentId, isGroup])

  useEffect(() => {
    void load()
  }, [load])

  const assignment = data?.assignment as {
    title?: string
    due_date?: string | null
    quarter?: string | null
    total_points?: number
  } | undefined

  const totalPoints = assignment?.total_points ?? 100
  const classPath = `/management/assignments/${classId}`
  const viewPath = isGroup
    ? `/management/assignments/${classId}/group/${assignmentId}/view`
    : `/management/assignments/${classId}/individual/${assignmentId}/view`

  const flatRows = useMemo(() => {
    if (!data) return [] as GradeStudentRow[]
    if (data.students) return data.students
    return (data.groups || []).flatMap((g) => g.members)
  }, [data])

  function updateDraft(key: string, patch: Partial<RowDraft>) {
    setDrafts((prev) => ({ ...prev, [key]: { ...prev[key], ...patch } }))
  }

  async function saveIndividualRow(row: GradeStudentRow) {
    if (!assignmentId) return
    const key = String(row.student.id)
    const draft = drafts[key]
    if (!draft) return
    setSaving(true)
    setMessage(null)
    try {
      await saveIndividualStudentGrade(Number(assignmentId), row.student.id, {
        score: draft.score,
        comment: draft.comment,
        submission_type: draft.submission_type,
        submission_notes_type: draft.submission_notes_type,
        submission_notes: draft.submission_notes,
      })
      setRowStatus((prev) => ({ ...prev, [key]: 'saved' }))
      setMessage(`Saved grade for ${row.student.display_name}`)
    } catch (e) {
      setRowStatus((prev) => ({ ...prev, [key]: 'error' }))
      setMessage(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function saveAllGroup() {
    if (!assignmentId || !data?.groups) return
    const formData = new FormData()
    for (const group of data.groups) {
      for (const row of group.members) {
        const gid = row.group_id ?? group.id
        const sid = row.student.id
        const draft = drafts[rowKey(row)]
        if (!draft) continue
        formData.append(`score_${gid}_${sid}`, draft.score || '0')
        formData.append(`comments_${gid}_${sid}`, draft.comment)
        formData.append(`submission_type_${gid}_${sid}`, draft.submission_type)
        formData.append(`submission_notes_type_${gid}_${sid}`, draft.submission_notes_type)
        formData.append(`submission_notes_${gid}_${sid}`, draft.submission_notes)
      }
    }
    setSaving(true)
    setMessage(null)
    try {
      const result = await saveGroupAssignmentGrades(Number(assignmentId), formData)
      setMessage(result.message || 'Grades saved')
      await load()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-2xl bg-white p-8 text-center text-hub-muted shadow-sm">
        Loading gradebook…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">{error || 'Could not load grades'}</p>
        <Link to={classPath} className="mt-4 inline-block text-sm font-semibold text-teal-700">
          Back to class
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Grade assignment</p>
          <h1 className="text-2xl font-extrabold text-hub-text">{assignment?.title}</h1>
          <p className="mt-1 text-sm text-hub-muted">
            {data.class.name}
            {assignment?.quarter ? ` · Quarter ${assignment.quarter}` : ''}
            {assignment?.due_date ? ` · Due ${formatDate(assignment.due_date)}` : ''}
            {` · ${totalPoints} pts`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to={classPath}
            className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-teal-400"
          >
            Back
          </Link>
          <Link
            to={viewPath}
            className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-teal-400"
          >
            View
          </Link>
          {isGroup ? (
            <button
              type="button"
              disabled={saving}
              onClick={() => void saveAllGroup()}
              className="rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
            >
              {saving ? 'Saving…' : 'Save all grades'}
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="text-2xl font-extrabold text-hub-text">{data.stats.total_students}</div>
          <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">Students</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="text-2xl font-extrabold text-hub-text">{data.stats.graded_count}</div>
          <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">Graded</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="text-2xl font-extrabold text-hub-text">{data.stats.pending_count}</div>
          <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">Pending</div>
        </div>
      </div>

      {message ? (
        <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          {message}
        </div>
      ) : null}

      {!isGroup ? (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                <th className="px-4 py-3">Student</th>
                <th className="px-3 py-3">Submission</th>
                <th className="px-3 py-3">Score</th>
                <th className="px-3 py-3">Comment</th>
                <th className="px-3 py-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {flatRows.map((row) => {
                const key = String(row.student.id)
                const draft = drafts[key] || draftFromRow(row)
                const voided = row.grade.is_voided
                return (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="px-4 py-3 font-semibold text-hub-text">
                      {row.student.display_name}
                      {voided ? (
                        <span className="ms-2 rounded-full bg-slate-200 px-2 py-0.5 text-[0.65rem] font-bold uppercase">
                          Voided
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-3">
                      <select
                        value={draft.submission_type}
                        disabled={voided}
                        onChange={(e) => updateDraft(key, { submission_type: e.target.value })}
                        className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
                      >
                        <option value="not_submitted">Not submitted</option>
                        <option value="in_person">In person</option>
                        <option value="online">Online</option>
                      </select>
                    </td>
                    <td className="px-3 py-3">
                      <input
                        type="number"
                        min={0}
                        max={totalPoints}
                        step="0.1"
                        disabled={voided}
                        value={draft.score}
                        onChange={(e) => updateDraft(key, { score: e.target.value })}
                        className="w-24 rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                        placeholder="0"
                      />
                    </td>
                    <td className="px-3 py-3">
                      <input
                        type="text"
                        disabled={voided}
                        value={draft.comment}
                        onChange={(e) => updateDraft(key, { comment: e.target.value })}
                        className="w-full min-w-[160px] rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                        placeholder="Feedback"
                      />
                    </td>
                    <td className="px-3 py-3 text-center">
                      <button
                        type="button"
                        disabled={voided || saving}
                        onClick={() => void saveIndividualRow(row)}
                        className="rounded-full border border-teal-300 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800 hover:bg-teal-100 disabled:opacity-50"
                      >
                        {rowStatus[key] === 'saved' ? 'Saved' : 'Save'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="space-y-4">
          {(data.groups || []).map((group) => (
            <div key={group.id} className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 font-semibold text-hub-text">
                {group.name}
              </div>
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                    <th className="px-4 py-2.5">Student</th>
                    <th className="px-3 py-2.5">Submission</th>
                    <th className="px-3 py-2.5">Score</th>
                    <th className="px-3 py-2.5">Comment</th>
                  </tr>
                </thead>
                <tbody>
                  {group.members.map((row) => {
                    const key = rowKey(row)
                    const draft = drafts[key] || draftFromRow(row)
                    return (
                      <tr key={key} className="border-b border-slate-100">
                        <td className="px-4 py-2.5 font-semibold">{row.student.display_name}</td>
                        <td className="px-3 py-2.5">
                          <select
                            value={draft.submission_type}
                            onChange={(e) => updateDraft(key, { submission_type: e.target.value })}
                            className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs"
                          >
                            <option value="not_submitted">Not submitted</option>
                            <option value="in_person">In person</option>
                            <option value="online">Online</option>
                          </select>
                        </td>
                        <td className="px-3 py-2.5">
                          <input
                            type="number"
                            min={0}
                            max={Math.max(totalPoints, 100)}
                            step="0.1"
                            value={draft.score}
                            onChange={(e) => updateDraft(key, { score: e.target.value })}
                            className="w-24 rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                          />
                        </td>
                        <td className="px-3 py-2.5">
                          <input
                            type="text"
                            value={draft.comment}
                            onChange={(e) => updateDraft(key, { comment: e.target.value })}
                            className="w-full min-w-[160px] rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                          />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
