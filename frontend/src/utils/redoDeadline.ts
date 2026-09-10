/** Default redo deadline: original close/due when still upcoming, else today + 7 days. */

function toDateOnly(value: string | null | undefined): string | null {
  if (!value) return null
  const m = String(value).match(/^(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : null
}

function todayDateOnly(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function plusDaysDateOnly(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * If the assignment is still before its close (or due) date, prefer that date.
 * Otherwise fall back to one week from today.
 */
export function defaultRedoDeadline(opts?: {
  dueDate?: string | null
  closeDate?: string | null
}): string {
  const today = todayDateOnly()
  const preferred = toDateOnly(opts?.closeDate) || toDateOnly(opts?.dueDate)
  if (preferred && preferred >= today) {
    return preferred
  }
  return plusDaysDateOnly(7)
}
