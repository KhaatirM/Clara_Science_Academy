import { useCallback, useEffect, useState } from 'react'
import {
  deleteDeadlineReminder,
  fetchClassDeadlineReminders,
  sendDeadlineReminderNow,
  toggleDeadlineReminder,
} from '../../api/deadlineReminders'
import type { ClassDeadlineRemindersResponse, DeadlineReminderRow } from '../../types/classTools'
import { DeadlineReminderFormPanel } from './DeadlineReminderFormPanel'

type Props = {
  open: boolean
  classId: number
  onClose: () => void
  scope?: 'management' | 'teacher'
}

type View = 'list' | 'create' | 'edit'

function formatDateTime(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function typeLabel(type: string) {
  if (type === 'group_assignment') return 'Group assignment'
  if (type === 'general') return 'General'
  return 'Assignment'
}

function StatCard({
  label,
  value,
  icon,
  gradient,
}: {
  label: string
  value: number
  icon: string
  gradient: string
}) {
  return (
    <div className={`rounded-xl p-4 text-center text-white ${gradient}`}>
      <i className={`bi ${icon} mb-1 block text-2xl opacity-80`} aria-hidden />
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs font-semibold uppercase tracking-wide text-white/80">{label}</div>
    </div>
  )
}

function ReminderActions({
  classId,
  reminder,
  busy,
  onAction,
  scope = 'management',
}: {
  classId: number
  reminder: DeadlineReminderRow
  busy: boolean
  onAction: () => void
  scope?: 'management' | 'teacher'
}) {
  const [acting, setActing] = useState(false)

  const run = async (fn: () => Promise<unknown>, confirmMsg?: string) => {
    if (confirmMsg && !window.confirm(confirmMsg)) return
    setActing(true)
    try {
      await fn()
      onAction()
    } catch (e) {
      window.alert(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setActing(false)
    }
  }

  const disabled = busy || acting
  const isActive = reminder.status === 'active'

  return (
    <div className="flex flex-wrap gap-1">
      <button
        type="button"
        title={isActive ? 'Deactivate' : 'Activate'}
        disabled={disabled}
        onClick={() =>
          void run(() => toggleDeadlineReminder(classId, reminder.id, scope))
        }
        className="rounded border border-amber-300 px-2 py-1 text-amber-800 hover:bg-amber-50 disabled:opacity-50"
      >
        <i className={`bi bi-${isActive ? 'pause' : 'play'}-fill`} aria-hidden />
      </button>
      <button
        type="button"
        title="Send now"
        disabled={disabled}
        onClick={() =>
          void run(() => sendDeadlineReminderNow(classId, reminder.id, scope), 'Send this reminder now?')
        }
        className="rounded border border-cyan-300 px-2 py-1 text-cyan-800 hover:bg-cyan-50 disabled:opacity-50"
      >
        <i className="bi bi-send-fill" aria-hidden />
      </button>
      <button
        type="button"
        title="Delete"
        disabled={disabled}
        onClick={() =>
          void run(
            () => deleteDeadlineReminder(classId, reminder.id, scope),
            'Delete this reminder permanently?',
          )
        }
        className="rounded border border-red-300 px-2 py-1 text-red-700 hover:bg-red-50 disabled:opacity-50"
      >
        <i className="bi bi-trash-fill" aria-hidden />
      </button>
    </div>
  )
}

export function ClassDeadlineRemindersModal({ open, classId, onClose, scope = 'management' }: Props) {
  const [data, setData] = useState<ClassDeadlineRemindersResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [view, setView] = useState<View>('list')
  const [editId, setEditId] = useState<number | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassDeadlineReminders(classId, scope))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load reminders')
    } finally {
      setLoading(false)
    }
  }, [classId, scope])

  useEffect(() => {
    if (open && classId) {
      setView('list')
      setEditId(null)
      void load()
    }
  }, [open, classId, load])

  const handleSaved = () => {
    setView('list')
    setEditId(null)
    setToast('Reminder saved.')
    void load()
  }

  const openEdit = (id: number) => {
    setEditId(id)
    setView('edit')
  }

  if (!open) return null

  const stats = data?.stats
  const upcoming = data?.upcoming ?? []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between bg-gradient-to-r from-pink-500 to-rose-500 px-5 py-4 text-white">
          <div>
            <h2 className="text-lg font-bold">
              <i className="bi bi-bell-fill me-2" aria-hidden />
              Deadline Reminders
            </h2>
            {data ? (
              <p className="mt-0.5 text-sm text-white/85">
                {data.name} · Stay on track
              </p>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            {view === 'list' ? (
              <button
                type="button"
                onClick={() => setView('create')}
                className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-bold text-pink-700 hover:bg-white/95"
              >
                <i className="bi bi-plus-circle" aria-hidden />
                Create reminder
              </button>
            ) : null}
            <button type="button" onClick={onClose} className="text-white/80 hover:text-white" aria-label="Close">
              <i className="bi bi-x-lg" aria-hidden />
            </button>
          </div>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          {toast ? (
            <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{toast}</p>
          ) : null}

          {view === 'create' ? (
            <DeadlineReminderFormPanel
              classId={classId}
              scope={scope}
              onSaved={handleSaved}
              onCancel={() => setView('list')}
            />
          ) : null}

          {view === 'edit' && editId != null ? (
            <DeadlineReminderFormPanel
              classId={classId}
              reminderId={editId}
              scope={scope}
              onSaved={handleSaved}
              onCancel={() => {
                setView('list')
                setEditId(null)
              }}
            />
          ) : null}

          {view === 'list' ? (
            <>
              {loading ? <p className="text-hub-muted">Loading reminders…</p> : null}
              {error ? <p className="text-red-700">{error}</p> : null}

              {data && stats ? (
                <div className="space-y-5">
                  {upcoming.length > 0 ? (
                    <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                      <h3 className="mb-3 text-sm font-bold text-amber-900">
                        <i className="bi bi-exclamation-triangle me-1" aria-hidden />
                        Upcoming reminders (next 7 days)
                      </h3>
                      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                        {upcoming.map((r) => (
                          <div key={r.id} className="rounded-lg border border-amber-200 bg-white p-3 text-sm">
                            <div className="font-semibold text-hub-text">{r.title}</div>
                            <p className="mt-1 line-clamp-2 text-hub-muted">{r.message}</p>
                            <div className="mt-1 text-xs text-hub-muted">
                              <i className="bi bi-clock me-1" aria-hidden />
                              {formatDateTime(r.send_at)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  ) : null}

                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <StatCard
                      label="Total"
                      value={stats.total}
                      icon="bi-bell-fill"
                      gradient="bg-gradient-to-br from-pink-500 to-rose-500"
                    />
                    <StatCard
                      label="Active"
                      value={stats.active}
                      icon="bi-check-circle-fill"
                      gradient="bg-gradient-to-br from-teal-600 to-indigo-900"
                    />
                    <StatCard
                      label="Next 7 days"
                      value={stats.upcoming}
                      icon="bi-clock-history"
                      gradient="bg-gradient-to-br from-pink-400 to-amber-300"
                    />
                    <StatCard
                      label="Assignments"
                      value={stats.assignment}
                      icon="bi-file-text-fill"
                      gradient="bg-gradient-to-br from-indigo-500 to-purple-700"
                    />
                  </div>

                  <section className="overflow-hidden rounded-xl border border-slate-200">
                    <div className="bg-blue-600 px-4 py-2.5 text-sm font-bold text-white">
                      <i className="bi bi-bell me-1" aria-hidden />
                      All deadline reminders
                    </div>
                    {data.reminders.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                            <tr>
                              <th className="px-3 py-2">Title</th>
                              <th className="px-3 py-2">Type</th>
                              <th className="px-3 py-2">Assignment</th>
                              <th className="px-3 py-2">Reminder date</th>
                              <th className="px-3 py-2">Frequency</th>
                              <th className="px-3 py-2">Status</th>
                              <th className="px-3 py-2">Last sent</th>
                              <th className="px-3 py-2">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.reminders.map((r) => (
                              <tr key={r.id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="px-3 py-2">
                                  <div className="font-semibold text-hub-text">{r.title}</div>
                                  <div className="max-w-[200px] truncate text-xs text-hub-muted">
                                    {r.message}
                                  </div>
                                </td>
                                <td className="px-3 py-2">
                                  <span className="rounded-full bg-cyan-100 px-2 py-0.5 text-xs font-semibold text-cyan-900">
                                    {typeLabel(r.reminder_type)}
                                  </span>
                                </td>
                                <td className="px-3 py-2">
                                  {r.assignment_title ? (
                                    <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-800">
                                      {r.assignment_title}
                                    </span>
                                  ) : (
                                    <span className="text-hub-muted">General</span>
                                  )}
                                </td>
                                <td className="px-3 py-2 whitespace-nowrap text-xs">
                                  {formatDateTime(r.send_at)}
                                </td>
                                <td className="px-3 py-2 capitalize">{r.reminder_frequency}</td>
                                <td className="px-3 py-2">
                                  <span
                                    className={`rounded-full px-2 py-0.5 text-xs font-bold uppercase ${
                                      r.status === 'active'
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : 'bg-slate-100 text-slate-600'
                                    }`}
                                  >
                                    {r.status}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-xs text-hub-muted whitespace-nowrap">
                                  {r.last_sent ? formatDateTime(r.last_sent) : 'Never sent'}
                                </td>
                                <td className="px-3 py-2">
                                  <div className="flex flex-wrap items-center gap-1">
                                    <button
                                      type="button"
                                      title="Edit"
                                      disabled={loading}
                                      onClick={() => openEdit(r.id)}
                                      className="rounded border border-blue-300 px-2 py-1 text-blue-800 hover:bg-blue-50"
                                    >
                                      <i className="bi bi-pencil-fill" aria-hidden />
                                    </button>
                                    <ReminderActions
                                      classId={classId}
                                      reminder={r}
                                      busy={loading}
                                      scope={scope}
                                      onAction={() => void load()}
                                    />
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="px-4 py-10 text-center">
                        <i className="bi bi-bell mb-2 block text-4xl text-slate-300" aria-hidden />
                        <h4 className="font-semibold text-hub-muted">No deadline reminders found</h4>
                        <p className="mt-1 text-sm text-hub-muted">
                          Create your first reminder to help students stay on track.
                        </p>
                        <button
                          type="button"
                          onClick={() => setView('create')}
                          className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-pink-600 px-4 py-2 text-sm font-bold text-white hover:bg-pink-700"
                        >
                          <i className="bi bi-plus-circle" aria-hidden />
                          Create first reminder
                        </button>
                      </div>
                    )}
                  </section>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4 text-sm">
                      <h4 className="font-bold text-cyan-900">
                        <i className="bi bi-lightbulb me-1" aria-hidden />
                        Reminder benefits
                      </h4>
                      <ul className="mt-2 list-disc space-y-1 ps-5 text-cyan-950">
                        <li>Help students stay on track with deadlines</li>
                        <li>Reduce late submissions</li>
                        <li>Improve time management skills</li>
                        <li>Increase assignment completion rates</li>
                      </ul>
                    </div>
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm">
                      <h4 className="font-bold text-amber-900">
                        <i className="bi bi-gear me-1" aria-hidden />
                        Quick actions
                      </h4>
                      <div className="mt-3 grid gap-2">
                        <button
                          type="button"
                          onClick={() => setView('create')}
                          className="rounded-lg bg-pink-600 px-3 py-2 text-left text-sm font-semibold text-white hover:bg-pink-700"
                        >
                          <i className="bi bi-plus-circle me-1" aria-hidden />
                          Create new reminder
                        </button>
                        <button
                          type="button"
                          onClick={onClose}
                          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700"
                        >
                          <i className="bi bi-arrow-left me-1" aria-hidden />
                          Back to class
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
