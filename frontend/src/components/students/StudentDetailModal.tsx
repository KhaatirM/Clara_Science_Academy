import { LegacyBootstrapModal } from '../legacy/LegacyBootstrapModal'
import type { StudentDetail, StudentParentPortalStatus } from '../../types/students'
import { formatStudentFullName, studentInitials } from '../../utils/studentDisplay'

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

function formatFullName(detail: StudentDetail) {
  return formatStudentFullName(detail)
}

function initials(detail: StudentDetail) {
  return studentInitials(detail)
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

function portalSlotLabel(slot: StudentParentPortalStatus['parent1']) {
  if (!slot || typeof slot !== 'object') return 'No parent email on file'
  if (!slot.has_email) return 'No parent email on file'
  if (!slot.has_login) return `${slot.email || slot.name || 'Parent'} — no login yet`
  if (slot.is_linked) return `${slot.username || slot.email} — linked to this student`
  return `${slot.username || slot.email} — login exists, not linked`
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
    <div key={label} className="col-md-6">
      <div className="mgmt-stu-modal-block h-100">
        <h6 className="mgmt-stu-modal-label">{label}</h6>
        <div className="mgmt-stu-modal-panel">
        {name ? <p className="mb-1 fw-semibold">{name}</p> : null}
        {relationship ? <p className="mb-1 text-muted small">{relationship}</p> : null}
        {email ? (
          <p className="mb-0 small">
            <i className="bi bi-envelope me-1" aria-hidden="true" />
            {email}
          </p>
        ) : null}
        {phone ? (
          <p className="mb-0 small">
            <i className="bi bi-telephone me-1" aria-hidden="true" />
            {phone}
          </p>
        ) : null}
        </div>
      </div>
    </div>
  )
}

export function StudentDetailModal({ detail, loading, onClose }: StudentDetailModalProps) {
  if (!detail && !loading) return null

  const show = Boolean(detail || loading)
  const address = detail ? formatAddress(detail) : null
  const schoolEmail =
    detail?.google_workspace_email || detail?.suggested_google_workspace_email || null

  return (
    <LegacyBootstrapModal
      show={show}
      onClose={onClose}
      size="lg"
      scrollable
      rootClassName="mgmt-stu-modal"
      headerClassName="text-white mgmt-stu-modal-header"
      closeWhite
      title={
        <>
          <i className="bi bi-person-lines-fill me-2" aria-hidden="true" />
          Student profile
        </>
      }
    >
      {loading ? (
        <div className="modal-body mgmt-stu-modal-body p-5 text-center text-muted">
          <div className="spinner-border text-success mb-3" role="status" aria-hidden="true" />
          <p className="mb-0">Loading student details…</p>
        </div>
      ) : detail ? (
        <>
          <div className="modal-body mgmt-stu-modal-body">
            <div className="mgmt-stu-detail-hero">
              <div className="mgmt-stu-detail-avatar" aria-hidden="true">
                {initials(detail)}
              </div>
              <div>
                <h3>{formatFullName(detail)}</h3>
                <p className="mgmt-stu-detail-meta">
                  ID {detail.student_id || 'N/A'} · {formatGrade(detail.grade_level)}
                </p>
              </div>
            </div>

            <div className="mgmt-stu-detail-chips">
              <span className="mgmt-stu-detail-chip">
                <i className="bi bi-trophy" aria-hidden="true" />
                GPA {detail.gpa != null ? detail.gpa.toFixed(2) : '—'}
              </span>
              <span className="mgmt-stu-detail-chip">
                <i className="bi bi-calendar3" aria-hidden="true" />
                DOB {detail.dob || '—'}
              </span>
              {detail.age != null ? (
                <span className="mgmt-stu-detail-chip">
                  <i className="bi bi-hourglass-split" aria-hidden="true" />
                  Age {detail.age}
                </span>
              ) : null}
              <span className="mgmt-stu-detail-chip">
                <i className="bi bi-mortarboard" aria-hidden="true" />
                Grad {detail.expected_grad_date || '—'}
              </span>
            </div>

            <section className="mgmt-stu-modal-section">
              <h6 className="mgmt-stu-modal-label mb-3">
                <i className="bi bi-person-badge me-2" aria-hidden="true" />
                Academic &amp; contact
              </h6>
              <DetailGrid
                rows={[
                  ['Middle name', String(detail.middle_name || '—')],
                  ['Gender', String(detail.gender || '—')],
                  ['Entrance year', String(detail.entrance_date || '—')],
                  ['Personal email', String(detail.email || '—')],
                  ['School email', String(schoolEmail || '—')],
                ]}
              />
            </section>

            {address ? (
              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-modal-label">
                  <i className="bi bi-geo-alt me-2" aria-hidden="true" />
                  Address
                </h6>
                <p className="mgmt-stu-modal-panel mb-0 small">{address}</p>
              </section>
            ) : null}

            <section className="mgmt-stu-modal-section">
              <h6 className="mgmt-stu-modal-label mb-3">
                <i className="bi bi-people me-2" aria-hidden="true" />
                Family &amp; emergency contacts
              </h6>
              <div className="row g-2">
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
              </div>
            </section>

            {detail.parent_portal ? (
              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-modal-label">
                  <i className="bi bi-heart me-2" aria-hidden="true" />
                  Family portal
                </h6>
                <ul className="mgmt-stu-modal-panel list-unstyled mb-0 small">
                  <li className="mb-2">
                    <strong>Parent 1:</strong> {portalSlotLabel(detail.parent_portal.parent1)}
                  </li>
                  <li>
                    <strong>Parent 2:</strong> {portalSlotLabel(detail.parent_portal.parent2)}
                  </li>
                </ul>
              </section>
            ) : null}

            {detail.previous_school || detail.medical_concerns || detail.notes ? (
              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-modal-label mb-3">
                  <i className="bi bi-journal-text me-2" aria-hidden="true" />
                  Additional information
                </h6>
                {detail.previous_school ? (
                  <div className="mgmt-stu-modal-block">
                    <h6 className="mgmt-stu-modal-label">Previous school</h6>
                    <p className="mgmt-stu-modal-panel mb-2 small">{detail.previous_school}</p>
                  </div>
                ) : null}
                {detail.medical_concerns ? (
                  <div className="mgmt-stu-modal-block">
                    <h6 className="mgmt-stu-modal-label">Medical concerns</h6>
                    <p className="mgmt-stu-modal-panel mb-2 small">{detail.medical_concerns}</p>
                  </div>
                ) : null}
                {detail.notes ? (
                  <div className="mgmt-stu-modal-block mb-0">
                    <h6 className="mgmt-stu-modal-label">Notes</h6>
                    <p className="mgmt-stu-modal-panel mb-0 small">{detail.notes}</p>
                  </div>
                ) : null}
              </section>
            ) : null}

            <section className="mgmt-stu-modal-section mb-0">
              <h6 className="mgmt-stu-modal-label mb-2">
                <i className="bi bi-book me-2" aria-hidden="true" />
                Enrolled classes
                {detail.assigned_classes_school_year ? (
                  <span className="text-muted fw-normal ms-1">
                    · {detail.assigned_classes_school_year.name}
                    {!detail.assigned_classes_school_year.is_active ? (
                      <span className="badge bg-secondary-subtle text-secondary ms-1">closed year</span>
                    ) : null}
                  </span>
                ) : null}
              </h6>
              {detail.assigned_classes && detail.assigned_classes.length > 0 ? (
                <ul className="list-unstyled mb-0">
                  {detail.assigned_classes.map((c) => (
                    <li key={`${c.name}-${c.subject || ''}`} className="mgmt-stu-modal-panel mb-2 small">
                      <i className="bi bi-journal-bookmark me-2 text-success" aria-hidden="true" />
                      {c.name}
                      {c.subject ? <span className="text-muted"> · {c.subject}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mgmt-stu-modal-panel mb-0 small text-muted">
                  {detail.assigned_classes_school_year
                    ? `No classes enrolled for ${detail.assigned_classes_school_year.name}.`
                    : 'No school year on file — class enrollments are unavailable.'}
                </p>
              )}
            </section>
          </div>
          <div className="modal-footer mgmt-stu-modal-footer">
            <button type="button" className="mgmt-stu-btn mgmt-stu-btn--footer-close" onClick={onClose}>
              Close
            </button>
          </div>
        </>
      ) : null}
    </LegacyBootstrapModal>
  )
}

function DetailGrid({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="row g-2 mb-0">
      {rows.map(([label, value]) => (
        <div key={label} className="col-sm-6">
          <div className="mgmt-stu-modal-panel h-100">
            <dt className="mgmt-stu-modal-dt">{label}</dt>
            <dd className="mgmt-stu-modal-dd mb-0">{value}</dd>
          </div>
        </div>
      ))}
    </dl>
  )
}
