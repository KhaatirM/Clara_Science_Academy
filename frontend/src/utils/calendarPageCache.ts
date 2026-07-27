import type { CalendarPageResponse } from '../types/calendar'

const cache = new Map<string, CalendarPageResponse>()

export function calendarCacheKey(month: number, year: number): string {
  return `${year}-${month}`
}

export function getCalendarPageCache(month: number, year: number): CalendarPageResponse | undefined {
  return cache.get(calendarCacheKey(month, year))
}

export function setCalendarPageCache(month: number, year: number, data: CalendarPageResponse): void {
  cache.set(calendarCacheKey(month, year), data)
}

export function invalidateCalendarPageCache(): void {
  cache.clear()
}
