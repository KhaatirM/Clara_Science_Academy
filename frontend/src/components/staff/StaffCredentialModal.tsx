import { useEffect, useId } from 'react'
import type { CredentialModalPayload } from '../../types/staff'

interface StaffCredentialModalProps {
  payload: CredentialModalPayload
  onClose: () => void
}

function FieldRow({
  label,
  value,
  mono,
  onCopy,
}: {
  label: string
  value: string
  mono?: boolean
  onCopy: (value: string) => void
}) {
  return (
    <div className="rounded-xl border border-slate-200/80 bg-white px-4 py-3 shadow-sm">
      <dt className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-hub-muted">
        {label}
      </dt>
      <dd className="mt-1.5 flex items-start justify-between gap-2">
        <span className={mono ? 'font-mono text-sm break-all text-hub-text' : 'text-sm text-hub-text'}>
          {value}
        </span>
        {value && value !== '—' ? (
          <button
            type="button"
            className="shrink-0 rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-hub-accent hover:bg-slate-200"
            onClick={() => onCopy(value)}
          >
            Copy
          </button>
        ) : null}
      </dd>
    </div>
  )
}

export function StaffCredentialModal({ payload, onClose }: StaffCredentialModalProps) {
  const titleId = useId()
  const isParent = payload.variant === 'parent_portal'
  const groups = payload.groups?.length ? payload.groups : null

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      /* ignore */
    }
  }

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-[2px]"
      role="presentation"
      onClick={onClose}
    >
      <div
        className={[
          'relative max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-white shadow-2xl ring-1 ring-black/5',
          isParent ? 'max-w-xl' : 'max-w-lg',
        ].join(' ')}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className={[
            'sticky top-0 z-10 border-b px-6 py-4',
            isParent
              ? 'border-rose-100 bg-gradient-to-br from-rose-50 via-white to-amber-50'
              : 'border-slate-100 bg-white',
          ].join(' ')}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              {isParent ? (
                <p className="text-[0.68rem] font-bold uppercase tracking-[0.14em] text-rose-600/80">
                  Family portal
                </p>
              ) : null}
              <h2 id={titleId} className="text-lg font-bold text-hub-text">
                {payload.title}
              </h2>
              {payload.subtitle ? (
                <p className="mt-1 text-sm text-hub-muted">{payload.subtitle}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-sm font-semibold text-hub-muted hover:bg-slate-50 hover:text-hub-text"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="space-y-4 px-6 py-5">
          {payload.alerts?.map((alert, i) => (
            <div
              key={`${alert.type}-${i}`}
              className={[
                'rounded-xl px-4 py-3 text-sm',
                alert.type === 'warning'
                  ? 'border border-amber-200 bg-amber-50 text-amber-950'
                  : isParent
                    ? 'border border-rose-100 bg-rose-50/80 text-rose-950'
                    : 'border border-sky-100 bg-sky-50 text-sky-950',
              ].join(' ')}
            >
              {alert.text}
            </div>
          ))}

          {groups ? (
            <div className="space-y-4">
              {groups.map((group, gi) => (
                <section
                  key={`${group.title}-${gi}`}
                  className="overflow-hidden rounded-2xl border border-rose-100/80 bg-gradient-to-b from-rose-50/40 to-white"
                >
                  <header className="border-b border-rose-100/70 px-4 py-3">
                    <h3 className="text-sm font-bold text-hub-text">{group.title}</h3>
                    {group.subtitle ? (
                      <p className="mt-0.5 text-xs text-hub-muted">{group.subtitle}</p>
                    ) : null}
                  </header>
                  <dl className="space-y-2.5 p-4">
                    {group.fields.map((field, fi) => (
                      <FieldRow
                        key={`${field.label}-${fi}`}
                        label={field.label}
                        value={field.value}
                        mono={field.mono}
                        onCopy={copy}
                      />
                    ))}
                  </dl>
                </section>
              ))}
            </div>
          ) : (
            <dl className="space-y-3">
              {payload.fields.map((field, fi) => (
                <FieldRow
                  key={`${field.label}-${fi}`}
                  label={field.label}
                  value={field.value}
                  mono={field.mono}
                  onCopy={copy}
                />
              ))}
            </dl>
          )}

          {payload.notes?.length ? (
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-hub-muted">
              {payload.notes.map((note, i) => (
                <li key={`${i}-${note.slice(0, 24)}`}>{note}</li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="sticky bottom-0 flex gap-2 border-t border-slate-100 bg-white/95 px-6 py-4 backdrop-blur">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-hub-text hover:bg-slate-50"
          >
            Close
          </button>
          <button
            type="button"
            onClick={onClose}
            className={[
              'flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold text-white',
              isParent
                ? 'bg-rose-600 hover:bg-rose-700'
                : 'bg-hub-accent hover:bg-hub-accent-deep',
            ].join(' ')}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
