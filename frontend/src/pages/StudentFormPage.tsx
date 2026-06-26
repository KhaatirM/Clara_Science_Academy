import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { submitStudentAddForm } from '../api/students'
import { LegacyMgmtScope } from '../components/legacy/LegacyMgmtScope'
import { StaffCredentialModal } from '../components/staff/StaffCredentialModal'
import {
  buildEntranceSchoolYearOptions,
  EMERGENCY_RELATIONSHIPS,
  PARENT_RELATIONSHIPS,
  STUDENT_GENDERS,
  STUDENT_GRADES_FOR_ADD,
  US_STATES,
} from '../config/studentForm'
import type { ManagementOutletContext } from '../types/layout'
import type { CredentialModalPayload } from '../types/staff'
import { canStudentAdminUi } from '../utils/studentAccess'

const inputClass = 'form-control'
const labelClass = 'form-label'
const sectionClass = 'students-search-card mb-4'

function Field({
  label,
  required,
  children,
  hint,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
  hint?: string
}) {
  return (
    <div>
      <label className={labelClass}>
        {label}
        {required ? <span className="text-red-600"> *</span> : null}
      </label>
      {children}
      {hint ? <p className="mt-1 text-xs text-hub-muted">{hint}</p> : null}
    </div>
  )
}

export function StudentFormPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const navigate = useNavigate()
  const formRef = useRef<HTMLFormElement>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [credentialModal, setCredentialModal] = useState<CredentialModalPayload | null>(null)
  const entranceYears = useMemo(() => buildEntranceSchoolYearOptions(), [])
  const canAdd = canStudentAdminUi(user)

  useEffect(() => {
    if (!canAdd) {
      navigate('/management/students', { replace: true })
    }
  }, [canAdd, navigate])

  if (!canAdd) {
    return null
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formRef.current) return
    setSaving(true)
    setError(null)
    try {
      const fd = new FormData(formRef.current)
      const result = await submitStudentAddForm(fd)
      if (result.credential_modal) {
        setCredentialModal(result.credential_modal)
      } else {
        navigate('/management/students')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const closeCredentialModal = () => {
    setCredentialModal(null)
    navigate('/management/students')
  }

  return (
    <LegacyMgmtScope>
      <div className="mgmt-stu container-fluid px-0 px-md-1">
        <div className="mgmt-stu-shell">
          {credentialModal ? (
            <StaffCredentialModal payload={credentialModal} onClose={closeCredentialModal} />
          ) : null}

          <header className="mgmt-stu-hero">
            <div>
              <Link to="/management/students" className="mgmt-stu-btn mgmt-stu-btn--ghost mb-2 d-inline-flex">
                <i className="bi bi-arrow-left me-2" aria-hidden="true" />
                Back to students
              </Link>
              <p className="mgmt-stu-eyebrow">Students</p>
              <h1 className="mgmt-stu-title">Add student</h1>
              <p className="mgmt-stu-subtitle">
                Complete each section below. Required fields are marked with an asterisk.
              </p>
            </div>
          </header>

          <div className="mgmt-stu-content">
            {error ? <div className="alert alert-danger">{error}</div> : null}

      <form ref={formRef} onSubmit={onSubmit} className="space-y-5" encType="multipart/form-data">
        <section className={sectionClass}>
          <div className="border-b border-teal-100 bg-slate-50 px-5 py-3">
            <h2 className="text-base font-bold text-hub-text">1. Student information</h2>
          </div>
          <div className="grid gap-4 p-5 md:grid-cols-2">
            <Field label="First name" required>
              <input name="student_first_name" required className={inputClass} />
            </Field>
            <Field label="Middle name / initial">
              <input name="student_middle_name" className={inputClass} />
            </Field>
            <Field label="Last name" required>
              <input name="student_last_name" required className={inputClass} />
            </Field>
            <Field label="Date of birth" required>
              <input type="date" name="dob" required className={inputClass} />
            </Field>
            <Field label="Grade level" required>
              <select name="grade_level" required defaultValue="" className={inputClass}>
                <option value="" disabled>
                  Choose grade…
                </option>
                {STUDENT_GRADES_FOR_ADD.map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Gender" required>
              <select name="gender" required defaultValue="" className={inputClass}>
                <option value="" disabled>
                  Choose…
                </option>
                {STUDENT_GENDERS.map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Entrance school year" required hint="Format YYYY-YYYY (e.g. 2025-2026).">
              <select name="entrance_date" required defaultValue="" className={inputClass}>
                <option value="" disabled>
                  Choose school year…
                </option>
                {entranceYears.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Previous school">
              <input name="previous_school" className={inputClass} />
            </Field>
            <Field label="Personal email" hint="Optional. Auto-filled for 3rd grade+ if left blank.">
              <input type="email" name="email" className={inputClass} />
            </Field>
            <Field label="Student photo">
              <input type="file" name="student_image" accept="image/jpeg,image/png,image/gif" className={inputClass} />
            </Field>
            <Field label="Transcript">
              <input type="file" name="transcript" className={inputClass} />
            </Field>
          </div>
        </section>

        <section className={sectionClass}>
          <div className="border-b border-teal-100 bg-slate-50 px-5 py-3">
            <h2 className="text-base font-bold text-hub-text">2. Address</h2>
          </div>
          <div className="grid gap-4 p-5 md:grid-cols-2">
            <Field label="Street address">
              <input name="street_address" className={inputClass} />
            </Field>
            <Field label="Apt, unit, suite">
              <input name="apt_unit_suite" className={inputClass} />
            </Field>
            <Field label="City">
              <input name="city" className={inputClass} />
            </Field>
            <Field label="State">
              <select name="state" defaultValue="" className={inputClass}>
                <option value="">Choose state…</option>
                {US_STATES.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="ZIP code">
              <input name="zip_code" className={inputClass} />
            </Field>
          </div>
        </section>

        <section className={sectionClass}>
          <div className="border-b border-teal-100 bg-slate-50 px-5 py-3">
            <h2 className="text-base font-bold text-hub-text">3. Parents &amp; emergency contact</h2>
          </div>
          <div className="space-y-6 p-5">
            <div className="grid gap-4 md:grid-cols-2">
              <p className="col-span-full text-sm font-semibold text-hub-text">Parent / guardian 1</p>
              <Field label="First name">
                <input name="parent1_first_name" className={inputClass} />
              </Field>
              <Field label="Last name">
                <input name="parent1_last_name" className={inputClass} />
              </Field>
              <Field label="Email">
                <input type="email" name="parent1_email" className={inputClass} />
              </Field>
              <Field label="Phone">
                <input type="tel" name="parent1_phone" maxLength={20} className={inputClass} />
              </Field>
              <Field label="Relationship">
                <select name="parent1_relationship" defaultValue="" className={inputClass}>
                  <option value="">Choose…</option>
                  {PARENT_RELATIONSHIPS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <p className="col-span-full text-sm font-semibold text-hub-text">Parent / guardian 2</p>
              <Field label="First name">
                <input name="parent2_first_name" className={inputClass} />
              </Field>
              <Field label="Last name">
                <input name="parent2_last_name" className={inputClass} />
              </Field>
              <Field label="Email">
                <input type="email" name="parent2_email" className={inputClass} />
              </Field>
              <Field label="Phone">
                <input type="tel" name="parent2_phone" maxLength={20} className={inputClass} />
              </Field>
              <Field label="Relationship">
                <select name="parent2_relationship" defaultValue="" className={inputClass}>
                  <option value="">Choose…</option>
                  {PARENT_RELATIONSHIPS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <p className="col-span-full text-sm font-semibold text-hub-text">Emergency contact</p>
              <Field label="First name">
                <input name="emergency_first_name" className={inputClass} />
              </Field>
              <Field label="Last name">
                <input name="emergency_last_name" className={inputClass} />
              </Field>
              <Field label="Email">
                <input type="email" name="emergency_email" className={inputClass} />
              </Field>
              <Field label="Phone">
                <input type="tel" name="emergency_phone" maxLength={20} className={inputClass} />
              </Field>
              <Field label="Relationship">
                <select name="emergency_relationship" defaultValue="" className={inputClass}>
                  <option value="">Choose…</option>
                  {EMERGENCY_RELATIONSHIPS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          </div>
        </section>

        <section className={sectionClass}>
          <div className="border-b border-teal-100 bg-slate-50 px-5 py-3">
            <h2 className="text-base font-bold text-hub-text">4. Additional information</h2>
          </div>
          <div className="grid gap-4 p-5">
            <Field label="Medical concerns">
              <textarea
                name="medical_concerns"
                rows={3}
                className={inputClass}
                placeholder="Allergies, medications, or pertinent medical conditions…"
              />
            </Field>
            <Field label="Notes">
              <textarea name="notes" rows={3} className={inputClass} placeholder="Any other relevant information…" />
            </Field>
          </div>
        </section>

        <div className="students-info-box mb-4">
          <strong>Student portal:</strong> Login accounts are created automatically for{' '}
          <strong>3rd grade and above</strong>. Kindergarten through 2nd grade are saved without a portal account until
          they reach 3rd grade.
        </div>

        <div className="d-flex flex-wrap gap-2 mb-4">
          <button type="submit" disabled={saving} className="mgmt-stu-btn mgmt-stu-btn--primary">
            <i className="bi bi-check-lg me-2" aria-hidden="true" />
            {saving ? 'Saving…' : 'Add student'}
          </button>
          <Link to="/management/students" className="mgmt-stu-btn mgmt-stu-btn--ghost">
            <i className="bi bi-x-lg me-2" aria-hidden="true" />
            Discard
          </Link>
        </div>
      </form>
          </div>
        </div>
      </div>
    </LegacyMgmtScope>
  )
}
