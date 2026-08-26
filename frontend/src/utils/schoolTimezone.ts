import type { SchoolTimezone } from '../types/session'

export const DEFAULT_SCHOOL_TIMEZONE = 'America/New_York'

export function resolveSchoolTimezone(
  input?: SchoolTimezone | null,
): SchoolTimezone {
  if (input?.iana?.trim()) {
    return {
      iana: input.iana.trim(),
      clock: input.clock ?? '',
      zone: input.zone ?? '',
    }
  }
  return { iana: DEFAULT_SCHOOL_TIMEZONE, clock: '', zone: '' }
}

/**
 * Convert a stored ISO datetime (usually UTC) into a `datetime-local` value
 * in school timezone — matching how create forms interpret the picker.
 */
export function isoToSchoolDatetimeLocal(
  iso: string | null | undefined,
  timeZone: string = DEFAULT_SCHOOL_TIMEZONE,
): string {
  if (!iso) return ''
  const trimmed = String(iso).trim()
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(trimmed)) return trimmed
  const d = new Date(trimmed)
  if (Number.isNaN(d.getTime())) return ''
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(d)
    const get = (type: Intl.DateTimeFormatPartTypes) =>
      parts.find((p) => p.type === type)?.value || ''
    const year = get('year')
    const month = get('month')
    const day = get('day')
    let hour = get('hour')
    const minute = get('minute')
    if (hour === '24') hour = '00'
    if (!year || !month || !day || !hour || !minute) return ''
    return `${year}-${month}-${day}T${hour}:${minute}`
  } catch {
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
}

export function formatSchoolTime(
  iana: string,
  fallbackClock: string,
  fallbackZone: string,
) {
  try {
    const fmt = new Intl.DateTimeFormat('en-US', {
      timeZone: iana,
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZoneName: 'short',
    })
    const parts = fmt.formatToParts(new Date())
    let hour = ''
    let minute = ''
    let dayPeriod = ''
    let zone = ''
    for (const part of parts) {
      if (part.type === 'hour') hour = part.value
      if (part.type === 'minute') minute = part.value
      if (part.type === 'dayPeriod') dayPeriod = part.value
      if (part.type === 'timeZoneName') zone = part.value
    }
    const clock =
      hour && minute ? `${hour}:${minute} ${dayPeriod}` : fallbackClock
    return { clock, zone: zone || fallbackZone }
  } catch {
    return { clock: fallbackClock, zone: fallbackZone }
  }
}
