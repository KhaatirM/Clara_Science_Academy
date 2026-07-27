import type { StaffDetail } from '../../types/staff'

interface StaffDetailModalProps {
  detail: StaffDetail | null
  loading: boolean
  onClose: () => void
}

export function StaffDetailModal({ detail, loading, onClose }: StaffDetailModalProps) {
  if (!detail && !loading) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" role="dialog" aria-modal="true">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-lg font-bold text-hub-text">Staff details</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-hub-muted hover:bg-slate-100" aria-label="Close">
            <i className="bi bi-x-lg" />
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-hub-muted">Loading…</div>
        ) : detail ? (
          <div className="space-y-4 p-5">
            <div>
              <h3 className="text-xl font-bold">
                {detail.first_name} {detail.last_name}
              </h3>
              <p className="text-sm text-hub-muted">Staff ID: {detail.staff_id || 'N/A'}</p>
            </div>

            <DetailGrid
              rows={[
                ['Role', String(detail.primary_role || detail.role || '—')],
                ['Email', String(detail.email || '—')],
                ['School email', String(detail.google_workspace_email || '—')],
                ['Username', String(detail.username || '—')],
                ['Department', String(detail.department || '—')],
                ['Employment', String(detail.employment_type || '—')],
                ['Status', String(detail.employment_status || 'Active')],
                ['Phone', String(detail.phone || '—')],
                ['Hire date', String(detail.hire_date || '—')],
                ['Portal login', detail.portal_login ? 'Yes' : 'No'],
              ]}
            />

            {detail.address && detail.address !== 'Not available' ? (
              <section>
                <h4 className="mb-1 text-sm font-semibold text-hub-muted">Address</h4>
                <p className="text-sm">{detail.address}</p>
              </section>
            ) : null}

            {detail.emergency_contact && detail.emergency_contact !== 'Not available' ? (
              <section>
                <h4 className="mb-1 text-sm font-semibold text-hub-muted">Emergency contact</h4>
                <p className="text-sm">{detail.emergency_contact}</p>
              </section>
            ) : null}

            {detail.assigned_classes && detail.assigned_classes.length > 0 ? (
              <section>
                <h4 className="mb-2 text-sm font-semibold text-hub-muted">Assigned classes</h4>
                <ul className="space-y-1 text-sm">
                  {detail.assigned_classes.map((c) => (
                    <li key={c.id} className="rounded-lg bg-slate-50 px-3 py-2">
                      {c.name}
                      {c.subject ? <span className="text-hub-muted"> · {c.subject}</span> : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function DetailGrid({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="rounded-xl bg-slate-50 px-3 py-2">
          <dt className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</dt>
          <dd className="mt-0.5 text-sm font-medium text-hub-text">{value}</dd>
        </div>
      ))}
    </dl>
  )
}
