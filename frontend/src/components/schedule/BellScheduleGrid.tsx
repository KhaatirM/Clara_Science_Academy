import type { BellGridPayload } from '../../types/bellSchedule'

type Props = {
  grid: BellGridPayload
  pdfUrl?: string | null
  showTeacher?: boolean
  compactListDays?: Array<{
    day_index: number
    day_name: string
    is_today: boolean
    blocks: Array<{
      class_id: number
      class_name: string
      subject: string
      time_str: string
      room: string
      teacher_name?: string
      student_count?: number
      is_now?: boolean
      is_upcoming?: boolean
      links?: { view_class?: string }
    }>
  }>
  onOpenClass?: (href: string) => void
}

function contrastText(hex: string): string {
  const raw = (hex || '#4A90D9').replace('#', '')
  if (raw.length < 6) return '#0f172a'
  const r = parseInt(raw.slice(0, 2), 16)
  const g = parseInt(raw.slice(2, 4), 16)
  const b = parseInt(raw.slice(4, 6), 16)
  const luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luma > 0.62 ? '#0f172a' : '#ffffff'
}

export function BellScheduleGrid({
  grid,
  pdfUrl,
  showTeacher = true,
  compactListDays,
  onOpenClass,
}: Props) {
  const title = grid.bell_schedule?.title || 'Bell Schedule'
  const columns = grid.day_columns || []
  const weekendDays = (compactListDays || []).filter((d) => d.day_index >= 5 && d.blocks.length > 0)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="mb-0 text-lg font-bold text-hub-text">{title}</h2>
          <p className="mb-0 text-sm text-hub-muted">Mon–Fri period grid · classes placed by meeting time</p>
        </div>
        {pdfUrl ? (
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-teal-800"
          >
            <i className="bi bi-file-earmark-pdf" aria-hidden />
            Download PDF
          </a>
        ) : null}
      </div>

      {columns.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-5 py-10 text-center text-hub-muted">
          No bell schedule configured yet.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
          <div className="grid min-w-[720px] grid-cols-5 gap-2">
            {columns.map((day) => (
              <div key={day.day_index} className="min-w-0">
                <div
                  className={`mb-2 rounded-lg px-2 py-2 text-center text-xs font-bold uppercase tracking-wide ${
                    day.is_today
                      ? 'bg-teal-700 text-white'
                      : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {day.day_name}
                  {day.is_today ? ' · Today' : ''}
                </div>
                <div className="space-y-1.5">
                  {day.cells.map((cell) => {
                    const text = contrastText(cell.color_hex)
                    const usageLabel = cell.usage_label?.trim() || ''
                    const isFixed = cell.kind !== 'class'
                    return (
                      <div
                        key={`${day.day_index}-${cell.period_id}`}
                        className={`rounded-md px-2 py-1.5 text-[11px] leading-snug shadow-sm ${
                          cell.is_now ? 'ring-2 ring-offset-1 ring-amber-400' : ''
                        }`}
                        style={{ backgroundColor: cell.color_hex, color: text }}
                      >
                        {isFixed ? (
                          <>
                            <div className="text-center text-[10px] font-extrabold uppercase tracking-wider">
                              {cell.name}
                            </div>
                            <div className="text-center opacity-90">{cell.time_str}</div>
                          </>
                        ) : (
                          <>
                            <div className="font-extrabold">{cell.name}</div>
                            <div className="opacity-90">{cell.time_str}</div>
                            {usageLabel ? (
                              <div className="mt-1 font-bold uppercase tracking-wide">
                                {usageLabel}
                              </div>
                            ) : cell.classes.length === 0 ? (
                              <div className="mt-1 opacity-70">—</div>
                            ) : (
                              <ul className="mb-0 mt-1 list-none space-y-1 p-0">
                                {cell.classes.map((c) => (
                                  <li key={`${c.class_id}-${c.time_str}`}>
                                    <div className="font-bold">{c.class_name}</div>
                                    <div className="opacity-85">
                                      Rm {c.room}
                                      {showTeacher && c.teacher_name ? ` · ${c.teacher_name}` : ''}
                                      {!showTeacher && c.student_count != null
                                        ? ` · ${c.student_count} students`
                                        : ''}
                                    </div>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {grid.unmapped && grid.unmapped.length > 0 ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
          <h3 className="mb-2 text-sm font-bold text-amber-950">Unmapped class times</h3>
          <ul className="mb-0 space-y-1 text-sm text-amber-950">
            {grid.unmapped.map((u) => (
              <li key={`${u.class_id}-${u.day_index}-${u.time_str}`}>
                <strong>{u.day_name}</strong>: {u.class_name} ({u.time_str}) · Rm {u.room}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {weekendDays.length > 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
          <h3 className="mb-2 text-sm font-bold text-hub-text">Weekend</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {weekendDays.map((day) => (
              <div key={day.day_index}>
                <p className="mb-1 text-xs font-bold uppercase text-hub-muted">{day.day_name}</p>
                <ul className="mb-0 space-y-1 text-sm">
                  {day.blocks.map((b) => (
                    <li key={`${b.class_id}-${b.time_str}`}>
                      {b.time_str} — {b.class_name}
                      {b.links?.view_class && onOpenClass ? (
                        <>
                          {' '}
                          <button
                            type="button"
                            className="font-bold text-teal-800 underline"
                            onClick={() => onOpenClass(b.links!.view_class!)}
                          >
                            Open
                          </button>
                        </>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
