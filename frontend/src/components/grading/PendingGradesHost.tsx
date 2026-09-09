import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { fetchPendingGrades, PENDING_GRADES_OPEN_EVENT } from '../../api/pendingGrades'
import type { PendingGradeAssignment } from '../../types/pendingGrades'

const SNOOZE_KEY = 'clara:pendingGradesToastSnoozeUntil'
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

function popupDisabledForPath(pathname: string) {
  if (pathname.includes('/grade')) return true
  if (pathname.includes('/take-quiz')) return true
  if (/\/assignments(\/|$)/.test(pathname) && pathname.includes('/individual/')) return true
  if (/\/assignments(\/|$)/.test(pathname) && pathname.includes('/group/')) return true
  if (pathname.includes('/assignments-and-grades/') && pathname.includes('/grade')) return true
  return false
}

function formatDue(iso: string | null) {
  if (!iso) return 'No due date'
  try {
    return new Date(iso).toLocaleDateString()
  } catch {
    return iso
  }
}

type Props = {
  scope: 'management' | 'teacher'
}

export function PendingGradesHost({ scope }: Props) {
  const location = useLocation()
  const [assignments, setAssignments] = useState<PendingGradeAssignment[]>([])
  const [totalPending, setTotalPending] = useState(0)
  const [yearActive, setYearActive] = useState(true)
  const [schoolwide, setSchoolwide] = useState(scope === 'management')
  const [toastVisible, setToastVisible] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const disabled = popupDisabledForPath(location.pathname)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchPendingGrades(scope)
      const active = Boolean(data.has_active_school_year)
      setYearActive(active)
      setSchoolwide(Boolean(data.schoolwide))
      const rows = active ? data.assignments || [] : []
      setAssignments(rows)
      setTotalPending(active ? data.total_pending || 0 : 0)
      const hasPending = active && (data.total_pending || 0) > 0
      setToastVisible(hasPending && !isSnoozed() && !disabled)
      if (!active) setModalOpen(false)
    } catch {
      setAssignments([])
      setTotalPending(0)
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
    if (totalPending > 0 && !isSnoozed() && !modalOpen) {
      setToastVisible(true)
    }
  }, [disabled, yearActive, totalPending, location.pathname, modalOpen])

  useEffect(() => {
    const onOpen = () => {
      if (!yearActive) return
      setModalOpen(true)
      setToastVisible(false)
      void load()
    }
    window.addEventListener(PENDING_GRADES_OPEN_EVENT, onOpen)
    return () => window.removeEventListener(PENDING_GRADES_OPEN_EVENT, onOpen)
  }, [yearActive, load])

  useEffect(() => {
    if (!modalOpen || !yearActive) return
    void load()
  }, [modalOpen, yearActive, load])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return assignments
    return assignments.filter(
      (a) =>
        a.title.toLowerCase().includes(q) ||
        a.class_name.toLowerCase().includes(q) ||
        (a.assignment_type || '').toLowerCase().includes(q),
    )
  }, [assignments, search])

  if (!yearActive) return null
  if (loading && assignments.length === 0 && !modalOpen) return null

  return (
    <>
      {toastVisible && totalPending > 0 && !modalOpen ? (
        <div className="pointer-events-none fixed bottom-[15.5rem] right-4 z-[1054] w-[min(22rem,calc(100vw-2rem))]">
          <div
            className="pointer-events-auto overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-black/5"
            role="alert"
          >
            <div className="flex items-center justify-between bg-gradient-to-r from-amber-600 to-orange-600 px-4 py-3 text-white">
              <strong className="flex items-center gap-2 text-sm">
                <i className="bi bi-pencil-square" aria-hidden />
                Grades pending
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
                  {totalPending} submission{totalPending === 1 ? '' : 's'}
                </strong>{' '}
                across {assignments.length} assignment{assignments.length === 1 ? '' : 's'}{' '}
                {schoolwide ? 'school-wide' : 'in your classes'} awaiting a grade.
              </p>
              <button
                type="button"
                className="w-full rounded-xl bg-amber-600 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-700"
                onClick={() => {
                  setModalOpen(true)
                  setToastVisible(false)
                }}
              >
                Review pending grades
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {modalOpen ? (
        <div className="fixed inset-0 z-[1060] flex items-end justify-center bg-black/40 p-3 sm:items-center">
          <div
            className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="pending-grades-title"
          >
            <div className="flex items-start justify-between gap-3 bg-gradient-to-r from-amber-600 to-orange-600 px-5 py-4 text-white">
              <div>
                <h2 id="pending-grades-title" className="text-lg font-extrabold">
                  Pending grades
                </h2>
                <p className="text-sm text-white/90">
                  {totalPending} submission{totalPending === 1 ? '' : 's'} waiting ·{' '}
                  {schoolwide ? 'All classes' : 'Your classes'}
                </p>
              </div>
              <button
                type="button"
                className="rounded-lg bg-white/15 px-2 py-1 text-white hover:bg-white/25"
                aria-label="Close"
                onClick={() => setModalOpen(false)}
              >
                <i className="bi bi-x-lg" aria-hidden />
              </button>
            </div>

            <div className="border-b border-slate-100 px-5 py-3">
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by assignment or class…"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              />
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
              {filtered.length === 0 ? (
                <p className="py-8 text-center text-sm text-hub-muted">
                  {totalPending === 0 ? 'All caught up — nothing awaiting a grade.' : 'No matches.'}
                </p>
              ) : (
                <ul className="space-y-2">
                  {filtered.map((row) => (
                    <li
                      key={`${row.is_group ? 'g' : 'i'}-${row.id}`}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold text-hub-text">{row.title}</p>
                        <p className="text-xs text-hub-muted">
                          {row.class_name} · {row.is_group ? 'Group' : 'Individual'} · Due{' '}
                          {formatDue(row.due_date)}
                        </p>
                        <p className="mt-1 text-xs font-semibold text-amber-800">
                          {row.pending_count} awaiting grade
                        </p>
                      </div>
                      <Link
                        to={row.grade_url}
                        className="inline-flex items-center gap-1 rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                        onClick={() => setModalOpen(false)}
                      >
                        <i className="bi bi-pencil-square" aria-hidden />
                        Grade
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
