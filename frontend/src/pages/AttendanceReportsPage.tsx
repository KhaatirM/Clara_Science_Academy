import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { fetchAttendanceReports, type AttendanceReportsQuery } from '../api/attendance'
import type { AttendanceReportsResponse } from '../types/attendance'

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    Present: 'bg-emerald-100 text-emerald-800',
    'Unexcused Absence': 'bg-slate-200 text-slate-800',
    'Excused Absence': 'bg-amber-100 text-amber-900',
    Late: 'bg-violet-100 text-violet-800',
    Suspended: 'bg-rose-100 text-rose-800',
  }
  const label =
    status === 'Unexcused Absence' ? 'Unexcused' : status === 'Excused Absence' ? 'Excused' : status
  return (
    <span
      className={[
        'inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold',
        styles[status] || 'bg-slate-100 text-slate-700',
      ].join(' ')}
    >
      {label}
    </span>
  )
}

function SummaryStat({ value, label, tone }: { value: number; label: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-center">
      <div className={['text-xl font-extrabold', tone || 'text-hub-text'].join(' ')}>{value}</div>
      <div className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
    </div>
  )
}

function parseIdList(values: string[]): number[] {
  return values.map((v) => Number(v)).filter((n) => Number.isFinite(n) && n > 0)
}

function readReportsQuery(searchParams: URLSearchParams): AttendanceReportsQuery {
  return {
    start_date: searchParams.get('start_date') || undefined,
    end_date: searchParams.get('end_date') || undefined,
    status: searchParams.get('status') || undefined,
    page: Math.max(1, Number(searchParams.get('page') || '1') || 1),
    student_ids: parseIdList(searchParams.getAll('student_ids')),
    class_ids: parseIdList(searchParams.getAll('class_ids')),
  }
}

export function AttendanceReportsPanel({
  embedded = false,
}: {
  embedded?: boolean
}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const query = useMemo(() => readReportsQuery(searchParams), [searchParams])

  const [data, setData] = useState<AttendanceReportsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(
    Boolean(query.student_ids?.length || query.class_ids?.length || query.status),
  )

  const [draftStudents, setDraftStudents] = useState<number[]>([])
  const [draftClasses, setDraftClasses] = useState<number[]>([])
  const [draftStatus, setDraftStatus] = useState('')
  const [draftStart, setDraftStart] = useState('')
  const [draftEnd, setDraftEnd] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchAttendanceReports(query)
      setData(response)
      setDraftStudents(response.filters.student_ids)
      setDraftClasses(response.filters.class_ids)
      setDraftStatus(response.filters.status)
      setDraftStart(response.filters.start_date)
      setDraftEnd(response.filters.end_date)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports')
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => {
    void load()
  }, [load])

  function applyQuery(next: AttendanceReportsQuery, replace = false) {
    const params = new URLSearchParams()
    if (embedded) params.set('tab', 'reports')
    if (next.start_date) params.set('start_date', next.start_date)
    if (next.end_date) params.set('end_date', next.end_date)
    if (next.status) params.set('status', next.status)
    next.student_ids?.forEach((id) => params.append('student_ids', String(id)))
    next.class_ids?.forEach((id) => params.append('class_ids', String(id)))
    if (next.page && next.page > 1) params.set('page', String(next.page))
    setSearchParams(params, { replace })
  }

  function applyFilters() {
    applyQuery({
      start_date: draftStart,
      end_date: draftEnd,
      status: draftStatus,
      student_ids: draftStudents,
      class_ids: draftClasses,
      page: 1,
    })
  }

  function applyPreset(startDate: string, endDate: string) {
    applyQuery({
      start_date: startDate,
      end_date: endDate,
      status: '',
      student_ids: [],
      class_ids: [],
      page: 1,
    })
  }

  function resetFilters() {
    if (embedded) {
      setSearchParams({ tab: 'reports' }, { replace: true })
    } else {
      setSearchParams({}, { replace: true })
    }
  }

  const activePreset = useMemo(() => {
    if (!data) return null
    return (
      data.presets.find(
        (p) => p.start_date === data.filters.start_date && p.end_date === data.filters.end_date,
      )?.label || null
    )
  }, [data])

  return (
    <div className="space-y-4">
      {!embedded ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-bold text-hub-text">Attendance reports</h2>
            <p className="text-sm text-hub-muted">
              Class-period records · default last {data?.default_range_days ?? 30} days
            </p>
          </div>
          <Link
            to="/management/attendance?tab=school-day"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
          >
            <i className="bi bi-arrow-left" aria-hidden />
            Back to attendance
          </Link>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      {data ? (
        <>
          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50/80 p-4 lg:flex-row lg:items-center lg:justify-between">
            <p className="text-sm text-hub-text">
              <i className="bi bi-calendar3 mr-1 text-teal-700" aria-hidden />
              <strong>{data.filters.start_date}</strong> → <strong>{data.filters.end_date}</strong>
              <span className="ml-2 text-hub-muted">
                · {data.summary_stats.total_records} record
                {data.summary_stats.total_records === 1 ? '' : 's'}
              </span>
            </p>
            <div className="flex flex-wrap gap-2">
              {data.presets.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => applyPreset(preset.start_date, preset.end_date)}
                  className={[
                    'rounded-full px-3 py-1.5 text-xs font-semibold transition',
                    activePreset === preset.label
                      ? 'bg-teal-700 text-white'
                      : 'bg-white text-hub-muted hover:text-hub-text',
                  ].join(' ')}
                >
                  {preset.label}
                </button>
              ))}
              {embedded ? (
                <Link
                  to={`/management/attendance/reports?${searchParams.toString()}`}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-hub-text hover:bg-slate-50"
                >
                  <i className="bi bi-box-arrow-up-right mr-1" aria-hidden />
                  Full page
                </Link>
              ) : null}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            <SummaryStat value={data.summary_stats.total_records} label="Total" />
            <SummaryStat value={data.summary_stats.present} label="Present" tone="text-emerald-700" />
            <SummaryStat value={data.summary_stats.late} label="Late" tone="text-violet-700" />
            <SummaryStat
              value={data.summary_stats.unexcused_absence}
              label="Unexcused"
              tone="text-slate-700"
            />
            <SummaryStat
              value={data.summary_stats.excused_absence}
              label="Excused"
              tone="text-amber-700"
            />
            <SummaryStat
              value={data.summary_stats.suspended}
              label="Suspended"
              tone="text-rose-700"
            />
          </div>

          <button
            type="button"
            onClick={() => setFiltersOpen((open) => !open)}
            className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-hub-text"
          >
            <span>
              <i className="bi bi-funnel mr-2 text-teal-700" aria-hidden />
              Filters
            </span>
            <i className={`bi bi-chevron-${filtersOpen ? 'up' : 'down'}`} aria-hidden />
          </button>

          {filtersOpen ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <div>
                  <label htmlFor="rpt-students" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                    Students
                  </label>
                  <select
                    id="rpt-students"
                    multiple
                    value={draftStudents.map(String)}
                    onChange={(e) =>
                      setDraftStudents(Array.from(e.target.selectedOptions, (o) => Number(o.value)))
                    }
                    className="min-h-[7rem] w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  >
                    {data.filter_options.students.map((student) => (
                      <option key={student.id} value={student.id}>
                        {student.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="rpt-classes" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                    Classes
                  </label>
                  <select
                    id="rpt-classes"
                    multiple
                    value={draftClasses.map(String)}
                    onChange={(e) =>
                      setDraftClasses(Array.from(e.target.selectedOptions, (o) => Number(o.value)))
                    }
                    className="min-h-[7rem] w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  >
                    {data.filter_options.classes.map((classItem) => (
                      <option key={classItem.id} value={classItem.id}>
                        {classItem.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-3">
                  <div>
                    <label htmlFor="rpt-status" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                      Status
                    </label>
                    <select
                      id="rpt-status"
                      value={draftStatus}
                      onChange={(e) => setDraftStatus(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                    >
                      <option value="">All statuses</option>
                      {data.filter_options.statuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="rpt-start" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                      Start
                    </label>
                    <input
                      id="rpt-start"
                      type="date"
                      value={draftStart}
                      onChange={(e) => setDraftStart(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor="rpt-end" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                      End
                    </label>
                    <input
                      id="rpt-end"
                      type="date"
                      value={draftEnd}
                      onChange={(e) => setDraftEnd(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={resetFilters}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={applyFilters}
                  className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                >
                  <i className="bi bi-search mr-1" aria-hidden />
                  Apply
                </button>
              </div>
            </div>
          ) : null}

          <div className="flex items-center justify-between text-sm text-hub-muted">
            <span>
              <i className="bi bi-table mr-1" aria-hidden />
              Records
            </span>
            <span>
              Page {data.pagination.page} of {data.pagination.pages} · showing {data.records.length} of{' '}
              {data.pagination.total}
            </span>
          </div>

          {loading ? (
            <div className="py-10 text-center text-hub-muted">Loading records…</div>
          ) : data.records.length ? (
            <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Student</th>
                    <th className="px-4 py-3">Class</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Recorded by</th>
                    <th className="px-4 py-3">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {data.records.map((record) => (
                    <tr key={record.id} className="border-b border-slate-100">
                      <td className="px-4 py-3">{record.date_display}</td>
                      <td className="px-4 py-3 font-medium text-hub-text">
                        {record.student?.label || '—'}
                      </td>
                      <td className="px-4 py-3">{record.class?.name || '—'}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={record.status} />
                      </td>
                      <td className="px-4 py-3">{record.recorded_by || '—'}</td>
                      <td className="max-w-xs truncate px-4 py-3 text-hub-muted" title={record.notes}>
                        {record.notes || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 px-6 py-14 text-center text-hub-muted">
              <i className="bi bi-inbox mb-2 block text-4xl text-slate-300" aria-hidden />
              <p>No records match these filters. Try a wider date range or clear filters.</p>
            </div>
          )}

          {data.pagination.pages > 1 ? (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-sm text-hub-muted">{data.pagination.per_page} per page</span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={!data.pagination.has_prev}
                  onClick={() => applyQuery({ ...query, page: data.pagination.prev_page || 1 })}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold disabled:opacity-50"
                >
                  Prev
                </button>
                <span className="rounded-lg bg-teal-50 px-3 py-1.5 text-sm font-semibold text-teal-800">
                  {data.pagination.page}
                </span>
                <button
                  type="button"
                  disabled={!data.pagination.has_next}
                  onClick={() => applyQuery({ ...query, page: data.pagination.next_page || data.pagination.page })}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          ) : null}
        </>
      ) : loading ? (
        <div className="py-10 text-center text-hub-muted">Loading reports…</div>
      ) : null}
    </div>
  )
}

export default function AttendanceReportsPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-1 pb-10 pt-2">
      <AttendanceReportsPanel />
    </div>
  )
}
