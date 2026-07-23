import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  fetchGroupAssignmentView,
  fetchIndividualAssignmentView,
  type AssignmentViewResponse,
} from '../api/assignmentWorkspace'
import { spaRoute } from '../utils/spaRoute'
import { useAssignmentWorkspaceScope, assignmentWorkspaceHubPath } from '../utils/assignmentWorkspaceScope'
import { DeleteAssignmentModal } from '../components/assignments/DeleteAssignmentModal'
import { EditAssignmentModal } from '../components/assignments/EditAssignmentModal'
import {
  AssignmentActionsCard,
  AssignmentDetailsGrid,
  AssignmentOverviewCard,
  AssignmentViewHeader,
  ClassDetailsCard,
  DocumentViewer,
} from '../components/assignments/AssignmentViewPanels'
import {
  GrantExtensionModal,
  RedoOpportunityModal,
  ReopenAssignmentModal,
  UnvoidAssignmentModal,
} from '../components/assignments/AssignmentViewModals'
import { VoidAssignmentModal, type VoidAssignmentTarget } from '../components/classes/VoidAssignmentModal'
import type { StudentBrief } from '../types/classDetail'

function toStudentBrief(row: { id: number; display_name: string; grade_level?: number | null }): StudentBrief {
  const parts = row.display_name.trim().split(/\s+/)
  const first_name = parts[0] || row.display_name
  const last_name = parts.slice(1).join(' ')
  return {
    id: row.id,
    display_name: row.display_name,
    grade_level: row.grade_level ?? null,
    student_id: null,
    first_name,
    last_name,
    initial: (first_name[0] || '?').toUpperCase(),
    photo_url: null,
  }
}

export function AssignmentViewPage() {
  const { classId, assignmentId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const workspaceScope = useAssignmentWorkspaceScope()
  const isGroup = location.pathname.includes('/group/')
  const numericClassId = Number(classId)
  const numericAssignmentId = Number(assignmentId)

  const [data, setData] = useState<AssignmentViewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [voidTarget, setVoidTarget] = useState<VoidAssignmentTarget | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [extensionOpen, setExtensionOpen] = useState(false)
  const [redoOpen, setRedoOpen] = useState(false)
  const [reopenOpen, setReopenOpen] = useState(false)
  const [unvoidOpen, setUnvoidOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)

  const load = useCallback(async (options?: { silent?: boolean }) => {
    if (!assignmentId) return
    if (!options?.silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const payload = isGroup
        ? await fetchGroupAssignmentView(numericAssignmentId, workspaceScope)
        : await fetchIndividualAssignmentView(numericAssignmentId, workspaceScope)
      setData(payload)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load assignment')
    } finally {
      if (!options?.silent) {
        setLoading(false)
      }
    }
  }, [assignmentId, isGroup, numericAssignmentId, workspaceScope])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const state = location.state as { openEdit?: boolean } | null
    if (state?.openEdit) {
      setEditOpen(true)
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.pathname, location.state, navigate])

  const assignment = data?.assignment as {
    id?: number
    title?: string
    description?: string
    due_date?: string | null
    quarter?: string | null
    status?: string | null
    total_points?: number
    assignment_type?: string | null
    class_id?: number
  } | undefined

  const voidScope = (data?.void_scope || {}) as {
    all_voided?: boolean
    partially_voided?: boolean
    voided_count?: number
    enrolled_count?: number
  }

  const voidedStudentIds = (data?.voided_student_ids || []) as number[]

  const actionMeta = useMemo(() => {
    const server = (data?.actions || {}) as {
      show_reopen?: boolean
      show_redo?: boolean
      show_unvoid?: boolean
      grade_disabled?: boolean
      grade_disabled_label?: string | null
      grade_via_submissions?: boolean
      grade_label?: string
      is_quiz?: boolean
      max_attempts?: number | null
    }
    const atype = (assignment?.assignment_type || '').toLowerCase()
    const isPdf = ['pdf', 'paper', 'pdf_paper'].includes(atype)
    const hasVoided =
      voidedStudentIds.length > 0 ||
      Boolean(voidScope.all_voided) ||
      Boolean(voidScope.partially_voided) ||
      (voidScope.voided_count ?? 0) > 0

    return {
      ...server,
      show_unvoid: server.show_unvoid ?? hasVoided,
      show_reopen: server.show_reopen ?? (!isPdf && atype !== 'discussion'),
      show_redo: server.show_redo ?? isPdf,
    }
  }, [assignment?.assignment_type, data?.actions, voidScope, voidedStudentIds.length])

  const students = useMemo(
    () => ((data?.students || []) as { id: number; display_name: string; grade_level?: number | null }[]).map(toStudentBrief),
    [data?.students],
  )

  const hasDocument = useMemo(() => {
    if (!data) return false
    return Boolean((data.attachments && data.attachments.length > 0) || data.attachment)
  }, [data])

  const classPath = assignmentWorkspaceHubPath(workspaceScope, Number(classId))
  const base = workspaceScope === 'teacher' ? `/teacher/assignments-and-grades/${classId}` : `/management/assignments/${classId}`
  const gradePath = isGroup
    ? `${base}/group/${assignmentId}/grade`
    : `${base}/individual/${assignmentId}/grade`

  const submissionsPath = isGroup
    ? `${base}/group/${assignmentId}/submissions`
    : `${base}/individual/${assignmentId}/submissions`

  const actionHandlers = {
    onEdit: () => setEditOpen(true),
    submissionsTo: data?.links?.submissions ? spaRoute(data.links.submissions) : submissionsPath,
    onGrade: () => {
      if (actionMeta.grade_disabled) return
      if (actionMeta.grade_via_submissions) {
        navigate(
          data?.links?.submissions ? spaRoute(data.links.submissions) : submissionsPath,
        )
        return
      }
      navigate(gradePath)
    },
    onExtensions: () => setExtensionOpen(true),
    onReopen: () => {
      if (isGroup) {
        window.alert(
          'Reopen for group assignments allows you to reopen the assignment for groups that have not yet submitted. This feature is available when the assignment is inactive or closed.',
        )
        return
      }
      setReopenOpen(true)
    },
    onRedo: () => setRedoOpen(true),
    onUnvoid: () => setUnvoidOpen(true),
    onVoid: () =>
      setVoidTarget({
        id: numericAssignmentId,
        title: assignment?.title || 'Assignment',
        type: isGroup ? 'group' : 'individual',
      }),
    onDelete: () => setDeleteOpen(true),
    onBack: () => navigate(classPath),
    actions: actionMeta,
  }

  if (loading) {
    return (
      <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">
        Loading assignment…
      </div>
    )
  }

  if (error || !data || !assignment) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">{error || 'Assignment not found'}</p>
        <Link to={classPath} className="mt-4 inline-block text-sm font-semibold text-teal-700">
          Back to class
        </Link>
      </div>
    )
  }

  const sidebar = (
    <div className="space-y-4">
      <AssignmentOverviewCard
        stats={data.stats}
        totalPoints={assignment.total_points}
        allVoided={Boolean(voidScope.all_voided)}
        partiallyVoided={Boolean(voidScope.partially_voided)}
        voidedCount={voidScope.voided_count ?? 0}
        enrolledCount={voidScope.enrolled_count ?? data.stats.total_students ?? 0}
        isGroup={isGroup}
      />
      <ClassDetailsCard classInfo={data.class} />
      {hasDocument ? <AssignmentActionsCard {...actionHandlers} /> : null}
    </div>
  )

  return (
    <div className="mx-auto max-w-[1400px]">
      {message ? (
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-900">
          {message}
        </div>
      ) : null}

      <AssignmentViewHeader
        title={assignment.title || 'Assignment'}
        className={data.class.name || 'Unknown class'}
        teacherName={data.class.teacher_name || 'Unknown'}
        status={assignment.status}
        allVoided={Boolean(voidScope.all_voided)}
      />

      {!isGroup && data.discussion ? (
        <div className="mb-4 space-y-4">
          <div className="rounded-2xl border border-sky-200 bg-sky-50 p-5 shadow-sm">
            <h2 className="text-sm font-bold uppercase tracking-wide text-sky-900">Discussion activity</h2>
            <p className="mt-1 text-sm text-sky-900/80">
              Requires {data.discussion.requirements.min_initial_posts} initial post(s) and{' '}
              {data.discussion.requirements.min_replies} reply/replies per student.
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-bold text-hub-text">Threads</h3>
              <ul className="mt-3 space-y-2 text-sm">
                {data.discussion.threads.map((thread) => (
                  <li key={thread.id} className="rounded-xl border border-slate-100 px-3 py-2">
                    <div className="font-semibold text-hub-text">
                      {thread.is_pinned ? '📌 ' : ''}
                      {thread.title}
                    </div>
                    <div className="text-hub-muted">
                      {thread.student.display_name} · {thread.reply_count} replies
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-bold text-hub-text">Participants</h3>
              <ul className="mt-3 space-y-2 text-sm">
                {data.discussion.participants.map((p, idx) => (
                  <li key={idx} className="flex justify-between gap-2 rounded-xl border border-slate-100 px-3 py-2">
                    <span className="font-medium text-hub-text">{p.student.display_name}</span>
                    <span className="text-hub-muted">
                      {p.threads} threads · {p.replies} replies
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-8">
          {hasDocument ? (
            <>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <AssignmentDetailsGrid
                  dueDate={assignment.due_date}
                  quarter={assignment.quarter}
                  assignmentType={assignment.assignment_type}
                />
              </div>
              <DocumentViewer attachments={data.attachments} single={data.attachment} />
            </>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4">
                <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-hub-muted">
                  <i className="bi bi-card-text" aria-hidden />
                  Description
                </h2>
                <p className="mt-2 whitespace-pre-wrap text-sm text-hub-text">
                  {assignment.description?.trim() ? assignment.description : 'N/A'}
                </p>
              </div>
              <AssignmentDetailsGrid
                dueDate={assignment.due_date}
                quarter={assignment.quarter}
                assignmentType={assignment.assignment_type}
              />
            </div>
          )}

          {!hasDocument ? <AssignmentActionsCard {...actionHandlers} /> : null}

          {data.groups && data.groups.length > 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold uppercase tracking-wide text-hub-muted">Groups</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {data.groups.map((g) => (
                  <div key={g.id} className="rounded-xl border border-slate-200 p-4">
                    <div className="font-semibold text-hub-text">{g.name}</div>
                    <ul className="mt-2 space-y-1 text-sm text-hub-muted">
                      {g.members.map((m) => (
                        <li key={m.id}>{m.display_name}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-4">{sidebar}</div>
      </div>

      <GrantExtensionModal
        open={extensionOpen}
        assignmentId={numericAssignmentId}
        classId={numericClassId}
        isGroup={isGroup}
        students={students}
        currentDueDate={assignment.due_date}
        onClose={() => setExtensionOpen(false)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load({ silent: true })
        }}
      />

      <RedoOpportunityModal
        open={redoOpen}
        assignmentId={numericAssignmentId}
        students={students}
        onClose={() => setRedoOpen(false)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load({ silent: true })
        }}
      />

      <ReopenAssignmentModal
        open={reopenOpen}
        assignmentId={numericAssignmentId}
        isQuiz={Boolean(actionMeta.is_quiz)}
        maxAttempts={actionMeta.max_attempts}
        onClose={() => setReopenOpen(false)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load({ silent: true })
        }}
      />

      <UnvoidAssignmentModal
        open={unvoidOpen}
        assignmentId={numericAssignmentId}
        type={isGroup ? 'group' : 'individual'}
        students={students}
        voidedStudentIds={voidedStudentIds}
        onClose={() => setUnvoidOpen(false)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load({ silent: true })
        }}
      />

      <VoidAssignmentModal
        target={voidTarget}
        students={students}
        onClose={() => setVoidTarget(null)}
        onSuccess={(msg) => {
          setMessage(msg)
          void load({ silent: true })
        }}
      />

      <EditAssignmentModal
        open={editOpen}
        assignmentId={numericAssignmentId}
        isGroup={isGroup}
        onClose={() => setEditOpen(false)}
        onSaved={(msg) => {
          setMessage(msg)
          void load({ silent: true })
        }}
      />

      <DeleteAssignmentModal
        target={
          deleteOpen
            ? {
                id: numericAssignmentId,
                title: assignment.title || 'Assignment',
                type: isGroup ? 'group' : 'individual',
              }
            : null
        }
        classId={numericClassId}
        workspaceScope={workspaceScope}
        onClose={() => setDeleteOpen(false)}
        onSuccess={(msg) => {
          setMessage(msg)
          navigate(classPath)
        }}
      />
    </div>
  )
}
