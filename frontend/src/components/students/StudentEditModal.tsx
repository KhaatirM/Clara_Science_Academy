import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchStudentDetail, submitStudentEditForm } from '../../api/students'
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

const inputClass =
  'w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20'
const labelClass = 'mb-1 block text-sm font-medium text-hub-muted'

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

      <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/50 p-4">
        <div
          className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
          role="dialog"
          aria-labelledby="edit-student-title"
        >
          <div className="flex items-center justify-between border-b border-teal-100 bg-gradient-to-r from-teal-700 to-teal-600 px-5 py-4 text-white">
            <h2 id="edit-student-title" className="flex items-center gap-2 text-lg font-bold">
              <i className="bi bi-pencil-square" aria-hidden />
              Edit student
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1 text-white/90 hover:bg-white/10"
              aria-label="Close"
            >
              <i className="bi bi-x-lg" aria-hidden />
            </button>
          </div>

          {loading ? (
            <div className="p-8 text-center text-hub-muted">Loading student…</div>
          ) : !student ? (
            <div className="p-8 text-center text-red-700">{error || 'Student not found.'}</div>
          ) : (
            <form ref={formRef} onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
              <div className="min-h-0 flex-1 overflow-y-auto p-5">
                {error ? (
                  <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                    {error}
                  </div>
                ) : null}

                <section className="mb-6">
                  <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-800">
                    Personal information
                  </h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className={labelClass}>First name *</label>
                      <input name="first_name" required defaultValue={student.first_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Last name *</label>
                      <input name="last_name" required defaultValue={student.last_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Date of birth</label>
                      <input type="date" name="dob" defaultValue={student.dob || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Grade level</label>
                      <select name="grade_level" defaultValue={gradeValue} className={inputClass}>
                        <option value="">Select grade…</option>
                        {STUDENT_GRADE_OPTIONS.map((g) => (
                          <option key={g.value} value={g.value}>
                            {g.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>Gender *</label>
                      <select name="gender" required defaultValue={student.gender || ''} className={inputClass}>
                        <option value="">Choose…</option>
                        {STUDENT_GENDERS.map((g) => (
                          <option key={g} value={g}>
                            {g}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>Entrance school year *</label>
                      <select name="entrance_date" required defaultValue={student.entrance_date || ''} className={inputClass}>
                        <option value="">Choose school year…</option>
                        {entranceYears.map((y) => (
                          <option key={y} value={y}>
                            {y}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>Student ID</label>
                      <input readOnly value={student.student_id || ''} className={`${inputClass} bg-slate-50`} />
                    </div>
                    <div>
                      <label className={labelClass}>Expected graduation</label>
                      <input
                        readOnly
                        value={student.expected_grad_date || ''}
                        className={`${inputClass} bg-slate-50`}
                      />
                    </div>
                    <div className="md:col-span-2">
                      <label className={labelClass}>Student photo</label>
                      {photoUrl ? (
                        <img src={photoUrl} alt="" className="mb-2 max-h-24 rounded-lg border border-slate-200" />
                      ) : (
                        <p className="mb-2 text-xs text-hub-muted">No photo on file.</p>
                      )}
                      <input
                        type="file"
                        name="student_image"
                        accept="image/jpeg,image/png,image/gif"
                        className={inputClass}
                      />
                    </div>
                  </div>
                </section>

                <section className="mb-6">
                  <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-800">
                    Contact &amp; authentication
                  </h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className={labelClass}>Personal email</label>
                      <input type="email" name="email" defaultValue={student.email || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Google Workspace email</label>
                      <input
                        type="email"
                        name="google_workspace_email"
                        defaultValue={
                          student.google_workspace_email ||
                          student.suggested_google_workspace_email ||
                          ''
                        }
                        placeholder="Leave blank to auto-fill"
                        className={inputClass}
                      />
                    </div>
                  </div>
                </section>

                <section className="mb-6">
                  <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-800">Parent / guardian 1</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className={labelClass}>First name</label>
                      <input name="parent1_first_name" defaultValue={student.parent1_first_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Last name</label>
                      <input name="parent1_last_name" defaultValue={student.parent1_last_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Email</label>
                      <input type="email" name="parent1_email" defaultValue={student.parent1_email || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Phone</label>
                      <input type="tel" name="parent1_phone" defaultValue={student.parent1_phone || ''} maxLength={20} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Relationship</label>
                      <select name="parent1_relationship" defaultValue={student.parent1_relationship || ''} className={inputClass}>
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

                <section className="mb-6">
                  <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-800">Parent / guardian 2</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className={labelClass}>First name</label>
                      <input name="parent2_first_name" defaultValue={student.parent2_first_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Last name</label>
                      <input name="parent2_last_name" defaultValue={student.parent2_last_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Email</label>
                      <input type="email" name="parent2_email" defaultValue={student.parent2_email || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Phone</label>
                      <input type="tel" name="parent2_phone" defaultValue={student.parent2_phone || ''} maxLength={20} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Relationship</label>
                      <select name="parent2_relationship" defaultValue={student.parent2_relationship || ''} className={inputClass}>
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

                <section className="mb-6">
                  <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-800">Emergency contact</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className={labelClass}>First name</label>
                      <input name="emergency_first_name" defaultValue={student.emergency_first_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Last name</label>
                      <input name="emergency_last_name" defaultValue={student.emergency_last_name || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Email</label>
                      <input type="email" name="emergency_email" defaultValue={student.emergency_email || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Phone</label>
                      <input type="tel" name="emergency_phone" defaultValue={student.emergency_phone || ''} maxLength={20} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Relationship</label>
                      <select name="emergency_relationship" defaultValue={student.emergency_relationship || ''} className={inputClass}>
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

                <section>
                  <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-800">Address</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className={labelClass}>Street</label>
                      <input name="street" defaultValue={student.street || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Apt, unit, suite</label>
                      <input name="apt_unit" defaultValue={student.apt_unit || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>City</label>
                      <input name="city" defaultValue={student.city || ''} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>State</label>
                      <select name="state" defaultValue={student.state || ''} className={inputClass}>
                        <option value="">Choose state…</option>
                        {US_STATES.map((s) => (
                          <option key={s.code} value={s.code}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>ZIP code</label>
                      <input name="zip_code" defaultValue={student.zip_code || ''} className={inputClass} />
                    </div>
                  </div>
                </section>
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-100 bg-slate-50 px-5 py-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-teal-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                >
                  <i className="bi bi-check-circle" aria-hidden />
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </>
  )
}
