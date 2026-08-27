import { useCallback, useEffect, useState } from 'react'
import {
  fetchGradeMasterSchedule,
  fetchManagementBellSchedule,
  gradeSchedulePdfUrl,
  saveManagementBellSchedule,
  type ManagementBellScheduleResponse,
} from '../api/bellSchedule'
import { BellScheduleGrid } from '../components/schedule/BellScheduleGrid'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { BellGridPayload, BellPeriodDto, BellPeriodKind } from '../types/bellSchedule'

const EMPTY_PERIOD = (): BellPeriodDto => ({
  name: 'Period',
  kind: 'class',
  start_time: '08:00',
  end_time: '09:00',
  color_hex: '#5B8DEE',
  sort_order: 0,
  days_of_week: [0, 1, 2, 3, 4],
})

export function ManagementSchedulePage() {
  const [hub, setHub] = useState<ManagementBellScheduleResponse | null>(null)
  const [title, setTitle] = useState('')
  const [periods, setPeriods] = useState<BellPeriodDto[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)
  const [selectedGrade, setSelectedGrade] = useState<number | null>(null)
  const [gradeGrid, setGradeGrid] = useState<
    (BellGridPayload & { grade_label?: string; class_count?: number }) | null
  >(null)
  const [gradeLoading, setGradeLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchManagementBellSchedule()
      setHub(data)
      setTitle(data.bell_schedule?.title || 'Bell Schedule')
      setPeriods(
        (data.bell_schedule?.periods || []).map((p, idx) => ({
          ...p,
          sort_order: p.sort_order ?? idx,
          days_of_week: p.days_of_week?.length ? p.days_of_week : [0, 1, 2, 3, 4],
        })),
      )
      setSelectedGrade((prev) => {
        if (prev != null) return prev
        return data.grades.length ? data.grades[0].grade : null
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load schedule')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (selectedGrade == null) {
      setGradeGrid(null)
      return
    }
    let cancelled = false
    setGradeLoading(true)
    void fetchGradeMasterSchedule(selectedGrade)
      .then((data) => {
        if (!cancelled) setGradeGrid(data)
      })
      .catch((err) => {
        if (!cancelled) {
          setGradeGrid(null)
          setFlash(err instanceof Error ? err.message : 'Could not load grade schedule')
        }
      })
      .finally(() => {
        if (!cancelled) setGradeLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedGrade])

  async function onSave() {
    setSaving(true)
    setFlash(null)
    setError(null)
    try {
      const payload = {
        title,
        periods: periods.map((p, idx) => ({
          ...p,
          sort_order: idx,
          kind: (p.kind || 'class') as BellPeriodKind,
        })),
      }
      const result = await saveManagementBellSchedule(payload)
      setFlash(result.message || 'Saved.')
      if (result.bell_schedule) {
        setPeriods(result.bell_schedule.periods || [])
        setTitle(result.bell_schedule.title || title)
      }
      // Refresh grade preview after save
      if (selectedGrade != null) {
        const grid = await fetchGradeMasterSchedule(selectedGrade)
        setGradeGrid(grid)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  function updatePeriod(index: number, patch: Partial<BellPeriodDto>) {
    setPeriods((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)))
  }

  function toggleDay(index: number, day: number) {
    setPeriods((prev) =>
      prev.map((p, i) => {
        if (i !== index) return p
        const has = p.days_of_week.includes(day)
        const days = has
          ? p.days_of_week.filter((d) => d !== day)
          : [...p.days_of_week, day].sort((a, b) => a - b)
        return { ...p, days_of_week: days }
      }),
    )
  }

  function movePeriod(index: number, dir: -1 | 1) {
    setPeriods((prev) => {
      const next = [...prev]
      const j = index + dir
      if (j < 0 || j >= next.length) return prev
      ;[next[index], next[j]] = [next[j], next[index]]
      return next
    })
  }

  return (
    <ManagementPageShell>
      <div className="container-fluid px-0 px-md-1">
        <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-slate-800 via-teal-800 to-emerald-700 px-5 py-6 text-white shadow-lg">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
            Management
          </p>
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Schedule</h1>
          <p className="mb-0 mt-1 text-sm text-teal-50/95">
            Configure the school bell schedule and print master schedules by grade
            {hub?.school_year ? ` · ${hub.school_year.name}` : ''}
          </p>
        </header>

        {loading ? (
          <div className="p-5 text-center text-muted">Loading schedule…</div>
        ) : error && !hub ? (
          <div className="alert alert-danger">{error}</div>
        ) : (
          <div className="space-y-6">
            {flash ? (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                {flash}
              </div>
            ) : null}
            {error ? (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
                {error}
              </div>
            ) : null}

            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
              <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                <div className="min-w-[220px] flex-1">
                  <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Schedule title
                  </label>
                  <input
                    className="form-control"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setPeriods((prev) => [...prev, EMPTY_PERIOD()])}
                  >
                    Add period
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={saving || periods.length === 0}
                    onClick={() => void onSave()}
                  >
                    {saving ? 'Saving…' : 'Save bell schedule'}
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {periods.map((period, index) => (
                  <div
                    key={`period-${index}`}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-3"
                  >
                    <div className="grid gap-2 md:grid-cols-12 md:items-end">
                      <div className="md:col-span-3">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Name
                        </label>
                        <input
                          className="form-control form-control-sm"
                          value={period.name}
                          onChange={(e) => updatePeriod(index, { name: e.target.value })}
                        />
                      </div>
                      <div className="md:col-span-2">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Kind
                        </label>
                        <select
                          className="form-select form-select-sm"
                          value={period.kind}
                          onChange={(e) => updatePeriod(index, { kind: e.target.value })}
                        >
                          {(hub?.kind_options || []).map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="md:col-span-2">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Start
                        </label>
                        <input
                          type="time"
                          className="form-control form-control-sm"
                          value={period.start_time}
                          onChange={(e) => updatePeriod(index, { start_time: e.target.value })}
                        />
                      </div>
                      <div className="md:col-span-2">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          End
                        </label>
                        <input
                          type="time"
                          className="form-control form-control-sm"
                          value={period.end_time}
                          onChange={(e) => updatePeriod(index, { end_time: e.target.value })}
                        />
                      </div>
                      <div className="md:col-span-1">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Color
                        </label>
                        <input
                          type="color"
                          className="form-control form-control-sm form-control-color w-100"
                          value={period.color_hex || '#5B8DEE'}
                          onChange={(e) => updatePeriod(index, { color_hex: e.target.value })}
                        />
                      </div>
                      <div className="flex gap-1 md:col-span-2 md:justify-end">
                        <button
                          type="button"
                          className="btn btn-outline-secondary btn-sm"
                          onClick={() => movePeriod(index, -1)}
                          disabled={index === 0}
                          title="Move up"
                        >
                          <i className="bi bi-arrow-up" aria-hidden />
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-secondary btn-sm"
                          onClick={() => movePeriod(index, 1)}
                          disabled={index === periods.length - 1}
                          title="Move down"
                        >
                          <i className="bi bi-arrow-down" aria-hidden />
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-danger btn-sm"
                          onClick={() => setPeriods((prev) => prev.filter((_, i) => i !== index))}
                          title="Remove"
                        >
                          <i className="bi bi-trash" aria-hidden />
                        </button>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(hub?.weekday_options || []).map((d) => {
                        const on = period.days_of_week.includes(d.value)
                        return (
                          <button
                            key={d.value}
                            type="button"
                            className={`btn btn-sm ${on ? 'btn-teal active' : 'btn-outline-secondary'}`}
                            style={
                              on
                                ? { backgroundColor: '#0f766e', borderColor: '#0f766e', color: '#fff' }
                                : undefined
                            }
                            onClick={() => toggleDay(index, d.value)}
                          >
                            {d.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
                {periods.length === 0 ? (
                  <p className="mb-0 text-sm text-hub-muted">
                    No periods yet. Click “Add period” or save after seeding from the server default.
                  </p>
                ) : null}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="mb-0 text-lg font-bold text-hub-text">Print by grade</h2>
                  <p className="mb-0 text-sm text-hub-muted">
                    Master schedule of all classes offered at that grade level
                  </p>
                </div>
                {selectedGrade != null ? (
                  <a
                    href={gradeSchedulePdfUrl(selectedGrade)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
                  >
                    <i className="bi bi-file-earmark-pdf" aria-hidden />
                    Download PDF
                  </a>
                ) : null}
              </div>

              {(hub?.grades || []).length === 0 ? (
                <p className="mb-0 text-sm text-hub-muted">
                  No grade levels found on active-year classes yet.
                </p>
              ) : (
                <div className="mb-4 flex flex-wrap gap-2">
                  {hub!.grades.map((g) => (
                    <button
                      key={g.grade}
                      type="button"
                      className={`btn btn-sm ${
                        selectedGrade === g.grade ? 'btn-primary' : 'btn-outline-secondary'
                      }`}
                      onClick={() => setSelectedGrade(g.grade)}
                    >
                      {g.label}
                    </button>
                  ))}
                </div>
              )}

              {gradeLoading ? (
                <p className="text-sm text-hub-muted">Loading grade preview…</p>
              ) : gradeGrid ? (
                <>
                  <p className="mb-3 text-sm text-hub-muted">
                    {gradeGrid.grade_label}
                    {gradeGrid.class_count != null ? ` · ${gradeGrid.class_count} classes` : ''}
                  </p>
                  <BellScheduleGrid grid={gradeGrid} showTeacher />
                </>
              ) : null}
            </section>
          </div>
        )}
      </div>
    </ManagementPageShell>
  )
}
