import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { fetchClosureScheduleForm, scheduleClosure } from '../api/schoolYearClosure'
import { CLOSURE_LEGACY_CSS } from '../config/legacyPages'
import { useLegacyStyles } from '../hooks/useLegacyStyles'
import type { ManagementOutletContext } from '../types/layout'
import type { ClosureScheduleResponse } from '../types/schoolYearClosure'
import { previewOffsetDate } from '../utils/formatDate'
import { spaRoute } from '../utils/spaRoute'

const PREVIEW_OFFSETS = [0, 7, 21, 28] as const

export function ClosureSchedulePage() {
  useLegacyStyles([CLOSURE_LEGACY_CSS])
  const { user } = useOutletContext<ManagementOutletContext>()
  const navigate = useNavigate()
  const isDirector = user.role_canonical === 'Director'

  const [data, setData] = useState<ClosureScheduleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [schoolYearId, setSchoolYearId] = useState<number | ''>('')
  const [closureDate, setClosureDate] = useState('')
  const [notes, setNotes] = useState('')
  const [confirm, setConfirm] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchClosureScheduleForm()
      setData(res)
      setSchoolYearId(res.suggested_year_id ?? '')
      setClosureDate(res.suggested_date ?? res.today)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load form')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const activeList = useMemo(
    () => (data ? Object.values(data.active_closures) : []),
    [data],
  )

  const handleSchoolYearChange = (value: string) => {
    const id = value ? Number(value) : ''
    setSchoolYearId(id)
    if (!data || !value) return
    const sy = data.school_years.find((y) => y.id === Number(value))
    if (sy?.end_date) setClosureDate(sy.end_date)
    if (sy?.has_active_closure) {
      window.alert(
        'This school year already has a closure in progress. Cancel or finalize it first before scheduling another.',
      )
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!schoolYearId) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await scheduleClosure({
        school_year_id: Number(schoolYearId),
        closure_date: closureDate,
        notes: notes.trim() || undefined,
        confirm,
      })
      if (res.redirect_url) {
        navigate(spaRoute(res.redirect_url))
      } else if (res.closure_id) {
        navigate(`/management/school-year/closure/${res.closure_id}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not schedule closure')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="mgmt-syc container-fluid px-0 px-md-1">
        <div className="mgmt-syc-shell p-5 text-center">Loading…</div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="mgmt-syc container-fluid px-0 px-md-1">
        <div className="mgmt-syc-shell p-5">
          <p>{error}</p>
          <Link to="/management/calendar" className="mgmt-syc-btn mgmt-syc-btn--ghost">
            School calendar
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="mgmt-syc container-fluid px-0 px-md-1">
        <div className={`mgmt-syc-shell${isDirector ? ' mgmt-syc-shell--director' : ''}`}>
          <header className="mgmt-syc-hero">
            <div>
              <p className="mgmt-syc-eyebrow">End of school year</p>
              <h1 className="mgmt-syc-title">Schedule school-year closure</h1>
              <p className="mgmt-syc-subtitle">
                <i className="bi bi-calendar-event" aria-hidden="true" />
                Phased Day&nbsp;0 → Day&nbsp;7 → Day&nbsp;21 → Day&nbsp;28 workflow
              </p>
            </div>
            <div className="mgmt-syc-hero-actions">
              {isDirector ? (
                <span className="mgmt-syc-role-badge mgmt-syc-role-badge--director">
                  <i className="bi bi-award-fill" aria-hidden="true" /> Director
                </span>
              ) : (
                <span className="mgmt-syc-role-badge mgmt-syc-role-badge--admin">
                  <i className="bi bi-shield-fill" aria-hidden="true" /> Administrator
                </span>
              )}
              <Link to="/management/calendar" className="mgmt-syc-btn mgmt-syc-btn--ghost">
                <i className="bi bi-arrow-left" aria-hidden="true" /> School calendar
              </Link>
            </div>
          </header>

          {activeList.length > 0 ? (
            <section className="mgmt-syc-active-banner">
              <div>
                <h2 className="mgmt-syc-active-title">
                  <i className="bi bi-clock-history" aria-hidden="true" />
                  {activeList.length} active closure{activeList.length !== 1 ? 's' : ''}
                </h2>
                <p className="mgmt-syc-active-sub">
                  A school year already has a closure in progress. You can open the dashboard to
                  monitor progress, grant extensions, or postpone milestones.
                </p>
              </div>
              <div className="mgmt-syc-active-list">
                {activeList.map((c) => (
                  <Link
                    key={c.id}
                    className="mgmt-syc-active-link"
                    to={`/management/school-year/closure/${c.id}`}
                  >
                    <span className="mgmt-syc-active-year">{c.school_year_name ?? `Closure #${c.id}`}</span>
                    <span className="mgmt-syc-active-phase">{c.phase_label}</span>
                    <span className="mgmt-syc-active-cta">
                      Open <i className="bi bi-arrow-right-short" aria-hidden="true" />
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}

          <section className="mgmt-syc-explainer" aria-labelledby="mgmtSycExplainerTitle">
            <h2 id="mgmtSycExplainerTitle" className="mgmt-syc-section-title">
              <i className="bi bi-info-circle-fill" aria-hidden="true" /> What this workflow does
            </h2>
            <p className="mgmt-syc-section-desc">
              Schedule one Day&nbsp;0 date (typically the Q4 end or the official school-year end).
              The system then handles every milestone automatically — no report cards generate on
              Day&nbsp;0, no classes archive, no students are promoted until Day&nbsp;28. You can
              pause, postpone, cancel, or grant per-user extensions at any point.
            </p>

            <ol className="mgmt-syc-timeline-preview">
              <li className="mgmt-syc-tlp-step mgmt-syc-tlp-step--day0">
                <span className="mgmt-syc-tlp-day">Day 0</span>
                <div>
                  <h3 className="mgmt-syc-tlp-title">Closure date</h3>
                  <p>
                    Students receive an in-app notification + no-reply email: &quot;You have one week
                    to submit any outstanding work and contact your teachers.&quot; Grades stay
                    editable for everyone.
                  </p>
                </div>
              </li>
              <li className="mgmt-syc-tlp-step mgmt-syc-tlp-step--day7">
                <span className="mgmt-syc-tlp-day">Day 7</span>
                <div>
                  <h3 className="mgmt-syc-tlp-title">Student lockout</h3>
                  <p>
                    Students&apos; current-year classes move to read-only and disappear from &quot;My
                    Classes&quot; (they stay visible under &quot;Previous years&quot;). Teachers get a
                    reminder that they have two more weeks to finalize grades.
                  </p>
                </div>
              </li>
              <li className="mgmt-syc-tlp-step mgmt-syc-tlp-step--day21">
                <span className="mgmt-syc-tlp-day">Day 21</span>
                <div>
                  <h3 className="mgmt-syc-tlp-title">Teacher lockout</h3>
                  <p>
                    Teachers lose write access to that year&apos;s gradebooks. Directors/Admins
                    receive a pre-finalize warning with the unfinished-work checklist. Admins can
                    still grant per-teacher extensions for special cases.
                  </p>
                </div>
              </li>
              <li className="mgmt-syc-tlp-step mgmt-syc-tlp-step--day28">
                <span className="mgmt-syc-tlp-day">Day 28</span>
                <div>
                  <h3 className="mgmt-syc-tlp-title">Auto-finalize</h3>
                  <p>
                    The system generates official Q1–Q4 report cards (marked as auto-generated),
                    archives the year&apos;s classes/enrollments, promotes students one grade level
                    (skipping anyone flagged as repeating and 12th graders), and deactivates the
                    school year.
                  </p>
                </div>
              </li>
            </ol>

            <div className="mgmt-syc-failsafes">
              <h3 className="mgmt-syc-failsafes-title">
                <i className="bi bi-shield-check" aria-hidden="true" /> Failsafes
              </h3>
              <ul>
                <li>
                  <strong>Pause</strong> — freeze all transitions and notifications without changing
                  the dates.
                </li>
                <li>
                  <strong>Postpone</strong> — slide every milestone forward by N days (snow days,
                  last-minute curriculum changes).
                </li>
                <li>
                  <strong>Cancel</strong> — abort the workflow entirely; the school year continues as
                  normal.
                </li>
                <li>
                  <strong>Manual advance</strong> — push to the next phase before its automatic
                  date.
                </li>
                <li>
                  <strong>Finalize now</strong> — run the Day&nbsp;28 archival ahead of schedule.
                </li>
                <li>
                  <strong>Per-teacher / per-student / per-class extensions</strong> — give specific
                  people more time without slowing everyone else down.
                </li>
                <li>
                  <strong>Reopen</strong> — undo a finalize after the fact for grade-book
                  corrections.
                </li>
              </ul>
            </div>
          </section>

          <section className="mgmt-syc-form-wrap" aria-labelledby="mgmtSycFormTitle">
            <h2 id="mgmtSycFormTitle" className="mgmt-syc-section-title">
              <i className="bi bi-pencil-square" aria-hidden="true" /> Schedule a new closure
            </h2>

            {error ? (
              <div className="mgmt-syc-alert mgmt-syc-alert--warning mb-3">
                <i className="bi bi-exclamation-triangle-fill" aria-hidden="true" /> {error}
              </div>
            ) : null}

            <form className="mgmt-syc-form" onSubmit={handleSubmit} noValidate>
              <div className="mgmt-syc-form-row">
                <label className="mgmt-syc-label" htmlFor="school_year_id">
                  School year
                </label>
                <select
                  name="school_year_id"
                  id="school_year_id"
                  className="mgmt-syc-input"
                  value={schoolYearId}
                  onChange={(e) => handleSchoolYearChange(e.target.value)}
                  required
                >
                  <option value="">— Select a school year —</option>
                  {data?.school_years.map((sy) => (
                    <option key={sy.id} value={sy.id}>
                      {sy.name}
                      {sy.is_active ? ' (active)' : ''}
                      {sy.has_active_closure ? ' — closure already in progress' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mgmt-syc-form-row">
                <label className="mgmt-syc-label" htmlFor="closure_date">
                  Day 0 — closure date
                </label>
                <input
                  type="date"
                  name="closure_date"
                  id="closure_date"
                  className="mgmt-syc-input"
                  value={closureDate}
                  onChange={(e) => setClosureDate(e.target.value)}
                  required
                />
                <p className="mgmt-syc-help">
                  Usually the last day of Q4 or the official school-year end date. Notifications go
                  out at midnight on this day.
                </p>
              </div>

              <div className="mgmt-syc-form-row">
                <label className="mgmt-syc-label" htmlFor="notes">
                  Internal notes (optional)
                </label>
                <textarea
                  name="notes"
                  id="notes"
                  rows={3}
                  className="mgmt-syc-input"
                  placeholder="e.g. End-of-year 2025–2026 closure scheduled by Director on signing day."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              <div className="mgmt-syc-preview-wrap" aria-live="polite">
                <h3 className="mgmt-syc-preview-title">Timeline preview</h3>
                <div className="mgmt-syc-preview" id="mgmt-syc-preview">
                  {PREVIEW_OFFSETS.map((offset) => (
                    <div
                      key={offset}
                      className={`mgmt-syc-preview-card mgmt-syc-preview-card--day${offset}`}
                    >
                      <span className="mgmt-syc-preview-day">Day {offset}</span>
                      <span className="mgmt-syc-preview-date" data-offset={offset}>
                        {previewOffsetDate(closureDate, offset)}
                      </span>
                      <span className="mgmt-syc-preview-label">
                        {offset === 0
                          ? 'Notify students'
                          : offset === 7
                            ? 'Lock students'
                            : offset === 21
                              ? 'Lock teachers'
                              : 'Auto-finalize'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mgmt-syc-confirm">
                <label className="mgmt-syc-label" htmlFor="confirm">
                  Type <code>SCHEDULE CLOSURE</code> to confirm
                </label>
                <input
                  type="text"
                  name="confirm"
                  id="confirm"
                  className="mgmt-syc-input"
                  autoComplete="off"
                  placeholder="SCHEDULE CLOSURE"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                />
              </div>

              <div className="mgmt-syc-actions">
                <Link to="/management/calendar" className="mgmt-syc-btn mgmt-syc-btn--ghost">
                  Cancel
                </Link>
                <button
                  type="submit"
                  className="mgmt-syc-btn mgmt-syc-btn--primary"
                  disabled={submitting}
                >
                  <i className="bi bi-calendar-check" aria-hidden="true" />{' '}
                  {submitting ? 'Scheduling…' : 'Schedule closure'}
                </button>
              </div>
            </form>
          </section>
        </div>
      </div>
  )
}
