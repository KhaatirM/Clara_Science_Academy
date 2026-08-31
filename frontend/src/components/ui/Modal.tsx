import { useEffect, type ReactNode } from 'react'

const SIZE_CLASS: Record<string, string> = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-3xl',
}

export type ModalSize = keyof typeof SIZE_CLASS

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  icon,
  size = 'md',
  footer,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  icon?: string
  size?: ModalSize
  footer?: ReactNode
  children: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previousOverflow
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`flex max-h-[92vh] w-full ${SIZE_CLASS[size]} flex-col overflow-hidden rounded-2xl bg-white shadow-2xl`}
      >
        <header className="flex items-start gap-3 border-b border-slate-200 px-5 py-4">
          {icon ? (
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
              <i className={`bi ${icon}`} aria-hidden />
            </span>
          ) : null}
          <div className="min-w-0 flex-1">
            <h2 className="mb-0 text-lg font-bold text-hub-text">{title}</h2>
            {subtitle ? <p className="mb-0 text-sm text-hub-muted">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>

        {footer ? (
          <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3">
            {footer}
          </footer>
        ) : null}
      </div>
    </div>
  )
}

export type ConfirmTone = 'danger' | 'primary'

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'danger',
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  body: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  tone?: ConfirmTone
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  const confirmClass =
    tone === 'danger'
      ? 'bg-red-600 text-white hover:bg-red-700'
      : 'bg-teal-700 text-white hover:bg-teal-800'

  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      icon={tone === 'danger' ? 'bi-exclamation-triangle' : 'bi-question-circle'}
      footer={
        <>
          <button
            type="button"
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
            onClick={onCancel}
            disabled={busy}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition disabled:opacity-60 ${confirmClass}`}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? 'Working…' : confirmLabel}
          </button>
        </>
      }
    >
      <div className="text-sm text-hub-text">{body}</div>
    </Modal>
  )
}

export function PromptDialog({
  open,
  title,
  label,
  value,
  placeholder,
  confirmLabel = 'Save',
  busy = false,
  onChange,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  label: string
  value: string
  placeholder?: string
  confirmLabel?: string
  busy?: boolean
  onChange: (next: string) => void
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      icon="bi-pencil"
      footer={
        <>
          <button
            type="button"
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
            onClick={onCancel}
            disabled={busy}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:opacity-60"
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? 'Saving…' : confirmLabel}
          </button>
        </>
      }
    >
      <label className="block">
        <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-hub-muted">
          {label}
        </span>
        <input
          autoFocus
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-semibold text-hub-text focus:border-teal-500 focus:bg-white focus:outline-none"
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onConfirm()
          }}
        />
      </label>
    </Modal>
  )
}
