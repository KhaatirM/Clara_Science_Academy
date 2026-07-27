import { useEffect, useState } from 'react'
import {
  dismissAppToast,
  subscribeAppToasts,
  type AppToastItem,
  type AppToastTone,
} from '../../utils/appToast'

const TONE_STYLES: Record<
  AppToastTone,
  {
    shell: string
    chip: string
    icon: string
    iconClass: string
    label: string
    labelClass: string
  }
> = {
  success: {
    shell: 'border-emerald-200/90 from-emerald-50/95 via-white to-white',
    chip: 'bg-emerald-100 ring-emerald-200/80',
    icon: 'bi-check-circle-fill',
    iconClass: 'text-emerald-600',
    label: 'Success',
    labelClass: 'text-emerald-800',
  },
  danger: {
    shell: 'border-rose-200/90 from-rose-50/95 via-white to-white',
    chip: 'bg-rose-100 ring-rose-200/80',
    icon: 'bi-exclamation-octagon-fill',
    iconClass: 'text-rose-600',
    label: 'Error',
    labelClass: 'text-rose-800',
  },
  warning: {
    shell: 'border-amber-200/90 from-amber-50/95 via-white to-white',
    chip: 'bg-amber-100 ring-amber-200/80',
    icon: 'bi-exclamation-triangle-fill',
    iconClass: 'text-amber-600',
    label: 'Warning',
    labelClass: 'text-amber-900',
  },
  info: {
    shell: 'border-sky-200/90 from-sky-50/95 via-white to-white',
    chip: 'bg-sky-100 ring-sky-200/80',
    icon: 'bi-info-circle-fill',
    iconClass: 'text-sky-600',
    label: 'Notice',
    labelClass: 'text-sky-800',
  },
}

export function AppToastHost() {
  const [toasts, setToasts] = useState<AppToastItem[]>([])

  useEffect(() => subscribeAppToasts(setToasts), [])

  if (!toasts.length) return null

  return (
    <div
      className="pointer-events-none fixed bottom-[4.75rem] right-4 z-[1090] flex w-[min(22rem,calc(100vw-2rem))] flex-col-reverse gap-2.5"
      aria-live="polite"
      aria-relevant="additions"
    >
      {toasts.map((toast) => {
        const style = TONE_STYLES[toast.tone]
        return (
          <div
            key={toast.id}
            className={[
              'pointer-events-auto spa-app-toast flex items-start gap-3 rounded-2xl border bg-gradient-to-br',
              'px-3.5 py-3 shadow-[0_14px_36px_rgba(15,23,42,0.16)] ring-1 ring-black/5 backdrop-blur-md',
              style.shell,
            ].join(' ')}
            role="status"
          >
            <span
              className={[
                'mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-1',
                style.chip,
              ].join(' ')}
              aria-hidden
            >
              <i className={`bi ${style.icon} text-sm ${style.iconClass}`} />
            </span>
            <div className="min-w-0 flex-1 pt-0.5">
              <p
                className={[
                  'mb-0.5 text-[0.68rem] font-bold uppercase tracking-[0.14em]',
                  style.labelClass,
                ].join(' ')}
              >
                {style.label}
              </p>
              <p className="mb-0 text-sm font-medium leading-snug text-slate-800">{toast.message}</p>
            </div>
            <button
              type="button"
              className="shrink-0 rounded-lg p-1 text-slate-400 transition hover:bg-slate-900/5 hover:text-slate-700"
              aria-label="Dismiss"
              onClick={() => dismissAppToast(toast.id)}
            >
              <i className="bi bi-x-lg text-xs" aria-hidden />
            </button>
          </div>
        )
      })}
    </div>
  )
}
