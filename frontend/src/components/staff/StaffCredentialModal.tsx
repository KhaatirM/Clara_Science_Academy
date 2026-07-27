import type { CredentialModalPayload } from '../../types/staff'

interface StaffCredentialModalProps {
  payload: CredentialModalPayload
  onClose: () => void
}

export function StaffCredentialModal({ payload, onClose }: StaffCredentialModalProps) {
  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/50 p-4">
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl"
        role="dialog"
        aria-labelledby="credential-modal-title"
      >
        <div className="border-b border-slate-100 px-6 py-4">
          <h2 id="credential-modal-title" className="text-lg font-bold text-hub-text">
            {payload.title}
          </h2>
          {payload.subtitle ? (
            <p className="mt-1 text-sm text-hub-muted">{payload.subtitle}</p>
          ) : null}
        </div>
        <div className="space-y-4 px-6 py-4">
          {payload.alerts?.map((alert) => (
            <div
              key={alert.text}
              className={[
                'rounded-xl px-4 py-3 text-sm',
                alert.type === 'warning'
                  ? 'bg-amber-50 text-amber-900'
                  : 'bg-sky-50 text-sky-900',
              ].join(' ')}
            >
              {alert.text}
            </div>
          ))}
          <dl className="space-y-3">
            {payload.fields.map((field) => (
              <div key={field.label} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
                  {field.label}
                </dt>
                <dd className="mt-1 flex items-start justify-between gap-2">
                  <span className={field.mono ? 'font-mono text-sm break-all' : 'text-sm'}>
                    {field.value}
                  </span>
                  {field.value && field.value !== '—' ? (
                    <button
                      type="button"
                      className="shrink-0 text-xs font-semibold text-hub-accent hover:underline"
                      onClick={() => void copy(field.value)}
                    >
                      Copy
                    </button>
                  ) : null}
                </dd>
              </div>
            ))}
          </dl>
          {payload.notes?.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-hub-muted">
              {payload.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <div className="border-t border-slate-100 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-xl bg-hub-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-hub-accent-deep"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
