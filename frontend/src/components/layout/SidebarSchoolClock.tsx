import { useEffect, useState } from 'react'
import type { SchoolTimezone } from '../../types/session'
import { formatSchoolTime, resolveSchoolTimezone } from '../../utils/schoolTimezone'

interface SidebarSchoolClockProps {
  timezone: SchoolTimezone | null
  collapsed: boolean
}

export function SidebarSchoolClock({ timezone, collapsed }: SidebarSchoolClockProps) {
  const resolved = resolveSchoolTimezone(timezone)
  const [display, setDisplay] = useState(() =>
    formatSchoolTime(resolved.iana, resolved.clock, resolved.zone),
  )

  useEffect(() => {
    const next = resolveSchoolTimezone(timezone)
    setDisplay(formatSchoolTime(next.iana, next.clock, next.zone))
  }, [timezone])

  useEffect(() => {
    if (collapsed) return

    const tick = () => {
      const tz = resolveSchoolTimezone(timezone)
      setDisplay(formatSchoolTime(tz.iana, tz.clock, tz.zone))
    }

    tick()
    const id = window.setInterval(tick, 30_000)
    return () => window.clearInterval(id)
  }, [timezone, collapsed])

  if (collapsed) return null

  return (
    <div
      className="spa-sidebar-school-tz mx-[0.65rem] mb-2 rounded-[10px] border border-white/20 bg-white/10 px-[0.65rem] py-[0.55rem] text-center leading-tight text-slate-100"
      title="School timezone for due dates and schedules"
      data-iana={resolved.iana}
    >
      <div className="flex flex-wrap items-center justify-center gap-x-[0.45rem] gap-y-[0.35rem] text-[0.92rem] font-bold tracking-wide">
        <i className="bi bi-clock text-[0.95rem] text-sky-300" aria-hidden />
        <time className="tabular-nums">{display.clock || '--:-- --'}</time>
        {display.zone ? (
          <span className="inline-block rounded-full bg-white/15 px-[0.4rem] py-[0.1rem] text-[0.68rem] font-extrabold uppercase tracking-wide">
            {display.zone}
          </span>
        ) : null}
      </div>
      <span className="mt-[0.3rem] block break-words text-[0.68rem] font-semibold text-white/75">
        {resolved.iana}
      </span>
    </div>
  )
}
