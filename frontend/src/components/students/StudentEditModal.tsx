import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchStudentDetail, submitStudentEditForm } from '../../api/students'
import { LegacyBootstrapModal } from '../legacy/LegacyBootstrapModal'
import { StaffCredentialModal } from '../staff/StaffCredentialModal'
import {
  buildEntranceSchoolYearOptions,
  EMERGENCY_RELATIONSHIPS,
  PARENT_RELATIONSHIPS,
  STUDENT_GENDERS,
  STUDENT_GRADE_OPTIONS,
  US_STATES,
} from '../../config/studentForm'
import type { CredentialModalPayload } from '../../types/staff'
import type { StudentDetail } from '../../types/students'
import { formatStudentFullName, studentInitials } from '../../utils/studentDisplay'

const inputClass = 'form-control'
const labelClass = 'form-label'

interface StudentEditModalProps {
  studentId: number
  onClose: () => void
  onSaved: (message: string) => void
}

export function StudentEditModal({ studentId, onClose, onSaved }: StudentEditModalProps) {
  const formRef = useRef<HTMLFormElement>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [student, setStudent] = useState<StudentDetail | null>(null)
  const [credentialModal, setCredentialModal] = useState<CredentialModalPayload | null>(null)
  const entranceYears = useMemo(() => buildEntranceSchoolYearOptions(), [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    void fetchStudentDetail(studentId)
      .then(setStudent)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load student'))
      .finally(() => setLoading(false))
  }, [studentId])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formRef.current) return
    setSaving(true)
    setError(null)
    try {
      const fd = new FormData(formRef.current)
      const result = await submitStudentEditForm(studentId, fd)
      if (result.credential_modal) {
        setCredentialModal(result.credential_modal)
      } else {
        onSaved(result.message || 'Student updated successfully.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const closeCredentialModal = () => {
    setCredentialModal(null)
    onSaved('Student updated successfully.')
  }

  const gradeValue =
    student?.grade_level !== null && student?.grade_level !== undefined
      ? String(student.grade_level)
      : ''

  const photoUrl =
    student?.photo_filename && /^[a-zA-Z0-9._-]+$/.test(String(student.photo_filename))
      ? `/static/uploads/${student.photo_filename}`
      : null

  return (
    <>
      {credentialModal ? (
        <StaffCredentialModal payload={credentialModal} onClose={closeCredentialModal} />
      ) : null}

      <LegacyBootstrapModal
        show
        onClose={onClose}
        size="lg"
        scrollable
        rootClassName="mgmt-stu-modal mgmt-stu-modal--edit"
        headerClassName="text-white mgmt-stu-modal-header mgmt-stu-modal-header--edit"
        closeWhite
        title={
          <>
            <i className="bi bi-pencil-square me-2" aria-hidden="true" />
            Edit student
          </>
        }
      >
        {loading ? (
          <div className="modal-body mgmt-stu-modal-body p-5 text-center text-muted">
            <div className="spinner-border text-success mb-3" role="status" aria-hidden="true" />
            <p className="mb-0">Loading student…</p>
          </div>
        ) : !student ? (
          <div className="modal-body mgmt-stu-modal-body p-5 text-center text-danger">
            {error || 'Student not found.'}
          </div>
        ) : (
          <form ref={formRef} onSubmit={onSubmit}>
            <div className="modal-body mgmt-stu-modal-body">
              {error ? <div className="alert alert-danger">{error}</div> : null}

              <div className="mgmt-stu-detail-hero">
                <div className="mgmt-stu-detail-avatar" aria-hidden="true">
                  {studentInitials(student)}
                </div>
                <div>
                  <h3 className="h5 mb-1">{formatStudentFullName(student)}</h3>
                  <p className="mgmt-stu-detail-meta mb-0">
                    ID {student.student_id || 'N/A'} · Grade{' '}
                    {student.grade_level === 0 ? 'K' : student.grade_level ?? '—'}
                  </p>
                </div>
              </div>

              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-form-section-title mb-3">Personal information</h6>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className={labelClass}>First name *</label>
                  <input name="first_name" required defaultValue={student.first_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Middle name / initial</label>
                  <input name="middle_name" defaultValue={student.middle_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Last name *</label>
                  <input name="last_name" required defaultValue={student.last_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Date of birth</label>
                  <input type="date" name="dob" defaultValue={student.dob || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Grade level</label>
                  <select name="grade_level" defaultValue={gradeValue} className={`form-select ${inputClass}`}>
                    <option value="">Select grade…</option>
                    {STUDENT_GRADE_OPTIONS.map((g) => (
                      <option key={g.value} value={g.value}>
                        {g.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Gender *</label>
                  <select name="gender" required defaultValue={student.gender || ''} className="form-select">
                    <option value="">Choose…</option>
                    {STUDENT_GENDERS.map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Entrance school year *</label>
                  <select name="entrance_date" required defaultValue={student.entrance_date || ''} className="form-select">
                    <option value="">Choose school year…</option>
                    {entranceYears.map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Student ID</label>
                  <input readOnly value={student.student_id || ''} className={`${inputClass} bg-light`} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Expected graduation</label>
                  <input readOnly value={student.expected_grad_date || ''} className={`${inputClass} bg-light`} />
                </div>
                <div className="col-12">
                  <label className={labelClass}>Student photo</label>
                  {photoUrl ? (
                    <img src={photoUrl} alt="" className="mb-2 rounded border" style={{ maxHeight: '6rem' }} />
                  ) : (
                    <p className="small text-muted mb-2">No photo on file.</p>
                  )}
                  <input type="file" name="student_image" accept="image/jpeg,image/png,image/gif" className={inputClass} />
                </div>
              </div>
              </section>

              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-form-section-title mb-3">Contact &amp; authentication</h6>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className={labelClass}>Personal email</label>
                  <input type="email" name="email" defaultValue={student.email || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Google Workspace email</label>
                  <input
                    type="email"
                    name="google_workspace_email"
                    defaultValue={
                      student.google_workspace_email || student.suggested_google_workspace_email || ''
                    }
                    placeholder="Leave blank to auto-fill"
                    className={inputClass}
                  />
                </div>
              </div>
              </section>

              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-form-section-title mb-3">Parent / guardian 1</h6>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className={labelClass}>First name</label>
                  <input name="parent1_first_name" defaultValue={student.parent1_first_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Last name</label>
                  <input name="parent1_last_name" defaultValue={student.parent1_last_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Email</label>
                  <input type="email" name="parent1_email" defaultValue={student.parent1_email || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Phone</label>
                  <input type="tel" name="parent1_phone" defaultValue={student.parent1_phone || ''} maxLength={20} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Relationship</label>
                  <select name="parent1_relationship" defaultValue={student.parent1_relationship || ''} className="form-select">
                    <option value="">Choose…</option>
                    {PARENT_RELATIONSHIPS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              </section>

              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-form-section-title mb-3">Parent / guardian 2</h6>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className={labelClass}>First name</label>
                  <input name="parent2_first_name" defaultValue={student.parent2_first_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Last name</label>
                  <input name="parent2_last_name" defaultValue={student.parent2_last_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Email</label>
                  <input type="email" name="parent2_email" defaultValue={student.parent2_email || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Phone</label>
                  <input type="tel" name="parent2_phone" defaultValue={student.parent2_phone || ''} maxLength={20} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Relationship</label>
                  <select name="parent2_relationship" defaultValue={student.parent2_relationship || ''} className="form-select">
                    <option value="">Choose…</option>
                    {PARENT_RELATIONSHIPS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              </section>

              <section className="mgmt-stu-modal-section">
                <h6 className="mgmt-stu-form-section-title mb-3">Emergency contact</h6>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className={labelClass}>First name</label>
                  <input name="emergency_first_name" defaultValue={student.emergency_first_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Last name</label>
                  <input name="emergency_last_name" defaultValue={student.emergency_last_name || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Email</label>
                  <input type="email" name="emergency_email" defaultValue={student.emergency_email || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Phone</label>
                  <input type="tel" name="emergency_phone" defaultValue={student.emergency_phone || ''} maxLength={20} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Relationship</label>
                  <select name="emergency_relationship" defaultValue={student.emergency_relationship || ''} className="form-select">
                    <option value="">Choose…</option>
                    {EMERGENCY_RELATIONSHIPS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              </section>

              <section className="mgmt-stu-modal-section mb-0">
                <h6 className="mgmt-stu-form-section-title mb-3">Address &amp; notes</h6>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className={labelClass}>Street</label>
                  <input name="street" defaultValue={student.street || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Apt, unit, suite</label>
                  <input name="apt_unit" defaultValue={student.apt_unit || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>City</label>
                  <input name="city" defaultValue={student.city || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>State</label>
                  <select name="state" defaultValue={student.state || ''} className="form-select">
                    <option value="">Choose state…</option>
                    {US_STATES.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>ZIP code</label>
                  <input name="zip_code" defaultValue={student.zip_code || ''} className={inputClass} />
                </div>
                <div className="col-md-6">
                  <label className={labelClass}>Previous school</label>
                  <input name="previous_school" defaultValue={student.previous_school || ''} className={inputClass} />
                </div>
                <div className="col-12">
                  <label className={labelClass}>Medical concerns</label>
                  <textarea
                    name="medical_concerns"
                    rows={2}
                    className="form-control"
                    defaultValue={student.medical_concerns || ''}
                  />
                </div>
                <div className="col-12">
                  <label className={labelClass}>Notes</label>
                  <textarea name="notes" rows={2} className="form-control" defaultValue={student.notes || ''} />
                </div>
              </div>
              </section>
            </div>

            <div className="modal-footer mgmt-stu-modal-footer">
              <button type="button" className="mgmt-stu-btn mgmt-stu-btn--footer-close" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" disabled={saving} className="mgmt-stu-btn mgmt-stu-btn--footer-save">
                <i className="bi bi-check-circle me-2" aria-hidden="true" />
                {saving ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </form>
        )}
      </LegacyBootstrapModal>
    </>
  )
}
