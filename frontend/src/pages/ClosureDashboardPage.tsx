import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  createNextSchoolYear,
  fetchClosureDashboard,
  grantClosureExtension,
  revokeClosureExtension,
  runClosureAction,
} from '../api/schoolYearClosure'
import { LegacyBootstrapModal } from '../components/legacy/LegacyBootstrapModal'
import { LegacyMgmtScope } from '../components/legacy/LegacyMgmtScope'
import type { ClosureDashboardResponse, ClosureExtension } from '../types/schoolYearClosure'
import {
  adminWindowPhaseState,
  finalizedPhaseState,
  phaseStepClass,
  scheduledPhaseState,
  studentWindowPhaseState,
  teacherWindowPhaseState,
} from '../utils/closurePhase'
import { daysUntilLabel, formatDateLong, formatDateTime } from '../utils/formatDate'

type ModalId = 'postpone' | 'reset' | 'advance' | 'finalize' | 'cancel' | 'reopen' | 'extension' | null

export function ClosureDashboardPage() {
  const { closureId: closureIdParam } = useParams()
  const closureId = closureIdParam && /^\d+$/.test(closureIdParam) ? Number(closureIdParam) : null

  const [data, setData] = useState<ClosureDashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)
  const [modal, setModal] = useState<ModalId>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!closureId) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClosureDashboard(closureId))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load closure')
    } finally {
      setLoading(false)
    }
  }, [closureId])

  useEffect(() => {
    void load()
  }, [load])

  const showMessage = (msg: string) => {
    setFlash(msg)
    window.setTimeout(() => setFlash(null), 6000)
  }

  const act = async (action: string, body: Record<string, unknown> = {}) => {
    if (!closureId) return
    setBusy(true)
    try {
      const res = await runClosureAction(closureId, action, body)
      showMessage(res.message)
      setModal(null)
      void load()
    } catch (e) {
      showMessage(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  if (!closureId) {
    return (
      <LegacyMgmtScope>
        <div className="mgmt-syc container-fluid px-0 px-md-1">
          <div className="mgmt-syc-shell p-5">
            <p>Invalid closure.</p>
            <Link to="/management/school-year/closure/schedule" className="mgmt-syc-btn mgmt-syc-btn--ghost">
              Schedule closure
            </Link>
          </div>
        </div>
      </LegacyMgmtScope>
    )
  }

  if (loading) {
    return (
      <LegacyMgmtScope>
        <div className="mgmt-syc container-fluid px-0 px-md-1">
          <div className="mgmt-syc-shell p-5 text-center">Loading closure…</div>
        </div>
      </LegacyMgmtScope>
    )
  }

  if (error || !data) {
    return (
      <LegacyMgmtScope>
        <div className="mgmt-syc container-fluid px-0 px-md-1">
          <div className="mgmt-syc-shell p-5">
            <p>{error || 'Could not load closure'}</p>
            <Link to="/management/calendar" className="mgmt-syc-btn mgmt-syc-btn--ghost">
              School calendar
            </Link>
          </div>
        </div>
      </LegacyMgmtScope>
    )
  }

  const { closure, school_year, days_to, checklist, finalize_stats, extensions, events } = data
  const phase = closure.phase
  const isTerminal = data.terminal_phases.includes(phase)
  const isPaused = phase === 'paused'
  const isFinalized = phase === 'finalized'

  return (
    <LegacyMgmtScope>
      <>
      <div className="mgmt-syc container-fluid px-0 px-md-1">
        <div className="mgmt-syc-shell">
          {flash ? (
            <div className="mgmt-syc-alert mgmt-syc-alert--success mb-3" role="status">
              <i className="bi bi-check-circle-fill" aria-hidden="true" /> {flash}
            </div>
          ) : null}

          <header className="mgmt-syc-hero">
            <div>
              <p className="mgmt-syc-eyebrow">School-year closure</p>
              <h1 className="mgmt-syc-title">
                {school_year.name ?? 'School year'}
                <span className={`mgmt-syc-phase-badge mgmt-syc-phase-badge--${phase}`}>
                  {closure.phase_label}
                </span>
              </h1>
              <p className="mgmt-syc-subtitle">
                <i className="bi bi-calendar3" aria-hidden="true" />
                Day&nbsp;0: {formatDateLong(closure.closure_date)}
                &nbsp;·&nbsp; Auto-finalize: {formatDateLong(closure.finalize_at)}
                {closure.created_by ? ` · Scheduled by ${closure.created_by}` : ''}
              </p>
            </div>
            <div className="mgmt-syc-hero-actions">
              <Link to="/management/school-year/closure/schedule" className="mgmt-syc-btn mgmt-syc-btn--ghost">
                <i className="bi bi-list" aria-hidden="true" /> All closures
              </Link>
              <Link to="/management/calendar" className="mgmt-syc-btn mgmt-syc-btn--ghost">
                <i className="bi bi-arrow-left" aria-hidden="true" /> School calendar
              </Link>
            </div>
          </header>

          <section className="mgmt-syc-timeline" aria-label="Phase timeline">
            <ol className="mgmt-syc-phase-rail">
              <PhasePill label="Scheduled" phaseKey="scheduled" {...scheduledPhaseState(phase)} />
              <PhasePill
                label="Day 0 · Student window"
                phaseKey="student_window"
                {...studentWindowPhaseState(phase)}
              />
              <PhasePill
                label="Day 7 · Teacher window"
                phaseKey="teacher_window"
                {...teacherWindowPhaseState(phase)}
              />
              <PhasePill
                label="Day 21 · Admin window"
                phaseKey="admin_window"
                {...adminWindowPhaseState(phase)}
              />
              <PhasePill
                label="Day 28 · Finalized"
                phaseKey="finalized"
                {...finalizedPhaseState(phase)}
              />
            </ol>

            {!isTerminal ? (
              <div className="mgmt-syc-countdowns">
                <CountdownBlock
                  label="Student lockout"
                  date={closure.student_lockout_at}
                  days={days_to.student_lockout}
                />
                <CountdownBlock
                  label="Teacher lockout"
                  date={closure.teacher_lockout_at}
                  days={days_to.teacher_lockout}
                />
                <CountdownBlock
                  label="Auto-finalize"
                  date={closure.finalize_at}
                  days={days_to.finalize}
                  final
                />
              </div>
            ) : null}

            {isPaused ? (
              <div className="mgmt-syc-alert mgmt-syc-alert--info">
                <i className="bi bi-pause-circle-fill" aria-hidden="true" />
                Closure is paused. Transitions and notifications are frozen.
                {closure.paused_by ? ` Paused by ${closure.paused_by}` : ''}
                {closure.paused_at ? ` at ${formatDateTime(closure.paused_at)}` : ''}.
              </div>
            ) : null}
            {phase === 'cancelled' ? (
              <div className="mgmt-syc-alert mgmt-syc-alert--warning">
                <i className="bi bi-x-octagon-fill" aria-hidden="true" />
                Closure was cancelled
                {closure.cancelled_by ? ` by ${closure.cancelled_by}` : ''}
                {closure.cancelled_at ? ` on ${formatDateLong(closure.cancelled_at)}` : ''}.
                {closure.cancellation_reason ? (
                  <>
                    <br />
                    <em>{closure.cancellation_reason}</em>
                  </>
                ) : null}
              </div>
            ) : null}
            {isFinalized ? (
              <div className="mgmt-syc-alert mgmt-syc-alert--success">
                <i className="bi bi-check-circle-fill" aria-hidden="true" />
                Closure finalized on{' '}
                {closure.finalized_at
                  ? formatDateTime(closure.finalized_at)
                  : formatDateLong(closure.finalize_at)}
                . The school year is archived.
              </div>
            ) : null}
          </section>

          {isFinalized && data.next_year_suggestion ? (
            <NextYearSection
              suggestion={data.next_year_suggestion}
              exists={data.next_year_exists}
              busy={busy}
              onCreate={async (body) => {
                setBusy(true)
                try {
                  const res = await createNextSchoolYear(body)
                  showMessage(res.message)
                  void load()
                } catch (e) {
                  showMessage(e instanceof Error ? e.message : 'Could not create year')
                } finally {
                  setBusy(false)
                }
              }}
            />
          ) : null}

          <div className="mgmt-syc-grid">
            <div className="mgmt-syc-col">
              {checklist ? (
                <section className="mgmt-syc-card">
                  <h2 className="mgmt-syc-card-title">
                    <i className="bi bi-clipboard-check" aria-hidden="true" />
                    Pre-finalization checklist
                  </h2>
                  <p className="mgmt-syc-card-sub">
                    {checklist.students_total} student{checklist.students_total !== 1 ? 's' : ''} across{' '}
                    {checklist.classes_total} class{checklist.classes_total !== 1 ? 'es' : ''}.{' '}
                    {checklist.classes_without_q4_grades.length > 0
                      ? `${checklist.classes_without_q4_grades.length} class${checklist.classes_without_q4_grades.length !== 1 ? 'es' : ''} still have missing Q4 grades.`
                      : 'No outstanding gradebook gaps detected.'}
                  </p>
                  {checklist.classes_without_q4_grades.length > 0 ? (
                    <ul className="mgmt-syc-checklist">
                      {checklist.classes_without_q4_grades.map((c) => (
                        <li key={`${c.class_name}-${c.subject}`}>
                          <span className="mgmt-syc-checklist-name">{c.class_name}</span>
                          <span className="mgmt-syc-checklist-subject">{c.subject}</span>
                          <span className="mgmt-syc-checklist-stat">
                            {c.missing_student_count} / {c.roster_size} student
                            {c.roster_size !== 1 ? 's' : ''} missing Q4
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </section>
              ) : null}

              {finalize_stats ? (
                <section className="mgmt-syc-card">
                  <h2 className="mgmt-syc-card-title">
                    <i className="bi bi-graph-up" aria-hidden="true" />
                    Finalize results
                  </h2>
                  <dl className="mgmt-syc-stat-grid">
                    <div>
                      <dt>Triggered by</dt>
                      <dd>{String(finalize_stats.triggered_by ?? '—')}</dd>
                    </div>
                    <div>
                      <dt>Report cards saved</dt>
                      <dd>{String(finalize_stats.report_cards_ok ?? 0)}</dd>
                    </div>
                    <div>
                      <dt>Skipped</dt>
                      <dd>{String(finalize_stats.report_cards_skipped ?? 0)}</dd>
                    </div>
                    <div>
                      <dt>Errors</dt>
                      <dd>{String(finalize_stats.report_cards_errors ?? 0)}</dd>
                    </div>
                    <div>
                      <dt>Classes archived</dt>
                      <dd>{String(finalize_stats.classes_archived ?? 0)}</dd>
                    </div>
                    <div>
                      <dt>Students processed</dt>
                      <dd>{String(finalize_stats.students_processed ?? 0)}</dd>
                    </div>
                    {finalize_stats.promotion && typeof finalize_stats.promotion === 'object' ? (
                      <>
                        <div>
                          <dt>Promoted one grade</dt>
                          <dd>{String((finalize_stats.promotion as Record<string, unknown>).promoted ?? 0)}</dd>
                        </div>
                        <div>
                          <dt>Repeating (flag cleared)</dt>
                          <dd>{String((finalize_stats.promotion as Record<string, unknown>).repeating_cleared ?? 0)}</dd>
                        </div>
                        <div>
                          <dt>Skipped (12th / no grade)</dt>
                          <dd>{String((finalize_stats.promotion as Record<string, unknown>).skipped ?? 0)}</dd>
                        </div>
                        <div>
                          <dt>New portal accounts</dt>
                          <dd>{String((finalize_stats.promotion as Record<string, unknown>).provisioned_accounts ?? 0)}</dd>
                        </div>
                      </>
                    ) : null}
                  </dl>
                  {Array.isArray(finalize_stats.errors_sample) && finalize_stats.errors_sample.length > 0 ? (
                    <details className="mgmt-syc-errors">
                      <summary>Errors sample ({finalize_stats.errors_sample.length})</summary>
                      <ul>
                        {(finalize_stats.errors_sample as string[]).map((err) => (
                          <li key={err}>{err}</li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </section>
              ) : null}

              <section className="mgmt-syc-card">
                <div className="mgmt-syc-card-head">
                  <h2 className="mgmt-syc-card-title">
                    <i className="bi bi-shield-plus" aria-hidden="true" />
                    Extensions
                  </h2>
                  {!isTerminal ? (
                    <button
                      type="button"
                      className="mgmt-syc-btn mgmt-syc-btn--primary mgmt-syc-btn--sm"
                      onClick={() => setModal('extension')}
                    >
                      <i className="bi bi-plus-circle" aria-hidden="true" /> Grant extension
                    </button>
                  ) : null}
                </div>
                {extensions.length > 0 ? (
                  <ul className="mgmt-syc-ext-list">
                    {extensions.map((ext) => (
                      <ExtensionItem
                        key={ext.id}
                        ext={ext}
                        isTerminal={isTerminal}
                        onRevoke={async () => {
                          if (!window.confirm('Revoke this extension?')) return
                          setBusy(true)
                          try {
                            const res = await revokeClosureExtension(closureId, ext.id)
                            showMessage(res.message)
                            void load()
                          } catch (e) {
                            showMessage(e instanceof Error ? e.message : 'Revoke failed')
                          } finally {
                            setBusy(false)
                          }
                        }}
                      />
                    ))}
                  </ul>
                ) : (
                  <p className="mgmt-syc-empty">No extensions granted yet.</p>
                )}
              </section>
            </div>

            <div className="mgmt-syc-col">
              {!isTerminal ? (
                <section className="mgmt-syc-card">
                  <h2 className="mgmt-syc-card-title">
                    <i className="bi bi-sliders" aria-hidden="true" /> Controls
                  </h2>
                  <div className="mgmt-syc-controls">
                    {!isPaused ? (
                      <button
                        type="button"
                        className="mgmt-syc-btn mgmt-syc-btn--ghost"
                        disabled={busy}
                        onClick={() => void act('pause')}
                      >
                        <i className="bi bi-pause-circle" aria-hidden="true" /> Pause workflow
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="mgmt-syc-btn mgmt-syc-btn--primary"
                        disabled={busy}
                        onClick={() => void act('resume')}
                      >
                        <i className="bi bi-play-circle" aria-hidden="true" /> Resume workflow
                      </button>
                    )}
                    <button
                      type="button"
                      className="mgmt-syc-btn mgmt-syc-btn--ghost"
                      disabled={busy}
                      onClick={() => setModal('postpone')}
                    >
                      <i className="bi bi-calendar-plus" aria-hidden="true" /> Postpone…
                    </button>
                    <button
                      type="button"
                      className="mgmt-syc-btn mgmt-syc-btn--ghost"
                      disabled={busy}
                      onClick={() => setModal('reset')}
                    >
                      <i className="bi bi-arrow-counterclockwise" aria-hidden="true" /> Restart clock…
                    </button>
                    <button
                      type="button"
                      className="mgmt-syc-btn mgmt-syc-btn--ghost"
                      disabled={busy}
                      onClick={() => setModal('advance')}
                    >
                      <i className="bi bi-skip-forward" aria-hidden="true" /> Advance phase…
                    </button>
                    {phase === 'admin_window' ? (
                      <button
                        type="button"
                        className="mgmt-syc-btn mgmt-syc-btn--danger"
                        disabled={busy}
                        onClick={() => setModal('finalize')}
                      >
                        <i className="bi bi-archive-fill" aria-hidden="true" /> Finalize now…
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="mgmt-syc-btn mgmt-syc-btn--danger mgmt-syc-btn--outline"
                      disabled={busy}
                      onClick={() => setModal('cancel')}
                    >
                      <i className="bi bi-x-octagon" aria-hidden="true" /> Cancel closure…
                    </button>
                  </div>
                </section>
              ) : null}

              {isFinalized ? (
                <section className="mgmt-syc-card">
                  <h2 className="mgmt-syc-card-title">
                    <i className="bi bi-arrow-counterclockwise" aria-hidden="true" /> Late corrections
                  </h2>
                  <p className="mgmt-syc-card-sub">
                    Reopening the closure re-activates the school year so admins can fix grades,
                    regenerate report cards, or unarchive a class. Use sparingly.
                  </p>
                  <button
                    type="button"
                    className="mgmt-syc-btn mgmt-syc-btn--ghost"
                    disabled={busy}
                    onClick={() => setModal('reopen')}
                  >
                    <i className="bi bi-unlock" aria-hidden="true" /> Reopen closure…
                  </button>
                </section>
              ) : null}

              <section className="mgmt-syc-card">
                <h2 className="mgmt-syc-card-title">
                  <i className="bi bi-list-ul" aria-hidden="true" /> Audit log
                </h2>
                {events.length > 0 ? (
                  <ol className="mgmt-syc-events">
                    {events.map((ev) => (
                      <li key={ev.id} className={`mgmt-syc-event mgmt-syc-event--${ev.event_type}`}>
                        <span className="mgmt-syc-event-time">
                          {ev.created_at ? formatAuditTime(ev.created_at) : '—'}
                        </span>
                        <span className="mgmt-syc-event-type">{ev.event_type.replace(/_/g, ' ')}</span>
                        <span className="mgmt-syc-event-actor">{ev.actor ?? ev.actor_label ?? 'system'}</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mgmt-syc-empty">No events recorded yet.</p>
                )}
              </section>
            </div>
          </div>
        </div>
      </div>

      <PostponeModal show={modal === 'postpone'} busy={busy} onClose={() => setModal(null)} onSubmit={(b) => void act('postpone', b)} />
      <ResetModal show={modal === 'reset'} busy={busy} onClose={() => setModal(null)} onSubmit={(b) => void act('reset-milestones', b)} />
      <AdvanceModal show={modal === 'advance'} phase={phase} busy={busy} onClose={() => setModal(null)} onSubmit={(b) => void act('advance', b)} />
      <FinalizeModal show={modal === 'finalize'} busy={busy} onClose={() => setModal(null)} onSubmit={(b) => void act('finalize-now', b)} />
      <CancelModal show={modal === 'cancel'} busy={busy} onClose={() => setModal(null)} onSubmit={(b) => void act('cancel', b)} />
      <ReopenModal show={modal === 'reopen'} busy={busy} onClose={() => setModal(null)} onSubmit={(b) => void act('reopen', b)} />
      <ExtensionModal
        show={modal === 'extension'}
        busy={busy}
        teachers={data.teachers}
        classes={data.classes}
        onClose={() => setModal(null)}
        onSubmit={async (body) => {
          setBusy(true)
          try {
            const res = await grantClosureExtension(closureId, body)
            showMessage(res.message)
            setModal(null)
            void load()
          } catch (e) {
            showMessage(e instanceof Error ? e.message : 'Grant failed')
          } finally {
            setBusy(false)
          }
        }}
      />
    </>
    </LegacyMgmtScope>
  )
}

function PhasePill({
  label,
  phaseKey,
  isDone,
  isCurrent,
}: {
  label: string
  phaseKey: string
  isDone: boolean
  isCurrent: boolean
}) {
  return (
    <li className={phaseStepClass(isDone, isCurrent)} data-phase={phaseKey}>
      <span className="mgmt-syc-phase-marker" aria-hidden="true" />
      <span className="mgmt-syc-phase-label">{label}</span>
    </li>
  )
}

function CountdownBlock({
  label,
  date,
  days,
  final,
}: {
  label: string
  date: string | null
  days: number
  final?: boolean
}) {
  return (
    <div className={`mgmt-syc-countdown${final ? ' mgmt-syc-countdown--final' : ''}`}>
      <span className="mgmt-syc-countdown-label">{label}</span>
      <span className="mgmt-syc-countdown-date">{formatDateLong(date)}</span>
      <span className="mgmt-syc-countdown-days">{daysUntilLabel(days)}</span>
    </div>
  )
}

function ExtensionItem({
  ext,
  isTerminal,
  onRevoke,
}: {
  ext: ClosureExtension
  isTerminal: boolean
  onRevoke: () => void
}) {
  const isUser = Boolean(ext.scope_user_id)
  return (
    <li className="mgmt-syc-ext-item">
      <div className="mgmt-syc-ext-target">
        {isUser ? (
          <>
            <i className="bi bi-person-fill" aria-hidden="true" />
            {ext.target_label} ({ext.for_role})
          </>
        ) : ext.scope_class_id ? (
          <>
            <i className="bi bi-easel-fill" aria-hidden="true" />
            {ext.target_label} ({ext.for_role})
          </>
        ) : (
          'Unknown scope'
        )}
      </div>
      <div className="mgmt-syc-ext-meta">
        Until <strong>{formatDateLong(ext.extended_until)}</strong>
        {ext.reason ? ` · ${ext.reason}` : ''}
        {ext.granted_by ? ` · by ${ext.granted_by}` : ''}
      </div>
      {!isTerminal ? (
        <div className="mgmt-syc-ext-revoke">
          <button type="button" className="mgmt-syc-btn mgmt-syc-btn--ghost mgmt-syc-btn--sm" onClick={onRevoke}>
            <i className="bi bi-x-circle" aria-hidden="true" /> Revoke
          </button>
        </div>
      ) : null}
    </li>
  )
}

function NextYearSection({
  suggestion,
  exists,
  busy,
  onCreate,
}: {
  suggestion: NonNullable<ClosureDashboardResponse['next_year_suggestion']>
  exists: boolean
  busy: boolean
  onCreate: (body: {
    name: string
    start_date: string
    end_date: string
    is_active?: boolean
    auto_generate_quarters?: boolean
  }) => void
}) {
  const [name, setName] = useState(suggestion.name)
  const [start, setStart] = useState(suggestion.start_date)
  const [end, setEnd] = useState(suggestion.end_date)

  return (
    <section className="mgmt-syc-next-year">
      <header className="mgmt-syc-next-year-head">
        <div>
          <p className="mgmt-syc-eyebrow">What&apos;s next</p>
          <h2 className="mgmt-syc-section-title">
            <i className="bi bi-arrow-right-circle-fill" aria-hidden="true" />
            Start the next school year
          </h2>
          <p className="mgmt-syc-section-desc">
            {exists ? (
              <span className="text-success">
                <i className="bi bi-check2-circle" aria-hidden="true" />
                School year <strong>{suggestion.name}</strong> already exists. Activate it from{' '}
                <Link to="/management/school-years">Settings → School Years</Link> if it isn&apos;t active yet.
              </span>
            ) : (
              <>
                The closed year ({suggestion.prior_year_name}) has been archived and students have been
                promoted. Create the next year below — quarters will be generated automatically and
                it&apos;ll be set active immediately.
              </>
            )}
          </p>
        </div>
      </header>

      {!exists ? (
        <form
          className="mgmt-syc-next-year-form"
          onSubmit={(e) => {
            e.preventDefault()
            onCreate({ name, start_date: start, end_date: end, is_active: true, auto_generate_quarters: true })
          }}
        >
          <p className="mgmt-syc-form-hint">
            <i className="bi bi-info-circle" aria-hidden="true" />
            Dates are pre-filled by adding one calendar year to {suggestion.prior_year_name}&apos;s start
            &amp; end dates ({formatDateLong(suggestion.prior_year_start)} →{' '}
            {formatDateLong(suggestion.prior_year_end)}). Edit them below if your calendar shifts
            year-to-year — quarters will be auto-generated from whatever range you set.
          </p>
          <div className="mgmt-syc-next-year-grid">
            <div className="mgmt-syc-form-row">
              <label className="mgmt-syc-label" htmlFor="next_year_name">
                Year name
              </label>
              <input
                className="mgmt-syc-input"
                type="text"
                id="next_year_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="mgmt-syc-form-row">
              <label className="mgmt-syc-label" htmlFor="next_year_start">
                Start date
              </label>
              <input
                className="mgmt-syc-input"
                type="date"
                id="next_year_start"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </div>
            <div className="mgmt-syc-form-row">
              <label className="mgmt-syc-label" htmlFor="next_year_end">
                End date
              </label>
              <input
                className="mgmt-syc-input"
                type="date"
                id="next_year_end"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </div>
          </div>
          <ul className="mgmt-syc-next-year-checks">
            <li>
              <i className="bi bi-check2-circle" aria-hidden="true" /> Sets the new year as active
              (deactivates {suggestion.prior_year_name}&apos;s archived state — already done).
            </li>
            <li>
              <i className="bi bi-check2-circle" aria-hidden="true" /> Auto-generates Q1–Q4 academic
              periods evenly across the year.
            </li>
            <li>
              <i className="bi bi-info-circle" aria-hidden="true" /> You&apos;ll still need to set up
              classes (Settings → Classes) and roster the students into them.
            </li>
          </ul>
          <div className="mgmt-syc-actions">
            <Link to="/management/school-years" className="mgmt-syc-btn mgmt-syc-btn--ghost">
              <i className="bi bi-gear" aria-hidden="true" /> Open full Settings instead
            </Link>
            <button type="submit" className="mgmt-syc-btn mgmt-syc-btn--primary" disabled={busy}>
              <i className="bi bi-calendar-plus" aria-hidden="true" /> Create {name}
            </button>
          </div>
        </form>
      ) : null}
    </section>
  )
}

function formatAuditTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function PostponeModal({
  show,
  busy,
  onClose,
  onSubmit,
}: {
  show: boolean
  busy: boolean
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => void
}) {
  const [days, setDays] = useState(7)
  const [reason, setReason] = useState('')
  return (
    <LegacyBootstrapModal show={show} onClose={onClose} title="Postpone closure">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit({ days, reason: reason.trim() || undefined })
        }}
      >
        <div className="modal-body">
          <p>Slides every milestone forward by N days. Useful for snow days or last-minute scheduling changes.</p>
          <div className="mb-3">
            <label className="form-label" htmlFor="postpone_days">
              Days to postpone
            </label>
            <input
              className="form-control"
              type="number"
              id="postpone_days"
              min={1}
              max={90}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              required
            />
          </div>
          <div className="mb-3">
            <label className="form-label" htmlFor="postpone_reason">
              Reason (optional)
            </label>
            <input
              className="form-control"
              type="text"
              id="postpone_reason"
              placeholder="e.g. Extra snow days extended Q4"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Postpone
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function ResetModal({
  show,
  busy,
  onClose,
  onSubmit,
}: {
  show: boolean
  busy: boolean
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => void
}) {
  const [reason, setReason] = useState('')
  return (
    <LegacyBootstrapModal show={show} onClose={onClose} title="Restart the lockout clock">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit({ reason: reason.trim() || undefined })
        }}
      >
        <div className="modal-body">
          <p>
            Recomputes the three milestone dates so they run from <strong>today</strong>:
          </p>
          <ul>
            <li>Student lockout = today + 7 days</li>
            <li>Teacher lockout = today + 21 days</li>
            <li>Auto-finalize = today + 28 days</li>
          </ul>
          <p>
            If the workflow has already advanced past the student window (e.g. you scheduled with a
            Day&nbsp;0 that was in the past, so students were locked out immediately), this also
            rewinds the phase to <em>Student window</em> and clears the student/teacher lockout stamps
            so they regain access.
          </p>
          <div className="mb-3">
            <label className="form-label" htmlFor="reset_reason">
              Reason (optional)
            </label>
            <input
              className="form-control"
              type="text"
              id="reset_reason"
              placeholder="e.g. Scheduled with old end-date; resetting so students get their week"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Restart clock
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function AdvanceModal({
  show,
  phase,
  busy,
  onClose,
  onSubmit,
}: {
  show: boolean
  phase: string
  busy: boolean
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => void
}) {
  const options = [
    phase === 'scheduled'
      ? { value: 'student_window', label: 'Student window (notify + open submissions)' }
      : null,
    ['scheduled', 'student_window'].includes(phase)
      ? { value: 'teacher_window', label: 'Teacher window (lock students)' }
      : null,
    ['scheduled', 'student_window', 'teacher_window'].includes(phase)
      ? { value: 'admin_window', label: 'Admin window (lock teachers)' }
      : null,
  ].filter(Boolean) as { value: string; label: string }[]
  const [target, setTarget] = useState(options[0]?.value ?? '')

  return (
    <LegacyBootstrapModal show={show} onClose={onClose} title="Advance to next phase">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit({ target_phase: target })
        }}
      >
        <div className="modal-body">
          <p>
            Force a phase transition before its scheduled date. Use only when you need to lock
            students or teachers out early.
          </p>
          <div className="mb-3">
            <label className="form-label" htmlFor="target_phase">
              Phase
            </label>
            <select
              className="form-select"
              id="target_phase"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              required
            >
              {options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Advance
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function FinalizeModal({
  show,
  busy,
  onClose,
  onSubmit,
}: {
  show: boolean
  busy: boolean
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => void
}) {
  const [confirm, setConfirm] = useState('')
  return (
    <LegacyBootstrapModal show={show} onClose={onClose} title="Finalize now">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit({ confirm })
        }}
      >
        <div className="modal-body">
          <p className="text-danger">
            <strong>This is irreversible.</strong> The system will:
          </p>
          <ul>
            <li>Generate official Q1–Q4 report cards for every enrolled student.</li>
            <li>Mark all classes / enrollments / assignments in this year inactive.</li>
            <li>
              Promote students one grade level (skipping <em>is_repeating</em> and 12th).
            </li>
            <li>Deactivate the school year.</li>
          </ul>
          <p>
            You can <em>Reopen</em> this closure later if grade corrections are needed, but report
            cards will need to be regenerated.
          </p>
          <div className="mb-3">
            <label className="form-label" htmlFor="finalize_confirm">
              Type <code>FINALIZE NOW</code> to confirm
            </label>
            <input
              className="form-control"
              type="text"
              id="finalize_confirm"
              autoComplete="off"
              placeholder="FINALIZE NOW"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-danger" disabled={busy}>
            Finalize closure
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function CancelModal({
  show,
  busy,
  onClose,
  onSubmit,
}: {
  show: boolean
  busy: boolean
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => void
}) {
  const [reason, setReason] = useState('')
  const [confirm, setConfirm] = useState('')
  return (
    <LegacyBootstrapModal show={show} onClose={onClose} title="Cancel closure workflow">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit({ reason: reason.trim() || undefined, confirm })
        }}
      >
        <div className="modal-body">
          <p>
            Aborts the workflow. The school year continues as normal — no archival, no
            notifications. The closure record stays for auditing.
          </p>
          <div className="mb-3">
            <label className="form-label" htmlFor="cancel_reason">
              Reason
            </label>
            <input
              className="form-control"
              type="text"
              id="cancel_reason"
              placeholder="e.g. End-of-year postponed by one month; will reschedule"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <div className="mb-3">
            <label className="form-label" htmlFor="cancel_confirm">
              Type <code>CANCEL</code> to confirm
            </label>
            <input
              className="form-control"
              type="text"
              id="cancel_confirm"
              autoComplete="off"
              placeholder="CANCEL"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Back
          </button>
          <button type="submit" className="btn btn-danger" disabled={busy}>
            Cancel closure
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function ReopenModal({
  show,
  busy,
  onClose,
  onSubmit,
}: {
  show: boolean
  busy: boolean
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => void
}) {
  const [reason, setReason] = useState('')
  const [confirm, setConfirm] = useState('')
  return (
    <LegacyBootstrapModal show={show} onClose={onClose} title="Reopen closure">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit({ reason: reason.trim() || undefined, confirm })
        }}
      >
        <div className="modal-body">
          <p>
            Re-activates the school year so directors/admins can make late corrections. Closure
            phase moves back to Admin window.
          </p>
          <div className="mb-3">
            <label className="form-label" htmlFor="reopen_reason">
              Reason
            </label>
            <input
              className="form-control"
              type="text"
              id="reopen_reason"
              placeholder="e.g. Late grade correction for student X"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <div className="mb-3">
            <label className="form-label" htmlFor="reopen_confirm">
              Type <code>REOPEN</code> to confirm
            </label>
            <input
              className="form-control"
              type="text"
              id="reopen_confirm"
              autoComplete="off"
              placeholder="REOPEN"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Back
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Reopen closure
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}

function ExtensionModal({
  show,
  busy,
  teachers,
  classes,
  onClose,
  onSubmit,
}: {
  show: boolean
  busy: boolean
  teachers: ClosureDashboardResponse['teachers']
  classes: ClosureDashboardResponse['classes']
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => void
}) {
  const [scope, setScope] = useState<'user' | 'class'>('user')
  const [targetUserId, setTargetUserId] = useState('')
  const [targetClassId, setTargetClassId] = useState('')
  const [forRole, setForRole] = useState('both')
  const [extendedUntil, setExtendedUntil] = useState('')
  const [reason, setReason] = useState('')

  return (
    <LegacyBootstrapModal show={show} onClose={onClose} title="Grant deadline extension">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit({
            scope,
            target_user_id: scope === 'user' ? Number(targetUserId) : undefined,
            target_class_id: scope === 'class' ? Number(targetClassId) : undefined,
            for_role: forRole,
            extended_until: extendedUntil,
            reason: reason.trim() || undefined,
          })
        }}
      >
        <div className="modal-body">
          <div className="mb-3">
            <label className="form-label">Scope</label>
            <div className="form-check">
              <input
                className="form-check-input"
                type="radio"
                name="ext_scope"
                id="ext_scope_user"
                checked={scope === 'user'}
                onChange={() => setScope('user')}
              />
              <label className="form-check-label" htmlFor="ext_scope_user">
                Specific teacher or student
              </label>
            </div>
            <div className="form-check">
              <input
                className="form-check-input"
                type="radio"
                name="ext_scope"
                id="ext_scope_class"
                checked={scope === 'class'}
                onChange={() => setScope('class')}
              />
              <label className="form-check-label" htmlFor="ext_scope_class">
                Whole class (teacher + students)
              </label>
            </div>
          </div>

          {scope === 'user' ? (
            <div className="mb-3" id="ext_user_picker">
              <label className="form-label" htmlFor="target_user_id">
                Person
              </label>
              <select
                className="form-select"
                id="target_user_id"
                value={targetUserId}
                onChange={(e) => setTargetUserId(e.target.value)}
                required
              >
                <option value="">— Select —</option>
                <optgroup label="Teachers / Staff">
                  {teachers.map((t) =>
                    t.user_id ? (
                      <option key={t.id} value={t.user_id}>
                        {t.name} ({t.username})
                      </option>
                    ) : null,
                  )}
                </optgroup>
              </select>
              <small className="form-text text-muted">
                For per-student extensions, use the student&apos;s user account id (or grant per-class).
              </small>
            </div>
          ) : (
            <div className="mb-3" id="ext_class_picker">
              <label className="form-label" htmlFor="target_class_id">
                Class
              </label>
              <select
                className="form-select"
                id="target_class_id"
                value={targetClassId}
                onChange={(e) => setTargetClassId(e.target.value)}
                required
              >
                <option value="">— Select —</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} — {c.subject}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="mb-3">
            <label className="form-label" htmlFor="ext_for_role">
              Applies to
            </label>
            <select
              className="form-select"
              id="ext_for_role"
              value={forRole}
              onChange={(e) => setForRole(e.target.value)}
            >
              <option value="both">Both student & teacher lockout</option>
              <option value="student">Student lockout only</option>
              <option value="teacher">Teacher lockout only</option>
            </select>
          </div>

          <div className="mb-3">
            <label className="form-label" htmlFor="ext_until">
              Extend until
            </label>
            <input
              className="form-control"
              type="date"
              id="ext_until"
              value={extendedUntil}
              onChange={(e) => setExtendedUntil(e.target.value)}
              required
            />
          </div>

          <div className="mb-3">
            <label className="form-label" htmlFor="ext_reason">
              Reason
            </label>
            <input
              className="form-control"
              type="text"
              id="ext_reason"
              placeholder="e.g. Teacher on medical leave through June 30"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Grant extension
          </button>
        </div>
      </form>
    </LegacyBootstrapModal>
  )
}
