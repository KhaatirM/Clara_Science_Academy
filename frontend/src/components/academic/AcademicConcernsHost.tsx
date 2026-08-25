import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import {
  ACADEMIC_CONCERNS_OPEN_EVENT,
  fetchAcademicConcernStudent,
  fetchAcademicConcerns,
} from '../../api/academicConcerns'
import type {
  AcademicConcernAlert,
  AcademicConcernAssignmentItem,
  AcademicConcernStudentDetailsResponse,
} from '../../types/academicConcerns'

const SNOOZE_KEY = 'clara:academicConcernsToastSnoozeUntil'
const SNOOZE_MS = 5 * 60 * 1000

function isSnoozed() {
  try {
    const until = Number(localStorage.getItem(SNOOZE_KEY) || '0')
    return Boolean(until && Date.now() < until)
  } catch {
    return false
  }
}

function snooze() {
  try {
    localStorage.setItem(SNOOZE_KEY, String(Date.now() + SNOOZE_MS))
  } catch {
    /* ignore */
  }
}

function gradeLabel(level: number | null | undefined) {
  if (level == null) return '—'
  if (level === 0) return 'Kindergarten'
  if (level === 1) return '1st'
  if (level === 2) return '2nd'
  if (level === 3) return '3rd'
  return `${level}th`
}

function popupDisabledForPath(pathname: string) {
  if (pathname.includes('/report-cards')) return true
  if (/\/assignments(\/|$)/.test(pathname) && pathname.includes('class')) return true
  return false
}

type Props = {
  scope: 'management' | 'teacher'
}

export function AcademicConcernsHost({ scope }: Props) {
  const location = useLocation()
  const [alerts, setAlerts] = useState<AcademicConcernAlert[]>([])
  const [failingCount, setFailingCount] = useState(0)
  const [overdueCount, setOverdueCount] = useState(0)
  const [schoolwide, setSchoolwide] = useState(scope === 'management')
  const [schoolYearName, setSchoolYearName] = useState<string | null>(null)
  const [yearActive, setYearActive] = useState(true)
  const [toastVisible, setToastVisible] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [detailsById, setDetailsById] = useState<
    Record<number, AcademicConcernStudentDetailsResponse['student'] | 'loading' | 'error'>
  >({})

  const disabled = popupDisabledForPath(location.pathname)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchAcademicConcerns(scope)
      const active = Boolean(data.has_active_school_year)
      setYearActive(active)
      setSchoolYearName(data.school_year?.name || null)
      setAlerts(active ? data.alerts || [] : [])
      setFailingCount(active ? data.failing_count || 0 : 0)
      setOverdueCount(active ? data.overdue_count || 0 : 0)
      setSchoolwide(Boolean(data.schoolwide))
      const hasAlerts = active && (data.alerts || []).length > 0
      setToastVisible(hasAlerts && !isSnoozed() && !disabled)
      if (!active) setModalOpen(false)
    } catch {
      setAlerts([])
      setYearActive(false)
      setToastVisible(false)
      setModalOpen(false)
    } finally {
      setLoading(false)
    }
  }, [scope, disabled])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (disabled || !yearActive) {
      setToastVisible(false)
      return
    }
    if (alerts.length > 0 && !isSnoozed() && !modalOpen) {
      setToastVisible(true)
    }
  }, [disabled, yearActive, alerts.length, location.pathname, modalOpen])

  useEffect(() => {
    const onOpen = () => {
      if (!yearActive) return
      setModalOpen(true)
      setToastVisible(false)
      setDetailsById({})
      void load()
    }
    window.addEventListener(ACADEMIC_CONCERNS_OPEN_EVENT, onOpen)
    return () => window.removeEventListener(ACADEMIC_CONCERNS_OPEN_EVENT, onOpen)
  }, [yearActive, load])

  // Refetch hub list whenever the modal opens so grade fixes show up immediately.
  useEffect(() => {
    if (!modalOpen || !yearActive) return
    setDetailsById({})
    void load()
  }, [modalOpen, yearActive, load])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return alerts.filter((a) => {
      if (typeFilter === 'failing' && !(a.failing_count > 0)) return false
      if (typeFilter === 'not_submitted' && !(a.not_submitted_count > 0)) return false
      if (typeFilter === 'overdue' && !(a.overdue_count > 0)) return false
      if (!q) return true
      return (
        a.student_name.toLowerCase().includes(q) ||
        (a.classes_label || '').toLowerCase().includes(q) ||
        (a.enrolled_class_names || []).some((n) => n.toLowerCase().includes(q))
      )
    })
  }, [alerts, search, typeFilter])

  async function expandStudent(studentId: number) {
    if (expandedId === studentId) {
      setExpandedId(null)
      return
    }
    setExpandedId(studentId)
    setDetailsById((prev) => ({ ...prev, [studentId]: 'loading' }))
    try {
      const res = await fetchAcademicConcernStudent(studentId, scope)
      if (!res.success || !res.student) {
        setDetailsById((prev) => ({ ...prev, [studentId]: 'error' }))
        return
      }
      setDetailsById((prev) => ({ ...prev, [studentId]: res.student }))
    } catch {
      setDetailsById((prev) => ({ ...prev, [studentId]: 'error' }))
    }
  }

  if (!yearActive) return null
  if (loading && alerts.length === 0) return null

  return (
    <>
      {toastVisible && alerts.length > 0 && !modalOpen ? (
        <div className="pointer-events-none fixed bottom-[4.75rem] right-4 z-[1055] w-[min(22rem,calc(100vw-2rem))]">
          <div
            className="pointer-events-auto overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-black/5"
            role="alert"
          >
            <div className="flex items-center justify-between bg-gradient-to-r from-red-600 to-red-700 px-4 py-3 text-white">
              <strong className="flex items-center gap-2 text-sm">
                <i className="bi bi-exclamation-triangle-fill" aria-hidden />
                Academic alert
              </strong>
              <button
                type="button"
                className="text-white/90 hover:text-white"
                aria-label="Dismiss"
                onClick={() => {
                  snooze()
                  setToastVisible(false)
                }}
              >
                <i className="bi bi-x-lg" aria-hidden />
              </button>
            </div>
            <div className="px-4 py-3">
              <p className="mb-3 text-sm text-slate-800">
                <strong>
                  {alerts.length} student{alerts.length === 1 ? '' : 's'}
                </strong>{' '}
                {alerts.length === 1 ? 'has' : 'have'} a GPA below 2.00 (
                {schoolwide ? 'school-wide' : 'in your classes'}
                {schoolYearName ? ` · ${schoolYearName}` : ''}).
              </p>
              <button
                type="button"
                className="inline-flex w-full items-center justify-center gap-1.5 rounded-full bg-teal-700 px-3 py-2.5 text-sm font-bold text-white hover:bg-teal-800"
                onClick={() => {
                  setModalOpen(true)
                  setToastVisible(false)
                  setDetailsById({})
                }}
              >
                <i className="bi bi-clipboard-data" aria-hidden />
                Review concerns
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {modalOpen ? (
        <div
          className="fixed inset-0 z-[1100] flex items-center justify-center bg-slate-900/50 p-4"
          onClick={() => {
            setModalOpen(false)
            if (alerts.length > 0 && !isSnoozed() && !disabled) setToastVisible(true)
          }}
          role="presentation"
        >
          <div
            className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="academic-concerns-title"
          >
            <div className="bg-gradient-to-r from-red-600 to-red-700 px-5 py-4 text-white">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15 text-xl">
                    <i className="bi bi-exclamation-triangle-fill" aria-hidden />
                  </span>
                  <div>
                    <p className="mb-0 text-xs font-semibold uppercase tracking-wide text-white/80">
                      Performance alerts
                    </p>
                    <h2 id="academic-concerns-title" className="mb-1 text-lg font-bold">
                      Student academic concerns
                    </h2>
                    <p className="mb-0 text-sm text-white/85">
                      {schoolwide
                        ? 'Students with school-wide GPA below 2.00 — expand a card for assignments by class.'
                        : 'Students with GPA below 2.00 in your classes — expand a card for assignments by class.'}
                      {schoolYearName ? ` Active year: ${schoolYearName}.` : ''}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="text-white/85 hover:text-white"
                  aria-label="Close"
                  onClick={() => {
                    setModalOpen(false)
                    if (alerts.length > 0 && !isSnoozed() && !disabled) setToastVisible(true)
                  }}
                >
                  <i className="bi bi-x-lg" aria-hidden />
                </button>
              </div>
            </div>

            <div className="grid gap-3 border-b border-slate-100 bg-slate-50 px-5 py-4 sm:grid-cols-3">
              <Insight value={alerts.length} label="GPA below 2.00" tone="warning" icon="bi-people-fill" />
              <Insight value={failingCount} label="Failing assignments" tone="danger" icon="bi-x-circle-fill" />
              <Insight value={overdueCount} label="Past due date" tone="info" icon="bi-clock-history" />
            </div>

            <div className="flex flex-wrap gap-2 border-b border-slate-100 px-5 py-3">
              <input
                className="min-w-[12rem] flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm"
                placeholder="Search student or class…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="">All alert types</option>
                <option value="failing">Failing only</option>
                <option value="not_submitted">Missing / not submitted</option>
                <option value="overdue">Past due only</option>
              </select>
            </div>

            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
              {filtered.length === 0 ? (
                <p className="py-10 text-center text-sm text-hub-muted">No matching concerns.</p>
              ) : (
                filtered.map((alert) => {
                  const open = expandedId === alert.student_user_id
                  const details = detailsById[alert.student_user_id]
                  return (
                    <article
                      key={alert.student_user_id}
                      className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
                    >
                      <button
                        type="button"
                        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
                        onClick={() => void expandStudent(alert.student_user_id)}
                        aria-expanded={open}
                      >
                        <div>
                          <h3 className="mb-1 text-base font-bold text-slate-900">
                            {alert.student_name}
                          </h3>
                          <p className="mb-2 text-xs text-hub-muted">
                            {gradeLabel(alert.grade_level)} · {alert.classes_label || 'No classes'}
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            <Badge tone="danger">GPA {Number(alert.current_gpa).toFixed(2)}</Badge>
                            {alert.failing_count > 0 ? (
                              <Badge tone="danger">{alert.failing_count} failing</Badge>
                            ) : null}
                            {alert.not_submitted_count > 0 ? (
                              <Badge tone="warn">{alert.not_submitted_count} not submitted</Badge>
                            ) : null}
                            {alert.overdue_count > 0 ? (
                              <Badge tone="muted">{alert.overdue_count} past due</Badge>
                            ) : null}
                          </div>
                        </div>
                        <i
                          className={`bi bi-chevron-${open ? 'up' : 'down'} mt-1 text-slate-500`}
                          aria-hidden
                        />
                      </button>
                      {open ? (
                        <div className="border-t border-slate-100 bg-slate-50 px-4 py-3">
                          {details === 'loading' || details == null ? (
                            <p className="text-sm text-hub-muted">Loading assignment details…</p>
                          ) : details === 'error' ? (
                            <p className="text-sm text-red-700">Could not load details.</p>
                          ) : (
                            <StudentDetailsPanel student={details} />
                          )}
                        </div>
                      ) : null}
                    </article>
                  )
                })
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

function Insight({
  value,
  label,
  tone,
  icon,
}: {
  value: number
  label: string
  tone: 'warning' | 'danger' | 'info'
  icon: string
}) {
  const toneClass =
    tone === 'danger'
      ? 'bg-red-100 text-red-800'
      : tone === 'warning'
        ? 'bg-amber-100 text-amber-900'
        : 'bg-sky-100 text-sky-900'
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
      <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${toneClass}`}>
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-lg font-extrabold text-slate-900">{value}</div>
        <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function Badge({
  children,
  tone,
}: {
  children: ReactNode
  tone: 'danger' | 'warn' | 'muted'
}) {
  const cls =
    tone === 'danger'
      ? 'bg-red-100 text-red-800'
      : tone === 'warn'
        ? 'bg-amber-100 text-amber-900'
        : 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-bold ${cls}`}>
      {children}
    </span>
  )
}

function StudentDetailsPanel({
  student,
}: {
  student: NonNullable<AcademicConcernStudentDetailsResponse['student']>
}) {
  const classes = Object.entries(student.missing_assignments || {})
  return (
    <div className="space-y-3">
      <p className="mb-0 text-sm text-slate-700">
        Current GPA <strong>{Number(student.current_gpa).toFixed(2)}</strong>
        {student.hypothetical_gpa != null ? (
          <>
            {' '}
            · If caught up:{' '}
            <strong>{Number(student.hypothetical_gpa).toFixed(2)}</strong>
          </>
        ) : null}
      </p>
      {classes.length === 0 ? (
        <p className="mb-0 text-sm text-hub-muted">No flagged assignments in the detail payload.</p>
      ) : (
        classes.map(([className, items]) => (
          <div key={className}>
            <h4 className="mb-1.5 text-sm font-bold text-slate-900">{className}</h4>
            <ul className="space-y-1.5">
              {(items || []).map((item, idx) => (
                <AssignmentRow key={`${className}-${idx}`} item={item} />
              ))}
            </ul>
          </div>
        ))
      )}
    </div>
  )
}

function AssignmentRow({ item }: { item: AcademicConcernAssignmentItem }) {
  const title = item.assignment_title || item.title || 'Assignment'
  const status = item.status || '—'
  const submitted = (item.submission_status || 'not_submitted') === 'submitted'
  return (
    <li className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
      <div className="font-semibold text-slate-900">{title}</div>
      <div className="mt-1 flex flex-wrap gap-2 text-xs text-hub-muted">
        <span className="capitalize">{status.replace(/_/g, ' ')}</span>
        <span>{submitted ? 'Submitted' : 'Not submitted'}</span>
        {item.due_display || item.due_date ? (
          <span>Due {item.due_display || item.due_date}</span>
        ) : null}
        {item.score_display ? <span>{item.score_display}</span> : null}
      </div>
    </li>
  )
}
