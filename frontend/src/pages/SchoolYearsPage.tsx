import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import {
  addSchoolYearPeriod,
  createSchoolYear,
  editActiveSchoolYear,
  editSchoolYear,
  editSchoolYearPeriod,
  fetchSchoolYearsPage,
  generateSchoolYearPeriods,
  setActiveSchoolYear,
} from '../api/schoolYears'
import { LegacyBootstrapModal } from '../components/legacy/LegacyBootstrapModal'
import { SCHOOL_YEARS_LEGACY_CSS } from '../config/legacyPages'
import { useLegacyStyles } from '../hooks/useLegacyStyles'
import type { ManagementOutletContext } from '../types/layout'
import type { AcademicPeriod, CalendarEventRow, SchoolYearRow, SchoolYearsPageResponse } from '../types/schoolYears'
import { formatDateLong, formatDateShort } from '../utils/formatDate'

type ModalKey =
  | 'add'
  | 'upload'
  | 'editActive'
  | { editYear: number }
  | { viewYear: number }
  | { managePeriods: number }
  | { editPeriod: number }
  | null

export function SchoolYearsPage() {
  useLegacyStyles([SCHOOL_YEARS_LEGACY_CSS])
  const { user } = useOutletContext<ManagementOutletContext>()

  const [data, setData] = useState<SchoolYearsPageResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)
  const [modal, setModal] = useState<ModalKey>(null)
  const [busy, setBusy] = useState(false)
  const [filter, setFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchSchoolYearsPage())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load school years')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const showMessage = (msg: string) => {
    setFlash(msg)
    window.setTimeout(() => setFlash(null), 6000)
  }

  const run = async (fn: () => Promise<{ message: string }>) => {
    setBusy(true)
    try {
      const res = await fn()
      showMessage(res.message)
      setModal(null)
      void load()
    } catch (e) {
      showMessage(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  const active = data?.active_school_year ?? null
  const years = data?.school_years ?? []
  const stats = data?.stats

  const filteredYears = useMemo(() => {
    const q = filter.trim().toLowerCase()
    if (!q) return years
    return years.filter((y) => y.name.toLowerCase().includes(q))
  }, [years, filter])

  const resultLabel = useMemo(() => {
    const total = years.length
    const base = total === 1 ? '1 year' : `${total} years`
    if (!filter.trim()) return base
    const shown = filteredYears.length
    return `${shown} of ${base} shown`
  }, [years.length, filteredYears.length, filter])

  if (loading) {
    return (
      <div className="mgmt-sy">
        <div className="mgmt-sy-shell p-5 text-center">Loading…</div>
      </div>
    )
  }

  if (error || !data || !stats) {
    return (
      <div className="mgmt-sy">
        <div className="mgmt-sy-shell p-5">
          <p>{error || 'Could not load school years'}</p>
          <Link to="/management/calendar" className="mgmt-sy-btn mgmt-sy-btn--ghost">
            Back to Calendar
          </Link>
        </div>
      </div>
    )
  }

  const quarters = active?.academic_periods.filter((p) => p.period_type === 'quarter') ?? []
  const semesters = active?.academic_periods.filter((p) => p.period_type === 'semester') ?? []

  return (
    <>
      <div className="mgmt-sy">
        <div className="mgmt-sy-shell">
          {flash ? (
            <div className="alert alert-success" role="status">
              {flash}
            </div>
          ) : null}

          <header className="mgmt-sy-hero">
            <div>
              <p className="mgmt-sy-eyebrow">Academic calendar</p>
              <h1 className="mgmt-sy-title">
                <i className="bi bi-mortarboard-fill" aria-hidden="true" />
                School Years
              </h1>
              <p className="mgmt-sy-subtitle">
                Create, activate, and edit school years and their quarters / semesters. Only one year
                can be active at a time — that&apos;s the year everything else in the system filters
                by.
              </p>
            </div>
            <div className="mgmt-sy-hero-actions">
              <Link to="/management/calendar" className="mgmt-sy-btn mgmt-sy-btn--ghost">
                <i className="bi bi-arrow-left" aria-hidden="true" /> Back to Calendar
              </Link>
              <button
                type="button"
                className="mgmt-sy-btn mgmt-sy-btn--ghost"
                onClick={() => setModal('upload')}
              >
                <i className="bi bi-file-earmark-pdf" aria-hidden="true" /> Upload PDF
              </button>
              <button
                type="button"
                className="mgmt-sy-btn mgmt-sy-btn--primary"
                onClick={() => setModal('add')}
              >
                <i className="bi bi-plus-circle" aria-hidden="true" /> Add school year
              </button>
            </div>
          </header>

          <section className="mgmt-sy-tiles">
            <div className="mgmt-sy-tile mgmt-sy-tile--success">
              <p className="mgmt-sy-tile-label">Active year</p>
              <p className="mgmt-sy-tile-value">{active?.name ?? '—'}</p>
              <p className="mgmt-sy-tile-sub">
                {active ? 'Currently in use across the system' : 'No year is currently active'}
              </p>
            </div>
            <div className="mgmt-sy-tile">
              <p className="mgmt-sy-tile-label">Total years</p>
              <p className="mgmt-sy-tile-value">{stats.total_years}</p>
              <p className="mgmt-sy-tile-sub">{stats.inactive_count} archived / inactive</p>
            </div>
            <div className="mgmt-sy-tile mgmt-sy-tile--info">
              <p className="mgmt-sy-tile-label">Periods this year</p>
              <p className="mgmt-sy-tile-value">{stats.active_periods}</p>
              <p className="mgmt-sy-tile-sub">Quarters &amp; semesters configured</p>
            </div>
            <div className="mgmt-sy-tile mgmt-sy-tile--warn">
              <p className="mgmt-sy-tile-label">Year length</p>
              <p className="mgmt-sy-tile-value">
                {stats.active_total_days != null ? `${stats.active_total_days}d` : '—'}
              </p>
              <p className="mgmt-sy-tile-sub">From start to end (calendar days)</p>
            </div>
          </section>

          {active ? (
            <section className="mgmt-sy-active">
              <div className="mgmt-sy-active-head">
                <div>
                  <h2 className="mgmt-sy-active-name">
                    <i className="bi bi-star-fill" aria-hidden="true" />
                    {active.name}
                  </h2>
                  <p className="mgmt-sy-section-desc">
                    The year every dashboard, gradebook, and roster currently points at.
                  </p>
                </div>
                <div className="d-flex align-items-center gap-2 flex-wrap">
                  <span className="mgmt-sy-active-badge">
                    <i className="bi bi-check2-circle" aria-hidden="true" /> Active
                  </span>
                  <button
                    type="button"
                    className="mgmt-sy-btn mgmt-sy-btn--outline mgmt-sy-btn--sm"
                    onClick={() => setModal('editActive')}
                  >
                    <i className="bi bi-pencil" aria-hidden="true" /> Edit dates
                  </button>
                </div>
              </div>
              <div className="mgmt-sy-active-grid">
                <ActiveStat label="Start date" icon="bi-calendar-plus" tone="start" value={formatDateLong(active.start_date)} />
                <ActiveStat label="End date" icon="bi-calendar-x" tone="end" value={formatDateLong(active.end_date)} />
                <ActiveStat
                  label="Total days"
                  icon="bi-stopwatch"
                  tone="days"
                  value={active.total_days != null ? String(active.total_days) : '—'}
                />
                <ActiveStat
                  label="Periods"
                  icon="bi-collection"
                  tone="periods"
                  value={String(active.academic_periods.length)}
                />
              </div>
            </section>
          ) : null}

          {active && active.academic_periods.length > 0 ? (
            <section className="mgmt-sy-section">
              <div className="mgmt-sy-section-head">
                <div>
                  <h2 className="mgmt-sy-section-title">
                    <i className="bi bi-calendar-week" aria-hidden="true" />
                    Academic periods — {active.name}
                  </h2>
                  <p className="mgmt-sy-section-desc">Quarters drive grading; semesters power transcripts.</p>
                </div>
                <button
                  type="button"
                  className="mgmt-sy-btn mgmt-sy-btn--outline mgmt-sy-btn--sm"
                  disabled={busy}
                  onClick={() => {
                    if (!window.confirm(`Regenerate all periods for ${active.name}? Existing dates will be overwritten.`)) return
                    void run(() => generateSchoolYearPeriods(active.id))
                  }}
                >
                  <i className="bi bi-magic" aria-hidden="true" /> Regenerate periods
                </button>
              </div>
              <div className="mgmt-sy-periods">
                <PeriodGroup
                  title="Quarters"
                  icon="bi-square-half"
                  cardClass="mgmt-sy-period-card--quarter"
                  btnClass="mgmt-sy-icon-btn--info"
                  periods={quarters}
                  onEdit={(id) => setModal({ editPeriod: id })}
                />
                <PeriodGroup
                  title="Semesters"
                  icon="bi-grid-3x2"
                  cardClass="mgmt-sy-period-card--semester"
                  btnClass="mgmt-sy-icon-btn--success"
                  periods={semesters}
                  onEdit={(id) => setModal({ editPeriod: id })}
                />
              </div>
            </section>
          ) : null}

          {active && active.calendar_events.length > 0 ? (
            <CalendarEventsSection events={active.calendar_events} />
          ) : null}

          <section className="mgmt-sy-section">
            <div className="mgmt-sy-section-head">
              <div>
                <h2 className="mgmt-sy-section-title">
                  <i className="bi bi-calendar-range" aria-hidden="true" />
                  All school years
                </h2>
                <p className="mgmt-sy-section-desc">Activate any inactive year to switch the system over to it.</p>
              </div>
            </div>
            <div className="mgmt-sy-table-wrap">
              <div className="mgmt-sy-toolbar">
                <div className="mgmt-sy-search">
                  <i className="bi bi-search" aria-hidden="true" />
                  <input
                    type="search"
                    id="mgmt-sy-year-filter"
                    placeholder="Filter years by name or year number…"
                    autoComplete="off"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  />
                </div>
                <span className="mgmt-sy-toolbar-meta" id="mgmt-sy-result-count">
                  {resultLabel}
                </span>
              </div>

              {years.length > 0 ? (
                <div className="table-responsive">
                  <table className="mgmt-sy-table" id="mgmt-sy-year-table">
                    <thead>
                      <tr>
                        <th>Year name</th>
                        <th>Start date</th>
                        <th>End date</th>
                        <th>Length</th>
                        <th>Status</th>
                        <th>Periods</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredYears.map((year) => (
                        <tr
                          key={year.id}
                          className={year.is_active ? 'is-active' : ''}
                          data-year-name={year.name.toLowerCase()}
                        >
                          <td>
                            <span className="mgmt-sy-year-name">
                              {year.name}
                              {year.is_active ? (
                                <span className="mgmt-sy-pill mgmt-sy-pill--active">
                                  <i className="bi bi-star-fill" aria-hidden="true" /> Active
                                </span>
                              ) : null}
                            </span>
                          </td>
                          <td>{formatDateLong(year.start_date)}</td>
                          <td>{formatDateLong(year.end_date)}</td>
                          <td>{year.total_days != null ? `${year.total_days}d` : '—'}</td>
                          <td>
                            {year.is_active ? (
                              <span className="mgmt-sy-pill mgmt-sy-pill--active">Active</span>
                            ) : (
                              <span className="mgmt-sy-pill mgmt-sy-pill--inactive">Inactive</span>
                            )}
                          </td>
                          <td>
                            <span className="mgmt-sy-pill mgmt-sy-pill--periods">
                              {year.academic_periods.length}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div className="mgmt-sy-row-actions">
                              {!year.is_active ? (
                                <button
                                  type="button"
                                  className="mgmt-sy-icon-btn mgmt-sy-icon-btn--success"
                                  title="Set as active year"
                                  disabled={busy}
                                  onClick={() => {
                                    if (!window.confirm(`Make ${year.name} the active school year? All other years will be deactivated.`)) return
                                    void run(() => setActiveSchoolYear(year.id))
                                  }}
                                >
                                  <i className="bi bi-check-circle" aria-hidden="true" />
                                </button>
                              ) : null}
                              <button
                                type="button"
                                className="mgmt-sy-icon-btn mgmt-sy-icon-btn--info"
                                title="Manage academic periods"
                                onClick={() => setModal({ managePeriods: year.id })}
                              >
                                <i className="bi bi-calendar-week" aria-hidden="true" />
                              </button>
                              <button
                                type="button"
                                className="mgmt-sy-icon-btn mgmt-sy-icon-btn--warn"
                                title="Edit year dates"
                                onClick={() => setModal({ editYear: year.id })}
                              >
                                <i className="bi bi-pencil" aria-hidden="true" />
                              </button>
                              <button
                                type="button"
                                className="mgmt-sy-icon-btn"
                                title="View details"
                                onClick={() => setModal({ viewYear: year.id })}
                              >
                                <i className="bi bi-eye" aria-hidden="true" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="mgmt-sy-empty">
                  <i className="bi bi-calendar-x" aria-hidden="true" />
                  <h4>No school years yet</h4>
                  <p>
                    Click <strong>Add school year</strong> above to create your first one. You can also
                    activate it on creation so the whole system starts using its dates immediately.
                  </p>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>

      <AddYearModal
        show={modal === 'add'}
        busy={busy}
        onClose={() => setModal(null)}
        onSubmit={(body) => run(() => createSchoolYear(body))}
      />
      <UploadPdfModal
        show={modal === 'upload'}
        onClose={() => setModal(null)}
        csrf={user.csrf_token}
        years={years}
      />
      {active ? (
        <EditYearDatesModal
          show={modal === 'editActive'}
          title={`Edit ${active.name}`}
          busy={busy}
          startDate={active.start_date ?? ''}
          endDate={active.end_date ?? ''}
          onClose={() => setModal(null)}
          onSubmit={(body) => run(() => editActiveSchoolYear(body))}
        />
      ) : null}
      {typeof modal === 'object' && modal && 'editYear' in modal ? (
        <EditYearModalById yearId={modal.editYear} years={years} busy={busy} onClose={() => setModal(null)} onRun={run} />
      ) : null}
      {typeof modal === 'object' && modal && 'viewYear' in modal ? (
        <ViewYearModal year={years.find((y) => y.id === modal.viewYear) ?? null} onClose={() => setModal(null)} />
      ) : null}
      {typeof modal === 'object' && modal && 'managePeriods' in modal ? (
        <ManagePeriodsModal
          year={years.find((y) => y.id === modal.managePeriods) ?? null}
          busy={busy}
          onClose={() => setModal(null)}
          onRun={run}
        />
      ) : null}
      {typeof modal === 'object' && modal && 'editPeriod' in modal ? (
        <EditPeriodModal
          period={years.flatMap((y) => y.academic_periods).find((p) => p.id === modal.editPeriod) ?? null}
          busy={busy}
          onClose={() => setModal(null)}
          onSubmit={(body) => run(() => editSchoolYearPeriod(modal.editPeriod, body))}
        />
      ) : null}
    </>
  )
}

function ActiveStat({
  label,
  icon,
  tone,
  value,
}: {
  label: string
  icon: string
  tone: string
  value: string
}) {
  return (
    <div className="mgmt-sy-active-stat">
      <span className="mgmt-sy-active-stat-label">{label}</span>
      <span className={`mgmt-sy-active-stat-value mgmt-sy-active-stat-value--${tone}`}>
        <i className={`bi ${icon}`} aria-hidden="true" />
        {value}
      </span>
    </div>
  )
}

function PeriodGroup({
  title,
  icon,
  cardClass,
  btnClass,
  periods,
  onEdit,
}: {
  title: string
  icon: string
  cardClass: string
  btnClass: string
  periods: AcademicPeriod[]
  onEdit: (id: number) => void
}) {
  return (
    <div>
      <h3 className="mgmt-sy-period-head">
        <i className={`bi ${icon}`} aria-hidden="true" /> {title}
      </h3>
      <div className="mgmt-sy-period-cards">
        {periods.length > 0 ? (
          periods.map((period) => (
            <div key={period.id} className={`mgmt-sy-period-card ${cardClass}`}>
              <p className="mgmt-sy-period-card-name">{period.name}</p>
              <p className="mgmt-sy-period-card-dates">
                {formatDateShort(period.start_date)} – {formatDateShort(period.end_date)}
              </p>
              <div className="mgmt-sy-period-card-actions">
                <button
                  type="button"
                  className={`mgmt-sy-icon-btn ${btnClass}`}
                  title="Edit dates"
                  onClick={() => onEdit(period.id)}
                >
                  <i className="bi bi-pencil" aria-hidden="true" />
                </button>
              </div>
            </div>
          ))
        ) : (
          <p className="mgmt-sy-section-desc">No {title.toLowerCase()} defined yet.</p>
        )}
      </div>
    </div>
  )
}

function CalendarEventsSection({ events }: { events: CalendarEventRow[] }) {
  const holidays = events.filter((e) => e.event_type === 'holiday')
  const breaks = events.filter((e) => e.event_type === 'break')
  const pd = events.filter((e) => e.event_type === 'professional_development')
  const other = events.filter(
    (e) => !['holiday', 'break', 'professional_development'].includes(e.event_type),
  )

  return (
    <section className="mgmt-sy-section">
      <div className="mgmt-sy-section-head">
        <div>
          <h2 className="mgmt-sy-section-title">
            <i className="bi bi-calendar-event" aria-hidden="true" />
            Events parsed from the calendar PDF
          </h2>
          <p className="mgmt-sy-section-desc">
            Holidays, breaks, and other dates pulled in by the calendar upload.
          </p>
        </div>
      </div>
      <div className="mgmt-sy-events">
        <EventGroup title="Holidays" icon="bi-calendar-x" items={holidays} />
        <EventGroup title="School breaks" icon="bi-calendar-minus" items={breaks} range />
        <EventGroup title="Professional development" icon="bi-person-workspace" items={pd} />
        <EventGroup title="Other events" icon="bi-calendar-plus" items={other} range />
      </div>
    </section>
  )
}

function EventGroup({
  title,
  icon,
  items,
  range,
}: {
  title: string
  icon: string
  items: CalendarEventRow[]
  range?: boolean
}) {
  if (items.length === 0) return null
  return (
    <div className="mgmt-sy-event-group">
      <div className="mgmt-sy-event-group-head">
        <span>
          <i className={`bi ${icon} me-2`} aria-hidden="true" />
          {title}
        </span>
        <span className="count">{items.length}</span>
      </div>
      {items.map((ev) => (
        <div key={ev.id} className="mgmt-sy-event-row">
          <strong>{ev.name}</strong>
          <span className="date">
            {range && ev.start_date && ev.end_date && ev.start_date !== ev.end_date
              ? `${formatDateShort(ev.start_date)} – ${formatDateLong(ev.end_date)}`
              : formatDateLong(ev.start_date)}
          </span>
        </div>
      ))}
    </div>
  )
}

function AddYearModal({
  show,
  busy,
  onClose,
  onSubmit,
}: {
  show: boolean
  busy: boolean
  onClose: () => void
  onSubmit: (body: {
    name: string
    start_date: string
    end_date: string
    is_active: boolean
    auto_generate_quarters: boolean
  }) => void
}) {
  const [name, setName] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [isActive, setIsActive] = useState(false)
  const [autoQ, setAutoQ] = useState(true)

  return (
    <LegacyBootstrapModal
      show={show}
      onClose={onClose}
      title={
        <>
          <i className="bi bi-plus-circle me-2" aria-hidden="true" /> Add a new school year
        </>
      }
      className="mgmt-sy-modal"
      size="lg"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (new Date(start) >= new Date(end)) {
            window.alert('End date must be after start date.')
            return
          }
          onSubmit({ name, start_date: start, end_date: end, is_active: isActive, auto_generate_quarters: autoQ })
        }}
      >
        <div className="modal-body">
          <div className="row g-3">
            <div className="col-md-6">
              <label htmlFor="add-name" className="form-label">
                Year name <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                className="form-control"
                id="add-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., 2026-2027"
                required
              />
              <div className="form-text">
                Use the YYYY-YYYY convention so the closure flow can auto-suggest the next year later.
              </div>
            </div>
            <div className="col-md-6">
              <label className="form-label">Status</label>
              <div className="form-check form-switch mt-2">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="add-is-active"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="add-is-active">
                  Set as active immediately
                </label>
              </div>
              <div className="form-text">All other years will be deactivated when you check this.</div>
            </div>
            <div className="col-md-6">
              <label htmlFor="add-start-date" className="form-label">
                Start date <span className="text-danger">*</span>
              </label>
              <input
                type="date"
                className="form-control"
                id="add-start-date"
                value={start}
                onChange={(e) => {
                  setStart(e.target.value)
                  if (!end && e.target.value) {
                    const d = new Date(`${e.target.value}T00:00:00`)
                    d.setFullYear(d.getFullYear() + 1)
                    d.setMonth(5)
                    d.setDate(15)
                    setEnd(d.toISOString().split('T')[0])
                  }
                }}
                required
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="add-end-date" className="form-label">
                End date <span className="text-danger">*</span>
              </label>
              <input
                type="date"
                className="form-control"
                id="add-end-date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </div>
            <div className="col-12">
              <div className="form-check form-switch">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="add-auto-q"
                  checked={autoQ}
                  onChange={(e) => setAutoQ(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="add-auto-q">
                  Auto-generate Q1–Q4 and S1–S2 periods
                </label>
              </div>
              <div className="form-text">Splits the date range evenly into 4 quarters and 2 semesters.</div>
            </div>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="mgmt-sy-btn mgmt-sy-btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="mgmt-sy-btn mgmt-sy-btn--primary" disabled={busy}>
            <i className="bi bi-plus-circle" aria-hidden="true" /> Create school year
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function UploadPdfModal({
  show,
  onClose,
  csrf,
  years,
}: {
  show: boolean
  onClose: () => void
  csrf: string
  years: SchoolYearRow[]
}) {
  return (
    <LegacyBootstrapModal
      show={show}
      onClose={onClose}
      title={
        <>
          <i className="bi bi-file-earmark-pdf me-2" aria-hidden="true" /> Upload calendar PDF
        </>
      }
      className="mgmt-sy-modal"
      size="lg"
    >
      <form method="POST" action="/management/upload-calendar-pdf" encType="multipart/form-data">
        <input type="hidden" name="csrf_token" value={csrf} />
        <div className="modal-body">
          <div className="alert alert-info">
            <i className="bi bi-info-circle me-2" aria-hidden="true" />
            We&apos;ll extract year start/end dates, quarters, holidays, breaks, PD days, and
            conferences automatically.
          </div>
          <div className="mb-3">
            <label htmlFor="calendar_pdf" className="form-label">
              Calendar PDF <span className="text-danger">*</span>
            </label>
            <input type="file" className="form-control" id="calendar_pdf" name="calendar_pdf" accept=".pdf" required />
          </div>
          <div className="mb-3">
            <label htmlFor="upload-school-year" className="form-label">
              Apply to school year <span className="text-danger">*</span>
            </label>
            <select className="form-select" id="upload-school-year" name="school_year" required>
              <option value="">Select a school year…</option>
              {years.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                </option>
              ))}
            </select>
          </div>
          <div className="mb-3">
            <label htmlFor="calendar_name" className="form-label">
              Calendar name (optional)
            </label>
            <input
              type="text"
              className="form-control"
              id="calendar_name"
              name="calendar_name"
              placeholder="e.g., 2026-2027 Official School Calendar"
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="mgmt-sy-btn mgmt-sy-btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="mgmt-sy-btn mgmt-sy-btn--primary">
            <i className="bi bi-upload" aria-hidden="true" /> Upload &amp; process
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function EditYearDatesModal({
  show,
  title,
  busy,
  startDate,
  endDate,
  onClose,
  onSubmit,
}: {
  show: boolean
  title: string
  busy: boolean
  startDate: string
  endDate: string
  onClose: () => void
  onSubmit: (body: { start_date: string; end_date: string }) => void
}) {
  const [start, setStart] = useState(startDate)
  const [end, setEnd] = useState(endDate)
  useEffect(() => {
    setStart(startDate)
    setEnd(endDate)
  }, [startDate, endDate, show])

  return (
    <LegacyBootstrapModal
      show={show}
      onClose={onClose}
      title={
        <>
          <i className="bi bi-pencil me-2" aria-hidden="true" /> {title}
        </>
      }
      className="mgmt-sy-modal"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (new Date(start) >= new Date(end)) {
            window.alert('End date must be after start date.')
            return
          }
          onSubmit({ start_date: start, end_date: end })
        }}
      >
        <div className="modal-body">
          <div className="mb-3">
            <label htmlFor="active_start_date" className="form-label">
              Start date
            </label>
            <input
              type="date"
              className="form-control"
              id="active_start_date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              required
            />
          </div>
          <div className="mb-3">
            <label htmlFor="active_end_date" className="form-label">
              End date
            </label>
            <input
              type="date"
              className="form-control"
              id="active_end_date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="mgmt-sy-btn mgmt-sy-btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="mgmt-sy-btn mgmt-sy-btn--success" disabled={busy}>
            Save changes
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function EditYearModalById({
  yearId,
  years,
  busy,
  onClose,
  onRun,
}: {
  yearId: number
  years: SchoolYearRow[]
  busy: boolean
  onClose: () => void
  onRun: (fn: () => Promise<{ message: string }>) => void
}) {
  const year = years.find((y) => y.id === yearId)
  if (!year) return null
  return (
    <EditYearDatesModal
      show
      title={`Edit ${year.name}`}
      busy={busy}
      startDate={year.start_date ?? ''}
      endDate={year.end_date ?? ''}
      onClose={onClose}
      onSubmit={(body) => onRun(() => editSchoolYear(yearId, body))}
    />
  )
}

function ViewYearModal({ year, onClose }: { year: SchoolYearRow | null; onClose: () => void }) {
  if (!year) return null
  return (
    <LegacyBootstrapModal
      show
      onClose={onClose}
      title={
        <>
          <i className="bi bi-eye me-2" aria-hidden="true" /> {year.name}
        </>
      }
      className="mgmt-sy-modal"
      size="lg"
    >
      <div className="modal-body">
        <div className="row g-3">
          <div className="col-md-6">
            <h6 className="text-uppercase small text-muted">Basics</h6>
            <p className="mb-1">
              <strong>Name:</strong> {year.name}
            </p>
            <p className="mb-1">
              <strong>Start:</strong> {formatDateLong(year.start_date)}
            </p>
            <p className="mb-1">
              <strong>End:</strong> {formatDateLong(year.end_date)}
            </p>
            <p className="mb-1">
              <strong>Status:</strong>{' '}
              {year.is_active ? (
                <span className="mgmt-sy-pill mgmt-sy-pill--active">Active</span>
              ) : (
                <span className="mgmt-sy-pill mgmt-sy-pill--inactive">Inactive</span>
              )}
            </p>
            {year.total_days != null ? (
              <p className="mb-1">
                <strong>Length:</strong> {year.total_days} days
              </p>
            ) : null}
          </div>
          <div className="col-md-6">
            <h6 className="text-uppercase small text-muted">Academic periods</h6>
            {year.academic_periods.length > 0 ? (
              year.academic_periods.map((period) => (
                <div key={period.id} className="mgmt-sy-event-row">
                  <strong>{period.name}</strong>
                  <span className="date">
                    {formatDateShort(period.start_date)} – {formatDateShort(period.end_date)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-muted small mb-0">No academic periods defined for this year.</p>
            )}
          </div>
        </div>
      </div>
      <div className="modal-footer">
        <button type="button" className="mgmt-sy-btn mgmt-sy-btn--ghost" onClick={onClose}>
          Close
        </button>
      </div>
    </LegacyBootstrapModal>
  )
}

function ManagePeriodsModal({
  year,
  busy,
  onClose,
  onRun,
}: {
  year: SchoolYearRow | null
  busy: boolean
  onClose: () => void
  onRun: (fn: () => Promise<{ message: string }>) => void
}) {
  const [name, setName] = useState('')
  const [periodType, setPeriodType] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')

  if (!year) return null
  const qs = year.academic_periods.filter((p) => p.period_type === 'quarter')
  const ss = year.academic_periods.filter((p) => p.period_type === 'semester')

  return (
    <LegacyBootstrapModal
      show
      onClose={onClose}
      title={
        <>
          <i className="bi bi-calendar-week me-2" aria-hidden="true" />
          Periods — {year.name}
        </>
      }
      className="mgmt-sy-modal"
      size="lg"
    >
      <div className="modal-body">
        <div className="row g-3 mb-3">
          <div className="col-md-6">
            <h6 className="text-uppercase small text-muted">Quarters</h6>
            {qs.length > 0 ? (
              qs.map((period) => (
                <div key={period.id} className="mgmt-sy-event-row">
                  <strong>{period.name}</strong>
                  <span className="date">
                    {formatDateShort(period.start_date)} – {formatDateShort(period.end_date)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-muted small mb-0">No quarters defined.</p>
            )}
          </div>
          <div className="col-md-6">
            <h6 className="text-uppercase small text-muted">Semesters</h6>
            {ss.length > 0 ? (
              ss.map((period) => (
                <div key={period.id} className="mgmt-sy-event-row">
                  <strong>{period.name}</strong>
                  <span className="date">
                    {formatDateShort(period.start_date)} – {formatDateShort(period.end_date)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-muted small mb-0">No semesters defined.</p>
            )}
          </div>
        </div>

        <button
          type="button"
          className="mgmt-sy-btn mgmt-sy-btn--outline mgmt-sy-btn--sm mb-3"
          disabled={busy}
          onClick={() => {
            if (!window.confirm(`Regenerate all periods for ${year.name}? Existing dates will be overwritten.`)) return
            onRun(() => generateSchoolYearPeriods(year.id))
          }}
        >
          <i className="bi bi-magic" aria-hidden="true" /> Regenerate Q1–Q4 / S1–S2 from year dates
        </button>

        <h6 className="text-uppercase small text-muted">Add a single period</h6>
        <form
          className="row g-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (new Date(start) >= new Date(end)) {
              window.alert('End date must be after start date.')
              return
            }
            onRun(() =>
              addSchoolYearPeriod(year.id, {
                name,
                period_type: periodType,
                start_date: start,
                end_date: end,
              }),
            )
          }}
        >
          <div className="col-md-6">
            <label className="form-label" htmlFor={`np-name-${year.id}`}>
              Period name
            </label>
            <input
              type="text"
              className="form-control"
              id={`np-name-${year.id}`}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor={`np-type-${year.id}`}>
              Type
            </label>
            <select
              className="form-select"
              id={`np-type-${year.id}`}
              value={periodType}
              onChange={(e) => setPeriodType(e.target.value)}
              required
            >
              <option value="">Select…</option>
              <option value="quarter">Quarter</option>
              <option value="semester">Semester</option>
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor={`np-start-${year.id}`}>
              Start date
            </label>
            <input
              type="date"
              className="form-control"
              id={`np-start-${year.id}`}
              value={start}
              onChange={(e) => setStart(e.target.value)}
              required
            />
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor={`np-end-${year.id}`}>
              End date
            </label>
            <input
              type="date"
              className="form-control"
              id={`np-end-${year.id}`}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              required
            />
          </div>
          <div className="col-12 text-end">
            <button type="submit" className="mgmt-sy-btn mgmt-sy-btn--primary mgmt-sy-btn--sm" disabled={busy}>
              <i className="bi bi-plus-circle" aria-hidden="true" /> Add period
            </button>
          </div>
        </form>
      </div>
      <div className="modal-footer">
        <button type="button" className="mgmt-sy-btn mgmt-sy-btn--ghost" onClick={onClose}>
          Close
        </button>
      </div>
    </LegacyBootstrapModal>
  )
}

function EditPeriodModal({
  period,
  busy,
  onClose,
  onSubmit,
}: {
  period: AcademicPeriod | null
  busy: boolean
  onClose: () => void
  onSubmit: (body: { start_date: string; end_date: string }) => void
}) {
  const [start, setStart] = useState(period?.start_date ?? '')
  const [end, setEnd] = useState(period?.end_date ?? '')
  useEffect(() => {
    setStart(period?.start_date ?? '')
    setEnd(period?.end_date ?? '')
  }, [period, period?.start_date, period?.end_date])

  if (!period) return null

  return (
    <LegacyBootstrapModal
      show
      onClose={onClose}
      title={
        <>
          <i className="bi bi-pencil me-2" aria-hidden="true" />
          Edit {period.name} ({period.period_type.charAt(0).toUpperCase() + period.period_type.slice(1)})
        </>
      }
      className="mgmt-sy-modal"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (new Date(start) >= new Date(end)) {
            window.alert('End date must be after start date.')
            return
          }
          onSubmit({ start_date: start, end_date: end })
        }}
      >
        <div className="modal-body">
          <div className="mb-3">
            <label className="form-label" htmlFor={`ep-start-${period.id}`}>
              Start date
            </label>
            <input
              type="date"
              className="form-control"
              id={`ep-start-${period.id}`}
              value={start}
              onChange={(e) => setStart(e.target.value)}
              required
            />
          </div>
          <div className="mb-3">
            <label className="form-label" htmlFor={`ep-end-${period.id}`}>
              End date
            </label>
            <input
              type="date"
              className="form-control"
              id={`ep-end-${period.id}`}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="mgmt-sy-btn mgmt-sy-btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="mgmt-sy-btn mgmt-sy-btn--primary" disabled={busy}>
            Save
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}
