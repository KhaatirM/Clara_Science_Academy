import { useCallback, useEffect, useMemo, useState } from 'react'
import { useOutletContext, useParams, useSearchParams } from 'react-router-dom'
import { fetchClassGrades } from '../api/classes'
import { GradeBadge } from '../components/classes/GradeBadge'
import { ClassWorkflowNav } from '../components/classes/ClassWorkflowNav'
import { VoidAssignmentModal, type VoidAssignmentTarget } from '../components/classes/VoidAssignmentModal'
import type { ManagementOutletContext } from '../types/layout'
import type { ClassGradesColumn, ClassGradesResponse, ClassGradesRow } from '../types/classDetail'

function InsightCard({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-white/90 bg-white px-3 py-2.5 shadow-sm">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
        <i className={`bi ${icon} text-sm`} aria-hidden />
      </span>
      <div className="min-w-0">
        <div className="truncate text-lg font-extrabold leading-tight text-hub-text">{value}</div>
        <div className="text-[0.62rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function buildStats(data: ClassGradesResponse) {
  if (data.stats) return data.stats
  const individual = data.columns.filter((c) => c.type === 'individual').length
  const group = data.columns.filter((c) => c.type === 'group').length
  return {
    students: data.rows.length,
    assignments: data.columns.length,
    individual_count: individual,
    group_count: group,
    schedule_display: data.class.schedule_display || data.class.schedule || 'TBD',
  }
}

function exportGradesCsv(data: ClassGradesResponse) {
  const headers = ['Student', 'Student ID', 'Grade Level', ...data.columns.map((c) => c.title), 'Average']
  const lines = [headers.join(',')]
  for (const row of data.rows) {
    const cells = [
      row.student.display_name,
      row.student.student_id || 'N/A',
      row.student.grade_level != null ? String(row.student.grade_level) : 'N/A',
      ...data.columns.map((col) => String(row.grades[col.key]?.grade ?? '—')),
      String(row.average),
    ]
    lines.push(cells.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${data.class.name.replace(/\s+/g, '_')}_grades.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function recentAssignments(row: ClassGradesRow, columns: ClassGradesColumn[]) {
  return [...columns]
    .filter((c) => c.status !== 'Voided')
    .sort((a, b) => {
      const ad = a.due_date ? new Date(a.due_date).getTime() : 0
      const bd = b.due_date ? new Date(b.due_date).getTime() : 0
      return bd - ad
    })
    .slice(0, 3)
    .map((col) => ({ col, grade: row.grades[col.key]?.grade ?? 'Not Graded' }))
}

function GradesTable({
  data,
  onVoid,
}: {
  data: ClassGradesResponse
  onVoid: (target: VoidAssignmentTarget) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
            <th className="sticky left-0 z-10 min-w-[10rem] bg-slate-50 px-3 py-2.5">Student</th>
            <th className="min-w-[6rem] px-2 py-2.5">ID</th>
            <th className="min-w-[5rem] px-2 py-2.5">Grade</th>
            {data.columns.map((col) => (
              <th key={col.key} className="min-w-[6.5rem] px-2 py-2.5 text-center">
                <div className="truncate font-bold normal-case text-hub-text" title={col.title}>
                  {col.title.length > 18 ? `${col.title.slice(0, 15)}…` : col.title}
                </div>
                <span
                  className={`mt-0.5 inline-block rounded-full border px-1.5 py-0.5 text-[0.6rem] font-semibold normal-case ${
                    col.type === 'group'
                      ? 'border-sky-300 bg-sky-50 text-sky-800'
                      : 'border-teal-300 bg-teal-50 text-teal-800'
                  }`}
                >
                  {col.type === 'group' ? 'Group' : 'Individual'}
                </span>
                {col.status !== 'Voided' ? (
                  <div className="mt-1.5 flex justify-center">
                    <button
                      type="button"
                      onClick={() =>
                        onVoid({
                          id: col.id,
                          title: col.title,
                          type: col.type,
                        })
                      }
                      className="inline-flex items-center gap-1 rounded-full border border-red-300 bg-white px-2 py-0.5 text-[0.62rem] font-semibold text-red-700 shadow-sm hover:border-red-500 hover:bg-red-50"
                      title="Void assignment"
                      aria-label={`Void ${col.title}`}
                    >
                      <i className="bi bi-slash-circle" aria-hidden />
                      Void
                    </button>
                  </div>
                ) : null}
              </th>
            ))}
            <th className="min-w-[4.5rem] px-2 py-2.5 text-center">Avg</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.student.id} className="border-b border-slate-100 hover:bg-slate-50/80">
              <td className="sticky left-0 z-10 bg-white px-3 py-2 font-semibold text-hub-text">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs text-emerald-700">
                    {row.student.initial}
                  </span>
                  <span className="truncate">{row.student.display_name}</span>
                </div>
              </td>
              <td className="px-2 py-2 text-xs text-hub-muted">{row.student.student_id || 'N/A'}</td>
              <td className="px-2 py-2 text-xs text-hub-muted">
                {row.student.grade_level != null ? row.student.grade_level : '—'}
              </td>
              {data.columns.map((col) => {
                const cell = row.grades[col.key]
                const value =
                  col.status === 'Voided' || cell?.grade === 'Voided'
                    ? 'Voided'
                    : (cell?.grade ?? 'Not Graded')
                return (
                  <td key={col.key} className="px-2 py-2 text-center" title={cell?.group_name || undefined}>
                    <GradeBadge grade={value} />
                  </td>
                )
              })}
              <td className="px-2 py-2 text-center">
                <GradeBadge grade={row.average} bold />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StudentCardsView({ data }: { data: ClassGradesResponse }) {
  const today = new Date().toLocaleDateString()
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {data.rows.map((row) => {
        const recent = recentAssignments(row, data.columns)
        return (
          <article
            key={row.student.id}
            className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
          >
            <div className="border-b border-indigo-100 bg-gradient-to-r from-indigo-600 to-teal-700 px-4 py-3 text-white">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20 text-sm font-bold">
                  {row.student.initial}
                </span>
                <div className="min-w-0">
                  <h3 className="truncate font-bold">{row.student.display_name}</h3>
                  <p className="text-xs text-white/85">{row.student.student_id || 'No ID'}</p>
                </div>
              </div>
            </div>
            <div className="flex-1 p-4">
              <div className="mb-3 flex items-center justify-between gap-2 text-sm">
                <span className="truncate font-semibold text-hub-text">{data.class.name}</span>
                {row.student.grade_level != null ? (
                  <span className="shrink-0 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-900">
                    Grade {row.student.grade_level}
                  </span>
                ) : null}
              </div>
              <div className="mb-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <span className="text-xs text-hub-muted">Current average</span>
                <GradeBadge grade={row.average} bold />
              </div>
              <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">Last 3 assignments</h4>
              {recent.length ? (
                <ul className="space-y-2">
                  {recent.map(({ col, grade }) => (
                    <li key={col.key} className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2 text-xs last:border-0">
                      <div className="min-w-0">
                        <div className="truncate font-semibold text-hub-text">{col.title}</div>
                        <div className="mt-0.5 text-hub-muted">
                          {col.type === 'group' ? 'Group' : 'Individual'}
                          {col.due_date ? ` · Due ${new Date(col.due_date).toLocaleDateString()}` : ''}
                        </div>
                      </div>
                      <GradeBadge grade={grade} />
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-hub-muted">No recent assignments</p>
              )}
            </div>
            <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-4 py-2.5">
              <span className="text-xs text-hub-muted">
                <i className="bi bi-calendar3 me-1" aria-hidden />
                {today}
              </span>
              <a
                href={`/management/view-student/${row.student.id}`}
                className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-teal-800 hover:border-teal-500"
              >
                View details
              </a>
            </div>
          </article>
        )
      })}
    </div>
  )
}

export function ClassGradesPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const { classId } = useParams()
  const id = Number(classId)
  const isDirector = user.role_canonical === 'Director'
  const [searchParams, setSearchParams] = useSearchParams()
  const viewMode = searchParams.get('view') === 'student_cards' ? 'student_cards' : 'table'

  const [data, setData] = useState<ClassGradesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [voidTarget, setVoidTarget] = useState<VoidAssignmentTarget | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassGrades(id, viewMode))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load grades')
    } finally {
      setLoading(false)
    }
  }, [id, viewMode])

  useEffect(() => {
    void load()
  }, [load])

  const stats = useMemo(() => (data ? buildStats(data) : null), [data])
  const hasGrades = Boolean(data?.rows.length && data.columns.length)
  const canAdminUi = data?.meta?.can_admin_ui ?? false

  const setView = (view: 'table' | 'student_cards') => {
    setSearchParams(view === 'table' ? {} : { view })
  }

  if (!Number.isFinite(id) || id <= 0) return null

  const cls = data?.class

  return (
    <div
      className={`rounded-3xl p-5 md:p-6 ${
        isDirector
          ? 'bg-gradient-to-br from-violet-50 via-purple-50/70 to-slate-100'
          : 'bg-gradient-to-br from-indigo-50 via-slate-50 to-slate-100'
      }`}
    >
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Gradebook</p>
          <h1 className="mt-0.5 text-2xl font-extrabold tracking-tight text-hub-text">{cls?.name || 'Grades'}</h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-hub-muted">
            <i className="bi bi-graph-up" aria-hidden />
            {cls ? `${cls.subject} · assignments and student performance` : 'Loading…'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ClassWorkflowNav classId={id} active="grades" isDirector={isDirector} canAdminUi={canAdminUi} />
        </div>
      </header>

      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div> : null}
      {message ? (
        <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900">{message}</div>
      ) : null}

      {data && stats ? (
        <>
          <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <InsightCard icon="bi-people-fill" value={stats.students} label="Students" />
            <InsightCard icon="bi-journal-text" value={stats.assignments} label="Assignments" />
            <InsightCard
              icon="bi-collection"
              value={`${stats.individual_count} / ${stats.group_count}`}
              label="Indiv / group"
            />
            <InsightCard icon="bi-calendar3" value={stats.schedule_display} label="Schedule" />
          </div>

          <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="Grades view mode">
            <button
              type="button"
              onClick={() => setView('table')}
              className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold ${
                viewMode === 'table'
                  ? 'bg-indigo-700 text-white shadow-sm'
                  : 'border border-slate-300 bg-white text-slate-700 hover:border-indigo-400'
              }`}
            >
              <i className="bi bi-table" aria-hidden />
              Assignments & grades table
            </button>
            <button
              type="button"
              onClick={() => setView('student_cards')}
              className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold ${
                viewMode === 'student_cards'
                  ? 'bg-indigo-700 text-white shadow-sm'
                  : 'border border-slate-300 bg-white text-slate-700 hover:border-indigo-400'
              }`}
            >
              <i className="bi bi-person-lines-fill" aria-hidden />
              Student grades view
            </button>
          </div>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/80 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-indigo-800">
                  <i className={`bi ${viewMode === 'table' ? 'bi-table' : 'bi-person-lines-fill'}`} aria-hidden />
                </span>
                <div>
                  <h2 className="text-sm font-bold text-hub-text">
                    {viewMode === 'table' ? 'Student Grades Overview' : 'Student Grades Cards'}
                  </h2>
                  <p className="text-xs text-hub-muted">View and manage student performance</p>
                </div>
              </div>
              {viewMode === 'table' && hasGrades ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => exportGradesCsv(data)}
                    className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:border-indigo-400"
                  >
                    <i className="bi bi-download me-1" aria-hidden />
                    Export
                  </button>
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:border-indigo-400"
                  >
                    <i className="bi bi-printer me-1" aria-hidden />
                    Print
                  </button>
                </div>
              ) : null}
            </div>

            <div className="p-0">
              {hasGrades ? (
                viewMode === 'table' ? (
                  <GradesTable data={data} onVoid={setVoidTarget} />
                ) : (
                  <div className="p-4">
                    <StudentCardsView data={data} />
                  </div>
                )
              ) : (
                <div className="px-4 py-12 text-center">
                  <i className="bi bi-graph-up mb-2 text-3xl text-hub-muted" aria-hidden />
                  <h3 className="font-bold text-hub-text">No Grades Available</h3>
                  <p className="mt-1 text-sm text-hub-muted">
                    {!data.rows.length
                      ? 'No students are enrolled in this class.'
                      : !data.columns.length
                        ? 'No assignments have been created for this class yet.'
                        : 'No grade data is available at this time.'}
                  </p>
                </div>
              )}
            </div>
          </section>

          <div className="mt-4 flex flex-wrap gap-2">
            <a
              href={`/app/management/assignments/${id}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
            >
              <i className="bi bi-clipboard-data" aria-hidden />
              Assignments hub
            </a>
          </div>
        </>
      ) : null}

      <VoidAssignmentModal
        target={voidTarget}
        students={data?.rows.map((r) => r.student) ?? []}
        onClose={() => setVoidTarget(null)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load()
        }}
      />
    </div>
  )
}
