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
