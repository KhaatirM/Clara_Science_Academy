import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  createAnnouncement,
  fetchAnnouncementCompose,
  type AnnouncementBroadcastOption,
  type AnnouncementPanelItem,
} from '../../api/announcements'

type Props = {
  open: boolean
  onClose: () => void
  /** When set, defaults broadcast to this class and shows class history. */
  classId?: number | null
  className?: string | null
  onSent?: () => void
}

function formatTime(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function AnnouncementComposeModal({
  open,
  onClose,
  classId = null,
  className = null,
  onSent,
}: Props) {
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [options, setOptions] = useState<AnnouncementBroadcastOption[]>([])
  const [past, setPast] = useState<AnnouncementPanelItem[]>([])
  const [broadcast, setBroadcast] = useState('')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [important, setImportant] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const data = await fetchAnnouncementCompose(classId)
      setOptions(data.broadcast_options || [])
      setPast(data.past_announcements || [])
      setBroadcast(data.default_broadcast || data.broadcast_options?.[0]?.value || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load announcement options')
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    if (!open) return
    setTitle('')
    setBody('')
    setImportant(false)
    void load()
  }, [open, load])

  const selected = useMemo(
    () => options.find((o) => o.value === broadcast) || null,
    [options, broadcast],
  )

  const submitLabel = useMemo(() => {
    if (broadcast === 'all_students') return 'Send to all students'
    if (selected?.is_current) return 'Send to this class'
    if (broadcast.startsWith('class:')) return 'Send to selected class'
    return 'Send announcement'
  }, [broadcast, selected])

  if (!open) return null

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setMessage(null)
    try {
      await createAnnouncement({
        title: title.trim(),
        message: body.trim(),
        broadcast,
        is_important: important,
      })
      setMessage('Announcement sent.')
      setTitle('')
      setBody('')
      setImportant(false)
      await load()
      onSent?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send announcement')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="announcement-compose-title"
      >
        <div className="flex items-center justify-between bg-teal-700 px-5 py-4 text-white">
          <div>
            <h2 id="announcement-compose-title" className="text-lg font-bold">
              <i className="bi bi-megaphone-fill me-2" aria-hidden />
              {className ? `Announce · ${className}` : 'Send announcement'}
            </h2>
            <p className="mt-0.5 text-sm text-white/80">
              {classId
                ? 'Message this class or choose another audience'
                : 'School-wide or class announcements'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-white/80 hover:text-white"
            aria-label="Close"
          >
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>

        <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-5">
          <form
            onSubmit={(e) => void handleSubmit(e)}
            className="flex min-h-0 flex-col overflow-y-auto border-b border-slate-200 p-5 lg:col-span-3 lg:border-b-0 lg:border-r"
          >
            {loading ? <p className="text-sm text-hub-muted">Loading options…</p> : null}
            {error ? (
              <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </div>
            ) : null}
            {message ? (
              <div className="mb-3 rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
                {message}
              </div>
            ) : null}

            <label className="mb-3 flex flex-col gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Title <span className="text-red-600">*</span>
              </span>
              <input
                className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={200}
                required
                placeholder="e.g. Homework reminder, field trip update"
              />
            </label>

            <label className="mb-3 flex flex-col gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Announcement <span className="text-red-600">*</span>
              </span>
              <textarea
                className="min-h-[10rem] rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                required
                rows={7}
                placeholder="Write the full message students will see…"
              />
            </label>

            <label className="mb-3 flex flex-col gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Broadcast to
              </span>
              <select
                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
                value={broadcast}
                onChange={(e) => setBroadcast(e.target.value)}
                required
                disabled={loading || options.length === 0}
              >
                {options.length === 0 ? <option value="">No audiences available</option> : null}
                {options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {selected?.description ? (
                <span className="text-xs text-hub-muted">{selected.description}</span>
              ) : null}
            </label>

            <label className="mb-5 flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300"
                checked={important}
                onChange={(e) => setImportant(e.target.checked)}
              />
              Mark as important
            </label>

            <div className="mt-auto flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
              <button
                type="submit"
                disabled={submitting || loading || !broadcast}
                className="rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
              >
                <i className="bi bi-send me-1" aria-hidden />
                {submitting ? 'Sending…' : submitLabel}
              </button>
            </div>
          </form>

          <aside className="min-h-0 overflow-y-auto bg-slate-50 p-5 lg:col-span-2">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="mb-0 text-sm font-bold uppercase tracking-wide text-slate-600">
                <i className="bi bi-clock-history me-1" aria-hidden />
                {classId ? 'Past for this class' : 'Recent options'}
              </h3>
              <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600">
                {past.length}
              </span>
            </div>
            {past.length === 0 ? (
              <p className="text-sm text-hub-muted">
                {classId
                  ? 'No announcements yet for this class.'
                  : 'Send an announcement to get started. Open a class view to see class history.'}
              </p>
            ) : (
              <ul className="space-y-2">
                {past.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="mb-0 text-sm font-semibold text-slate-900">{item.title}</p>
                      {item.is_important ? (
                        <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-900">
                          Important
                        </span>
                      ) : null}
                    </div>
                    <p className="mb-1 mt-1 line-clamp-3 text-xs text-slate-600">{item.message}</p>
                    <p className="mb-0 text-[11px] text-hub-muted">
                      {item.target_label}
                      {item.timestamp ? ` · ${formatTime(item.timestamp)}` : ''}
                      {item.sender_name ? ` · ${item.sender_name}` : ''}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </div>
    </div>
  )
}
