import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { fetchAttendanceAnalytics, type AttendanceAnalyticsQuery } from '../api/attendance'
import type { AttendanceAnalyticsResponse } from '../types/attendance'

function rateBadgeClass(rate: number): string {
  if (rate >= 90) return 'bg-emerald-100 text-emerald-800'
  if (rate >= 75) return 'bg-amber-100 text-amber-900'
  return 'bg-rose-100 text-rose-800'
}

function exportAnalyticsCsv(data: AttendanceAnalyticsResponse, visibleRows: AttendanceAnalyticsResponse['at_risk_students']) {
  const header = 'Student,Grade,Attendance Rate,Present,Absent,Late,Max Consecutive Absences,Risk Level\n'
  const lines = visibleRows.map((row) => {
    const values = [
      row.student.label,
      row.student.grade_display,
      `${row.attendance_rate}%`,
      String(row.pattern.present),
      String(row.pattern.absent),
      String(row.pattern.late),
      `${row.pattern.max_consecutive_absences}d`,
      row.risk_level === 'high' ? 'High' : 'Medium',
    ]
    return values.map((v) => `"${v.replace(/"/g, '""')}"`).join(',')
  })
  const blob = new Blob([header + lines.join('\n') + '\n'], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `attendance_analytics_${data.filters.start_date}_to_${data.filters.end_date}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

function readAnalyticsQuery(searchParams: URLSearchParams): AttendanceAnalyticsQuery {
  return {
    start_date: searchParams.get('start_date') || undefined,
    end_date: searchParams.get('end_date') || undefined,
    risk: searchParams.get('risk') || undefined,
  }
}

export default function AttendanceAnalyticsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const query = useMemo(() => readAnalyticsQuery(searchParams), [searchParams])

  const [data, setData] = useState<AttendanceAnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(query.risk && query.risk !== 'all')
  const [search, setSearch] = useState('')

  const [draftStart, setDraftStart] = useState('')
  const [draftEnd, setDraftEnd] = useState('')
  const [draftRisk, setDraftRisk] = useState<'all' | 'high' | 'medium'>('all')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchAttendanceAnalytics(query)
      setData(response)
      setDraftStart(response.filters.start_date)
      setDraftEnd(response.filters.end_date)
      setDraftRisk(response.filters.risk)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => {
    void load()
  }, [load])

  function applyQuery(next: AttendanceAnalyticsQuery) {
    const params = new URLSearchParams()
    if (next.start_date) params.set('start_date', next.start_date)
    if (next.end_date) params.set('end_date', next.end_date)
    if (next.risk && next.risk !== 'all') params.set('risk', next.risk)
    setSearchParams(params, { replace: true })
  }

  function applyFilters() {
    applyQuery({ start_date: draftStart, end_date: draftEnd, risk: draftRisk })
  }

  function applyPreset(startDate: string, endDate: string) {
    applyQuery({ start_date: startDate, end_date: endDate, risk: draftRisk })
  }

  const filteredStudents = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    if (!q) return data.at_risk_students
    return data.at_risk_students.filter((row) => row.student.label.toLowerCase().includes(q))
  }, [data, search])

  const activePreset = useMemo(() => {
    if (!data) return null
    return (
      data.presets.find(
        (p) => p.start_date === data.filters.start_date && p.end_date === data.filters.end_date,
      )?.label || null
    )
  }, [data])

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-1 pb-10 pt-2">
      <header className="rounded-3xl border border-white/80 bg-gradient-to-br from-indigo-900 via-indigo-800 to-violet-900 p-6 text-white shadow-lg md:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-100/90">
              Class-period attendance
            </p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight">Attendance analytics</h1>
            <p className="mt-2 text-sm text-indigo-50/90">
              Spot trends, absences, and students who may need follow-up.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!data || !filteredStudents.length}
              onClick={() => data && exportAnalyticsCsv(data, filteredStudents)}
              className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-indigo-900 transition hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <i className="bi bi-download" aria-hidden />
              Export CSV
            </button>
            <Link
              to={`/management/attendance/reports?start_date=${data?.filters.start_date || ''}&end_date=${data?.filters.end_date || ''}`}
              className="inline-flex items-center gap-2 rounded-xl border border-white/30 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              <i className="bi bi-table" aria-hidden />
              View records
            </Link>
            <Link
              to="/management/attendance"
              className="inline-flex items-center gap-2 rounded-xl border border-white/30 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              <i className="bi bi-arrow-left" aria-hidden />
              Attendance
            </Link>
          </div>
        </div>
      </header>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      {loading && !data ? (
        <div className="py-16 text-center text-hub-muted">Loading analytics…</div>
      ) : null}

      {data ? (
        <>
          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50/80 p-4 lg:flex-row lg:items-center lg:justify-between">
            <p className="text-sm text-hub-text">
              <i className="bi bi-calendar3 mr-1 text-indigo-700" aria-hidden />
              <strong>{data.filters.start_date}</strong> → <strong>{data.filters.end_date}</strong>
              <span className="ml-2 text-hub-muted">
                · {data.summary.days_analyzed} day{data.summary.days_analyzed === 1 ? '' : 's'}
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
                      ? 'bg-indigo-700 text-white'
                      : 'bg-white text-hub-muted hover:text-hub-text',
                  ].join(' ')}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            {[
              { value: `${data.summary.overall_rate}%`, label: 'Present rate' },
              { value: data.summary.at_risk_high + data.summary.at_risk_medium, label: 'At risk' },
              { value: data.summary.students_tracked, label: 'Students' },
              { value: data.summary.total_records, label: 'Records' },
              { value: data.status_counts.present, label: 'Present' },
              { value: data.status_counts.late, label: 'Late' },
              { value: data.status_counts.unexcused, label: 'Unexcused' },
            ].map((stat) => (
              <div key={stat.label} className="rounded-2xl border border-white/90 bg-white/95 p-4 shadow-sm">
                <div className="text-2xl font-extrabold text-hub-text">{stat.value}</div>
                <div className="text-[0.72rem] font-semibold uppercase tracking-wide text-hub-muted">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setFiltersOpen((open) => !open)}
            className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-hub-text"
          >
            <span>
              <i className="bi bi-sliders mr-2 text-indigo-700" aria-hidden />
              Options
            </span>
            <i className={`bi bi-chevron-${filtersOpen ? 'up' : 'down'}`} aria-hidden />
          </button>

          {filtersOpen ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="grid gap-3 md:grid-cols-4">
                <div>
                  <label htmlFor="an-start" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                    Start
                  </label>
                  <input
                    id="an-start"
                    type="date"
                    value={draftStart}
                    onChange={(e) => setDraftStart(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="an-end" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                    End
                  </label>
                  <input
                    id="an-end"
                    type="date"
                    value={draftEnd}
                    onChange={(e) => setDraftEnd(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="an-risk" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                    Risk level
                  </label>
                  <select
                    id="an-risk"
                    value={draftRisk}
                    onChange={(e) => setDraftRisk(e.target.value as 'all' | 'high' | 'medium')}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  >
                    <option value="all">All concerns</option>
                    <option value="high">High only</option>
                    <option value="medium">Medium only</option>
                  </select>
                </div>
                <div className="flex items-end gap-2">
                  <button
                    type="button"
                    onClick={() => applyQuery({})}
                    className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
                  >
                    Reset
                  </button>
                  <button
                    type="button"
                    onClick={applyFilters}
                    className="rounded-xl bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
                  >
                    Apply
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-base font-bold text-hub-text">
                  <i className="bi bi-bar-chart-line mr-2 text-indigo-700" aria-hidden />
                  Daily volume
                </h2>
                {data.summary.total_records > 0 ? (
                  <div className="flex h-40 items-end gap-1 overflow-x-auto pb-6">
                    {data.daily_trend.map((day, index) => (
                      <div
                        key={day.date}
                        className="flex min-w-[10px] flex-1 flex-col items-center justify-end"
                        title={`${day.date_label}: ${day.total} records${day.rate != null ? `, ${day.rate}% present` : ''}`}
                      >
                        <div
                          className="w-full rounded-t bg-indigo-500/80"
                          style={{
                            height: `${Math.max(4, Math.round((day.total / data.trend_max) * 100))}%`,
                          }}
                        />
                        {index % 7 === 0 || index === data.daily_trend.length - 1 ? (
                          <span className="mt-1 text-[0.6rem] text-hub-muted">{day.date_short}</span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-hub-muted">No records in this range.</p>
                )}
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-base font-bold text-hub-text">
                  <i className="bi bi-pie-chart mr-2 text-indigo-700" aria-hidden />
                  Status mix
                </h2>
                <ul className="space-y-2 text-sm text-hub-text">
                  {[
                    ['Present', data.status_counts.present, 'bg-emerald-500'],
                    ['Late', data.status_counts.late, 'bg-violet-500'],
                    ['Unexcused', data.status_counts.unexcused, 'bg-slate-500'],
                    ['Excused', data.status_counts.excused, 'bg-amber-500'],
                    ['Suspended', data.status_counts.suspended, 'bg-rose-500'],
                  ].map(([label, count, dotClass]) => (
                    <li key={label as string} className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${dotClass as string}`} />
                        {label as string}
                      </span>
                      <strong>{count as number}</strong>
                    </li>
                  ))}
                </ul>
                <div className="mt-4 flex gap-2">
                  <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-bold text-rose-800">
                    {data.summary.at_risk_high} high
                  </span>
                  <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-900">
                    {data.summary.at_risk_medium} medium
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-base font-bold text-hub-text">
                  <i className="bi bi-exclamation-triangle mr-2 text-rose-600" aria-hidden />
                  Students with concerns
                </h2>
                <div className="relative">
                  <i className="bi bi-search absolute left-3 top-1/2 -translate-y-1/2 text-hub-muted" aria-hidden />
                  <input
                    type="search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search students…"
                    className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm sm:w-56"
                  />
                </div>
              </div>

              {filteredStudents.length ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                        <th className="px-3 py-2">Student</th>
                        <th className="px-3 py-2">Grade</th>
                        <th className="px-3 py-2">Rate</th>
                        <th className="px-3 py-2">Present</th>
                        <th className="px-3 py-2">Absent</th>
                        <th className="px-3 py-2">Late</th>
                        <th className="px-3 py-2">Streak</th>
                        <th className="px-3 py-2">Risk</th>
                        <th className="px-3 py-2" />
                      </tr>
                    </thead>
                    <tbody>
                      {filteredStudents.map((row) => (
                        <tr key={row.student.id} className="border-b border-slate-100">
                          <td className="px-3 py-2 font-medium text-hub-text">{row.student.label}</td>
                          <td className="px-3 py-2">
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold">
                              {row.student.grade_display}
                            </span>
                          </td>
                          <td className="px-3 py-2">
                            <span
                              className={[
                                'rounded-full px-2 py-0.5 text-xs font-semibold',
                                rateBadgeClass(row.attendance_rate),
                              ].join(' ')}
                            >
                              {row.attendance_rate}%
                            </span>
                          </td>
                          <td className="px-3 py-2">{row.pattern.present}</td>
                          <td className="px-3 py-2 font-semibold text-rose-700">{row.pattern.absent}</td>
                          <td className="px-3 py-2">{row.pattern.late}</td>
                          <td className="px-3 py-2">
                            {row.pattern.max_consecutive_absences >= 3 ? (
                              <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-800">
                                {row.pattern.max_consecutive_absences}d
                              </span>
                            ) : (
                              `${row.pattern.max_consecutive_absences}d`
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <span
                              className={[
                                'rounded-full px-2 py-0.5 text-xs font-semibold',
                                row.risk_level === 'high'
                                  ? 'bg-rose-100 text-rose-800'
                                  : 'bg-amber-100 text-amber-900',
                              ].join(' ')}
                            >
                              {row.risk_level === 'high' ? 'High' : 'Medium'}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-right">
                            <a
                              href={row.student.view_url}
                              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-hub-text hover:bg-slate-50"
                              title="View student"
                            >
                              <i className="bi bi-eye" aria-hidden />
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-200 px-6 py-12 text-center text-hub-muted">
                  <i className="bi bi-check-circle mb-2 block text-4xl text-emerald-500" aria-hidden />
                  <p className="font-semibold text-hub-text">No students match these criteria</p>
                  <p className="mt-1 text-sm">
                    {data.filters.risk !== 'all'
                      ? 'Try clearing the risk filter or widening the date range.'
                      : data.summary.total_records === 0
                        ? 'No class-period attendance was recorded in this date range.'
                        : 'Everyone is within attendance thresholds for this period.'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
