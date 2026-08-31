import { useCallback, useEffect, useState } from 'react'
import {
  assignClassToPeriod,
  fetchSchedulePlanner,
  unassignClassFromGradeSchedule,
  updateAssignmentDays,
} from '../../api/bellSchedule'
import type { PlannerAssignedClass, PlannerClassCard, PlannerPeriodRow } from '../../types/schedulePlanner'
import { showAppToast } from '../../utils/appToast'

type Props = {
  grade: number
}

const WEEKDAYS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
]

function labelDays(days: number[]): string {
  const labels = WEEKDAYS.filter((d) => days.includes(d.value)).map((d) => d.label)
  return labels.length ? labels.join(', ') : 'no days'
}

export function PeriodClassPlanner({ grade }: Props) {
  const [periods, setPeriods] = useState<PlannerPeriodRow[]>([])
  const [classes, setClasses] = useState<PlannerClassCard[]>([])
  const [gradeLabel, setGradeLabel] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragClassId, setDragClassId] = useState<number | null>(null)
  const [pendingAssign, setPendingAssign] = useState<{ classId: number; periodId: number } | null>(
    null,
  )
  const [pendingDays, setPendingDays] = useState<number[]>([0, 1, 2, 3, 4])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSchedulePlanner(grade)
      setPeriods(
        (data.periods || []).map((p) => ({
          ...p,
          days_of_week: p.days_of_week || [],
          day_labels: p.day_labels || [],
          assigned_classes: (p.assigned_classes || []).map((c) => ({
            ...c,
            days_of_week: c.days_of_week || [],
            day_labels: c.day_labels || [],
          })),
        })),
      )
      setClasses(
        (data.classes || []).map((c) => ({ ...c, placements: c.placements || [] })),
      )
      setGradeLabel(data.grade_label || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load planner')
    } finally {
      setLoading(false)
    }
  }, [grade])

  useEffect(() => {
    void load()
  }, [load])

  async function onAssign(classId: number, periodId: number, daysOfWeek: number[]) {
    setBusy(true)
    setError(null)
    try {
      const result = await assignClassToPeriod(classId, periodId, daysOfWeek)
      showAppToast(`Assigned on ${labelDays(result.days_of_week || daysOfWeek)}.`, 'success')
      setPendingAssign(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not assign class')
    } finally {
      setBusy(false)
    }
  }

  async function onUpdateDays(classId: number, periodId: number, daysOfWeek: number[]) {
    if (daysOfWeek.length === 0) return
    setBusy(true)
    setError(null)
    try {
      const result = await updateAssignmentDays(classId, periodId, daysOfWeek)
      showAppToast(`Now meets on ${labelDays(result.days_of_week || daysOfWeek)}.`, 'success')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update days')
    } finally {
      setBusy(false)
    }
  }

  async function onUnassign(classId: number, periodId?: number) {
    setBusy(true)
    setError(null)
    try {
      await unassignClassFromGradeSchedule(classId, grade, periodId)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not unassign class')
    } finally {
      setBusy(false)
    }
  }

  function handleDrop(periodId: number, e: React.DragEvent) {
    e.preventDefault()
    const raw = e.dataTransfer.getData('text/class-id') || String(dragClassId ?? '')
    const classId = Number.parseInt(raw, 10)
    if (!Number.isFinite(classId)) return
    const period = periods.find((p) => p.id === periodId)
    const periodDays = period?.days_of_week?.length ? period.days_of_week : [0, 1, 2, 3, 4]
    // Preselect only the days this class is still free, so dropping it into a
    // second period does not steal the days it already meets elsewhere.
    const taken = new Set(
      periods
        .filter((p) => p.id !== periodId)
        .flatMap((p) =>
          (p.assigned_classes || [])
            .filter((c) => c.class_id === classId)
            .flatMap((c) => c.days_of_week || []),
        ),
    )
    const free = periodDays.filter((day) => !taken.has(day))
    setPendingAssign({ classId, periodId })
    setPendingDays(free.length ? free : periodDays)
    setDragClassId(null)
  }

  function togglePendingDay(day: number) {
    setPendingDays((prev) => {
      const has = prev.includes(day)
      const next = has ? prev.filter((d) => d !== day) : [...prev, day].sort((a, b) => a - b)
      return next
    })
  }

  if (loading) {
    return <p className="text-sm text-hub-muted">Loading class planner…</p>
  }

  const classPeriods = periods.filter((p) => p.kind === 'class')
  const reservedPeriods = periods.filter((p) => p.kind !== 'class')
  const pendingPeriodDays = pendingAssign
    ? periods.find((p) => p.id === pendingAssign.periodId)?.days_of_week
    : undefined
  const pendingDayChoices = pendingPeriodDays?.length
    ? WEEKDAYS.filter((d) => pendingPeriodDays.includes(d.value))
    : WEEKDAYS

  return (
    <div className="space-y-3">
      <p className="mb-0 text-sm text-hub-muted">
        Drag a class into a period, then choose which days it meets. The same class can go in
        different periods on different days. Period times apply for {gradeLabel || 'this grade'} on
        the days you select.
      </p>
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
          {error}
        </div>
      ) : null}
      {busy ? (
        <p className="mb-0 text-xs font-semibold text-teal-800">Saving assignment…</p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-2">
          <h3 className="mb-0 text-sm font-bold uppercase tracking-wide text-hub-muted">
            Weekly periods
          </h3>
          {classPeriods.length === 0 ? (
            <p className="text-sm text-hub-muted">Add class periods in the editor first.</p>
          ) : (
            classPeriods.map((period) => (
              <div
                key={period.id}
                className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
                style={{ borderLeftWidth: 4, borderLeftColor: period.color_hex }}
                onDragOver={(e) => {
                  e.preventDefault()
                  e.dataTransfer.dropEffect = 'move'
                }}
                onDrop={(e) => handleDrop(period.id, e)}
              >
                <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 bg-slate-50 px-3 py-2">
                  <div>
                    <p className="mb-0 text-sm font-bold text-hub-text">{period.name}</p>
                    <p className="mb-0 text-xs text-hub-muted">
                      {(period.day_labels || []).join(' · ')}
                      {(period.day_labels?.length ? ' · ' : '') +
                        (period.time_str || `${period.start_time}–${period.end_time}`)}
                      {period.usage_label?.trim() ? (
                        <span className="ms-1 font-semibold text-amber-800">
                          · shows “{period.usage_label.trim()}” on days without a class
                        </span>
                      ) : null}
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-700">
                    Drop class here
                  </span>
                </div>
                <div className="min-h-[3.5rem] space-y-1.5 p-2">
                  {(period.assigned_classes || []).length === 0 ? (
                    <p className="mb-0 px-1 py-2 text-xs text-hub-muted">
                      {period.usage_label?.trim()
                        ? `No class yet — “${period.usage_label.trim()}” shows on empty days`
                        : 'No class assigned'}
                    </p>
                  ) : (
                    (period.assigned_classes || []).map((c) => (
                      <AssignedClassChip
                        key={c.class_id}
                        card={c}
                        periodId={period.id}
                        periodDays={period.days_of_week}
                        busy={busy}
                        onRemove={() => void onUnassign(c.class_id, period.id)}
                        onDaysChange={(days) => void onUpdateDays(c.class_id, period.id, days)}
                      />
                    ))
                  )}
                </div>
              </div>
            ))
          )}
          {reservedPeriods.map((period) => (
            <div
              key={period.id}
              className="rounded-lg px-3 py-2 text-center text-xs font-bold uppercase tracking-wide text-slate-700"
              style={{ backgroundColor: period.color_hex }}
            >
              {period.name} · {period.time_str}
              {period.usage_label?.trim() ? (
                <span className="ml-1 font-extrabold">· {period.usage_label.trim()}</span>
              ) : null}
            </div>
          ))}
        </div>

        <div className="min-w-0">
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-hub-muted">
            Classes ({gradeLabel})
          </h3>
          <div className="max-h-[32rem] space-y-2 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-2">
            {classes.length === 0 ? (
              <p className="mb-0 px-2 py-4 text-center text-sm text-hub-muted">
                No classes for this grade yet.
              </p>
            ) : (
              classes.map((c) => (
                <ClassChip
                  key={c.class_id}
                  card={c}
                  draggable
                  onDragStart={() => setDragClassId(c.class_id)}
                  onDragEnd={() => setDragClassId(null)}
                />
              ))
            )}
          </div>
          <p className="mt-2 mb-0 text-xs text-hub-muted">
            A class can sit in more than one period — drag it again and pick different days. Taking a
            day here removes it from whichever period had it.
          </p>
        </div>
      </div>

      {pendingAssign ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="assign-days-title"
        >
          <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
            <h2 id="assign-days-title" className="mb-1 text-lg font-bold text-hub-text">
              Which days?
            </h2>
            <p className="mb-4 text-sm text-hub-muted">
              Select the weekdays this class meets during{' '}
              {periods.find((p) => p.id === pendingAssign.periodId)?.name || 'this period'}. Other
              classes can use the same period on the days you leave off, and this class keeps any
              other period it sits in on the remaining days.
            </p>
            <div className="mb-4 flex flex-wrap gap-2">
              {pendingDayChoices.map((d) => {
                const on = pendingDays.includes(d.value)
                return (
                  <button
                    key={d.value}
                    type="button"
                    className={['spa-mgmt-tab text-sm', on ? 'is-active' : ''].join(' ')}
                    onClick={() => togglePendingDay(d.value)}
                  >
                    {d.label}
                  </button>
                )
              })}
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="spa-mgmt-btn-ghost px-4 py-2 text-sm"
                onClick={() => setPendingAssign(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="spa-mgmt-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                disabled={pendingDays.length === 0 || busy}
                onClick={() =>
                  void onAssign(pendingAssign.classId, pendingAssign.periodId, pendingDays)
                }
              >
                Assign
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function AssignedClassChip({
  card,
  periodId,
  periodDays,
  busy,
  onRemove,
  onDaysChange,
}: {
  card: PlannerAssignedClass
  periodId: number
  periodDays?: number[]
  busy: boolean
  onRemove: () => void
  onDaysChange: (days: number[]) => void
}) {
  const selectedDays = card.days_of_week || []
  const dayChoices = periodDays?.length
    ? WEEKDAYS.filter((d) => periodDays.includes(d.value))
    : WEEKDAYS

  function toggleDay(day: number) {
    const has = selectedDays.includes(day)
    const next = has
      ? selectedDays.filter((d) => d !== day)
      : [...selectedDays, day].sort((a, b) => a - b)
    if (next.length === 0) return
    onDaysChange(next)
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="mb-0 truncate text-sm font-bold text-hub-text">{card.class_name}</p>
          <p className="mb-0 truncate text-xs text-hub-muted">
            {card.subject} · {card.teacher_name}
            {card.schedule_text ? ` · ${card.schedule_text}` : ''}
          </p>
        </div>
        <button
          type="button"
          className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-red-200 bg-red-50 text-sm font-bold text-red-700 hover:bg-red-100"
          title="Remove from period"
          onClick={onRemove}
        >
          ×
        </button>
      </div>
      <p className="mb-1 mt-2 text-[10px] font-bold uppercase tracking-wide text-hub-muted">
        Meets: {labelDays(selectedDays)}
      </p>
      <div className="flex flex-wrap gap-1">
        {dayChoices.map((d) => {
          const on = selectedDays.includes(d.value)
          return (
            <button
              key={`${periodId}-${card.class_id}-${d.value}`}
              type="button"
              disabled={busy}
              className={[
                'rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase',
                on
                  ? 'border-teal-600 bg-teal-600 text-white'
                  : 'border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300',
              ].join(' ')}
              onClick={() => toggleDay(d.value)}
            >
              {d.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ClassChip({
  card,
  draggable,
  onDragStart,
  onDragEnd,
}: {
  card: PlannerClassCard
  draggable?: boolean
  onDragStart?: () => void
  onDragEnd?: () => void
}) {
  const placements = card.placements || []
  return (
    <div
      draggable={draggable}
      onDragStart={(e) => {
        e.dataTransfer.setData('text/class-id', String(card.class_id))
        e.dataTransfer.effectAllowed = 'move'
        onDragStart?.()
      }}
      onDragEnd={onDragEnd}
      className={`flex items-start justify-between gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2 shadow-sm ${
        draggable ? 'cursor-grab active:cursor-grabbing' : ''
      }`}
    >
      <div className="min-w-0">
        <p className="mb-0 truncate text-sm font-bold text-hub-text">{card.class_name}</p>
        <p className="mb-0 truncate text-xs text-hub-muted">
          {card.subject} · {card.teacher_name}
        </p>
        {placements.length ? (
          <div className="mt-1 flex flex-wrap gap-1">
            {placements.map((placement) => (
              <span
                key={placement.period_id}
                className="rounded-md bg-teal-50 px-1.5 py-0.5 text-[10px] font-bold uppercase text-teal-800"
              >
                {placement.period_name} · {labelDays(placement.days_of_week)}
              </span>
            ))}
          </div>
        ) : (
          <span className="mt-1 inline-block rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-500">
            Not scheduled
          </span>
        )}
      </div>
      <i className="bi bi-grip-vertical shrink-0 text-hub-muted" aria-hidden />
    </div>
  )
}
