import { useCallback, useEffect, useState } from 'react'
import {
  fetchGradeMasterSchedule,
  fetchManagementBellSchedule,
  gradeSchedulePdfUrl,
  resetBellSchedulePeriods,
  saveManagementBellSchedule,
  type ManagementBellScheduleResponse,
} from '../api/bellSchedule'
import { BellScheduleGrid } from '../components/schedule/BellScheduleGrid'
import { PeriodClassPlanner } from '../components/schedule/PeriodClassPlanner'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { BellGridPayload, BellPeriodDto, BellPeriodKind } from '../types/bellSchedule'

const EMPTY_PERIOD = (): BellPeriodDto => ({
  name: 'Period',
  kind: 'class',
  usage_label: null,
  start_time: '08:00',
  end_time: '09:00',
  color_hex: '#5B8DEE',
  sort_order: 0,
  days_of_week: [0, 1, 2, 3, 4],
})

const SCHEDULE_TABS = [
  { id: 'assign' as const, label: 'Assign classes', icon: 'bi-arrows-move' },
  { id: 'periods' as const, label: 'Edit bell periods', icon: 'bi-calendar-week' },
  { id: 'print' as const, label: 'Preview & print', icon: 'bi-printer' },
]

const fieldInput =
  'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-hub-text shadow-sm focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-200'
const fieldInputSm =
  'w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-hub-text focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-200'

export function ManagementSchedulePage() {
  const [hub, setHub] = useState<ManagementBellScheduleResponse | null>(null)
  const [title, setTitle] = useState('')
  const [periods, setPeriods] = useState<BellPeriodDto[]>([])
  /** Grade this bell schedule belongs to (null = all grades). */
  const [editGrade, setEditGrade] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)
  const [previewGrade, setPreviewGrade] = useState<number | null>(null)
  const [gradeGrid, setGradeGrid] = useState<
    (BellGridPayload & { grade_label?: string; class_count?: number }) | null
  >(null)
  const [gradeLoading, setGradeLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'assign' | 'periods' | 'print'>('assign')

  const applyPayload = useCallback((data: ManagementBellScheduleResponse) => {
    setHub(data)
    setTitle(data.bell_schedule?.title || 'Bell Schedule')
    setPeriods(
      (data.bell_schedule?.periods || []).map((p, idx) => ({
        ...p,
        sort_order: p.sort_order ?? idx,
        days_of_week: p.days_of_week?.length ? p.days_of_week : [0, 1, 2, 3, 4],
      })),
    )
    const selected =
      data.selected_grade !== undefined
        ? data.selected_grade
        : (data.bell_schedule?.grade_level ?? null)
    setEditGrade(selected)
  }, [])

  const load = useCallback(
    async (grade: number | null) => {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchManagementBellSchedule(grade)
        applyPayload(data)
        const firstNumeric = data.grades.find((g) => g.grade != null)?.grade ?? null
        setPreviewGrade((prev) => prev ?? firstNumeric)
        if (grade === null && firstNumeric != null) {
          setEditGrade(firstNumeric)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load schedule')
      } finally {
        setLoading(false)
      }
    },
    [applyPayload],
  )

  useEffect(() => {
    void (async () => {
      try {
        const data = await fetchManagementBellSchedule(null)
        const firstNumeric = data.grades.find((g) => g.grade != null)?.grade ?? null
        await load(firstNumeric ?? null)
        if (firstNumeric != null) {
          setEditGrade(firstNumeric)
          setPreviewGrade(firstNumeric)
        }
      } catch {
        await load(null)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (previewGrade == null) {
      setGradeGrid(null)
      return
    }
    let cancelled = false
    setGradeLoading(true)
    void fetchGradeMasterSchedule(previewGrade)
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
  }, [previewGrade])

  async function onEditGradeChange(next: number | null) {
    setFlash(null)
    setEditGrade(next)
    await load(next)
  }

  async function onResetTemplate() {
    if (
      !window.confirm(
        'Reset to the simplified weekly template? This removes all current periods and class assignments for this schedule.',
      )
    ) {
      return
    }
    setSaving(true)
    setFlash(null)
    setError(null)
    try {
      const result = await resetBellSchedulePeriods(editGrade)
      setFlash(result.message || 'Bell periods reset.')
      if (result.bell_schedule) {
        setPeriods(result.bell_schedule.periods || [])
        setTitle(result.bell_schedule.title || title)
      }
      await load(editGrade)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed')
    } finally {
      setSaving(false)
    }
  }

  async function onSave() {
    setSaving(true)
    setFlash(null)
    setError(null)
    try {
      const payload = {
        title,
        grade_level: editGrade,
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
        setEditGrade(
          result.selected_grade !== undefined
            ? result.selected_grade
            : (result.bell_schedule.grade_level ?? null),
        )
      }
      if (previewGrade != null) {
        const grid = await fetchGradeMasterSchedule(previewGrade)
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

  const numericGrades = (hub?.grades || []).filter((g) => g.grade != null) as Array<{
    grade: number
    label: string
  }>

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

            <div className="flex flex-wrap gap-2" role="tablist" aria-label="Schedule sections">
              {SCHEDULE_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  className={['spa-mgmt-tab', activeTab === tab.id ? 'is-active' : ''].join(' ')}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <i className={`bi ${tab.icon}`} aria-hidden />
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'assign' ? (
              <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
                <div className="mb-4 flex flex-wrap items-end gap-3">
                  <div className="min-w-[160px] sm:max-w-xs">
                    <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-hub-muted">
                      Grade
                    </label>
                    <select
                      className={fieldInput}
                      value={editGrade === null ? '' : String(editGrade)}
                      onChange={(e) => {
                        const g = Number(e.target.value)
                        if (!Number.isFinite(g)) return
                        setEditGrade(g)
                        setPreviewGrade(g)
                        void load(g)
                      }}
                    >
                      {numericGrades.length === 0 ? (
                        <option value="">No grades</option>
                      ) : (
                        numericGrades.map((g) => (
                          <option key={g.grade} value={g.grade}>
                            {g.label}
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                </div>
                {editGrade != null ? (
                  <PeriodClassPlanner grade={editGrade} />
                ) : (
                  <p className="text-sm text-hub-muted">Select a grade to assign classes to periods.</p>
                )}
              </section>
            ) : null}

            {activeTab === 'periods' ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
              <div className="mb-4 flex flex-wrap items-end gap-3">
                <div className="min-w-[160px] flex-1 sm:max-w-xs">
                  <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Schedule is for
                  </label>
                  <select
                    className={fieldInput}
                    value={editGrade === null ? 'all' : String(editGrade)}
                    onChange={(e) => {
                      const v = e.target.value
                      void onEditGradeChange(v === 'all' ? null : Number(v))
                    }}
                  >
                    {(hub?.grades || [{ grade: null, label: 'All grades' }]).map((g) => (
                      <option
                        key={g.grade === null ? 'all' : `g-${g.grade}`}
                        value={g.grade === null ? 'all' : String(g.grade)}
                      >
                        {g.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="min-w-[220px] flex-[2]">
                  <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Schedule title
                  </label>
                  <input
                    className={fieldInput}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="spa-mgmt-btn-ghost px-3 py-2 text-sm"
                    onClick={() => setPeriods((prev) => [...prev, EMPTY_PERIOD()])}
                  >
                    <i className="bi bi-plus-lg" aria-hidden />
                    Add period
                  </button>
                  <button
                    type="button"
                    className="spa-mgmt-btn-ghost px-3 py-2 text-sm"
                    disabled={saving}
                    onClick={() => void onResetTemplate()}
                  >
                    <i className="bi bi-arrow-counterclockwise" aria-hidden />
                    Reset weekly template
                  </button>
                  <button
                    type="button"
                    className="spa-mgmt-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={saving || periods.length === 0}
                    onClick={() => void onSave()}
                  >
                    <i className="bi bi-check-lg" aria-hidden />
                    {saving ? 'Saving…' : 'Save bell schedule'}
                  </button>
                </div>
              </div>

              <p className="mb-3 text-sm text-hub-muted">
                Choose which weekdays each period appears on the grid. When assigning classes, you
                also pick which days that class meets within the period.
              </p>

              <div className="space-y-3">
                {periods.map((period, index) => (
                  <div
                    key={`period-${index}`}
                    className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 p-3"
                  >
                    <div className="flex flex-wrap items-end gap-2">
                      <div className="min-w-[8rem] flex-1 basis-[8rem]">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Name
                        </label>
                        <input
                          className={fieldInputSm}
                          value={period.name}
                          onChange={(e) => updatePeriod(index, { name: e.target.value })}
                        />
                      </div>
                      <div className="w-[8.5rem] shrink-0">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Kind
                        </label>
                        <select
                          className={fieldInputSm}
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
                      <div className="w-[7.25rem] shrink-0">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Start
                        </label>
                        <input
                          type="time"
                          className={fieldInputSm}
                          value={period.start_time}
                          onChange={(e) => updatePeriod(index, { start_time: e.target.value })}
                        />
                      </div>
                      <div className="w-[7.25rem] shrink-0">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          End
                        </label>
                        <input
                          type="time"
                          className={fieldInputSm}
                          value={period.end_time}
                          onChange={(e) => updatePeriod(index, { end_time: e.target.value })}
                        />
                      </div>
                      <div className="w-12 shrink-0">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Color
                        </label>
                        <input
                          type="color"
                          aria-label={`Color for ${period.name || 'period'}`}
                          className="h-8 w-10 cursor-pointer rounded border border-slate-300 bg-white p-0.5"
                          value={period.color_hex || '#5B8DEE'}
                          onChange={(e) => updatePeriod(index, { color_hex: e.target.value })}
                        />
                      </div>
                      <div className="ml-auto flex shrink-0 gap-1 pb-0.5">
                        <button
                          type="button"
                          className="spa-mgmt-btn-ghost px-2 py-1.5 text-sm"
                          onClick={() => movePeriod(index, -1)}
                          disabled={index === 0}
                          title="Move up"
                        >
                          <i className="bi bi-arrow-up" aria-hidden />
                        </button>
                        <button
                          type="button"
                          className="spa-mgmt-btn-ghost px-2 py-1.5 text-sm"
                          onClick={() => movePeriod(index, 1)}
                          disabled={index === periods.length - 1}
                          title="Move down"
                        >
                          <i className="bi bi-arrow-down" aria-hidden />
                        </button>
                        <button
                          type="button"
                          className="inline-flex items-center rounded-lg border border-red-200 bg-red-50 px-2 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-100"
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
                            className={['spa-mgmt-tab text-xs', on ? 'is-active' : ''].join(' ')}
                            onClick={() => toggleDay(index, d.value)}
                          >
                            {d.label}
                          </button>
                        )
                      })}
                    </div>
                    {period.kind === 'class' ? (
                      <div className="mt-2">
                        <label className="mb-1 block text-[10px] font-bold uppercase text-hub-muted">
                          Default label (optional)
                        </label>
                        <input
                          className={fieldInputSm}
                          placeholder="e.g. Electives — shows on days without a class"
                          value={period.usage_label || ''}
                          onChange={(e) => updatePeriod(index, { usage_label: e.target.value })}
                        />
                        {period.usage_label?.trim() ? (
                          <p className="mb-0 mt-1 text-[11px] text-amber-700">
                            “{period.usage_label.trim()}” appears on the schedule for any day this
                            period has no class assigned. You can still drag classes in.
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ))}
                {periods.length === 0 ? (
                  <p className="mb-0 text-sm text-hub-muted">
                    No periods yet. Click “Add period” or switch grade to load a seeded schedule.
                  </p>
                ) : null}
              </div>
            </section>
            ) : null}

            {activeTab === 'print' ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="mb-0 text-lg font-bold text-hub-text">Print by grade</h2>
                  <p className="mb-0 text-sm text-hub-muted">
                    Master schedule of all classes offered at that grade level
                  </p>
                </div>
                {previewGrade != null ? (
                  <a
                    href={gradeSchedulePdfUrl(previewGrade)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
                  >
                    <i className="bi bi-file-earmark-pdf" aria-hidden />
                    Download PDF
                  </a>
                ) : null}
              </div>

              {numericGrades.length === 0 ? (
                <p className="mb-0 text-sm text-hub-muted">No grade levels available.</p>
              ) : (
                <div className="mb-4 flex flex-wrap gap-2">
                  {numericGrades.map((g) => (
                    <button
                      key={g.grade}
                      type="button"
                      className={['spa-mgmt-tab', previewGrade === g.grade ? 'is-active' : ''].join(' ')}
                      onClick={() => setPreviewGrade(g.grade)}
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
            ) : null}
          </div>
        )}
      </div>
    </ManagementPageShell>
  )
}
