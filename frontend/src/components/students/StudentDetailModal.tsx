import type { StudentDetail } from '../../types/students'

interface StudentDetailModalProps {
  detail: StudentDetail | null
  loading: boolean
  onClose: () => void
}

function formatGrade(grade: number | null | undefined) {
  if (grade === 0) return 'Kindergarten'
  if (grade == null) return '—'
  return `Grade ${grade}`
}

function formatAddress(detail: StudentDetail) {
  const parts = [
    detail.street,
    detail.apt_unit,
    [detail.city, detail.state].filter(Boolean).join(', '),
    detail.zip_code,
  ].filter(Boolean)
  return parts.length ? parts.join(', ') : null
}

function parentBlock(
  label: string,
  first: string | null | undefined,
  last: string | null | undefined,
  email: string | null | undefined,
  phone: string | null | undefined,
  relationship: string | null | undefined,
) {
  const name = [first, last].filter(Boolean).join(' ').trim()
  if (!name && !email && !phone) return null
  return (
    <section key={label}>
      <h4 className="mb-1 text-sm font-semibold text-hub-muted">{label}</h4>
      <div className="rounded-xl bg-slate-50 px-3 py-2 text-sm">
        {name ? <p className="font-medium text-hub-text">{name}</p> : null}
        {relationship ? <p className="text-hub-muted">{relationship}</p> : null}
        {email ? <p>{email}</p> : null}
        {phone ? <p>{phone}</p> : null}
      </div>
    </section>
  )
}

export function StudentDetailModal({ detail, loading, onClose }: StudentDetailModalProps) {
  if (!detail && !loading) return null

  const address = detail ? formatAddress(detail) : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-lg font-bold text-hub-text">Student details</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-hub-muted hover:bg-slate-100"
            aria-label="Close"
          >
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
              <p className="text-sm text-hub-muted">
                Student ID: {detail.student_id || 'N/A'} · {formatGrade(detail.grade_level)}
              </p>
            </div>

            <DetailGrid
              rows={[
                ['GPA', detail.gpa != null ? detail.gpa.toFixed(2) : '—'],
                ['Date of birth', String(detail.dob || '—')],
                ['Age', detail.age != null ? String(detail.age) : '—'],
                ['Gender', String(detail.gender || '—')],
                ['Entrance year', String(detail.entrance_date || '—')],
                ['Expected graduation', String(detail.expected_grad_date || '—')],
                ['Email', String(detail.email || '—')],
                ['School email', String(detail.google_workspace_email || detail.suggested_google_workspace_email || '—')],
              ]}
            />

            {address ? (
              <section>
                <h4 className="mb-1 text-sm font-semibold text-hub-muted">Address</h4>
                <p className="text-sm">{address}</p>
              </section>
            ) : null}

            {parentBlock(
              'Parent / guardian 1',
              detail.parent1_first_name,
              detail.parent1_last_name,
              detail.parent1_email,
              detail.parent1_phone,
              detail.parent1_relationship,
            )}
            {parentBlock(
              'Parent / guardian 2',
              detail.parent2_first_name,
              detail.parent2_last_name,
              detail.parent2_email,
              detail.parent2_phone,
              detail.parent2_relationship,
            )}
            {parentBlock(
              'Emergency contact',
              detail.emergency_first_name,
              detail.emergency_last_name,
              detail.emergency_email,
              detail.emergency_phone,
              detail.emergency_relationship,
            )}

            {detail.assigned_classes && detail.assigned_classes.length > 0 ? (
              <section>
                <h4 className="mb-2 text-sm font-semibold text-hub-muted">Enrolled classes</h4>
                <ul className="space-y-1 text-sm">
                  {detail.assigned_classes.map((c) => (
                    <li key={`${c.name}-${c.subject || ''}`} className="rounded-lg bg-slate-50 px-3 py-2">
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
