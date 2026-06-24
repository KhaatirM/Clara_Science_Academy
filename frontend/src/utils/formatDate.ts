export function formatDateLong(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return 'TBD'
  const d = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function previewOffsetDate(baseIso: string, offsetDays: number): string {
  if (!baseIso) return '—'
  const d = new Date(`${baseIso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return '—'
  d.setDate(d.getDate() + offsetDays)
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function daysUntilLabel(days: number): string {
  if (days > 0) return `in ${days} day${days !== 1 ? 's' : ''}`
  if (days === 0) return 'today'
  return `${-days} day${days !== -1 ? 's' : ''} ago`
}
