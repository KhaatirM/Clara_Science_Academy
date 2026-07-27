const KNOWN_EVENT_TYPES = new Set([
  'quarter_start',
  'quarter_end',
  'semester_start',
  'semester_end',
  'school_year_start',
  'school_year_end',
  'teacher_work_day',
  'school_break_start',
  'school_break_end',
  'holiday',
  'professional_development',
  'other_event',
])

/** Normalize event type to legacy shared_calendar.css class suffix (event-*). */
export function normalizeCalendarEventType(type: string): string {
  if (type === 'other' || type === 'other_event') return 'other_event'
  if (type === 'break' || type === 'school_break') return 'school_break_start'
  if (type === 'professional_development' || type === 'pd') return 'professional_development'
  if (KNOWN_EVENT_TYPES.has(type)) return type
  return 'other_event'
}

/** Legacy calendar-event badge class (pairs with shared_calendar.css). */
export function calendarEventClass(type: string): string {
  return `event-${normalizeCalendarEventType(type)}`
}
