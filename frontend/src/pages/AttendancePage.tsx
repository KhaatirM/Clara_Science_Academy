import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext, useSearchParams } from 'react-router-dom'

import {
  fetchAttendanceHub,
  markClassAllPresent,
  saveSchoolDayAttendance,
} from '../api/attendance'
import { AttendanceReportsPanel } from './AttendanceReportsPage'
import type { ManagementOutletContext } from '../types/layout'
import type {
  AttendanceHubResponse,
  ClassPeriodItem,
  SchoolDayStatus,
  SchoolDayStudentRow,
} from '../types/attendance'

type AttendanceTab = 'school-day' | 'class-period' | 'reports'

const STATUS_LABELS: Record<string, string> = {
  Present: 'Present',
  'Unexcused Absence': 'Absent',
  Late: 'Late',
  'Excused Absence': 'Excused',
}

const STATUS_STYLES: Record<string, { base: string; active: string }> = {
  Present: {
    base: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    active: 'border-emerald-600 bg-emerald-600 text-white shadow-sm',
  },
  'Unexcused Absence': {
    base: 'border-rose-200 bg-rose-50 text-rose-800',
    active: 'border-rose-600 bg-rose-600 text-white shadow-sm',
  },
  Late: {
    base: 'border-amber-200 bg-amber-50 text-amber-900',
    active: 'border-amber-500 bg-amber-500 text-white shadow-sm',
  },
  'Excused Absence': {
    base: 'border-sky-200 bg-sky-50 text-sky-800',
    active: 'border-sky-600 bg-sky-600 text-white shadow-sm',
  },
}

function localDateInputValue(d = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function StatCard({
  icon,
  value,
  label,
  featured,
}: {
  icon: string
  value: string | number
  label: string
  featured?: boolean
}) {
  return (
    <div
      className={[
        'flex items-start gap-3 rounded-2xl border p-4 shadow-sm',
        featured
          ? 'border-teal-200 bg-gradient-to-br from-teal-50 to-white'
          : 'border-white/90 bg-white/95',
      ].join(' ')}
      role="listitem"
    >
      <span
        className={[
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-base',
          featured ? 'bg-teal-100 text-teal-800' : 'bg-slate-100 text-slate-700',
        ].join(' ')}
      >
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-2xl font-extrabold text-hub-text">{value}</div>
        <div className="text-[0.72rem] font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function TabButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean
  icon: string
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition',
        active
          ? 'bg-teal-700 text-white shadow-sm'
          : 'bg-white/90 text-hub-muted hover:bg-white hover:text-hub-text',
      ].join(' ')}
    >
      <i className={`bi ${icon}`} aria-hidden />
      {label}
    </button>
  )
}

function StatusPill({
  status,
  selected,
  onClick,
}: {
  status: SchoolDayStatus
  selected: boolean
  onClick: () => void
}) {
  const styles = STATUS_STYLES[status] || STATUS_STYLES.Present
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-full border px-3 py-1.5 text-xs font-semibold transition',
        selected ? styles.active : styles.base,
      ].join(' ')}
    >
      {STATUS_LABELS[status] || status}
    </button>
  )
}

function ClassPeriodCard({
  item,
  classDate,
  onMarkAllPresent,
  busyClassId,
}: {
  item: ClassPeriodItem
  classDate: string
  onMarkAllPresent: (classId: number) => void
  busyClassId: number | null
}) {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-bold text-hub-text" title={item.name}>
            {item.name}
          </h3>
          <p className="text-sm text-hub-muted">{item.subject}</p>
        </div>
        <span
          className={[
            'shrink-0 rounded-full px-2.5 py-1 text-xs font-bold uppercase tracking-wide',
            item.attendance_taken ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900',
          ].join(' ')}
        >
          {item.attendance_taken ? 'Completed' : 'Pending'}
        </span>
      </div>

      <div className="space-y-2 text-sm text-hub-muted">
        <div>
          <i className="bi bi-people-fill mr-2 text-teal-700" aria-hidden />
          Students: <strong className="text-hub-text">{item.student_count}</strong>
        </div>
        <div>
          <i className="bi bi-person-badge mr-2 text-teal-700" aria-hidden />
          Teacher: <strong className="text-hub-text">{item.teacher_name}</strong>
        </div>
        <div>
          <i className="bi bi-mortarboard mr-2 text-teal-700" aria-hidden />
          Grade: <strong className="text-hub-text">{item.grade_levels_display}</strong>
        </div>
        {item.attendance_taken ? (
          <div className="pt-1 text-xs">
            Present {item.today_present} · Absent {item.today_absent}
          </div>
        ) : null}
      </div>

      <div className="mt-auto space-y-2 pt-5">
        <a
          href={item.take_attendance_url}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-800"
        >
          <i className="bi bi-clipboard-check" aria-hidden />
          Take Attendance
        </a>
        <div className="flex gap-2">
          <a
            href={item.view_class_url}
            className="flex flex-1 items-center justify-center gap-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-hub-text transition hover:bg-white"
          >
            <i className="bi bi-eye" aria-hidden />
            View
          </a>
          <button
            type="button"
            disabled={busyClassId === item.id}
            onClick={() => onMarkAllPresent(item.id)}
            className="flex flex-1 items-center justify-center gap-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-hub-text transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            <i className="bi bi-check-all" aria-hidden />
            {busyClassId === item.id ? 'Saving…' : 'All Present'}
          </button>
        </div>
        <p className="text-center text-[0.7rem] text-hub-muted">Class period · {classDate}</p>
      </div>
    </div>
  )
}

export default function AttendancePage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const [searchParams, setSearchParams] = useSearchParams()

  const tab: AttendanceTab = (() => {
    const explicit = searchParams.get('tab') as AttendanceTab | null
    if (explicit === 'school-day' || explicit === 'class-period' || explicit === 'reports') {
      return explicit
    }
    if (searchParams.get('reports_tab') === '1') return 'reports'
    return 'school-day'
  })()
  const schoolDate = searchParams.get('date') || localDateInputValue()
  const classDate = searchParams.get('class_date') || localDateInputValue()

  const [hub, setHub] = useState<AttendanceHubResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [busyClassId, setBusyClassId] = useState<number | null>(null)

  const [draftDate, setDraftDate] = useState(schoolDate)
  const [draftClassDate, setDraftClassDate] = useState(classDate)
  const [rows, setRows] = useState<SchoolDayStudentRow[]>([])

  const statusOptions = useMemo(
    () => (hub?.status_options || ['Present', 'Unexcused Absence', 'Late', 'Excused Absence']) as SchoolDayStatus[],
    [hub?.status_options],
  )

  const loadHub = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAttendanceHub({ date: schoolDate, class_date: classDate })
      setHub(data)
      setRows(
        data.school_day_students.map((row) => ({
          ...row,
          status: row.status || '',
          notes: row.notes || '',
        })),
      )
      setDraftDate(data.school_date)
      setDraftClassDate(data.class_date)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load attendance')
    } finally {
      setLoading(false)
    }
  }, [schoolDate, classDate])

  useEffect(() => {
    void loadHub()
  }, [loadHub])

  function setTab(nextTab: AttendanceTab) {
    const next = new URLSearchParams(searchParams)
    next.set('tab', nextTab)
    if (!next.get('date')) next.set('date', schoolDate)
    if (!next.get('class_date')) next.set('class_date', classDate)
    setSearchParams(next, { replace: true })
  }

  function applySchoolDate() {
    const next = new URLSearchParams(searchParams)
    next.set('tab', 'school-day')
    next.set('date', draftDate)
    if (!next.get('class_date')) next.set('class_date', classDate)
    setSearchParams(next)
  }

  function applyClassDate() {
    const next = new URLSearchParams(searchParams)
    next.set('tab', 'class-period')
    next.set('class_date', draftClassDate)
    if (!next.get('date')) next.set('date', schoolDate)
    setSearchParams(next)
  }

  function setRowStatus(studentId: number, status: SchoolDayStatus) {
    setRows((prev) =>
      prev.map((row) => {
        if (row.id !== studentId) return row
        const nextStatus = row.status === status ? '' : status
        return { ...row, status: nextStatus }
      }),
    )
  }

  function setRowNotes(studentId: number, notes: string) {
    setRows((prev) => prev.map((row) => (row.id === studentId ? { ...row, notes } : row)))
  }

  function bulkSetStatus(status: SchoolDayStatus) {
    setRows((prev) => prev.map((row) => ({ ...row, status })))
  }

  function clearAllStatuses() {
    setRows((prev) => prev.map((row) => ({ ...row, status: '' })))
  }

  async function handleSaveSchoolDay() {
    setSaving(true)
    setSaveMessage(null)
    setError(null)
    try {
      const entries = rows
        .filter((row) => row.status)
        .map((row) => ({
          student_id: row.id,
          status: row.status,
          notes: row.notes,
        }))
      const result = await saveSchoolDayAttendance(schoolDate, entries)
      setSaveMessage(result.message)
      await loadHub()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save attendance')
    } finally {
      setSaving(false)
    }
  }

  async function handleMarkAllPresent(classId: number) {
    setBusyClassId(classId)
    setError(null)
    try {
      const result = await markClassAllPresent(classId, classDate)
      setSaveMessage(result.message)
      await loadHub()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark all present')
    } finally {
      setBusyClassId(null)
    }
  }

  const isDirector = user.role_canonical === 'Director'

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-1 pb-10 pt-2">
      <header className="rounded-3xl border border-white/80 bg-gradient-to-br from-teal-900 via-teal-800 to-cyan-900 p-6 text-white shadow-lg md:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-100/90">Attendance</p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight">Unified attendance</h1>
            <p className="mt-2 flex items-center gap-2 text-sm text-teal-50/90">
              <i className="bi bi-calendar-week" aria-hidden />
              School day, class period, and reports in one place
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {isDirector ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">
                <i className="bi bi-award-fill" aria-hidden />
                Director
              </span>
            ) : user.management_entry ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">
                <i className="bi bi-shield-fill" aria-hidden />
                Administrator
              </span>
            ) : null}
            <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">
              <i className="bi bi-calendar3" aria-hidden />
              {schoolDate}
            </span>
            {hub ? (
              <Link
                to={hub.urls.analytics}
                className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-teal-900 transition hover:bg-teal-50"
              >
                <i className="bi bi-graph-up-arrow" aria-hidden />
                Analytics
              </Link>
            ) : null}
            <button
              type="button"
              onClick={() => void loadHub()}
              className="inline-flex items-center gap-2 rounded-xl border border-white/30 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              <i className="bi bi-arrow-clockwise" aria-hidden />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {hub ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="list">
          <StatCard icon="bi-people-fill" value={hub.insights.total_students} label="Students" featured />
          <StatCard icon="bi-check-circle-fill" value={hub.insights.school_day_present} label="School day present" />
          <StatCard icon="bi-journal-check" value={hub.insights.classes_completed} label="Classes completed" />
          <StatCard icon="bi-percent" value={`${hub.insights.class_period_rate}%`} label="Class period rate" />
        </div>
      ) : null}

      {(error || saveMessage) && (
        <div
          className={[
            'rounded-2xl border px-4 py-3 text-sm font-medium',
            error ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800',
          ].join(' ')}
        >
          {error || saveMessage}
        </div>
      )}

      <div className="rounded-3xl border border-white/90 bg-white/95 p-4 shadow-sm md:p-6">
        <div className="mb-6 flex flex-wrap gap-2">
          <TabButton
            active={tab === 'school-day'}
            icon="bi-calendar-day"
            label="School Day"
            onClick={() => setTab('school-day')}
          />
          <TabButton
            active={tab === 'class-period'}
            icon="bi-calendar-check"
            label="Class Period"
            onClick={() => setTab('class-period')}
          />
          <TabButton
            active={tab === 'reports'}
            icon="bi-file-earmark-bar-graph"
            label="Reports"
            onClick={() => setTab('reports')}
          />
        </div>

        {loading && !hub ? (
          <div className="py-16 text-center text-hub-muted">Loading attendance…</div>
        ) : null}

        {!loading && tab === 'school-day' && hub ? (
          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-hub-muted">
                Select date for school day attendance
              </h2>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="sm:w-56">
                  <label htmlFor="school-date" className="mb-1 block text-xs font-semibold uppercase text-hub-muted">
                    Attendance date
                  </label>
                  <input
                    id="school-date"
                    type="date"
                    value={draftDate}
                    onChange={(e) => setDraftDate(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-hub-text"
                  />
                </div>
                <button
                  type="button"
                  onClick={applySchoolDate}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800"
                >
                  <i className="bi bi-search" aria-hidden />
                  Load date
                </button>
                <button
                  type="button"
                  onClick={() => setDraftDate(localDateInputValue())}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-hub-text hover:bg-slate-50"
                >
                  Today
                </button>
              </div>
              <p className="mt-3 text-sm text-hub-muted">
                Building attendance for all students on the active roster — not limited to the current school year,
                so summer or off-calendar days can still be recorded.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard icon="bi-check-circle-fill" value={hub.school_day_stats.present} label="Present" />
              <StatCard icon="bi-x-circle-fill" value={hub.school_day_stats.absent} label="Absent" />
              <StatCard icon="bi-clock-fill" value={hub.school_day_stats.late} label="Late" />
              <StatCard icon="bi-shield-fill-check" value={hub.school_day_stats.excused} label="Excused" />
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white">
              <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-4 md:flex-row md:items-center md:justify-between md:px-6">
                <h2 className="text-lg font-bold text-hub-text">Mark school day attendance</h2>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => bulkSetStatus('Present')}
                    className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
                  >
                    All present
                  </button>
                  <button
                    type="button"
                    onClick={() => bulkSetStatus('Unexcused Absence')}
                    className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-700"
                  >
                    All absent
                  </button>
                  <button
                    type="button"
                    onClick={() => bulkSetStatus('Late')}
                    className="rounded-xl bg-amber-500 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-600"
                  >
                    All late
                  </button>
                  <button
                    type="button"
                    onClick={clearAllStatuses}
                    className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-hub-text hover:bg-white"
                  >
                    Clear all
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                      <th className="px-5 py-3">Student</th>
                      <th className="px-5 py-3">Grade</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.id} className="border-b border-slate-100">
                        <td className="px-5 py-3 font-semibold text-hub-text">{row.name}</td>
                        <td className="px-5 py-3 text-hub-muted">{row.grade_display}</td>
                        <td className="px-5 py-3">
                          <div className="flex flex-wrap gap-2">
                            {statusOptions.map((status) =>
                              status ? (
                                <StatusPill
                                  key={status}
                                  status={status}
                                  selected={row.status === status}
                                  onClick={() => setRowStatus(row.id, status)}
                                />
                              ) : null,
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <input
                            type="text"
                            value={row.notes}
                            onChange={(e) => setRowNotes(row.id, e.target.value)}
                            placeholder="Optional notes"
                            className="w-full min-w-[12rem] rounded-lg border border-slate-200 px-3 py-2 text-sm"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="border-t border-slate-200 px-4 py-5 text-center md:px-6">
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void handleSaveSchoolDay()}
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-3 text-sm font-bold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <i className="bi bi-save" aria-hidden />
                  {saving ? 'Saving…' : 'Save school day attendance'}
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {!loading && tab === 'class-period' && hub ? (
          <div className="space-y-6">
            {!hub.meta.has_active_school_year ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                No active school year is set. Class period attendance is only available when a school year is active.
              </div>
            ) : (
              <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
                Showing classes from the active school year
                {hub.meta.active_school_year_name ? (
                  <>
                    : <strong>{hub.meta.active_school_year_name}</strong>
                  </>
                ) : null}
                .
              </div>
            )}

            <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
                <div className="sm:w-56">
                  <label htmlFor="class-date" className="mb-1 block text-xs font-semibold uppercase text-hub-muted">
                    Select date
                  </label>
                  <input
                    id="class-date"
                    type="date"
                    value={draftClassDate}
                    onChange={(e) => setDraftClassDate(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-hub-text"
                  />
                </div>
                <button
                  type="button"
                  onClick={applyClassDate}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800"
                >
                  <i className="bi bi-calendar-check" aria-hidden />
                  Load attendance
                </button>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setDraftClassDate(localDateInputValue())}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
                  >
                    Today
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const yesterday = new Date()
                      yesterday.setDate(yesterday.getDate() - 1)
                      setDraftClassDate(localDateInputValue(yesterday))
                    }}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
                  >
                    Yesterday
                  </button>
                </div>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard icon="bi-journal-check" value={hub.class_period_stats.classes_completed} label="Completed" />
              <StatCard icon="bi-hourglass-split" value={hub.class_period_stats.pending_classes} label="Pending" />
              <StatCard icon="bi-percent" value={`${hub.class_period_stats.overall_rate}%`} label="Overall rate" />
            </div>

            {hub.classes.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {hub.classes.map((item) => (
                  <ClassPeriodCard
                    key={item.id}
                    item={item}
                    classDate={hub.class_date}
                    onMarkAllPresent={(classId) => void handleMarkAllPresent(classId)}
                    busyClassId={busyClassId}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 px-6 py-16 text-center text-hub-muted">
                <i className="bi bi-inbox mb-3 block text-4xl text-slate-300" aria-hidden />
                <p className="font-semibold text-hub-text">
                  {hub.meta.has_active_school_year ? 'No classes available' : 'Class period attendance unavailable'}
                </p>
                <p className="mt-1 text-sm">
                  {hub.meta.has_active_school_year
                    ? "You don't have any classes in the active school year to take attendance for."
                    : 'Activate a school year to manage class period attendance.'}
                </p>
              </div>
            )}
          </div>
        ) : null}

        {!loading && tab === 'reports' ? <AttendanceReportsPanel embedded /> : null}
      </div>
    </div>
  )
}
