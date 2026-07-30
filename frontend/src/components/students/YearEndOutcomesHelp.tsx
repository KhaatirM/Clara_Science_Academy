import { useId, useState } from 'react'

const HELP_POINTS = [
  {
    title: 'Default at year finalize',
    body: 'If you never use these buttons, every enrolled student is still promoted one grade when the school year is finalized (except anyone marked repeating, graduate, withdraw, or already in 12th).',
  },
  {
    title: 'Promote',
    body: 'Moves the student up one grade right away (or stages promote for finalize if “end-of-year intent only” is checked).',
  },
  {
    title: 'Graduate',
    body: 'Marks middle-school completion: off the active roster as alumni; profile and report cards kept. Grade stays at the finished level (e.g. 8th).',
  },
  {
    title: 'Withdraw',
    body: 'Removes the student to the former/withdrawn roster (or stages withdraw for finalize). Records are preserved.',
  },
  {
    title: 'Repeat grade',
    body: 'Keeps the same grade and flags repeating so finalize does not promote them. Graduation year may bump when known.',
  },
  {
    title: 'Stage as end-of-year intent only',
    body: 'When checked on the Students page, buttons only save what should happen at year finalize—they do not change grade or roster now.',
  },
] as const

type HelpTone = 'onTeal' | 'muted'

export function YearEndOutcomesHelp({
  tone = 'onTeal',
  title = 'Grade & exit actions',
  className = '',
}: {
  tone?: HelpTone
  title?: string
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const triggerClass =
    tone === 'onTeal'
      ? 'inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/30 bg-white/15 text-white transition hover:bg-white/25'
      : 'inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-teal-800 transition hover:bg-teal-50'

  return (
    <div className={`relative inline-flex ${className}`}>
      <button
        type="button"
        className={triggerClass}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={`Help: ${title}`}
        title={`How ${title.toLowerCase()} work`}
        onClick={() => setOpen((v) => !v)}
      >
        <i className="bi bi-question-lg text-sm font-bold" aria-hidden />
      </button>
      {open ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-[40] cursor-default bg-transparent"
            aria-label="Close help"
            onClick={() => setOpen(false)}
          />
          <div
            id={panelId}
            role="dialog"
            aria-label={`${title} help`}
            className="absolute right-0 top-full z-[50] mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-xl"
          >
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <p className="mb-0 text-xs font-bold uppercase tracking-wide text-teal-800">How this works</p>
                <p className="mb-0 mt-1 text-sm font-semibold text-hub-text">{title}</p>
              </div>
              <button
                type="button"
                className="rounded-lg px-2 py-1 text-sm text-hub-muted hover:bg-slate-100"
                onClick={() => setOpen(false)}
              >
                Close
              </button>
            </div>
            <ul className="mb-0 space-y-3 pl-0">
              {HELP_POINTS.map((item) => (
                <li key={item.title} className="list-none">
                  <p className="mb-0.5 text-sm font-semibold text-hub-text">{item.title}</p>
                  <p className="mb-0 text-xs leading-relaxed text-hub-muted">{item.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </>
      ) : null}
    </div>
  )
}
