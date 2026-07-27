import { useMemo, useState } from 'react'

const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri'] as const
const DAY_LABELS: Record<(typeof DAYS)[number], string> = {
  mon: 'Mon',
  tue: 'Tue',
  wed: 'Wed',
  thu: 'Thu',
  fri: 'Fri',
}

const DAY_FROM_LABEL: Record<string, (typeof DAYS)[number]> = {
  mon: 'mon',
  monday: 'mon',
  tue: 'tue',
  tuesday: 'tue',
  wed: 'wed',
  wednesday: 'wed',
  thu: 'thu',
  thursday: 'thu',
  fri: 'fri',
  friday: 'fri',
}

type SlotKey = `${(typeof DAYS)[number]}-${string}`

function formatDisplay(hour: number, minute: number) {
  const period = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  return `${displayHour}:${minute.toString().padStart(2, '0')} ${period}`
}

function buildTimeSlots() {
  const slots: { value: string; display: string }[] = []
  for (let hour = 8; hour <= 15; hour++) {
    const startMinute = hour === 8 ? 30 : 0
    const endMinute = hour === 15 ? 30 : 60
    for (let minute = startMinute; minute < endMinute; minute += 30) {
      const value = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
      slots.push({ value, display: formatDisplay(hour, minute) })
    }
  }
  return slots
}

function parseTime(timeStr: string) {
  const [hours, minutes] = timeStr.split(':').map(Number)
  return hours * 60 + minutes
}

function add30Minutes(timeStr: string) {
  const [hours, minutes] = timeStr.split(':').map(Number)
  let newMinutes = minutes + 30
  let newHours = hours
  if (newMinutes >= 60) {
    newMinutes = 0
    newHours += 1
  }
  return `${newHours.toString().padStart(2, '0')}:${newMinutes.toString().padStart(2, '0')}`
}

function formatTimeForDisplay(timeStr: string) {
  const [hours, minutes] = timeStr.split(':').map(Number)
  return formatDisplay(hours, minutes)
}

function parseDisplayTime(display: string): string | null {
  const match = display.trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i)
  if (!match) return null
  let hour = Number.parseInt(match[1], 10)
  const minute = Number.parseInt(match[2], 10)
  const period = match[3].toUpperCase()
  if (period === 'PM' && hour !== 12) hour += 12
  if (period === 'AM' && hour === 12) hour = 0
  return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
}

/** Parse stored schedule text into grid slot keys (Mon 9:00 AM-10:00 AM, …). */
export function parseScheduleToSlots(scheduleStr: string): Record<SlotKey, boolean> {
  const slots: Record<SlotKey, boolean> = {}
  if (!scheduleStr.trim()) return slots

  const validSlotTimes = new Set(buildTimeSlots().map((s) => s.value))

  for (const entry of scheduleStr.split(',')) {
    const trimmed = entry.trim()
    if (!trimmed) continue
    const parts = trimmed.split(/\s+/)
    if (parts.length < 2) continue

    const day = DAY_FROM_LABEL[parts[0].toLowerCase()]
    if (!day) continue

    const timePart = parts.slice(1).join(' ')
    let startDisplay: string
    let endDisplay: string
    if (timePart.includes('-')) {
      const [start, end] = timePart.split('-', 2)
      startDisplay = start.trim()
      endDisplay = end.trim()
    } else {
      startDisplay = timePart.trim()
      const start24 = parseDisplayTime(startDisplay)
      if (!start24) continue
      const endMinutes = parseTime(start24) + 60
      const endHours = Math.floor(endMinutes / 60)
      const endMins = endMinutes % 60
      endDisplay = formatDisplay(endHours, endMins)
    }

    const start24 = parseDisplayTime(startDisplay)
    const end24 = parseDisplayTime(endDisplay)
    if (!start24 || !end24) continue

    let cursor = start24
    const endMinutes = parseTime(end24)
    while (parseTime(cursor) < endMinutes) {
      if (validSlotTimes.has(cursor)) {
        slots[`${day}-${cursor}` as SlotKey] = true
      }
      cursor = add30Minutes(cursor)
    }
  }

  return slots
}

function groupConsecutiveTimes(times: string[]) {
  if (!times.length) return []
  const sorted = [...times].sort()
  const ranges: { start: string; end: string }[] = []
  let currentStart = sorted[0]
  let currentEnd = sorted[0]
  for (let i = 1; i < sorted.length; i++) {
    if (parseTime(sorted[i]) - parseTime(currentEnd) === 30) {
      currentEnd = sorted[i]
    } else {
      ranges.push({ start: currentStart, end: add30Minutes(currentEnd) })
      currentStart = sorted[i]
      currentEnd = sorted[i]
    }
  }
  ranges.push({ start: currentStart, end: add30Minutes(currentEnd) })
  return ranges
}

function serializeSlots(slots: Record<SlotKey, boolean>) {
  const parts: string[] = []
  for (const day of DAYS) {
    const daySlots = Object.keys(slots)
      .filter((key) => key.startsWith(`${day}-`) && slots[key as SlotKey])
      .map((key) => key.split('-')[1])
      .sort()
    for (const range of groupConsecutiveTimes(daySlots)) {
      const start = formatTimeForDisplay(range.start)
      const end = formatTimeForDisplay(range.end)
      parts.push(range.start === range.end ? `${DAY_LABELS[day]} ${start}` : `${DAY_LABELS[day]} ${start}-${end}`)
    }
  }
  return parts.join(', ')
}

export function ScheduleBuilder({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const timeSlots = useMemo(() => buildTimeSlots(), [])
  const [slots, setSlots] = useState<Record<SlotKey, boolean>>(() => parseScheduleToSlots(value))

  const toggle = (day: (typeof DAYS)[number], time: string) => {
    const key = `${day}-${time}` as SlotKey
    setSlots((prev) => {
      const next = { ...prev, [key]: !prev[key] }
      onChange(serializeSlots(next))
      return next
    })
  }

  const clearAll = () => {
    setSlots({})
    onChange('')
  }

  return (
    <div>
      <div className="max-h-52 overflow-auto rounded-lg border border-slate-200">
        <table className="w-full min-w-[32rem] border-collapse text-[0.65rem]">
          <thead className="sticky top-0 z-10 bg-slate-800 text-white">
            <tr>
              <th className="px-1.5 py-1 text-left font-semibold">Time</th>
              {DAYS.map((d) => (
                <th key={d} className="px-1 py-1 text-center font-semibold">
                  {DAY_LABELS[d]}
                </th>
              ))}
              <th className="bg-slate-600 px-1 py-1 text-center text-slate-300">Sat</th>
              <th className="bg-slate-600 px-1 py-1 text-center text-slate-300">Sun</th>
            </tr>
          </thead>
          <tbody>
            {timeSlots.map((slot) => (
              <tr key={slot.value} className="border-t border-slate-100">
                <td className="whitespace-nowrap bg-slate-50 px-1.5 py-0.5 font-medium text-slate-600">{slot.display}</td>
                {DAYS.map((day) => {
                  const key = `${day}-${slot.value}` as SlotKey
                  const active = !!slots[key]
                  return (
                    <td key={day} className="p-0.5">
                      <button
                        type="button"
                        onClick={() => toggle(day, slot.value)}
                        className={`h-5 w-full rounded-sm border transition ${
                          active
                            ? 'border-teal-600 bg-teal-500 hover:bg-teal-600'
                            : 'border-slate-200 bg-white hover:border-teal-300 hover:bg-teal-50'
                        }`}
                        aria-label={`${DAY_LABELS[day]} ${slot.display}`}
                        aria-pressed={active}
                      />
                    </td>
                  )
                })}
                <td className="bg-slate-100 p-0.5">
                  <div className="h-5 rounded-sm bg-slate-200" />
                </td>
                <td className="bg-slate-100 p-0.5">
                  <div className="h-5 rounded-sm bg-slate-200" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          onClick={clearAll}
          className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 hover:border-red-300 hover:text-red-700"
        >
          <i className="bi bi-x-circle me-1" aria-hidden />
          Clear all
        </button>
        <p className="text-[0.68rem] text-hub-muted">Click slots to mark meetings. Weekends disabled.</p>
      </div>
      {value ? <p className="mt-1 truncate text-xs text-teal-800">{value}</p> : null}
    </div>
  )
}
