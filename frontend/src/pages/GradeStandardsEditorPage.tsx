import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import {
  fetchGradeStandardsEditor,
  saveGradeStandardsMarks,
  type GradeLevelRoute,
} from '../api/gradeStandards'
import type { GradeStandardsEditorResponse, GradeStandardsStandard } from '../types/gradeStandards'
import { spaRoute } from '../utils/spaRoute'

function markSelectClass(value: string): string {
  switch (value) {
    case 'M':
      return 'border-emerald-300 bg-emerald-50 text-emerald-900'
    case 'W':
      return 'border-amber-300 bg-amber-50 text-amber-900'
    case 'NA':
      return 'border-slate-300 bg-slate-50 text-slate-700'
    case 'UA':
      return 'border-violet-300 bg-violet-50 text-violet-900'
    default:
      return 'border-slate-200 bg-white text-hub-muted'
  }
}

function MarkSelect({
  value,
  validMarks,
  onChange,
}: {
  value: string
  validMarks: string[]
  onChange: (value: string) => void
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className={`w-full min-w-[3.25rem] rounded-lg border px-1 py-1 text-center text-xs font-bold ${markSelectClass(value)}`}
      aria-label="Standard mark"
    >
      <option value="">—</option>
      {validMarks.map((mark) => (
        <option key={mark} value={mark}>
          {mark}
        </option>
      ))}
    </select>
  )
}

function buildGridDraft(data: GradeStandardsEditorResponse): Record<number, Record<string, string>> {
  const draft: Record<number, Record<string, string>> = {}
  for (const student of data.students) {
    draft[student.id] = { ...(data.marks_grid[student.id] || {}) }
  }
  return draft
}

function buildStudentDraft(
  data: GradeStandardsEditorResponse,
  studentId: number | null,
): Record<string, Record<string, string>> {
  if (!studentId) return {}
  return { ...(data.marks_student_view[studentId] || {}) }
}

function collectGridChanges(
  draft: Record<number, Record<string, string>>,
  original: Record<number, Record<string, string>>,
  studentIds: number[],
  standardIds: string[],
): Array<{ student_id: number; standard_id: string; value: string }> {
  const changes: Array<{ student_id: number; standard_id: string; value: string }> = []
  for (const studentId of studentIds) {
    for (const standardId of standardIds) {
      const next = draft[studentId]?.[standardId] ?? ''
      const prev = original[studentId]?.[standardId] ?? ''
      if (next !== prev) {
        changes.push({ student_id: studentId, standard_id: standardId, value: next })
      }
    }
  }
  return changes
}

function collectStudentChanges(
  draft: Record<string, Record<string, string>>,
  original: Record<string, Record<string, string>>,
  studentId: number,
  standardIds: string[],
  quarterColumns: string[],
): Array<{ student_id: number; standard_id: string; quarter: string; value: string }> {
  const changes: Array<{ student_id: number; standard_id: string; quarter: string; value: string }> = []
  for (const standardId of standardIds) {
    for (const quarter of quarterColumns) {
      const next = draft[standardId]?.[quarter] ?? ''
      const prev = original[standardId]?.[quarter] ?? ''
      if (next !== prev) {
        changes.push({
          student_id: studentId,
          standard_id: standardId,
          quarter,
          value: next,
        })
      }
    }
  }
  return changes
}

function groupStandardsBySection(standards: GradeStandardsStandard[]) {
  const sections: Array<{ title: string; standards: GradeStandardsStandard[] }> = []
  let currentTitle = ''
  let currentItems: GradeStandardsStandard[] = []
  for (const standard of standards) {
    const sectionTitle = standard.section || 'Standards'
    if (sectionTitle !== currentTitle) {
      if (currentItems.length) sections.push({ title: currentTitle, standards: currentItems })
      currentTitle = sectionTitle
      currentItems = [standard]
    } else {
      currentItems.push(standard)
    }
  }
  if (currentItems.length) sections.push({ title: currentTitle, standards: currentItems })
  return sections
}

export default function GradeStandardsEditorPage() {
  const { grade = 'grade1', classId = '' } = useParams<{ grade: GradeLevelRoute; classId: string }>()
  const gradeRoute = grade === 'grade3' ? 'grade3' : 'grade1'
  const classIdNum = Number(classId)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const quarter = searchParams.get('quarter') || undefined
  const view = searchParams.get('view') || 'grid'
  const studentIdParam = searchParams.get('student_id')
  const studentId = studentIdParam ? Number(studentIdParam) : undefined

  const [data, setData] = useState<GradeStandardsEditorResponse | null>(null)
  const [gridDraft, setGridDraft] = useState<Record<number, Record<string, string>>>({})
  const [studentDraft, setStudentDraft] = useState<Record<string, Record<string, string>>>({})
  const [standardSearch, setStandardSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!classIdNum) return
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const response = await fetchGradeStandardsEditor(gradeRoute, classIdNum, {
        quarter,
        view,
        studentId,
      })
      setData(response)
      setGridDraft(buildGridDraft(response))
      setStudentDraft(buildStudentDraft(response, response.selected_student_id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load standards editor.')
    } finally {
      setLoading(false)
    }
  }, [classIdNum, gradeRoute, quarter, view, studentId])

  useEffect(() => {
    void load()
  }, [load])

  const standardIds = useMemo(() => (data?.standards ?? []).map((item) => item.id), [data?.standards])
  const studentIds = useMemo(() => (data?.students ?? []).map((item) => item.id), [data?.students])
  const sections = useMemo(() => groupStandardsBySection(data?.standards ?? []), [data?.standards])

  const filteredSections = useMemo(() => {
    const query = standardSearch.trim().toLowerCase()
    if (!query) return sections
    return sections
      .map((section) => ({
        ...section,
        standards: section.standards.filter(
          (standard) =>
            standard.text.toLowerCase().includes(query) || section.title.toLowerCase().includes(query),
        ),
      }))
      .filter((section) => section.standards.length > 0)
  }, [sections, standardSearch])

  function updateSearchParams(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(next)) {
      if (value === null || value === '') params.delete(key)
      else params.set(key, value)
    }
    setSearchParams(params, { replace: true })
  }

  async function handleSave() {
    if (!data) return
    setSaving(true)
    setMessage(null)
    setError(null)
    try {
      const marks =
        data.view_mode === 'student' && data.selected_student_id
          ? collectStudentChanges(
              studentDraft,
              data.marks_student_view[data.selected_student_id] || {},
              data.selected_student_id,
              standardIds,
              data.quarter_columns,
            )
          : collectGridChanges(gridDraft, data.marks_grid, studentIds, standardIds)

      const result = await saveGradeStandardsMarks(gradeRoute, classIdNum, {
        quarter: data.quarter,
        marks,
      })
      setMessage(result.message)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save marks.')
    } finally {
      setSaving(false)
    }
  }

  async function handleBulkAction(action: string) {
    if (!data) return
    const labels: Record<string, string> = {
      copy_previous: 'Copy marks from the previous quarter into this quarter?',
      mark_all_m: 'Mark every cell in this quarter as M?',
      mark_all_w: 'Mark every cell in this quarter as W?',
      mark_all_na: 'Mark every cell in this quarter as NA?',
      mark_all_ua: 'Mark every cell in this quarter as UA?',
      clear_all: 'Clear all marks for this quarter?',
    }
    if (!window.confirm(labels[action] || 'Apply this bulk action?')) return

    setSaving(true)
    setMessage(null)
    setError(null)
    try {
      const result = await saveGradeStandardsMarks(gradeRoute, classIdNum, {
        quarter: data.quarter,
        bulk_action: action,
      })
      setMessage(result.message)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk action failed.')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !data) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
        Loading standards editor…
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="space-y-4">
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">{error}</div>
        <Link
          to={spaRoute(`/management/report-cards/standards/${gradeRoute}`)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-violet-700"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          Back to all classes
        </Link>
      </div>
    )
  }

  if (!data) return null

  const qStats = data.overall_stats.quarters[data.quarter]
  const selectedStudent =
    data.students.find((student) => student.id === data.selected_student_id) ?? data.students[0] ?? null

  return (
    <div className="space-y-6">
      <header className="rounded-2xl border border-slate-200 bg-gradient-to-br from-violet-50 to-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <Link
              to={spaRoute(data.urls.hub)}
              className="inline-flex items-center gap-1 text-sm font-semibold text-violet-700 hover:text-violet-900"
            >
              <i className="bi bi-arrow-left" aria-hidden />
              All {gradeRoute === 'grade1' ? '1st' : '3rd'} grade classes
            </Link>
            <p className="mt-2 text-xs font-bold uppercase tracking-wide text-violet-700">
              {data.subject_catalog.subject} · {gradeRoute === 'grade1' ? '1st' : '3rd'} Grade Standards
            </p>
            <h1 className="mt-1 text-2xl font-bold text-hub-text">{data.class.name}</h1>
            <p className="mt-2 text-sm text-hub-muted">
              <i className="bi bi-people-fill mr-1" aria-hidden />
              {data.students.length} students · {data.standards.length} standards · {data.school_year.name}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800 disabled:opacity-60"
            >
              <i className="bi bi-save" aria-hidden />
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </div>
      </header>

      {message ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">{message}</div>
      ) : null}
      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-2xl font-bold text-hub-text">{data.overall_stats.overall.percent}%</div>
          <div className="text-sm text-hub-muted">Year-to-date complete</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-2xl font-bold text-hub-text">{qStats?.percent ?? 0}%</div>
          <div className="text-sm text-hub-muted">{data.quarter} complete</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold text-hub-text">
            {data.overall_stats.last_updated_display ?? '—'}
          </div>
          <div className="text-sm text-hub-muted">Last edit</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-2xl font-bold text-hub-text">{data.standards.length}</div>
          <div className="text-sm text-hub-muted">Standards in catalog</div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">Quarter</span>
            {data.quarter_columns.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => updateSearchParams({ quarter: q })}
                className={[
                  'rounded-full px-3 py-1.5 text-xs font-semibold',
                  q === data.quarter ? 'bg-violet-700 text-white' : 'bg-slate-100 text-hub-muted hover:bg-slate-200',
                ].join(' ')}
              >
                {q}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">View</span>
            <button
              type="button"
              onClick={() => updateSearchParams({ view: 'grid', student_id: null })}
              className={[
                'rounded-full px-3 py-1.5 text-xs font-semibold',
                data.view_mode === 'grid' ? 'bg-violet-700 text-white' : 'bg-slate-100 text-hub-muted',
              ].join(' ')}
            >
              Grid
            </button>
            <button
              type="button"
              onClick={() =>
                updateSearchParams({
                  view: 'student',
                  student_id: String(selectedStudent?.id ?? data.students[0]?.id ?? ''),
                })
              }
              className={[
                'rounded-full px-3 py-1.5 text-xs font-semibold',
                data.view_mode === 'student' ? 'bg-violet-700 text-white' : 'bg-slate-100 text-hub-muted',
              ].join(' ')}
            >
              Per student
            </button>
          </div>
          {data.other_classes.length > 1 ? (
            <label className="flex items-center gap-2 text-sm text-hub-muted">
              Class
              <select
                value={classIdNum}
                onChange={(event) => {
                  const nextId = event.target.value
                  navigate(
                    spaRoute(
                      `/management/report-cards/standards/${gradeRoute}/${nextId}?quarter=${data.quarter}&view=${data.view_mode}`,
                    ),
                  )
                }}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-hub-text"
              >
                {data.other_classes.map((classItem) => (
                  <option key={classItem.id} value={classItem.id}>
                    {classItem.name} · {classItem.subject}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>

        <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative max-w-md flex-1">
            <i className="bi bi-search absolute left-3 top-1/2 -translate-y-1/2 text-hub-muted" aria-hidden />
            <input
              type="search"
              value={standardSearch}
              onChange={(event) => setStandardSearch(event.target.value)}
              placeholder="Search standards…"
              className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-3 text-sm"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {data.can_copy_previous ? (
              <button
                type="button"
                disabled={saving}
                onClick={() => void handleBulkAction('copy_previous')}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-hub-text hover:bg-slate-50"
              >
                Copy previous quarter
              </button>
            ) : null}
            {(['mark_all_m', 'mark_all_w', 'mark_all_na', 'mark_all_ua'] as const).map((action) => (
              <button
                key={action}
                type="button"
                disabled={saving}
                onClick={() => void handleBulkAction(action)}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-hub-text hover:bg-slate-50"
              >
                All {action.split('_').pop()?.toUpperCase()}
              </button>
            ))}
            <button
              type="button"
              disabled={saving}
              onClick={() => void handleBulkAction('clear_all')}
              className="rounded-xl border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
            >
              Clear quarter
            </button>
          </div>
        </div>
      </div>

      {Object.keys(data.section_stats).length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Object.entries(data.section_stats).map(([title, stats]) => (
            <div key={title} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-sm font-bold text-hub-text">{title}</div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-violet-600" style={{ width: `${stats.percent}%` }} />
              </div>
              <div className="mt-2 text-xs text-hub-muted">
                {data.quarter} · {stats.filled} / {stats.total} · {stats.percent}%
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {!data.students.length ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
          No students are currently enrolled in this class.
        </div>
      ) : !data.standards.length ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
          No standards are defined for this subject.
        </div>
      ) : data.view_mode === 'student' ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <label className="flex flex-col gap-2 text-sm text-hub-muted">
              Student
              <select
                value={selectedStudent?.id ?? ''}
                onChange={(event) => updateSearchParams({ student_id: event.target.value, view: 'student' })}
                className="max-w-md rounded-xl border border-slate-200 px-3 py-2 text-sm text-hub-text"
              >
                {data.students.map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.display_name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {selectedStudent ? (
            <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-hub-muted">
                  <tr>
                    <th className="min-w-[16rem] px-4 py-3">Standard</th>
                    {data.quarter_columns.map((q) => (
                      <th key={q} className="px-3 py-3 text-center">
                        {q}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredSections.map((section) => (
                    <Fragment key={section.title}>
                      <tr key={`section-${section.title}`} className="bg-violet-50">
                        <td colSpan={data.quarter_columns.length + 1} className="px-4 py-2 font-bold text-violet-900">
                          {section.title}
                        </td>
                      </tr>
                      {section.standards.map((standard) => (
                        <tr key={standard.id} className="border-t border-slate-100">
                          <td className="px-4 py-3 align-top text-hub-text">{standard.text}</td>
                          {data.quarter_columns.map((q) => (
                            <td key={q} className="px-2 py-2">
                              <MarkSelect
                                value={studentDraft[standard.id]?.[q] ?? ''}
                                validMarks={data.valid_marks}
                                onChange={(value) =>
                                  setStudentDraft((prev) => ({
                                    ...prev,
                                    [standard.id]: {
                                      ...(prev[standard.id] || {}),
                                      [q]: value,
                                    },
                                  }))
                                }
                              />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-hub-muted">
              <tr>
                <th className="sticky left-0 z-10 min-w-[16rem] bg-slate-50 px-4 py-3">Standard</th>
                {data.students.map((student) => (
                  <th key={student.id} className="min-w-[5rem] px-2 py-3 text-center">
                    <span className="block max-w-[6rem] truncate" title={student.display_name}>
                      {student.display_name}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredSections.map((section) => (
                <Fragment key={section.title}>
                  <tr className="bg-violet-50">
                    <td
                      colSpan={data.students.length + 1}
                      className="sticky left-0 px-4 py-2 font-bold text-violet-900"
                    >
                      {section.title}
                    </td>
                  </tr>
                  {section.standards.map((standard) => (
                    <tr key={standard.id} className="border-t border-slate-100">
                      <td className="sticky left-0 bg-white px-4 py-3 align-top text-hub-text">{standard.text}</td>
                      {data.students.map((student) => (
                        <td key={student.id} className="px-2 py-2">
                          <MarkSelect
                            value={gridDraft[student.id]?.[standard.id] ?? ''}
                            validMarks={data.valid_marks}
                            onChange={(value) =>
                              setGridDraft((prev) => ({
                                ...prev,
                                [student.id]: {
                                  ...(prev[student.id] || {}),
                                  [standard.id]: value,
                                },
                              }))
                            }
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
          {!filteredSections.length ? (
            <div className="p-6 text-center text-sm text-hub-muted">No standards match your search.</div>
          ) : null}
        </div>
      )}
    </div>
  )
}
