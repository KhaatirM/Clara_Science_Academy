type Props = {
  totalSelectable: number
  selectedCount: number
  allSelected: boolean
  onToggleSelectAll: () => void
  onMarkSubmitted: (type: 'online' | 'in_person') => void
  onMarkNotes: (notes: 'On-Time' | 'Late' | 'Other') => void
  onClearSelection: () => void
}

export function BulkGradingToolbar({
  totalSelectable,
  selectedCount,
  allSelected,
  onToggleSelectAll,
  onMarkSubmitted,
  onMarkNotes,
  onClearSelection,
}: Props) {
  const hasSelection = selectedCount > 0

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm print:hidden">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-hub-text">
          <input
            type="checkbox"
            checked={allSelected && totalSelectable > 0}
            onChange={onToggleSelectAll}
            className="h-4 w-4 rounded border-slate-300 text-violet-600"
          />
          Select all
        </label>
        <span className="text-xs text-hub-muted">
          {hasSelection ? `${selectedCount} selected` : `${totalSelectable} students`}
        </span>
        {hasSelection ? (
          <button
            type="button"
            onClick={onClearSelection}
            className="text-xs font-semibold text-violet-700 hover:underline"
          >
            Clear
          </button>
        ) : null}
      </div>

      <div
        className={`mt-2 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2 ${!hasSelection ? 'opacity-50' : ''}`}
      >
        <span className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
          Mark selected:
        </span>
        <button
          type="button"
          disabled={!hasSelection}
          onClick={() => onMarkSubmitted('online')}
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 disabled:cursor-not-allowed"
        >
          <i className="bi bi-cloud-upload me-1" />
          Submitted (Online)
        </button>
        <button
          type="button"
          disabled={!hasSelection}
          onClick={() => onMarkSubmitted('in_person')}
          className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed"
        >
          <i className="bi bi-file-earmark-text me-1" />
          Submitted (Paper)
        </button>
        <span className="mx-1 hidden h-4 w-px bg-slate-200 sm:inline" />
        <span className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">
          Notes:
        </span>
        {(['On-Time', 'Late', 'Other'] as const).map((note) => (
          <button
            key={note}
            type="button"
            disabled={!hasSelection}
            onClick={() => onMarkNotes(note)}
            className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed"
          >
            {note}
          </button>
        ))}
      </div>
    </div>
  )
}
