function formatDue(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

type Props = {
  className: string
  subject?: string | null
  dueDate?: string | null
  quarter?: string | null
  description?: string
}

export function AssignmentDetailsStrip({
  className,
  subject,
  dueDate,
  quarter,
  description,
}: Props) {
  const items = [
    { icon: 'bi-book', label: 'Class', value: className },
    { icon: 'bi-calendar3', label: 'Due', value: formatDue(dueDate) },
    { icon: 'bi-grid-3x3-gap', label: 'Quarter', value: quarter || '—' },
    { icon: 'bi-bookmark', label: 'Subject', value: subject || 'N/A' },
  ]

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-2.5">
        <h2 className="text-sm font-bold text-hub-text">
          <i className="bi bi-info-circle me-2 text-violet-600" />
          Assignment details
        </h2>
      </div>
      <div className="grid gap-3 px-4 py-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2 min-w-0">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-50 text-violet-700">
              <i className={`bi ${item.icon} text-sm`} />
            </span>
            <div className="min-w-0">
              <div className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
                {item.label}
              </div>
              <div className="truncate text-sm font-semibold text-hub-text">{item.value}</div>
            </div>
          </div>
        ))}
      </div>
      {description ? (
        <div className="border-t border-slate-100 px-4 py-2.5 text-sm text-hub-muted">
          <span className="font-semibold text-hub-text">Description: </span>
          {description}
        </div>
      ) : null}
    </div>
  )
}
