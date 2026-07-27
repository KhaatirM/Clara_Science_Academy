export type AppToastTone = 'success' | 'danger' | 'warning' | 'info'

export type AppToastItem = {
  id: number
  message: string
  tone: AppToastTone
  createdAt: number
}

export type AppToastInput = {
  message: string
  tone?: AppToastTone | string
}

type Listener = (toasts: AppToastItem[]) => void

const DEFAULT_DURATION_MS = 4500
const MAX_VISIBLE = 4

let nextId = 1
let toasts: AppToastItem[] = []
const listeners = new Set<Listener>()
const dismissTimers = new Map<number, ReturnType<typeof setTimeout>>()

function normalizeTone(raw?: string): AppToastTone {
  const t = (raw || 'info').toLowerCase()
  if (t === 'error' || t === 'danger') return 'danger'
  if (t === 'success') return 'success'
  if (t === 'warning') return 'warning'
  return 'info'
}

function emit() {
  const snapshot = [...toasts]
  listeners.forEach((fn) => fn(snapshot))
}

function scheduleDismiss(id: number, durationMs: number) {
  const existing = dismissTimers.get(id)
  if (existing) clearTimeout(existing)
  dismissTimers.set(
    id,
    setTimeout(() => {
      dismissAppToast(id)
    }, durationMs),
  )
}

export function subscribeAppToasts(listener: Listener): () => void {
  listeners.add(listener)
  listener([...toasts])
  return () => {
    listeners.delete(listener)
  }
}

export function dismissAppToast(id: number) {
  const timer = dismissTimers.get(id)
  if (timer) {
    clearTimeout(timer)
    dismissTimers.delete(id)
  }
  const before = toasts.length
  toasts = toasts.filter((t) => t.id !== id)
  if (toasts.length !== before) emit()
}

export function showAppToast(
  message: string,
  tone: AppToastTone | string = 'info',
  durationMs: number = DEFAULT_DURATION_MS,
) {
  const text = String(message || '').trim()
  if (!text) return

  const item: AppToastItem = {
    id: nextId++,
    message: text,
    tone: normalizeTone(tone),
    createdAt: Date.now(),
  }
  toasts = [...toasts, item].slice(-MAX_VISIBLE)
  emit()
  scheduleDismiss(item.id, durationMs)
}

export function showAppToasts(items: AppToastInput[], durationMs: number = DEFAULT_DURATION_MS) {
  for (const item of items) {
    if (!item?.message) continue
    showAppToast(item.message, item.tone, durationMs)
  }
}

/** Browser event bridge for non-React callers (optional). */
if (typeof window !== 'undefined') {
  window.addEventListener('clara:app-toast', ((event: Event) => {
    const detail = (event as CustomEvent<AppToastInput>).detail
    if (detail?.message) showAppToast(detail.message, detail.tone)
  }) as EventListener)
}
