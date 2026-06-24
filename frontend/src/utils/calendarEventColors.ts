/** Tailwind classes for calendar event badges (mirrors legacy shared_calendar.css). */
export function calendarEventClass(type: string): string {
  const normalized = type === 'other' ? 'other_event' : type
  const map: Record<string, string> = {
    quarter_start: 'bg-emerald-600 hover:bg-emerald-700',
    quarter_end: 'bg-teal-700 hover:bg-teal-800',
    semester_start: 'bg-indigo-600 hover:bg-indigo-700',
    semester_end: 'bg-violet-700 hover:bg-violet-800',
    teacher_work_day: 'bg-amber-600 hover:bg-amber-700',
    school_break_start: 'bg-sky-600 hover:bg-sky-700',
    school_break_end: 'bg-blue-700 hover:bg-blue-800',
    holiday: 'bg-rose-600 hover:bg-rose-700',
    professional_development: 'bg-orange-600 hover:bg-orange-700',
    other_event: 'bg-slate-600 hover:bg-slate-700',
  }
  return map[normalized] || map.other_event
}
