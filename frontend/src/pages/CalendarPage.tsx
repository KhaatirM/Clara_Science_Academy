import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useOutletContext, useSearchParams } from 'react-router-dom'
import {
  addCalendarEvent,
  addSchoolBreak,
  addTeacherWorkDays,
  deleteCalendarEvent,
  deleteSchoolBreak,
  deleteTeacherWorkDay,
  fetchCalendarPage,
} from '../api/calendar'
import { LegacyBootstrapModal } from '../components/legacy/LegacyBootstrapModal'
import { LegacyMgmtScope } from '../components/legacy/LegacyMgmtScope'
import type { CalendarEventItem, CalendarPageResponse } from '../types/calendar'
import type { ManagementOutletContext } from '../types/layout'
import { calendarEventClass } from '../utils/calendarEventColors'
import {
  getCalendarPageCache,
  setCalendarPageCache,
} from '../utils/calendarPageCache'
import { formatDateLong, formatDateShort } from '../utils/formatDate'

const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

const LEGEND_ITEMS: { type: string; label: string }[] = [
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
]

export function CalendarPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const isDirector = user.role_canonical === 'Director'

  const [searchParams, setSearchParams] = useSearchParams()
  const month = Number(searchParams.get('month')) || new Date().getMonth() + 1
  const year = Number(searchParams.get('year')) || new Date().getFullYear()

  const initialCache = getCalendarPageCache(month, year)

  const [data, setData] = useState<CalendarPageResponse | null>(() => initialCache ?? null)
  const [booting, setBooting] = useState(() => !initialCache)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const hasLoadedOnce = useRef(!!initialCache)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEventItem | null>(null)

  const [showAddEvent, setShowAddEvent] = useState(false)
  const [showBreaks, setShowBreaks] = useState(false)
  const [showWorkDays, setShowWorkDays] = useState(false)

  const [eventForm, setEventForm] = useState({
    event_title: '',
    event_date: '',
    event_category: 'quarter_start',
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
    const cached = getCalendarPageCache(month, year)
    const silent = hasLoadedOnce.current || !!cached
    if (silent) setRefreshing(true)
    else setBooting(true)
    setError(null)
    if (cached && !hasLoadedOnce.current) {
      setData(cached)
      hasLoadedOnce.current = true
      setBooting(false)
    }
    try {
      const next = await fetchCalendarPage(month, year)
      setData(next)
      setCalendarPageCache(month, year, next)
      hasLoadedOnce.current = true
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load calendar')
      if (!hasLoadedOnce.current) setData(null)
    } finally {
      setBooting(false)
      setRefreshing(false)
    }
  }, [month, year])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const open = searchParams.get('open')
    if (open === 'teacher-work-days') setShowWorkDays(true)
    else if (open === 'school-breaks') setShowBreaks(true)
  }, [searchParams])

  const goMonth = (m: number, y: number) => {
    const next = new URLSearchParams(searchParams)
    next.set('month', String(m))
    next.set('year', String(y))
    setSearchParams(next, { replace: true })
  }

  const goToday = () => {
    const today = new Date()
    const next = new URLSearchParams(searchParams)
    next.set('month', String(today.getMonth() + 1))
    next.set('year', String(today.getFullYear()))
    next.delete('open')
    setSearchParams(next, { replace: true })
  }

  const showMessage = (msg: string) => {
    setFlash(msg)
    window.setTimeout(() => setFlash(null), 5000)
  }

  const handleAddEvent = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      const res = await addCalendarEvent(eventForm)
      showMessage(res.message)
      setShowAddEvent(false)
      setEventForm({
        event_title: '',
        event_date: '',
        event_category: 'quarter_start',
        event_description: '',
      })
      void load()
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Could not add event')
    } finally {
      setBusy(false)
    }
  }

  const handleAddBreak = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      const res = await addSchoolBreak(breakForm)
      showMessage(res.message)
      setBreakForm({ name: '', start_date: '', end_date: '', break_type: 'Vacation', description: '' })
      void load()
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Could not add break')
    } finally {
      setBusy(false)
    }
  }

  const handleAddWorkDays = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      const res = await addTeacherWorkDays(workDayForm)
      showMessage(res.message)
      setWorkDayForm({ dates: '', title: '', attendance_requirement: 'Mandatory', description: '' })
      void load()
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Could not add work days')
    } finally {
      setBusy(false)
    }
  }

  const handleDeleteSelectedEvent = async () => {
    if (!selectedEvent?.deletable || selectedEvent.entity_id == null) return
    const { source, entity_id, title } = selectedEvent
    if (!window.confirm(`Delete "${title}"?`)) return
    setBusy(true)
    try {
      let res: { message: string }
      if (source === 'calendar_event') {
        res = await deleteCalendarEvent(entity_id)
      } else if (source === 'teacher_work_day') {
        res = await deleteTeacherWorkDay(entity_id)
      } else if (source === 'school_break') {
        res = await deleteSchoolBreak(entity_id)
      } else {
        return
      }
      showMessage(res.message)
      setSelectedEvent(null)
      void load()
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setBusy(false)
    }
  }

  if (booting && !data) {
    return (
      <LegacyMgmtScope>
        <div className="mgmt-cal mgmt-cal-page container-fluid px-0 px-md-1">
          <div className="mgmt-cal-shell p-5 text-center">Loading calendar…</div>
        </div>
      </LegacyMgmtScope>
    )
  }

  if ((error && !data) || !data) {
    return (
      <LegacyMgmtScope>
        <div className="mgmt-cal mgmt-cal-page container-fluid px-0 px-md-1">
          <div className="mgmt-cal-shell p-5">
            <p>{error || 'Could not load calendar'}</p>
          </div>
        </div>
      </LegacyMgmtScope>
    )
  }

  return (
    <LegacyMgmtScope>
      <>
      <div className="mgmt-cal mgmt-cal-page mgmt-cal-page--compact container-fluid px-0 px-md-1">
        <div className={`mgmt-cal-shell mgmt-cal-shell--compact${isDirector ? ' mgmt-cal-shell--director' : ''}`}>
          {flash ? (
            <div className="alert alert-success mgmt-cal-flash" role="status">
              {flash}
            </div>
          ) : null}

          <header className="mgmt-cal-hero mgmt-cal-hero--compact">
            <div className="mgmt-cal-hero-main">
              <p className="mgmt-cal-eyebrow">School calendar</p>
              <h1 className="mgmt-cal-title">
                {data.month_name} {data.year}
                {refreshing ? (
                  <span className="mgmt-cal-refresh-indicator" aria-live="polite">
                    <i className="bi bi-arrow-repeat" aria-hidden="true" /> Updating…
                  </span>
                ) : null}
              </h1>
            </div>
            <div className="mgmt-cal-hero-toolbar">
              {isDirector ? (
                <span className="mgmt-cal-role-badge mgmt-cal-role-badge--director">
                  <i className="bi bi-award-fill" aria-hidden="true" /> Director
                </span>
              ) : (
                <span className="mgmt-cal-role-badge mgmt-cal-role-badge--admin">
                  <i className="bi bi-shield-fill" aria-hidden="true" /> Administrator
                </span>
              )}
              <div className="mgmt-cal-nav-group" role="group" aria-label="Month navigation">
                <button
                  type="button"
                  className="mgmt-cal-btn mgmt-cal-btn--ghost mgmt-cal-btn--sm"
                  disabled={refreshing}
                  onClick={() => goMonth(data.prev_month.month, data.prev_month.year)}
                >
                  <i className="bi bi-chevron-left" aria-hidden="true" /> Prev
                </button>
                <button
                  type="button"
                  className="mgmt-cal-btn mgmt-cal-btn--ghost mgmt-cal-btn--sm"
                  disabled={refreshing}
                  onClick={goToday}
                >
                  Today
                </button>
                <button
                  type="button"
                  className="mgmt-cal-btn mgmt-cal-btn--ghost mgmt-cal-btn--sm"
                  disabled={refreshing}
                  onClick={() => goMonth(data.next_month.month, data.next_month.year)}
                >
                  Next <i className="bi bi-chevron-right" aria-hidden="true" />
                </button>
              </div>
              <button
                type="button"
                className="mgmt-cal-btn mgmt-cal-btn--primary mgmt-cal-btn--sm"
                onClick={() => setShowAddEvent(true)}
              >
                <i className="bi bi-plus-circle" aria-hidden="true" /> Add event
              </button>
              <div className="mgmt-cal-toolbar-divider" aria-hidden="true" />
              <Link
                to="/management/school-years"
                className="mgmt-cal-btn mgmt-cal-btn--ghost mgmt-cal-btn--sm"
                title="School Years workspace"
              >
                <i className="bi bi-mortarboard-fill" aria-hidden="true" /> School years
              </Link>
              <button
                type="button"
                className="mgmt-cal-btn mgmt-cal-btn--ghost mgmt-cal-btn--sm"
                onClick={() => setShowWorkDays(true)}
              >
                <i className="bi bi-person-badge" aria-hidden="true" /> Teacher Workdays
              </button>
              <button
                type="button"
                className="mgmt-cal-btn mgmt-cal-btn--ghost mgmt-cal-btn--sm"
                onClick={() => setShowBreaks(true)}
              >
                <i className="bi bi-calendar-x" aria-hidden="true" /> School Breaks
              </button>
              <Link
                to="/management/school-year/closure/schedule"
                className="mgmt-cal-btn mgmt-cal-btn--danger-outline mgmt-cal-btn--sm"
                title="End of year closure"
              >
                <i className="bi bi-flag-fill" aria-hidden="true" /> End of year closure
              </Link>
            </div>
          </header>

          <div className="mgmt-cal-insights mgmt-cal-insights--strip" role="list">
            <div className="mgmt-cal-insight" role="listitem">
              <span className="mgmt-cal-insight-icon">
                <i className="bi bi-calendar-event" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-cal-insight-value">{data.events_this_month}</div>
                <div className="mgmt-cal-insight-label">Events this month</div>
              </div>
            </div>
            <div className="mgmt-cal-insight" role="listitem">
              <span className="mgmt-cal-insight-icon">
                <i className="bi bi-person-badge" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-cal-insight-value">{data.work_days.length}</div>
                <div className="mgmt-cal-insight-label">Teacher workdays</div>
              </div>
            </div>
            <div className="mgmt-cal-insight" role="listitem">
              <span className="mgmt-cal-insight-icon">
                <i className="bi bi-calendar-x" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-cal-insight-value">{data.breaks.length}</div>
                <div className="mgmt-cal-insight-label">School breaks</div>
              </div>
            </div>
            <div className="mgmt-cal-insight" role="listitem">
              <span className="mgmt-cal-insight-icon">
                <i className="bi bi-mortarboard" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-cal-insight-value" style={{ fontSize: '0.85rem' }}>
                  {data.active_school_year?.name || '—'}
                </div>
                <div className="mgmt-cal-insight-label">School year</div>
              </div>
            </div>
          </div>

          <div className={`mgmt-cal-content${refreshing ? ' mgmt-cal-content--refreshing' : ''}`}>
            <div className="row">
              <div className="col-12">
                <div className="card border-0 shadow-lg" style={{ borderRadius: '1rem', overflow: 'hidden' }}>
                  <div className="card-body p-0">
                    <div className="calendar-container">
                      <div
                        className="calendar-header"
                        style={{
                          background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                          borderBottomWidth: '3px',
                          borderBottomStyle: 'solid',
                        }}
                      >
                        <div className="row text-center fw-bold g-0 calendar-week">
                          {WEEKDAY_LABELS.map((label, i) => (
                            <div
                              key={label}
                              className={`col calendar-day-header py-3${
                                i >= 5 ? ' weekend-header' : ''
                              }`}
                              style={{
                                fontSize: '1rem',
                                color: '#495057',
                                textTransform: 'uppercase',
                                letterSpacing: '1px',
                              }}
                            >
                              <i className="bi bi-calendar-week me-1" aria-hidden="true" />
                              {label}
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="calendar-body">
                        {data.weeks.length > 0 ? (
                          data.weeks.map((week, wi) => (
                            <div key={wi} className="row calendar-week g-0 border-bottom">
                              {week.map((day, di) => (
                                <div
                                  key={di}
                                  className={`col calendar-day${
                                    !day.is_current_month ? ' calendar-day-other-month' : ''
                                  }${day.is_today ? ' calendar-day-today' : ''}`}
                                  style={{ position: 'relative' }}
                                >
                                  {day.is_current_month ? (
                                    <>
                                      <div
                                        className="day-number fw-bold p-2"
                                        style={{
                                          fontSize: '1.2rem',
                                          flexShrink: 0,
                                          ...(day.is_today ? {} : { color: '#212529' }),
                                        }}
                                      >
                                        {day.is_today ? (
                                          <span
                                            className="cal-day-today-pill"
                                            style={{
                                              color: 'white',
                                              padding: '0.25rem 0.5rem',
                                              borderRadius: '50%',
                                              display: 'inline-block',
                                              minWidth: '2rem',
                                              textAlign: 'center',
                                            }}
                                          >
                                            {day.day_num}
                                          </span>
                                        ) : (
                                          day.day_num
                                        )}
                                      </div>
                                      <div
                                        className="day-events px-2 pb-2"
                                        style={{
                                          flex: 1,
                                          overflow: 'hidden',
                                          display: 'flex',
                                          flexDirection: 'column',
                                          gap: '0.25rem',
                                        }}
                                      >
                                        {day.events.map((ev, ei) => (
                                          <div
                                            key={ei}
                                            role="button"
                                            tabIndex={0}
                                            className={`calendar-event ${calendarEventClass(ev.type)} mb-0`}
                                            onClick={() => setSelectedEvent(ev)}
                                            onKeyDown={(e) => {
                                              if (e.key === 'Enter' || e.key === ' ') setSelectedEvent(ev)
                                            }}
                                            style={{
                                              cursor: 'pointer',
                                              borderRadius: '0.375rem',
                                              padding: '0.375rem 0.5rem',
                                              fontSize: '0.75rem',
                                              fontWeight: 500,
                                              transition: 'all 0.2s ease',
                                              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                                              flexShrink: 0,
                                              whiteSpace: 'nowrap',
                                              overflow: 'hidden',
                                              textOverflow: 'ellipsis',
                                              display: 'flex',
                                              alignItems: 'center',
                                              minHeight: '24px',
                                              maxHeight: '24px',
                                            }}
                                          >
                                            <i
                                              className="bi bi-circle-fill me-1"
                                              style={{ fontSize: '0.5rem', flexShrink: 0 }}
                                              aria-hidden="true"
                                            />
                                            <span
                                              className="event-title text-white"
                                              style={{
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap',
                                              }}
                                            >
                                              {ev.title}
                                            </span>
                                          </div>
                                        ))}
                                      </div>
                                    </>
                                  ) : (
                                    <div
                                      className="day-number text-muted p-2"
                                      style={{ fontSize: '1rem', opacity: 0.4, flexShrink: 0 }}
                                    >
                                      {day.day_num}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          ))
                        ) : (
                          <div className="text-center py-5">
                            <i className="bi bi-calendar-x" style={{ fontSize: '4rem', color: '#dee2e6' }} />
                            <h5 className="text-muted mt-3">No calendar data available</h5>
                            <p className="text-muted">Calendar data is not available for this month.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="row mt-3">
              <div className="col-12">
                <div className="mgmt-cal-legend" aria-label="Calendar legend">
                  <div className="mgmt-cal-legend-head">
                    <span className="mgmt-cal-legend-title">
                      <i className="bi bi-palette-fill" aria-hidden="true" /> Calendar legend
                    </span>
                  </div>
                  <ul className="mgmt-cal-legend-list">
                    {LEGEND_ITEMS.map((item) => (
                      <li key={item.type} className="mgmt-cal-legend-item">
                        <span className={`calendar-legend-item event-${item.type}`} aria-hidden="true" />
                        <span>{item.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {selectedEvent ? (
        <LegacyBootstrapModal
          id="eventDetailsModal"
          show
          hideHeaderClose
          onClose={() => setSelectedEvent(null)}
          rootClassName="mgmt-cal-modal mgmt-cal-modal--accent"
          headerClassName="text-white cal-modal-header-themed"
          closeWhite
          title={
            <>
              <i className="bi bi-calendar-event me-2" aria-hidden="true" />
              Event Details
            </>
          }
        >
          <div className="modal-body mgmt-cal-modal-body">
            <div className="mgmt-cal-modal-field">
              <h6 className="mgmt-cal-modal-label">
                <i className="bi bi-tag me-2" aria-hidden="true" />
                Event Title
              </h6>
              <p className="mgmt-cal-modal-value">{selectedEvent.title}</p>
            </div>
            <div className="mgmt-cal-modal-field">
              <h6 className="mgmt-cal-modal-label">
                <i className="bi bi-folder me-2" aria-hidden="true" />
                Category
              </h6>
              <span className="badge cal-modal-badge-themed mgmt-cal-modal-badge">{selectedEvent.category || 'Event'}</span>
            </div>
            <div className="mgmt-cal-modal-field mb-0">
              <h6 className="mgmt-cal-modal-label">
                <i className="bi bi-text-paragraph me-2" aria-hidden="true" />
                Description
              </h6>
              <p className="mgmt-cal-modal-muted mb-0">
                {selectedEvent.description || 'No additional details available for this event.'}
              </p>
            </div>
          </div>
          <div
            className={`modal-footer mgmt-cal-modal-footer mgmt-cal-modal-footer--event-details${
              selectedEvent.deletable && selectedEvent.entity_id != null ? ' has-delete' : ''
            }`}
          >
            {selectedEvent.deletable && selectedEvent.entity_id != null ? (
              <button
                type="button"
                className="mgmt-cal-btn mgmt-cal-btn--footer-delete"
                disabled={busy}
                onClick={() => void handleDeleteSelectedEvent()}
              >
                <i className="bi bi-trash3" aria-hidden="true" />
                Delete event
              </button>
            ) : null}
            <button
              type="button"
              className="mgmt-cal-btn mgmt-cal-btn--footer-close"
              onClick={() => setSelectedEvent(null)}
            >
              Close
            </button>
          </div>
        </LegacyBootstrapModal>
      ) : null}

      <LegacyBootstrapModal
        id="addEventModal"
        show={showAddEvent}
        onClose={() => setShowAddEvent(false)}
        rootClassName="mgmt-cal-modal mgmt-cal-modal--warm"
        headerClassName="text-white"
        closeWhite
        title={
          <>
            <i className="bi bi-plus-circle me-2" aria-hidden="true" />
            Add calendar event
          </>
        }
      >
        <form onSubmit={handleAddEvent}>
          <div className="modal-body mgmt-cal-modal-body">
            <p className="mgmt-cal-modal-intro">
              Add a one-day milestone to the active school year — quarters, holidays, PD, and more.
            </p>
            <div className="mgmt-cal-modal-form-card">
              <div className="row g-3">
                <div className="col-md-7">
                  <label htmlFor="event_title" className="mgmt-cal-form-label">
                    <i className="bi bi-type" aria-hidden="true" /> Event title <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control mgmt-cal-form-control"
                    id="event_title"
                    placeholder="e.g., Q1 ends"
                    value={eventForm.event_title}
                    onChange={(e) => setEventForm({ ...eventForm, event_title: e.target.value })}
                    required
                  />
                </div>
                <div className="col-md-5">
                  <label htmlFor="event_date" className="mgmt-cal-form-label">
                    <i className="bi bi-calendar3" aria-hidden="true" /> Date <span className="text-danger">*</span>
                  </label>
                  <input
                    type="date"
                    className="form-control mgmt-cal-form-control"
                    id="event_date"
                    value={eventForm.event_date}
                    onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
                    required
                  />
                </div>
                <div className="col-12">
                  <label htmlFor="event_category" className="mgmt-cal-form-label">
                    <i className="bi bi-bookmark" aria-hidden="true" /> Category
                  </label>
                  <select
                    className="form-select mgmt-cal-form-control"
                    id="event_category"
                    value={eventForm.event_category}
                    onChange={(e) => setEventForm({ ...eventForm, event_category: e.target.value })}
                  >
                    {data.event_categories.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-12 mb-0">
                  <label htmlFor="event_description" className="mgmt-cal-form-label">
                    <i className="bi bi-card-text" aria-hidden="true" /> Description
                  </label>
                  <textarea
                    className="form-control mgmt-cal-form-control"
                    id="event_description"
                    rows={3}
                    placeholder="Optional notes for staff viewing the calendar"
                    value={eventForm.event_description}
                    onChange={(e) => setEventForm({ ...eventForm, event_description: e.target.value })}
                  />
                </div>
              </div>
            </div>
          </div>
          <div className="modal-footer mgmt-cal-modal-footer">
            <button type="button" className="mgmt-cal-btn mgmt-cal-btn--ghost" onClick={() => setShowAddEvent(false)} disabled={busy}>
              Cancel
            </button>
            <button type="submit" className="mgmt-cal-btn mgmt-cal-btn--warm" disabled={busy}>
              <i className="bi bi-plus-circle me-2" aria-hidden="true" />
              {busy ? 'Adding…' : 'Add event'}
            </button>
          </div>
        </form>
      </LegacyBootstrapModal>

      <LegacyBootstrapModal
        id="teacherWorkDaysModal"
        show={showWorkDays}
        onClose={() => setShowWorkDays(false)}
        rootClassName="mgmt-cal-modal mgmt-cal-modal--teacher"
        headerClassName="text-white"
        closeWhite
        size="lg"
        scrollable
        title={
          <>
            <i className="bi bi-person-badge me-2" aria-hidden="true" />
            Teacher Workdays
          </>
        }
      >
        <div className="modal-body mgmt-cal-modal-body">
          <p className="mgmt-cal-modal-intro">
            Schedule professional development and other staff-only days. You can add multiple dates at once.
          </p>
          <section className="mgmt-cal-modal-form-card">
            <h6 className="mgmt-cal-modal-section-title">
              <i className="bi bi-plus-square" aria-hidden="true" /> Add teacher workday
            </h6>
            <form id="work-days-form" onSubmit={handleAddWorkDays} className="mgmt-cal-modal-form-block">
              <div className="row g-3">
                <div className="col-md-6">
                  <label htmlFor="twd_title" className="mgmt-cal-form-label">
                    Title <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control mgmt-cal-form-control"
                    id="twd_title"
                    value={workDayForm.title}
                    onChange={(e) => setWorkDayForm({ ...workDayForm, title: e.target.value })}
                    placeholder="e.g., PD Day"
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label htmlFor="twd_attendance" className="mgmt-cal-form-label">
                    Attendance
                  </label>
                  <select
                    className="form-select mgmt-cal-form-control"
                    id="twd_attendance"
                    value={workDayForm.attendance_requirement}
                    onChange={(e) =>
                      setWorkDayForm({ ...workDayForm, attendance_requirement: e.target.value })
                    }
                  >
                    <option value="Mandatory">Mandatory</option>
                    <option value="Optional">Optional</option>
                  </select>
                </div>
                <div className="col-12">
                  <label htmlFor="twd_dates" className="mgmt-cal-form-label">
                    Dates <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control mgmt-cal-form-control"
                    id="twd_dates"
                    value={workDayForm.dates}
                    onChange={(e) => setWorkDayForm({ ...workDayForm, dates: e.target.value })}
                    placeholder="01/15/2026, 02/20/2026"
                    required
                  />
                  <p className="mgmt-cal-form-hint">Comma-separated — MM/DD/YYYY or YYYY-MM-DD</p>
                </div>
                <div className="col-12 mb-0">
                  <label htmlFor="twd_description" className="mgmt-cal-form-label">
                    Description
                  </label>
                  <textarea
                    className="form-control mgmt-cal-form-control"
                    id="twd_description"
                    rows={2}
                    placeholder="Optional details for staff"
                    value={workDayForm.description}
                    onChange={(e) => setWorkDayForm({ ...workDayForm, description: e.target.value })}
                  />
                </div>
              </div>
            </form>
          </section>

          <section className="mgmt-cal-modal-list-section">
            <h6 className="mgmt-cal-modal-section-title">
              <i className="bi bi-list-ul" aria-hidden="true" /> Current teacher workdays{' '}
              <span className="mgmt-cal-modal-count">{data.work_days.length}</span>
            </h6>
            {data.work_days.length > 0 ? (
              <ul className="mgmt-cal-modal-list">
                {data.work_days.map((wd) => (
                  <li key={wd.id} className="mgmt-cal-modal-list-item">
                    <div className="mgmt-cal-modal-list-main">
                      <span className="mgmt-cal-modal-list-date">{formatDateLong(wd.date)}</span>
                      <strong>{wd.title}</strong>
                      <span
                        className={`mgmt-cal-modal-pill mgmt-cal-modal-pill--${
                          wd.attendance_requirement === 'Mandatory' ? 'danger' : 'warn'
                        }`}
                      >
                        {wd.attendance_requirement || 'Mandatory'}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="mgmt-cal-btn mgmt-cal-btn--icon-danger"
                      aria-label={`Delete ${wd.title}`}
                      onClick={async () => {
                        if (!window.confirm('Delete this teacher workday?')) return
                        try {
                          const res = await deleteTeacherWorkDay(wd.id)
                          showMessage(res.message)
                          void load()
                        } catch (err) {
                          showMessage(err instanceof Error ? err.message : 'Delete failed')
                        }
                      }}
                    >
                      <i className="bi bi-trash" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mgmt-cal-modal-empty">
                <i className="bi bi-inbox" aria-hidden="true" /> No teacher workdays yet.
              </p>
            )}
          </section>
        </div>
        <div className="modal-footer mgmt-cal-modal-footer">
          <button type="button" className="mgmt-cal-btn mgmt-cal-btn--ghost" onClick={() => setShowWorkDays(false)} disabled={busy}>
            Close
          </button>
          <button type="submit" form="work-days-form" className="mgmt-cal-btn mgmt-cal-btn--teacher" disabled={busy}>
            <i className="bi bi-plus-circle me-1" aria-hidden="true" />
            {busy ? 'Saving…' : 'Add workday'}
          </button>
        </div>
      </LegacyBootstrapModal>

      <LegacyBootstrapModal
        id="schoolBreaksModal"
        show={showBreaks}
        onClose={() => setShowBreaks(false)}
        rootClassName="mgmt-cal-modal mgmt-cal-modal--breaks"
        headerClassName="text-white"
        closeWhite
        size="lg"
        scrollable
        title={
          <>
            <i className="bi bi-calendar-x me-2" aria-hidden="true" />
            School Breaks
          </>
        }
      >
        <div className="modal-body mgmt-cal-modal-body">
          <p className="mgmt-cal-modal-intro">
            Block out vacation and holiday ranges. Each break appears on the calendar for the active school year.
          </p>
          <section className="mgmt-cal-modal-form-card">
            <h6 className="mgmt-cal-modal-section-title">
              <i className="bi bi-plus-square" aria-hidden="true" /> Add school break
            </h6>
            <form id="breaks-form" onSubmit={handleAddBreak} className="mgmt-cal-modal-form-block">
              <div className="row g-3">
                <div className="col-md-6">
                  <label htmlFor="sb_name" className="mgmt-cal-form-label">
                    Break name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control mgmt-cal-form-control"
                    id="sb_name"
                    value={breakForm.name}
                    onChange={(e) => setBreakForm({ ...breakForm, name: e.target.value })}
                    placeholder="e.g., Winter Break"
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label htmlFor="sb_type" className="mgmt-cal-form-label">
                    Type
                  </label>
                  <select
                    className="form-select mgmt-cal-form-control"
                    id="sb_type"
                    value={breakForm.break_type}
                    onChange={(e) => setBreakForm({ ...breakForm, break_type: e.target.value })}
                  >
                    {data.break_types.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label htmlFor="sb_start" className="mgmt-cal-form-label">
                    Start date <span className="text-danger">*</span>
                  </label>
                  <input
                    type="date"
                    className="form-control mgmt-cal-form-control"
                    id="sb_start"
                    value={breakForm.start_date}
                    onChange={(e) => setBreakForm({ ...breakForm, start_date: e.target.value })}
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label htmlFor="sb_end" className="mgmt-cal-form-label">
                    End date <span className="text-danger">*</span>
                  </label>
                  <input
                    type="date"
                    className="form-control mgmt-cal-form-control"
                    id="sb_end"
                    value={breakForm.end_date}
                    onChange={(e) => setBreakForm({ ...breakForm, end_date: e.target.value })}
                    required
                  />
                </div>
                <div className="col-12 mb-0">
                  <label htmlFor="sb_description" className="mgmt-cal-form-label">
                    Description
                  </label>
                  <textarea
                    className="form-control mgmt-cal-form-control"
                    id="sb_description"
                    rows={2}
                    placeholder="Optional details for staff"
                    value={breakForm.description}
                    onChange={(e) => setBreakForm({ ...breakForm, description: e.target.value })}
                  />
                </div>
              </div>
            </form>
          </section>

          <section className="mgmt-cal-modal-list-section">
            <h6 className="mgmt-cal-modal-section-title">
              <i className="bi bi-list-ul" aria-hidden="true" /> Current school breaks{' '}
              <span className="mgmt-cal-modal-count">{data.breaks.length}</span>
            </h6>
            {data.breaks.length > 0 ? (
              <ul className="mgmt-cal-modal-list">
                {data.breaks.map((b) => (
                  <li key={b.id} className="mgmt-cal-modal-list-item">
                    <div className="mgmt-cal-modal-list-main">
                      <strong>{b.name}</strong>
                      <span className="mgmt-cal-modal-pill mgmt-cal-modal-pill--muted">{b.break_type}</span>
                      <span className="mgmt-cal-modal-list-dates">
                        {formatDateShort(b.start_date)} – {formatDateLong(b.end_date)}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="mgmt-cal-btn mgmt-cal-btn--icon-danger"
                      aria-label={`Delete ${b.name}`}
                      onClick={async () => {
                        if (!window.confirm('Delete this school break?')) return
                        try {
                          const res = await deleteSchoolBreak(b.id)
                          showMessage(res.message)
                          void load()
                        } catch (err) {
                          showMessage(err instanceof Error ? err.message : 'Delete failed')
                        }
                      }}
                    >
                      <i className="bi bi-trash" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mgmt-cal-modal-empty">
                <i className="bi bi-inbox" aria-hidden="true" /> No school breaks yet.
              </p>
            )}
          </section>
        </div>
        <div className="modal-footer mgmt-cal-modal-footer">
          <button type="button" className="mgmt-cal-btn mgmt-cal-btn--ghost" onClick={() => setShowBreaks(false)} disabled={busy}>
            Close
          </button>
          <button type="submit" form="breaks-form" className="mgmt-cal-btn mgmt-cal-btn--breaks" disabled={busy}>
            <i className="bi bi-plus-circle me-1" aria-hidden="true" />
            {busy ? 'Saving…' : 'Add break'}
          </button>
        </div>
      </LegacyBootstrapModal>
    </>
    </LegacyMgmtScope>
  )
}
