export type QuizMode = 'quiz' | 'test'

type Props = {
  value: QuizMode
  onChange: (mode: QuizMode) => void
  disabled?: boolean
  disabledReason?: string
}

const OPTIONS: Array<{ id: QuizMode; label: string; icon: string; blurb: string }> = [
  {
    id: 'quiz',
    label: 'Quiz',
    icon: 'bi-ui-checks',
    blurb: 'Standard quiz. Students can switch tabs and resume saved progress.',
  },
  {
    id: 'test',
    label: 'Test (lockdown)',
    icon: 'bi-shield-lock',
    blurb: 'Camera and entire-screen monitoring. Leaving the tab auto-submits and locks the test.',
  },
]

export function QuizModeToggle({ value, onChange, disabled, disabledReason }: Props) {
  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Quiz or test">
        {OPTIONS.map((opt) => {
          const active = value === opt.id
          return (
            <button
              key={opt.id}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              onClick={() => onChange(opt.id)}
              className={`flex items-start gap-3 rounded-xl border-2 p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                active
                  ? opt.id === 'test'
                    ? 'border-red-500 bg-red-50'
                    : 'border-teal-600 bg-teal-50'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <i
                className={`bi ${opt.icon} mt-0.5 text-xl ${
                  active ? (opt.id === 'test' ? 'text-red-600' : 'text-teal-700') : 'text-slate-400'
                }`}
                aria-hidden
              />
              <span>
                <span className="block text-sm font-bold text-slate-900">{opt.label}</span>
                <span className="mt-0.5 block text-xs text-slate-600">{opt.blurb}</span>
              </span>
            </button>
          )
        })}
      </div>
      {disabled && disabledReason ? <p className="mt-2 text-xs text-hub-muted">{disabledReason}</p> : null}
      {value === 'test' && !disabled ? (
        <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900">
          <p className="font-semibold">How lockdown tests work</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            <li>Students must allow their camera and share their entire screen before starting.</li>
            <li>Screen and camera images are captured every ~10 seconds, along with mouse activity.</li>
            <li>Leaving the tab, switching windows, reloading, or stopping sharing auto-submits and locks the test.</li>
            <li>You can review the recording and unlock a student to grant one retake.</li>
            <li>Saved progress and timer pausing are turned off for tests.</li>
          </ul>
        </div>
      ) : null}
    </div>
  )
}
