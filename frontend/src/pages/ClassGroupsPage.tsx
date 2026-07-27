import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useOutletContext, useParams } from 'react-router-dom'
import { fetchClassGroups, mutateClassGroups, type ClassGroupsScope } from '../api/classGroups'
import { ClassSubpageShell } from '../components/classes/ClassSubpageShell'
import { ClassWorkflowNav } from '../components/classes/ClassWorkflowNav'
import type { ManagementOutletContext } from '../types/layout'
import type { ClassGroupItem, ClassGroupsResponse } from '../types/classGroups'

function StatCard({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <div className="rounded-2xl border border-white/90 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
          <i className={`bi ${icon}`} aria-hidden />
        </span>
        <div>
          <div className="text-xl font-extrabold text-hub-text">{value}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
        </div>
      </div>
    </div>
  )
}

function GroupCard({
  group,
  availableStudentIds,
  enrolledNames,
  busy,
  onAddMembers,
  onRemoveMember,
  onSetLeader,
  onUpdate,
  onDelete,
}: {
  group: ClassGroupItem
  availableStudentIds: number[]
  enrolledNames: Map<number, string>
  busy: boolean
  onAddMembers: (groupId: number, studentIds: number[]) => Promise<void>
  onRemoveMember: (groupId: number, studentId: number) => Promise<void>
  onSetLeader: (groupId: number, studentId: number) => Promise<void>
  onUpdate: (groupId: number, name: string, description: string) => Promise<void>
  onDelete: (groupId: number) => Promise<void>
}) {
  const [addOpen, setAddOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [editName, setEditName] = useState(group.name)
  const [editDescription, setEditDescription] = useState(group.description)

  const memberIds = new Set(group.members.map((m) => m.student_id))
  const addable = availableStudentIds.filter((id) => !memberIds.has(id))

  return (
    <article className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-teal-100 bg-gradient-to-r from-teal-50 to-white px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-bold text-hub-text">{group.name}</h3>
            <p className="mt-0.5 text-xs text-hub-muted">
              {group.member_count} member{group.member_count === 1 ? '' : 's'}
            </p>
          </div>
          <span className="rounded-full bg-teal-100 px-2 py-0.5 text-[0.65rem] font-bold text-teal-900">
            Group
          </span>
        </div>
        {group.description ? <p className="mt-2 text-sm text-hub-muted">{group.description}</p> : null}
      </div>

      <div className="flex-1 p-4">
        {group.members.length ? (
          <ul className="space-y-2">
            {group.members.map((m) => (
              <li key={m.student_id} className="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-hub-text">
                  {m.display_name}
                  {m.is_leader ? (
                    <span className="ms-2 rounded-full bg-amber-100 px-1.5 py-0.5 text-[0.6rem] font-bold uppercase text-amber-900">
                      Leader
                    </span>
                  ) : null}
                </span>
                <div className="flex shrink-0 gap-1">
                  {!m.is_leader ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void onSetLeader(group.id, m.student_id)}
                      className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                      title="Set as leader"
                    >
                      <i className="bi bi-star" aria-hidden />
                    </button>
                  ) : null}
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void onRemoveMember(group.id, m.student_id)}
                    className="rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-800 hover:bg-red-100 disabled:opacity-50"
                    title="Remove from group"
                  >
                    <i className="bi bi-x-lg" aria-hidden />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-4 text-center text-sm text-hub-muted">No members yet.</p>
        )}
      </div>

      <div className="flex flex-wrap gap-2 border-t border-slate-100 bg-slate-50 p-3">
        <button
          type="button"
          disabled={busy || !addable.length}
          onClick={() => {
            setSelectedIds([])
            setAddOpen((v) => !v)
          }}
          className="rounded-full border border-teal-300 bg-white px-3 py-1.5 text-xs font-semibold text-teal-800 hover:bg-teal-50 disabled:opacity-50"
        >
          <i className="bi bi-person-plus me-1" aria-hidden />
          Add members
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setEditName(group.name)
            setEditDescription(group.description)
            setEditOpen((v) => !v)
          }}
          className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-400"
        >
          <i className="bi bi-pencil me-1" aria-hidden />
          Edit
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            if (
              window.confirm(
                `Delete "${group.name}"?\n\nExisting grades and submissions for this group are kept per student.`,
              )
            ) {
              void onDelete(group.id)
            }
          }}
          className="rounded-full border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-50 disabled:opacity-50"
        >
          <i className="bi bi-trash me-1" aria-hidden />
          Delete
        </button>
      </div>

      {addOpen ? (
        <div className="border-t border-slate-200 bg-white p-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">Add students</p>
          {addable.length ? (
            <div className="max-h-40 space-y-1 overflow-y-auto">
              {addable.map((id) => (
                <label key={id} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(id)}
                    onChange={(e) =>
                      setSelectedIds((prev) =>
                        e.target.checked ? [...prev, id] : prev.filter((x) => x !== id),
                      )
                    }
                  />
                  {enrolledNames.get(id) || `Student #${id}`}
                </label>
              ))}
            </div>
          ) : (
            <p className="text-sm text-hub-muted">All enrolled students are already in this group.</p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy || !selectedIds.length}
              onClick={() =>
                void onAddMembers(group.id, selectedIds).then(() => {
                  setAddOpen(false)
                  setSelectedIds([])
                })
              }
              className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              Add selected
            </button>
            <button
              type="button"
              onClick={() => setAddOpen(false)}
              className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {editOpen ? (
        <div className="border-t border-slate-200 bg-white p-4">
          <div className="space-y-2">
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="Group name"
            />
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="Description (optional)"
            />
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy || !editName.trim()}
              onClick={() =>
                void onUpdate(group.id, editName.trim(), editDescription).then(() => setEditOpen(false))
              }
              className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              Save
            </button>
            <button
              type="button"
              onClick={() => setEditOpen(false)}
              className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </article>
  )
}

export function ClassGroupsPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const { classId } = useParams()
  const location = useLocation()
  const scope: ClassGroupsScope = location.pathname.startsWith('/teacher/') ? 'teacher' : 'management'
  const id = Number(classId)
  const isDirector = user.role_canonical === 'Director'
  const [data, setData] = useState<ClassGroupsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [createName, setCreateName] = useState('')
  const [createDescription, setCreateDescription] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassGroups(id, scope))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load groups')
    } finally {
      setLoading(false)
    }
  }, [id, scope])

  useEffect(() => {
    void load()
  }, [load])

  const enrolledNames = useMemo(() => {
    const map = new Map<number, string>()
    for (const s of data?.enrolled_students ?? []) {
      map.set(s.id, s.display_name)
    }
    return map
  }, [data?.enrolled_students])

  const enrolledIds = useMemo(() => data?.enrolled_students.map((s) => s.id) ?? [], [data?.enrolled_students])

  async function runMutation(fn: () => Promise<{ success: boolean; message: string }>) {
    setBusy(true)
    setToast(null)
    try {
      const result = await fn()
      if (!result.success) {
        setToast(result.message)
        return
      }
      setToast(result.message)
      await load()
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  if (!Number.isFinite(id) || id <= 0) {
    return (
      <ClassSubpageShell eyebrow="Class groups" title="Manage groups">
        <p className="text-hub-muted">Invalid class link.</p>
      </ClassSubpageShell>
    )
  }

  const cls = data?.class

  return (
    <ClassSubpageShell
      eyebrow="Class groups"
      title={cls?.name ? `Manage groups — ${cls.name}` : 'Manage groups'}
      subtitle={cls?.subject || undefined}
      actions={
        data && scope === 'management' ? (
          <ClassWorkflowNav
            classId={id}
            active="view"
            isDirector={isDirector}
            canAdminUi={data.meta?.can_admin_ui ?? true}
          />
        ) : null
      }
    >
      {loading ? <p className="text-hub-muted">Loading groups…</p> : null}
      {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {toast ? (
        <div className="mb-4 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-hub-text">{toast}</div>
      ) : null}

      {data ? (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <StatCard icon="bi-people" value={data.stats.total_groups} label="Total groups" />
            <StatCard icon="bi-person-check" value={data.stats.total_students} label="Enrolled students" />
            <StatCard icon="bi-activity" value={data.stats.avg_group_size} label="Avg group size" />
          </div>

          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <Link
              to={scope === 'teacher' ? `/teacher/classes/${id}` : `/management/classes/${id}`}
              className="text-sm font-semibold text-teal-700 hover:underline"
            >
              <i className="bi bi-arrow-left me-1" aria-hidden />
              Back to class view
            </Link>
            <button
              type="button"
              onClick={() => setShowCreate((v) => !v)}
              className="inline-flex items-center gap-1.5 rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
            >
              <i className="bi bi-plus-circle" aria-hidden />
              Create group
            </button>
          </div>

          {showCreate ? (
            <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-hub-muted">New group</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  type="text"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="Group name"
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  value={createDescription}
                  onChange={(e) => setCreateDescription(e.target.value)}
                  placeholder="Description (optional)"
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  disabled={busy || !createName.trim()}
                  onClick={() =>
                    void runMutation(() =>
                      mutateClassGroups(
                        id,
                        {
                          action: 'create',
                          name: createName.trim(),
                          description: createDescription.trim() || undefined,
                        },
                        scope,
                      ),
                    ).then(() => {
                      setCreateName('')
                      setCreateDescription('')
                      setShowCreate(false)
                    })
                  }
                  className="rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}

          {data.groups.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {data.groups.map((group) => (
                <GroupCard
                  key={group.id}
                  group={group}
                  availableStudentIds={enrolledIds}
                  enrolledNames={enrolledNames}
                  busy={busy}
                  onAddMembers={(groupId, studentIds) =>
                    runMutation(() =>
                      mutateClassGroups(id, { action: 'add_members', group_id: groupId, student_ids: studentIds }, scope),
                    )
                  }
                  onRemoveMember={(groupId, studentId) =>
                    runMutation(() =>
                      mutateClassGroups(id, { action: 'remove_member', group_id: groupId, student_id: studentId }, scope),
                    )
                  }
                  onSetLeader={(groupId, studentId) =>
                    runMutation(() =>
                      mutateClassGroups(id, { action: 'set_leader', group_id: groupId, student_id: studentId }, scope),
                    )
                  }
                  onUpdate={(groupId, name, description) =>
                    runMutation(() =>
                      mutateClassGroups(id, { action: 'update', group_id: groupId, name, description }, scope),
                    )
                  }
                  onDelete={(groupId) =>
                    runMutation(() => mutateClassGroups(id, { action: 'delete', group_id: groupId }, scope))
                  }
                />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-white/80 px-6 py-12 text-center">
              <i className="bi bi-people mb-2 block text-3xl text-teal-600" aria-hidden />
              <p className="font-semibold text-hub-text">No groups yet</p>
              <p className="mt-1 text-sm text-hub-muted">Create a group to organize students for collaborative work.</p>
            </div>
          )}
        </>
      ) : null}
    </ClassSubpageShell>
  )
}
