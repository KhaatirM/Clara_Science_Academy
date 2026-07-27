import { useCallback, useEffect, useState } from 'react'
import { fetchClassAssessmentTool, type AssessmentToolSlug } from '../../api/classTools'
import type { ClassAssessmentToolResponse } from '../../types/classTools'

const TOOL_META: Record<
  AssessmentToolSlug,
  { title: string; icon: string; headerClass: string; emptyMessage: string }
> = {
  '360-feedback': {
    title: '360° Feedback',
    icon: 'bi-arrow-repeat',
    headerClass: 'bg-cyan-700',
    emptyMessage: 'No 360° feedback sessions for this class yet.',
  },
  'reflection-journals': {
    title: 'Reflection Journals',
    icon: 'bi-journal-text',
    headerClass: 'bg-pink-600',
    emptyMessage: 'No reflection journals submitted for this class yet.',
  },
  conflicts: {
    title: 'Conflict Resolution',
    icon: 'bi-exclamation-triangle',
    headerClass: 'bg-amber-600',
    emptyMessage: 'No group conflicts reported for this class yet.',
  },
}

type Props = {
  open: boolean
  classId: number
  tool: AssessmentToolSlug
  onClose: () => void
  scope?: 'management' | 'teacher'
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return null
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function renderItems(tool: AssessmentToolSlug, data: ClassAssessmentToolResponse) {
  if (tool === '360-feedback' && 'sessions' in data) {
    if (!data.sessions.length) return null
    return (
      <ul className="space-y-2">
        {data.sessions.map((s) => (
          <li key={s.id} className="rounded-xl border border-slate-200 px-4 py-3 text-sm">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="font-semibold text-hub-text">{s.title}</div>
              <span
                className={`rounded-full px-2 py-0.5 text-[0.65rem] font-bold uppercase ${
                  s.status === 'active' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {s.status}
              </span>
            </div>
            <div className="mt-1 text-xs text-hub-muted">
              {s.feedback_type ? `${s.feedback_type.replace(/_/g, ' ')} · ` : ''}
              {formatDate(s.due_date) ? `Due ${formatDate(s.due_date)}` : formatDate(s.created_at) || 'No date'}
            </div>
          </li>
        ))}
      </ul>
    )
  }

  if (tool === 'reflection-journals' && 'journals' in data) {
    if (!data.journals.length) return null
    return (
      <ul className="space-y-2">
        {data.journals.map((j) => (
          <li key={j.id} className="rounded-xl border border-slate-200 px-4 py-3 text-sm">
            <div className="font-semibold text-hub-text">{j.title}</div>
            {j.assignment_title ? <div className="text-hub-muted">{j.assignment_title}</div> : null}
            <div className="mt-1 text-xs text-hub-muted">
              {formatDate(j.submitted_at) || 'Not submitted'}
              {j.collaboration_rating != null ? ` · Collaboration ${j.collaboration_rating}/5` : ''}
              {j.learning_rating != null ? ` · Learning ${j.learning_rating}/5` : ''}
            </div>
          </li>
        ))}
      </ul>
    )
  }

  if (tool === 'conflicts' && 'conflicts' in data) {
    if (!data.conflicts.length) return null
    return (
      <ul className="space-y-2">
        {data.conflicts.map((c) => (
          <li key={c.id} className="rounded-xl border border-slate-200 px-4 py-3 text-sm">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="font-semibold capitalize text-hub-text">{c.title.replace(/_/g, ' ')}</div>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-bold uppercase text-slate-700">
                {c.status}
              </span>
            </div>
            {c.description ? <p className="mt-1 text-hub-muted">{c.description}</p> : null}
            <div className="mt-1 text-xs text-hub-muted">
              {c.severity ? `${c.severity} severity · ` : ''}
              {formatDate(c.created_at) || 'No date'}
            </div>
          </li>
        ))}
      </ul>
    )
  }

  return null
}

function renderStats(tool: AssessmentToolSlug, data: ClassAssessmentToolResponse) {
  if (!('stats' in data) || !data.stats) return null
  const stats = data.stats
  const entries =
    tool === '360-feedback' && 'active' in stats
      ? [
          [stats.total, 'Sessions'],
          [stats.active, 'Active'],
        ]
      : tool === 'conflicts' && 'open' in stats
        ? [
            [stats.total, 'Total'],
            [stats.open, 'Open'],
          ]
        : 'total' in stats
          ? [[stats.total, 'Total']]
          : []

  if (!entries.length) return null
  return (
    <div className={`grid gap-3 ${entries.length > 1 ? 'sm:grid-cols-2' : ''}`}>
      {entries.map(([value, label]) => (
        <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
          <div className="text-2xl font-bold text-hub-text">{value}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
        </div>
      ))}
    </div>
  )
}

export function ClassAssessmentToolModal({ open, classId, tool, onClose, scope = 'management' }: Props) {
  const meta = TOOL_META[tool]
  const [data, setData] = useState<ClassAssessmentToolResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassAssessmentTool(classId, tool, scope))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [classId, tool, scope])

  useEffect(() => {
    if (open && classId) void load()
  }, [open, classId, load])

  if (!open) return null

  const items = data ? renderItems(tool, data) : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className={`flex items-center justify-between px-5 py-4 text-white ${meta.headerClass}`}>
          <div>
            <h2 className="text-lg font-bold">
              <i className={`bi ${meta.icon} me-2`} aria-hidden />
              {meta.title}
            </h2>
            {data ? <p className="mt-0.5 text-sm text-white/80">{data.name}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="text-white/80 hover:text-white" aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          {loading ? <p className="text-hub-muted">Loading…</p> : null}
          {error ? <p className="text-red-700">{error}</p> : null}
          {data ? (
            <div className="space-y-4">
              {renderStats(tool, data)}
              {items ?? (
                <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-hub-muted">
                  {meta.emptyMessage}
                </p>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
