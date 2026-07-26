import type { ParentChildBrief } from '../../types/parentPortal'

export function ParentChildPicker({
  children,
  activeChildId,
  busy,
  onSelect,
}: {
  children: ParentChildBrief[]
  activeChildId: number | null
  busy?: boolean
  onSelect: (studentId: number) => void
}) {
  if (!children.length) return null

  if (children.length === 1) {
    const only = children[0]
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3.5 py-2 text-sm font-semibold text-teal-900">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-700 text-xs font-bold text-white">
          {only.initial}
        </span>
        Viewing {only.display_name}
      </div>
    )
  }

  return (
    <label className="inline-flex items-center gap-2 text-sm font-semibold text-hub-text">
      <span className="text-hub-muted">Child</span>
      <select
        disabled={busy}
        value={activeChildId ?? ''}
        onChange={(e) => onSelect(Number(e.target.value))}
        className="rounded-full border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 shadow-sm focus:border-teal-500 focus:outline-none"
      >
        {children.map((child) => (
          <option key={child.id} value={child.id}>
            {child.display_name}
          </option>
        ))}
      </select>
    </label>
  )
}
