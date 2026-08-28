import { useCallback, useEffect, useState } from 'react'
import {
  assignClassToPeriod,
  fetchSchedulePlanner,
  unassignClassFromGradeSchedule,
} from '../../api/bellSchedule'
import type { PlannerClassCard, PlannerPeriodRow } from '../../types/schedulePlanner'

type Props = {
  grade: number
}

export function PeriodClassPlanner({ grade }: Props) {
  const [periods, setPeriods] = useState<PlannerPeriodRow[]>([])
  const [unassigned, setUnassigned] = useState<PlannerClassCard[]>([])
  const [gradeLabel, setGradeLabel] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragClassId, setDragClassId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSchedulePlanner(grade)
      setPeriods(data.periods || [])
      setUnassigned(data.unassigned_classes || [])
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

  async function onAssign(classId: number, periodId: number) {
    setBusy(true)
    setError(null)
    try {
      await assignClassToPeriod(classId, periodId)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not assign class')
    } finally {
      setBusy(false)
    }
  }

  async function onUnassign(classId: number) {
    setBusy(true)
    setError(null)
    try {
      await unassignClassFromGradeSchedule(classId, grade)
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
    void onAssign(classId, periodId)
    setDragClassId(null)
  }

  if (loading) {
    return <p className="text-sm text-hub-muted">Loading class planner…</p>
  }

  const classPeriods = periods.filter((p) => p.kind === 'class')

  return (
    <div className="space-y-3">
      <p className="mb-0 text-sm text-hub-muted">
        Drag classes from the right into a period on the left. Times on the class are updated
        automatically for {gradeLabel || 'this grade'}.
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
            Periods &amp; days
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
                      {(period.day_labels || []).join(' · ')} · {period.time_str || `${period.start_time}–${period.end_time}`}
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-700">
                    Drop class here
                  </span>
                </div>
                <div className="min-h-[3.5rem] space-y-1.5 p-2">
                  {period.assigned_classes.length === 0 ? (
                    <p className="mb-0 px-1 py-2 text-xs text-hub-muted">No class assigned</p>
                  ) : (
                    period.assigned_classes.map((c) => (
                      <ClassChip
                        key={c.class_id}
                        card={c}
                        draggable={false}
                        onRemove={() => void onUnassign(c.class_id)}
                      />
                    ))
                  )}
                </div>
              </div>
            ))
          )}
          {periods
            .filter((p) => p.kind !== 'class')
            .map((period) => (
              <div
                key={period.id}
                className="rounded-lg px-3 py-2 text-center text-xs font-bold uppercase tracking-wide text-slate-700"
                style={{ backgroundColor: period.color_hex }}
              >
                {period.name} · {(period.day_labels || []).join('/')} · {period.time_str}
              </div>
            ))}
        </div>

        <div className="min-w-0">
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-hub-muted">
            Classes ({gradeLabel})
          </h3>
          <div className="max-h-[32rem] space-y-2 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-2">
            {unassigned.length === 0 ? (
              <p className="mb-0 px-2 py-4 text-center text-sm text-hub-muted">
                All classes for this grade are assigned to a period.
              </p>
            ) : (
              unassigned.map((c) => (
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
            Assigned classes appear in their period on the left. Remove with × to drag again.
          </p>
        </div>
      </div>
    </div>
  )
}

function ClassChip({
  card,
  draggable,
  onDragStart,
  onDragEnd,
  onRemove,
}: {
  card: PlannerClassCard
  draggable?: boolean
  onDragStart?: () => void
  onDragEnd?: () => void
  onRemove?: () => void
}) {
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
          {card.schedule_text ? ` · ${card.schedule_text}` : ''}
        </p>
      </div>
      {onRemove ? (
        <button
          type="button"
          className="btn btn-sm btn-outline-danger shrink-0 px-2 py-0"
          title="Remove from period"
          onClick={onRemove}
        >
          ×
        </button>
      ) : (
        <i className="bi bi-grip-vertical shrink-0 text-hub-muted" aria-hidden />
      )}
    </div>
  )
}
