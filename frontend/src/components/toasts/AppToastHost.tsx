import { useEffect, useState } from 'react'
import {
  dismissAppToast,
  subscribeAppToasts,
  type AppToastItem,
  type AppToastTone,
} from '../../utils/appToast'

const TONE_STYLES: Record<
  AppToastTone,
  { bar: string; icon: string; iconClass: string; label: string }
> = {
  success: {
    bar: 'border-l-emerald-500',
    icon: 'bi-check-circle-fill',
    iconClass: 'text-emerald-600',
    label: 'Success',
  },
  danger: {
    bar: 'border-l-rose-500',
    icon: 'bi-exclamation-octagon-fill',
    iconClass: 'text-rose-600',
    label: 'Error',
  },
  warning: {
    bar: 'border-l-amber-500',
    icon: 'bi-exclamation-triangle-fill',
    iconClass: 'text-amber-600',
    label: 'Warning',
  },
  info: {
    bar: 'border-l-sky-500',
    icon: 'bi-info-circle-fill',
    iconClass: 'text-sky-600',
    label: 'Notice',
  },
}

export function AppToastHost() {
  const [toasts, setToasts] = useState<AppToastItem[]>([])

  useEffect(() => subscribeAppToasts(setToasts), [])

  if (!toasts.length) return null

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[1090] flex w-[min(22rem,calc(100vw-2rem))] flex-col-reverse gap-2"
      aria-live="polite"
      aria-relevant="additions"
    >
      {toasts.map((toast) => {
        const style = TONE_STYLES[toast.tone]
        return (
          <div
            key={toast.id}
            className={[
              'pointer-events-auto spa-app-toast flex items-start gap-3 rounded-2xl border border-slate-200/90',
              'border-l-4 bg-white/95 px-3.5 py-3 shadow-[0_12px_32px_rgba(15,23,42,0.14)] backdrop-blur-sm',
              style.bar,
            ].join(' ')}
            role="status"
          >
            <i className={`bi ${style.icon} mt-0.5 text-base ${style.iconClass}`} aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="mb-0.5 text-[0.68rem] font-bold uppercase tracking-[0.12em] text-slate-500">
                {style.label}
              </p>
              <p className="mb-0 text-sm font-medium leading-snug text-slate-800">{toast.message}</p>
            </div>
            <button
              type="button"
              className="shrink-0 rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
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
