export function formatWhen(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export const STATUS_BADGE: Record<string, string> = {
  on_time: 'bg-emerald-100 text-emerald-800',
  late: 'bg-amber-100 text-amber-900',
  not_submitted: 'bg-slate-100 text-slate-600',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${STATUS_BADGE[status] || STATUS_BADGE.not_submitted}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export function StudentAvatar({ name }: { name: string }) {
  const parts = name.trim().split(/\s+/)
  const initials = (parts[0]?.[0] || '?') + (parts[parts.length - 1]?.[0] || '')
  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-indigo-700 text-sm font-bold text-white">
      {initials.toUpperCase()}
    </div>
  )
}

export function StatGrid({ stats }: { stats: Record<string, number> }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {Object.entries(stats).map(([key, value]) => (
        <div key={key} className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="text-2xl font-extrabold text-hub-text">{value}</div>
          <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">
            {key.replace(/_/g, ' ')}
          </div>
        </div>
      ))}
    </div>
  )
}
