import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams, useSearchParams } from 'react-router-dom'
import { openAssignmentGrade, openAssignmentView, type DeleteAssignmentTarget } from '../api/assignmentActions'
import { fetchAssignmentsClass } from '../api/assignments'
import { DeleteAssignmentModal } from '../components/assignments/DeleteAssignmentModal'
import { GradeBadge } from '../components/classes/GradeBadge'
import { VoidAssignmentModal, type VoidAssignmentTarget } from '../components/classes/VoidAssignmentModal'
import type { ManagementOutletContext } from '../types/layout'
import type { AssignmentWorkspaceItem, AssignmentsClassResponse } from '../types/assignments'

type ViewMode = 'grades' | 'assignments' | 'table'

function InsightCard({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-white/90 bg-white px-3 py-2.5 shadow-sm">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
        <i className={`bi ${icon} text-sm`} aria-hidden />
      </span>
      <div>
        <div className="text-lg font-extrabold leading-tight text-hub-text">{value}</div>
        <div className="text-[0.62rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function avgClass(score: number | null | undefined) {
  if (score == null || score <= 0) return 'border-slate-300 bg-slate-100 text-slate-700'
  if (score >= 80) return 'border-emerald-300 bg-emerald-50 text-emerald-900'
  if (score >= 70) return 'border-sky-300 bg-sky-50 text-sky-900'
  if (score >= 60) return 'border-amber-300 bg-amber-50 text-amber-900'
  return 'border-red-300 bg-red-50 text-red-800'
}

function AssignmentActionButtons({
  item,
  classId,
  onVoid,
  onDelete,
  layout = 'inline',
}: {
  item: AssignmentWorkspaceItem
  classId: number
  onVoid: (target: VoidAssignmentTarget) => void
  onDelete: (target: DeleteAssignmentTarget) => void
  layout?: 'inline' | 'stacked'
}) {
  const navigate = useNavigate()
  const voided = item.stats.all_voided || item.status === 'Voided'
  const pill =
    'rounded-full border px-2 py-0.5 text-[0.65rem] font-semibold transition hover:brightness-95'
  const stacked = 'w-full rounded-lg px-3 py-2 text-center text-xs font-semibold transition hover:brightness-95'

  const viewBtn = (
    <button
      type="button"
      onClick={() => openAssignmentView(item, navigate, classId)}
      className={layout === 'stacked' ? `${stacked} border border-slate-200 bg-white hover:border-teal-400` : `${pill} border-slate-300 bg-white text-slate-700 hover:border-teal-500`}
    >
      <i className="bi bi-eye me-1" aria-hidden />
      View
    </button>
  )
  const gradeBtn = (
    <button
      type="button"
      onClick={() => openAssignmentGrade(item, navigate, classId)}
      className={
        layout === 'stacked'
          ? `${stacked} bg-teal-700 text-white hover:bg-teal-800`
          : `${pill} border-teal-300 bg-teal-50 text-teal-800 hover:border-teal-500`
      }
    >
      <i className="bi bi-pencil-square me-1" aria-hidden />
      Grade
    </button>
  )
  const voidBtn = !voided ? (
    <button
      type="button"
      onClick={() => onVoid({ id: item.id, title: item.title, type: item.type })}
      className={layout === 'stacked' ? `${stacked} border border-amber-300 bg-amber-50 text-amber-900` : `${pill} border-amber-300 bg-amber-50 text-amber-900 hover:border-amber-500`}
    >
      <i className="bi bi-slash-circle me-1" aria-hidden />
      Void
    </button>
  ) : null
  const deleteBtn = (
    <button
      type="button"
      onClick={() => onDelete({ id: item.id, title: item.title, type: item.type })}
      className={layout === 'stacked' ? `${stacked} border border-red-300 bg-red-50 text-red-800` : `${pill} border-red-300 bg-red-50 text-red-800 hover:border-red-500`}
    >
      <i className="bi bi-trash me-1" aria-hidden />
      Delete
    </button>
  )

  if (layout === 'stacked') {
    return (
      <div className="grid gap-2">
        {viewBtn}
        {gradeBtn}
        {voidBtn}
        {deleteBtn}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap justify-center gap-1">
      {viewBtn}
      {gradeBtn}
      {voidBtn}
      {deleteBtn}
    </div>
  )
}

function GradesByAssignmentTable({
  items,
  classId,
  onVoid,
  onDelete,
}: {
  items: AssignmentWorkspaceItem[]
  classId: number
  onVoid: (t: VoidAssignmentTarget) => void
  onDelete: (t: DeleteAssignmentTarget) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
            <th className="px-3 py-2.5">Assignment</th>
            <th className="px-2 py-2.5 text-center">Due</th>
            <th className="px-2 py-2.5 text-center">Quarter</th>
            <th className="px-2 py-2.5 text-center">Submissions</th>
            <th className="px-2 py-2.5 text-center">Graded</th>
            <th className="px-2 py-2.5 text-center">Average</th>
            <th className="px-2 py-2.5 text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const s = item.stats
            const voided = s.all_voided || item.status === 'Voided'
            return (
              <tr key={item.key} className={`border-b border-slate-100 ${voided ? 'bg-slate-50/80' : 'hover:bg-slate-50/80'}`}>
                <td className="px-3 py-2.5">
                  <div className="font-semibold text-hub-text">{item.title}</div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <span
                      className={`rounded-full border px-1.5 py-0.5 text-[0.6rem] font-semibold ${
                        item.type === 'group'
                          ? 'border-sky-300 bg-sky-50 text-sky-800'
                          : 'border-teal-300 bg-teal-50 text-teal-800'
                      }`}
                    >
                      {item.type === 'group' ? 'Group' : 'Individual'}
                    </span>
                    {voided ? <GradeBadge grade="Voided" /> : null}
                    {s.partially_voided ? (
                      <span className="rounded-full border border-slate-300 bg-slate-100 px-1.5 py-0.5 text-[0.6rem] font-semibold text-slate-700">
                        Partially voided
                      </span>
                    ) : null}
                  </div>
                </td>
                <td className="px-2 py-2.5 text-center text-xs text-hub-muted">
                  {item.due_date ? new Date(item.due_date).toLocaleDateString() : '—'}
                </td>
                <td className="px-2 py-2.5 text-center text-xs">{item.quarter || 'N/A'}</td>
                <td className="px-2 py-2.5 text-center text-sm font-semibold">{voided ? '—' : s.total_submissions}</td>
                <td className="px-2 py-2.5 text-center text-sm font-semibold">
                  {voided ? <GradeBadge grade="Voided" /> : `${s.graded_count}${s.total_submissions > 0 ? `/${s.total_submissions}` : ''}`}
                </td>
                <td className="px-2 py-2.5 text-center">
                  {voided ? (
                    <span className="text-xs text-hub-muted">—</span>
                  ) : s.average_score > 0 ? (
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-bold ${avgClass(s.average_score)}`}>
                      {s.average_score}%
                    </span>
                  ) : (
                    <span className="text-xs text-hub-muted">N/A</span>
                  )}
                </td>
                <td className="px-2 py-2.5">
                  <AssignmentActionButtons item={item} classId={classId} onVoid={onVoid} onDelete={onDelete} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function AssignmentCards({
  items,
  classId,
  onVoid,
  onDelete,
}: {
  items: AssignmentWorkspaceItem[]
  classId: number
  onVoid: (t: VoidAssignmentTarget) => void
  onDelete: (t: DeleteAssignmentTarget) => void
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => {
        const s = item.stats
        const voided = s.all_voided || item.status === 'Voided'
        return (
          <article key={item.key} className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className={`border-b px-4 py-3 ${item.type === 'group' ? 'border-sky-100 bg-sky-600 text-white' : 'border-indigo-100 bg-indigo-700 text-white'}`}>
              <h3 className="font-bold">{item.title}</h3>
              <p className="text-xs opacity-85">{item.type === 'group' ? 'Group assignment' : item.assignment_type || 'Assignment'}</p>
            </div>
            <div className="flex-1 space-y-2 p-4 text-sm">
              <p className="text-hub-muted">
                Due: {item.due_date ? new Date(item.due_date).toLocaleDateString() : 'No due date'}
              </p>
              <p className="text-hub-muted">Quarter: {item.quarter || 'N/A'}</p>
              <div className="flex justify-between">
                <span className="text-hub-muted">Submissions</span>
                <strong>{voided ? '—' : s.total_submissions}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-hub-muted">Graded</span>
                <strong>{voided ? '—' : s.graded_count}</strong>
              </div>
              {voided ? <GradeBadge grade="Voided" /> : null}
            </div>
            <div className="border-t border-slate-100 bg-slate-50 p-3">
              <AssignmentActionButtons item={item} classId={classId} onVoid={onVoid} onDelete={onDelete} layout="stacked" />
            </div>
          </article>
        )
      })}
    </div>
  )
}

export function AssignmentsClassPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const { classId } = useParams()
  const id = Number(classId)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const viewMode = (searchParams.get('view') as ViewMode) || 'grades'
  const isDirector = user.role_canonical === 'Director'

  const [data, setData] = useState<AssignmentsClassResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [voidTarget, setVoidTarget] = useState<VoidAssignmentTarget | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DeleteAssignmentTarget | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchAssignmentsClass(id, { view: viewMode }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load class assignments')
    } finally {
      setLoading(false)
    }
  }, [id, viewMode])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (viewMode === 'table' && id) {
      navigate(`/management/classes/${id}/grades`, { replace: true })
    }
  }, [viewMode, id, navigate])

  const setView = (view: ViewMode) => {
    setSearchParams(view === 'grades' ? {} : { view })
  }

  if (!Number.isFinite(id) || id <= 0) return null

  const cls = data?.class
  const toolbar = data?.toolbar

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
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Assignments & grades</p>
          <h1 className="mt-0.5 text-2xl font-extrabold tracking-tight text-hub-text">{cls?.name || 'Class'}</h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-hub-muted">
            <i className="bi bi-clipboard-data" aria-hidden />
            Manage assignments and grades for this class
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isDirector ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2.5 py-1 text-xs font-bold text-violet-900">
              <i className="bi bi-award-fill" aria-hidden />
              Director
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-1 text-xs font-bold text-teal-900">
              <i className="bi bi-shield-fill" aria-hidden />
              Administrator
            </span>
          )}
          <Link
            to="/management/assignments"
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
          >
            <i className="bi bi-arrow-left" aria-hidden />
            All classes
          </Link>
          {toolbar ? (
            <>
              <a href={toolbar.redo_url} className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500">
                <i className="bi bi-arrow-repeat" aria-hidden />
                Redo
                {toolbar.redo_request_count > 0 ? (
                  <span className="rounded-full bg-red-600 px-1.5 text-[0.65rem] text-white">{toolbar.redo_request_count}</span>
                ) : null}
              </a>
              <a href={toolbar.extensions_url} className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500">
                <i className="bi bi-clock-history" aria-hidden />
                Extensions
                {toolbar.extension_request_count > 0 ? (
                  <span className="rounded-full bg-red-600 px-1.5 text-[0.65rem] text-white">{toolbar.extension_request_count}</span>
                ) : null}
              </a>
              {toolbar.pending_assistant_count > 0 ? (
                <a href={toolbar.assistant_proposals_url} className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-900">
                  <i className="bi bi-person-badge" aria-hidden />
                  Proposals ({toolbar.pending_assistant_count})
                </a>
              ) : null}
              <Link
                to={`/management/assignments/create?class_id=${id}`}
                className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br from-rose-800 to-teal-900 px-3.5 py-2 text-[0.82rem] font-semibold text-white shadow-sm hover:brightness-105"
              >
                <i className="bi bi-plus-circle" aria-hidden />
                New assignment
              </Link>
            </>
          ) : null}
        </div>
      </header>

      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div> : null}
      {message ? (
        <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900">{message}</div>
      ) : null}

      {data && cls ? (
        <>
          <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <InsightCard icon="bi-journal-text" value={data.stats.total_assignments} label="Total assignments" />
            <InsightCard icon="bi-check-circle" value={data.stats.active_assignments} label="Active" />
            <InsightCard icon="bi-people-fill" value={data.stats.students} label="Students" />
            <InsightCard
              icon="bi-graph-up"
              value={data.stats.average_score != null ? `${data.stats.average_score}%` : 'N/A'}
              label="Avg score"
            />
          </div>

          <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="Assignments view mode">
            {(['grades', 'assignments', 'table'] as const).map((view) => (
              <button
                key={view}
                type="button"
                onClick={() => setView(view)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold ${
                  viewMode === view
                    ? 'bg-indigo-700 text-white shadow-sm'
                    : 'border border-slate-300 bg-white text-slate-700 hover:border-indigo-400'
                }`}
              >
                <i
                  className={`bi ${view === 'grades' ? 'bi-bar-chart' : view === 'assignments' ? 'bi-collection' : 'bi-table'}`}
                  aria-hidden
                />
                {view === 'grades' ? 'Grades view' : view === 'assignments' ? 'Assignments view' : 'Table view'}
              </button>
            ))}
          </div>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 bg-slate-50/80 px-4 py-3">
              <h2 className="text-sm font-bold text-hub-text">
                {viewMode === 'assignments' ? 'Assignment cards' : 'Grades by assignment'}
              </h2>
              <p className="text-xs text-hub-muted">
                {viewMode === 'assignments'
                  ? 'Browse assignments with quick actions'
                  : 'Submissions, grading progress, and class average per assignment'}
              </p>
            </div>
            <div className="p-0">
              {data.assignments.length ? (
                viewMode === 'assignments' ? (
                  <div className="p-4">
                    <AssignmentCards items={data.assignments} classId={id} onVoid={setVoidTarget} onDelete={setDeleteTarget} />
                  </div>
                ) : (
                  <GradesByAssignmentTable items={data.assignments} classId={id} onVoid={setVoidTarget} onDelete={setDeleteTarget} />
                )
              ) : (
                <div className="px-4 py-12 text-center">
                  <i className="bi bi-inbox mb-2 text-3xl text-hub-muted" aria-hidden />
                  <h3 className="font-bold text-hub-text">No assignments yet</h3>
                  <p className="mt-1 text-sm text-hub-muted">Create an assignment to get started.</p>
                  {toolbar ? (
                    <Link
                      to={`/management/assignments/create?class_id=${id}`}
                      className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white"
                    >
                      <i className="bi bi-plus-circle" aria-hidden />
                      New assignment
                    </Link>
                  ) : null}
                </div>
              )}
            </div>
          </section>

          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to={`/management/classes/${id}/grades`}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
            >
              <i className="bi bi-table" aria-hidden />
              Student grades matrix
            </Link>
            <Link
              to={`/management/classes/${id}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
            >
              <i className="bi bi-building" aria-hidden />
              Class view
            </Link>
          </div>
        </>
      ) : null}

      <VoidAssignmentModal
        target={voidTarget}
        students={[]}
        onClose={() => setVoidTarget(null)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load()
        }}
      />
      <DeleteAssignmentModal
        target={deleteTarget}
        classId={id}
        onClose={() => setDeleteTarget(null)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load()
        }}
      />
    </div>
  )
}
