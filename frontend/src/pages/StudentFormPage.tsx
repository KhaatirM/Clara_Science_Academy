import { useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { submitStudentAddForm } from '../api/students'
import { StaffCredentialModal } from '../components/staff/StaffCredentialModal'
import {
  buildEntranceSchoolYearOptions,
  EMERGENCY_RELATIONSHIPS,
  PARENT_RELATIONSHIPS,
  STUDENT_GENDERS,
  STUDENT_GRADES_FOR_ADD,
  US_STATES,
} from '../config/studentForm'
import type { CredentialModalPayload } from '../types/staff'

const inputClass =
  'w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20'
const labelClass = 'mb-1 block text-sm font-medium text-hub-muted'
const sectionClass = 'overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg'

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
  const navigate = useNavigate()
  const formRef = useRef<HTMLFormElement>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [credentialModal, setCredentialModal] = useState<CredentialModalPayload | null>(null)
  const entranceYears = useMemo(() => buildEntranceSchoolYearOptions(), [])

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
    <div className="rounded-3xl bg-gradient-to-br from-rose-50 via-orange-50/80 to-amber-100 p-5 md:p-8">
      {credentialModal ? (
        <StaffCredentialModal payload={credentialModal} onClose={closeCredentialModal} />
      ) : null}

      <header className="mb-6">
        <Link
          to="/management/students"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-hub-accent hover:underline"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          Back to students
        </Link>
        <p className="mt-3 text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">
          Students
        </p>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-hub-text">Add student</h1>
        <p className="mt-2 text-sm text-hub-muted">
          Complete each section below. Required fields are marked with an asterisk.
        </p>
      </header>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <form ref={formRef} onSubmit={onSubmit} className="space-y-5" encType="multipart/form-data">
        <section className={sectionClass}>
          <div className="border-b border-teal-100 bg-slate-50 px-5 py-3">
            <h2 className="text-base font-bold text-hub-text">1. Student information</h2>
          </div>
          <div className="grid gap-4 p-5 md:grid-cols-2">
            <Field label="First name" required>
              <input name="student_first_name" required className={inputClass} />
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

        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-5 py-4 text-sm text-sky-900">
          <strong>Student portal:</strong> Login accounts are created automatically for{' '}
          <strong>3rd grade and above</strong>. Kindergarten through 2nd grade are saved without a portal account until
          they reach 3rd grade.
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-br from-rose-500 to-orange-400 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:brightness-105 disabled:opacity-60"
          >
            <i className="bi bi-check-lg" aria-hidden />
            {saving ? 'Saving…' : 'Add student'}
          </button>
          <Link
            to="/management/students"
            className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:border-teal-600 hover:text-teal-800"
          >
            <i className="bi bi-x-lg" aria-hidden />
            Discard
          </Link>
        </div>
      </form>
    </div>
  )
}
