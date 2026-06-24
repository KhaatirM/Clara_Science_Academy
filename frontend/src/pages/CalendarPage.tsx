import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  addCalendarEvent,
  addSchoolBreak,
  addTeacherWorkDays,
  deleteSchoolBreak,
  deleteTeacherWorkDay,
  fetchCalendarPage,
} from '../api/calendar'
import type { CalendarEventItem, CalendarPageResponse } from '../types/calendar'
import { calendarEventClass } from '../utils/calendarEventColors'

function Modal({
  title,
  children,
  onClose,
}: {
  title: string
  children: React.ReactNode
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" role="dialog" aria-modal>
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-slate-800">{title}</h2>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

function EventDetailModal({
  event,
  onClose,
}: {
  event: CalendarEventItem
  onClose: () => void
}) {
  return (
    <Modal title={event.title} onClose={onClose}>
      <p className="text-sm font-semibold text-teal-700">{event.category || 'Event'}</p>
      <p className="mt-3 text-sm text-slate-600">{event.description || 'No additional details.'}</p>
      <button type="button" onClick={onClose} className="mt-5 rounded-lg bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
        Close
      </button>
    </Modal>
  )
}

export function CalendarPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const month = Number(searchParams.get('month')) || new Date().getMonth() + 1
  const year = Number(searchParams.get('year')) || new Date().getFullYear()

  const [data, setData] = useState<CalendarPageResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEventItem | null>(null)

  const [showAddEvent, setShowAddEvent] = useState(false)
  const [showBreaks, setShowBreaks] = useState(false)
  const [showWorkDays, setShowWorkDays] = useState(false)

  const [eventForm, setEventForm] = useState({
    event_title: '',
    event_date: '',
    event_category: 'other_event',
    event_description: '',
  })
  const [breakForm, setBreakForm] = useState({
    name: '',
    start_date: '',
    end_date: '',
    break_type: 'Vacation',
    description: '',
  })
  const [workDayForm, setWorkDayForm] = useState({
    dates: '',
    title: '',
    attendance_requirement: 'Mandatory',
    description: '',
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchCalendarPage(month, year))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load calendar')
    } finally {
      setLoading(false)
    }
  }, [month, year])

  useEffect(() => {
    void load()
  }, [load])

  const goMonth = (m: number, y: number) => {
    setSearchParams({ month: String(m), year: String(y) })
  }

  const showMessage = (msg: string) => {
    setToast(msg)
    window.setTimeout(() => setToast(null), 4000)
  }

  const handleAddEvent = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await addCalendarEvent(eventForm)
      showMessage(res.message)
      setShowAddEvent(false)
      setEventForm({ event_title: '', event_date: '', event_category: 'other_event', event_description: '' })
      void load()
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Could not add event')
    }
  }

  const handleAddBreak = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await addSchoolBreak(breakForm)
      showMessage(res.message)
      setBreakForm({ name: '', start_date: '', end_date: '', break_type: 'Vacation', description: '' })
      void load()
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Could not add break')
    }
  }

  const handleAddWorkDays = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await addTeacherWorkDays(workDayForm)
      showMessage(res.message)
      setWorkDayForm({ dates: '', title: '', attendance_requirement: 'Mandatory', description: '' })
      void load()
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Could not add work days')
    }
  }

  if (loading) {
    return <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">Loading calendar…</div>
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">{error || 'Could not load calendar'}</p>
      </div>
    )
  }

  const today = new Date()

  return (
    <div className="mx-auto max-w-[1400px] px-1 pb-10">
      {toast ? (
        <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-medium text-teal-900">
          {toast}
        </div>
      ) : null}

      <header className="mb-6 rounded-[20px] bg-gradient-to-br from-teal-600 to-emerald-700 px-6 py-5 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-white/80">School calendar</p>
            <h1 className="text-2xl font-bold">
              {data.month_name} {data.year}
            </h1>
            <p className="mt-1 text-sm text-white/90">
              <i className="bi bi-calendar-event me-1" aria-hidden />
              Manage and view school calendar events
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/management/school-year/closure/schedule"
              className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-700"
            >
              <i className="bi bi-flag-fill" aria-hidden />
              End-of-year closure
            </Link>
            <div className="flex rounded-lg bg-white/10 p-0.5">
              <button
                type="button"
                onClick={() => goMonth(data.prev_month.month, data.prev_month.year)}
                className="rounded-md px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/15"
              >
                <i className="bi bi-chevron-left" aria-hidden /> Prev
              </button>
              <button
                type="button"
                onClick={() => goMonth(today.getMonth() + 1, today.getFullYear())}
                className="rounded-md px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/15"
              >
                Today
              </button>
              <button
                type="button"
                onClick={() => goMonth(data.next_month.month, data.next_month.year)}
                className="rounded-md px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/15"
              >
                Next <i className="bi bi-chevron-right" aria-hidden />
              </button>
            </div>
            <button
              type="button"
              onClick={() => setShowAddEvent(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-teal-800 hover:bg-white/95"
            >
              <i className="bi bi-plus-circle" aria-hidden />
              Add event
            </button>
            <Link
              to="/management/school-years"
              className="inline-flex items-center gap-1.5 rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/25"
            >
              <i className="bi bi-mortarboard-fill" aria-hidden />
              School years
            </Link>
            <button
              type="button"
              onClick={() => setShowWorkDays(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/25"
            >
              <i className="bi bi-person-badge" aria-hidden />
              Work days
            </button>
            <button
              type="button"
              onClick={() => setShowBreaks(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/25"
            >
              <i className="bi bi-calendar-x" aria-hidden />
              Breaks
            </button>
          </div>
        </div>
      </header>

      {data.active_closures.length > 0 ? (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="font-semibold text-amber-900">
            <i className="bi bi-clock-history me-1" aria-hidden />
            Active school-year closure in progress
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.active_closures.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => navigate(`/management/school-year/closure/${c.id}`)}
                className="rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-amber-900 shadow-sm hover:bg-amber-100"
              >
                {c.school_year_name} · {c.phase_label} →
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <InsightCard icon="bi-calendar-event" value={data.events_this_month} label="Events this month" />
        <InsightCard icon="bi-person-badge" value={data.work_days.length} label="Work days" />
        <InsightCard icon="bi-calendar-x" value={data.breaks.length} label="School breaks" />
        <InsightCard
          icon="bi-mortarboard"
          value={data.active_school_year?.name || '—'}
          label="School year"
          small
        />
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="grid grid-cols-7 border-b border-slate-200 bg-slate-50">
          {data.weekdays.map((d) => (
            <div key={d} className="py-3 text-center text-xs font-bold uppercase tracking-wide text-slate-500">
              {d}
            </div>
          ))}
        </div>
        {data.weeks.map((week, wi) => (
          <div key={wi} className="grid grid-cols-7 border-b border-slate-100 last:border-b-0">
            {week.map((day, di) => (
              <div
                key={di}
                className={`min-h-[110px] border-r border-slate-100 p-1 last:border-r-0 ${
                  !day.is_current_month ? 'bg-slate-50/80' : ''
                } ${day.is_today ? 'bg-teal-50/60' : ''}`}
              >
                {day.is_current_month && day.day_num ? (
                  <>
                    <div
                      className={`mb-1 px-1 text-sm font-bold ${
                        day.is_today
                          ? 'inline-flex h-7 w-7 items-center justify-center rounded-full bg-teal-600 text-white'
                          : 'text-slate-800'
                      }`}
                    >
                      {day.day_num}
                    </div>
                    <div className="space-y-0.5">
                      {day.events.map((ev, ei) => (
                        <button
                          key={ei}
                          type="button"
                          onClick={() => setSelectedEvent(ev)}
                          className={`block w-full truncate rounded px-1.5 py-0.5 text-left text-[0.65rem] font-medium text-white ${calendarEventClass(ev.type)}`}
                          title={ev.title}
                        >
                          {ev.title}
                        </button>
                      ))}
                    </div>
                  </>
                ) : null}
              </div>
            ))}
          </div>
        ))}
      </div>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-bold text-slate-700">
          <i className="bi bi-info-circle me-1 text-teal-600" aria-hidden />
          Legend
        </h2>
        <div className="flex flex-wrap gap-2 text-xs">
          {[
            ['Quarter start/end', 'bg-emerald-600'],
            ['Teacher work day', 'bg-amber-600'],
            ['School break', 'bg-sky-600'],
            ['Holiday', 'bg-rose-600'],
            ['Professional development', 'bg-orange-600'],
            ['Other', 'bg-slate-600'],
          ].map(([label, cls]) => (
            <span key={label} className={`rounded px-2 py-1 font-semibold text-white ${cls}`}>
              {label}
            </span>
          ))}
        </div>
      </section>

      {selectedEvent ? (
        <EventDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
      ) : null}

      {showAddEvent ? (
        <Modal title="Add calendar event" onClose={() => setShowAddEvent(false)}>
          <form onSubmit={handleAddEvent} className="space-y-4">
            <Field label="Title" required>
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={eventForm.event_title}
                onChange={(e) => setEventForm({ ...eventForm, event_title: e.target.value })}
                required
              />
            </Field>
            <Field label="Date" required>
              <input
                type="date"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={eventForm.event_date}
                onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
                required
              />
            </Field>
            <Field label="Category">
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={eventForm.event_category}
                onChange={(e) => setEventForm({ ...eventForm, event_category: e.target.value })}
              >
                {data.event_categories.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Description">
              <textarea
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                rows={3}
                value={eventForm.event_description}
                onChange={(e) => setEventForm({ ...eventForm, event_description: e.target.value })}
              />
            </Field>
            <button type="submit" className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700">
              Add event
            </button>
          </form>
        </Modal>
      ) : null}

      {showBreaks ? (
        <Modal title="School breaks" onClose={() => setShowBreaks(false)}>
          <form onSubmit={handleAddBreak} className="mb-6 space-y-3 border-b border-slate-200 pb-6">
            <Field label="Name" required>
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={breakForm.name}
                onChange={(e) => setBreakForm({ ...breakForm, name: e.target.value })}
                required
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start" required>
                <input
                  type="date"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  value={breakForm.start_date}
                  onChange={(e) => setBreakForm({ ...breakForm, start_date: e.target.value })}
                  required
                />
              </Field>
              <Field label="End" required>
                <input
                  type="date"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  value={breakForm.end_date}
                  onChange={(e) => setBreakForm({ ...breakForm, end_date: e.target.value })}
                  required
                />
              </Field>
            </div>
            <Field label="Type">
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={breakForm.break_type}
                onChange={(e) => setBreakForm({ ...breakForm, break_type: e.target.value })}
              >
                {data.break_types.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </Field>
            <button type="submit" className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-bold text-white">
              Add break
            </button>
          </form>
          <ul className="space-y-2">
            {data.breaks.map((b) => (
              <li key={b.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <span>
                  <strong>{b.name}</strong> · {b.start_date} → {b.end_date}
                </span>
                <button
                  type="button"
                  className="text-red-600 hover:underline"
                  onClick={async () => {
                    if (!window.confirm('Delete this break?')) return
                    try {
                      const res = await deleteSchoolBreak(b.id)
                      showMessage(res.message)
                      void load()
                    } catch (err) {
                      showMessage(err instanceof Error ? err.message : 'Delete failed')
                    }
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </Modal>
      ) : null}

      {showWorkDays ? (
        <Modal title="Teacher work days" onClose={() => setShowWorkDays(false)}>
          <form onSubmit={handleAddWorkDays} className="mb-6 space-y-3 border-b border-slate-200 pb-6">
            <Field label="Dates (comma-separated YYYY-MM-DD)" required>
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="2026-08-15, 2026-08-16"
                value={workDayForm.dates}
                onChange={(e) => setWorkDayForm({ ...workDayForm, dates: e.target.value })}
                required
              />
            </Field>
            <Field label="Title" required>
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={workDayForm.title}
                onChange={(e) => setWorkDayForm({ ...workDayForm, title: e.target.value })}
                required
              />
            </Field>
            <button type="submit" className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-bold text-white">
              Add work days
            </button>
          </form>
          <ul className="space-y-2">
            {data.work_days.map((w) => (
              <li key={w.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <span>
                  <strong>{w.title}</strong> · {w.date}
                </span>
                <button
                  type="button"
                  className="text-red-600 hover:underline"
                  onClick={async () => {
                    if (!window.confirm('Delete this work day?')) return
                    try {
                      const res = await deleteTeacherWorkDay(w.id)
                      showMessage(res.message)
                      void load()
                    } catch (err) {
                      showMessage(err instanceof Error ? err.message : 'Delete failed')
                    }
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </Modal>
      ) : null}
    </div>
  )
}

function InsightCard({
  icon,
  value,
  label,
  small,
}: {
  icon: string
  value: string | number
  label: string
  small?: boolean
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className={`font-bold text-slate-800 ${small ? 'text-sm' : 'text-xl'}`}>{value}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  )
}

function Field({
  label,
  children,
  required,
}: {
  label: string
  children: React.ReactNode
  required?: boolean
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-semibold text-slate-700">
        {label}
        {required ? ' *' : ''}
      </span>
      {children}
    </label>
  )
}
