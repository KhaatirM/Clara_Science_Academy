import { calendarEventClass } from '../../utils/calendarEventColors'

/** Matches management calendar legend labels (CalendarPage / legacy shared calendar). */
export const CALENDAR_LEGEND_ITEMS = [
  { type: 'quarter_start', label: 'Quarter Start' },
  { type: 'quarter_end', label: 'Quarter End' },
  { type: 'semester_start', label: 'Semester Start' },
  { type: 'semester_end', label: 'Semester End' },
  { type: 'school_year_start', label: 'School Year Begins' },
  { type: 'school_year_end', label: 'School Year Ends' },
  { type: 'teacher_work_day', label: 'Teacher Work Day' },
  { type: 'school_break_start', label: 'School Break Start' },
  { type: 'school_break_end', label: 'School Break End' },
  { type: 'holiday', label: 'Holiday' },
  { type: 'professional_development', label: 'Professional Development' },
  { type: 'other_event', label: 'Other Events' },
] as const

type CalendarLegendProps = {
  /** When true, use management calendar legend layout classes (mgmt-cal-*). */
  managementLayout?: boolean
  className?: string
}

export function CalendarLegend({ managementLayout = false, className = '' }: CalendarLegendProps) {
  if (managementLayout) {
    return (
      <div className={`mgmt-cal-legend ${className}`.trim()} aria-label="Calendar legend">
        <div className="mgmt-cal-legend-head">
          <span className="mgmt-cal-legend-title">
            <i className="bi bi-palette-fill" aria-hidden="true" /> Calendar legend
          </span>
        </div>
        <ul className="mgmt-cal-legend-list">
          {CALENDAR_LEGEND_ITEMS.map(({ type, label }) => (
            <li key={type} className="mgmt-cal-legend-item">
              <span className={`calendar-legend-item ${calendarEventClass(type)}`} aria-hidden="true" />
              <span>{label}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`.trim()}
      aria-label="Calendar legend"
    >
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
        <i className="bi bi-palette-fill text-slate-500" aria-hidden="true" />
        Calendar legend
      </h2>
      <ul className="m-0 grid list-none grid-cols-2 gap-x-4 gap-y-2.5 p-0 sm:grid-cols-3 lg:grid-cols-4">
        {CALENDAR_LEGEND_ITEMS.map(({ type, label }) => (
          <li key={type} className="flex items-center gap-2 text-sm text-slate-600">
            <span
              className={`calendar-legend-item shrink-0 ${calendarEventClass(type)}`}
              aria-hidden="true"
            />
            <span>{label}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
