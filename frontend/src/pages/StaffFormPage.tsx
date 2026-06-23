import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchStaffDetail, submitStaffForm } from '../api/staff'
import { StaffCredentialModal } from '../components/staff/StaffCredentialModal'
import {
  EMERGENCY_RELATIONSHIPS,
  STAFF_DEPARTMENTS,
  STAFF_GRADES,
  STAFF_PERMISSIONS,
  STAFF_ROLE_OPTIONS,
  US_STATES,
} from '../config/staffForm'
import type { CredentialModalPayload, StaffDetail } from '../types/staff'

const inputClass =
  'w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20'
const labelClass = 'mb-1 block text-sm font-medium text-hub-muted'
const sectionClass = 'overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg'

function detailToDefaults(data: StaffDetail) {
  return {
    first_name: data.first_name || '',
    middle_initial: (data.middle_initial as string) || '',
    last_name: data.last_name || '',
    dob: (data.dob as string) || '',
    phone: (data.phone as string) || '',
    staff_ssn: (data.staff_ssn as string) || '',
    email: (data.email as string) || '',
    street_address: (data.street as string) || '',
    apt_unit_suite: (data.apt_unit as string) || '',
    city: (data.city as string) || '',
    state: (data.state as string) || '',
    zip_code: (data.zip_code as string) || '',
    emergency_contact_name: (data.emergency_first_name as string) || '',
    emergency_contact_last_name: (data.emergency_last_name as string) || '',
    emergency_contact_relationship: (data.emergency_relationship as string) || '',
    emergency_contact_phone: (data.emergency_phone as string) || '',
    emergency_contact_email: (data.emergency_email as string) || '',
    assigned_role: (data.primary_role as string) || (data.assigned_role as string) || '',
    additional_roles: (data.secondary_roles as string[]) || [],
    hire_date: (data.hire_date as string) || '',
    departments: (data.department_list as string[]) || [],
    permissions: (data.permissions as string[]) || [],
    position: (data.position as string) || '',
    subject: (data.subject as string) || '',
    employment_type: (data.employment_type as string) || '',
    portal_login: data.portal_login !== false,
    is_temporary: Boolean(data.is_temporary),
    access_expires_at: (data.access_expires_at as string) || '',
    grades_taught: (data.grades_taught_list as string[]) || [],
    employment_status: (data.employment_status as string) || 'Active',
    marked_for_removal: Boolean(data.marked_for_removal),
    removal_note: (data.removal_note as string) || '',
    google_workspace_email: (data.google_workspace_email as string) || '',
    image: (data.image as string) || '',
  }
}

type FormDefaults = ReturnType<typeof detailToDefaults>

const emptyDefaults: FormDefaults = {
  first_name: '',
  middle_initial: '',
  last_name: '',
  dob: '',
  phone: '',
  staff_ssn: '',
  email: '',
  street_address: '',
  apt_unit_suite: '',
  city: '',
  state: '',
  zip_code: '',
  emergency_contact_name: '',
  emergency_contact_last_name: '',
  emergency_contact_relationship: '',
  emergency_contact_phone: '',
  emergency_contact_email: '',
  assigned_role: '',
  additional_roles: [],
  hire_date: '',
  departments: [],
  permissions: [],
  position: '',
  subject: '',
  employment_type: '',
  portal_login: true,
  is_temporary: false,
  access_expires_at: '',
  grades_taught: [],
  employment_status: 'Active',
  marked_for_removal: false,
  removal_note: '',
  google_workspace_email: '',
  image: '',
}

export function StaffFormPage() {
  const { staffId: staffIdParam } = useParams()
  const staffId = staffIdParam ? Number(staffIdParam) : null
  const editing = staffId !== null && !Number.isNaN(staffId)
  const navigate = useNavigate()
  const formRef = useRef<HTMLFormElement>(null)

  const [defaults, setDefaults] = useState<FormDefaults>(emptyDefaults)
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [credentialModal, setCredentialModal] = useState<CredentialModalPayload | null>(null)

  const [portalLogin, setPortalLogin] = useState(true)
  const [isTemporary, setIsTemporary] = useState(false)
  const [assignedRole, setAssignedRole] = useState('')
  const [departments, setDepartments] = useState<string[]>([])

  useEffect(() => {
    if (!editing || !staffId) return
    setLoading(true)
    void fetchStaffDetail(staffId)
      .then((data) => {
        const d = detailToDefaults(data)
        setDefaults(d)
        setPortalLogin(d.portal_login)
        setIsTemporary(d.is_temporary)
        setAssignedRole(d.assigned_role)
        setDepartments(d.departments)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load staff'))
      .finally(() => setLoading(false))
  }, [editing, staffId])

  const showPermissions = useMemo(() => {
    const hasAdminDept = departments.includes('Administration')
    const privileged = assignedRole === 'School Administrator' || assignedRole === 'Director'
    return hasAdminDept && !privileged
  }, [departments, assignedRole])

  const toggleList = (list: string[], value: string, checked: boolean) =>
    checked ? [...list, value] : list.filter((v) => v !== value)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formRef.current) return
    setSaving(true)
    setError(null)
    try {
      const fd = new FormData(formRef.current)
      const result = await submitStaffForm(editing, staffId, fd)
      if (result.credential_modal) {
        setCredentialModal(result.credential_modal)
      } else {
        navigate('/management/teachers')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const closeCredentialModal = () => {
    setCredentialModal(null)
    navigate('/management/teachers')
  }

  if (loading) {
    return (
      <div className="rounded-3xl bg-white/90 p-8 text-center text-hub-muted shadow-lg">
        Loading staff record…
      </div>
    )
  }

  return (
    <div className="rounded-3xl bg-gradient-to-br from-violet-50 via-violet-50/80 to-indigo-100 p-5 md:p-8">
      {credentialModal ? (
        <StaffCredentialModal payload={credentialModal} onClose={closeCredentialModal} />
      ) : null}

      <header className="mb-6">
        <Link
          to="/management/teachers"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-hub-accent hover:underline"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          Back to teachers &amp; staff
        </Link>
        <p className="mt-3 text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">
          Teachers &amp; staff
        </p>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-hub-text">
          {editing ? 'Update staff member' : 'Add staff member'}
        </h1>
        <p className="mt-2 text-sm text-hub-muted">
          {editing
            ? 'Update contact, role, and employment details.'
            : 'Complete each section below. Required fields are marked with an asterisk.'}
        </p>
      </header>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <form ref={formRef} onSubmit={onSubmit} className="space-y-5" encType="multipart/form-data">
        <div className="grid gap-5 lg:grid-cols-2">
          <section className={sectionClass}>
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="font-bold text-hub-text">1 · Personal information</h2>
            </div>
            <div className="grid gap-3 p-5 sm:grid-cols-12">
              <label className="sm:col-span-5">
                <span className={labelClass}>First name *</span>
                <input className={inputClass} name="first_name" required defaultValue={defaults.first_name} />
              </label>
              <label className="sm:col-span-2">
                <span className={labelClass}>M.I.</span>
                <input className={inputClass} name="middle_initial" maxLength={1} defaultValue={defaults.middle_initial} />
              </label>
              <label className="sm:col-span-5">
                <span className={labelClass}>Last name *</span>
                <input className={inputClass} name="last_name" required defaultValue={defaults.last_name} />
              </label>
              <label className="sm:col-span-4">
                <span className={labelClass}>Date of birth *</span>
                <input className={inputClass} type="date" name="dob" required defaultValue={defaults.dob} />
              </label>
              <label className="sm:col-span-4">
                <span className={labelClass}>Phone *</span>
                <input className={inputClass} type="tel" name="phone" required defaultValue={defaults.phone} />
              </label>
              <label className="sm:col-span-4">
                <span className={labelClass}>SSN</span>
                <input className={inputClass} name="staff_ssn" defaultValue={defaults.staff_ssn} />
              </label>
              <label className="sm:col-span-12">
                <span className={labelClass}>Email *</span>
                <input className={inputClass} type="email" name="email" required defaultValue={defaults.email} />
              </label>
              <label className="sm:col-span-12">
                <span className={labelClass}>Profile photo</span>
                <input className={inputClass} type="file" name="staff_image" accept="image/jpeg,image/png,image/gif,.jpg,.jpeg,.png,.gif" />
                {defaults.image ? (
                  <p className="mt-1 text-xs text-hub-muted">Current photo on file. Upload to replace.</p>
                ) : null}
              </label>
            </div>
          </section>

          <section className={sectionClass}>
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="font-bold text-hub-text">2 · Address</h2>
            </div>
            <div className="grid gap-3 p-5">
              <label>
                <span className={labelClass}>Street address *</span>
                <input className={inputClass} name="street_address" required defaultValue={defaults.street_address} />
              </label>
              <label>
                <span className={labelClass}>Apt / unit / suite</span>
                <input className={inputClass} name="apt_unit_suite" defaultValue={defaults.apt_unit_suite} />
              </label>
              <div className="grid gap-3 sm:grid-cols-12">
                <label className="sm:col-span-5">
                  <span className={labelClass}>City *</span>
                  <input className={inputClass} name="city" required defaultValue={defaults.city} />
                </label>
                <label className="sm:col-span-4">
                  <span className={labelClass}>State *</span>
                  <select className={inputClass} name="state" required defaultValue={defaults.state}>
                    <option value="">Choose state…</option>
                    {US_STATES.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="sm:col-span-3">
                  <span className={labelClass}>Zip *</span>
                  <input className={inputClass} name="zip_code" required defaultValue={defaults.zip_code} />
                </label>
              </div>
            </div>
          </section>
        </div>

        <section className={sectionClass}>
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="font-bold text-hub-text">Website access</h2>
          </div>
          <div className="space-y-3 p-5">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                name="portal_login"
                value="on"
                className="mt-1"
                checked={portalLogin}
                onChange={(e) => setPortalLogin(e.target.checked)}
              />
              <span className="text-sm">
                <span className="font-semibold">Allow website (portal) login</span>
                <span className="mt-1 block text-hub-muted">
                  Creates a website username/password and assigns a school email for Google sign-in.
                </span>
              </span>
            </label>
            {editing && portalLogin ? (
              <label>
                <span className={labelClass}>School email (Google)</span>
                <input
                  className={inputClass}
                  name="google_workspace_email"
                  defaultValue={defaults.google_workspace_email}
                  placeholder="first.last@clarascienceacademy.org"
                />
              </label>
            ) : null}
          </div>
        </section>

        <section className={sectionClass}>
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="font-bold text-hub-text">3 · Emergency contact</h2>
          </div>
          <div className="grid gap-3 p-5 md:grid-cols-2">
            <label>
              <span className={labelClass}>First name *</span>
              <input className={inputClass} name="emergency_contact_name" required defaultValue={defaults.emergency_contact_name} />
            </label>
            <label>
              <span className={labelClass}>Last name *</span>
              <input className={inputClass} name="emergency_contact_last_name" required defaultValue={defaults.emergency_contact_last_name} />
            </label>
            <label>
              <span className={labelClass}>Relationship</span>
              <select className={inputClass} name="emergency_contact_relationship" defaultValue={defaults.emergency_contact_relationship}>
                <option value="">Choose…</option>
                {EMERGENCY_RELATIONSHIPS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelClass}>Phone *</span>
              <input className={inputClass} type="tel" name="emergency_contact_phone" required defaultValue={defaults.emergency_contact_phone} />
            </label>
            <label className="md:col-span-2">
              <span className={labelClass}>Email</span>
              <input className={inputClass} type="email" name="emergency_contact_email" defaultValue={defaults.emergency_contact_email} />
            </label>
          </div>
        </section>

        <section className={sectionClass}>
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="font-bold text-hub-text">4 · Professional information</h2>
          </div>
          <div className="space-y-4 p-5">
            <div className="grid gap-3 md:grid-cols-2">
              <label>
                <span className={labelClass}>Primary role *</span>
                <select
                  className={inputClass}
                  name="assigned_role"
                  required
                  value={assignedRole}
                  onChange={(e) => setAssignedRole(e.target.value)}
                >
                  <option value="">Choose role…</option>
                  {STAFF_ROLE_OPTIONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className={labelClass}>Hire date *</span>
                <input className={inputClass} type="date" name="hire_date" required defaultValue={defaults.hire_date} />
              </label>
            </div>

            <div>
              <p className={labelClass}>Additional roles</p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {STAFF_ROLE_OPTIONS.map((role) => (
                  <label key={role} className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm">
                    <input
                      type="checkbox"
                      name="additional_roles"
                      value={role}
                      defaultChecked={defaults.additional_roles.includes(role)}
                    />
                    {role}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <p className={labelClass}>Department(s) *</p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {STAFF_DEPARTMENTS.map((dept) => (
                  <label key={dept} className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm">
                    <input
                      type="checkbox"
                      name="department"
                      value={dept}
                      checked={departments.includes(dept)}
                      onChange={(e) => setDepartments((prev) => toggleList(prev, dept, e.target.checked))}
                    />
                    {dept}
                  </label>
                ))}
              </div>
            </div>

            {showPermissions ? (
              <div>
                <p className={labelClass}>Administration permissions</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {STAFF_PERMISSIONS.map((perm) => (
                    <label key={perm.key} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        name="permissions"
                        value={perm.key}
                        defaultChecked={defaults.permissions.includes(perm.key)}
                      />
                      {perm.label}
                    </label>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2">
              <label>
                <span className={labelClass}>Position</span>
                <input className={inputClass} name="position" defaultValue={defaults.position} />
              </label>
              <label>
                <span className={labelClass}>Primary subject(s)</span>
                <input className={inputClass} name="subject" defaultValue={defaults.subject} />
              </label>
            </div>

            <fieldset>
              <legend className={labelClass}>Employment type *</legend>
              <div className="flex flex-wrap gap-3">
                {(['Full Time', 'Part Time'] as const).map((type) => (
                  <label key={type} className="flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm">
                    <input
                      type="radio"
                      name="employment_type"
                      value={type}
                      required
                      defaultChecked={defaults.employment_type === type}
                    />
                    {type}
                  </label>
                ))}
              </div>
            </fieldset>

            {editing ? (
              <div className="grid gap-3 md:grid-cols-2">
                <label>
                  <span className={labelClass}>Employment status</span>
                  <select className={inputClass} name="employment_status" defaultValue={defaults.employment_status}>
                    <option value="Active">Active</option>
                    <option value="On Leave">On leave</option>
                    <option value="Inactive">Inactive (no longer employed)</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 self-end rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm">
                  <input
                    type="checkbox"
                    name="marked_for_removal"
                    value="on"
                    defaultChecked={defaults.marked_for_removal}
                  />
                  Mark for removal
                </label>
                <label className="md:col-span-2">
                  <span className={labelClass}>Removal note</span>
                  <textarea className={inputClass} name="removal_note" rows={2} defaultValue={defaults.removal_note} />
                </label>
              </div>
            ) : null}

            {portalLogin ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4">
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    name="is_temporary"
                    value="on"
                    className="mt-1"
                    checked={isTemporary}
                    onChange={(e) => setIsTemporary(e.target.checked)}
                  />
                  <span className="text-sm font-semibold">Temporary staff member (time-limited access)</span>
                </label>
                {isTemporary ? (
                  <label className="mt-3 block">
                    <span className={labelClass}>Access expires on *</span>
                    <input
                      className={inputClass}
                      type="datetime-local"
                      name="access_expires_at"
                      required={isTemporary}
                      defaultValue={defaults.access_expires_at}
                    />
                  </label>
                ) : null}
              </div>
            ) : null}

            <div>
              <p className={labelClass}>Grade(s) taught / overseeing</p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {STAFF_GRADES.map((grade) => (
                  <label key={grade} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      name="grades_taught"
                      value={grade}
                      defaultChecked={defaults.grades_taught.includes(grade)}
                    />
                    {grade}
                  </label>
                ))}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label>
                <span className={labelClass}>Resume (PDF, DOC, DOCX)</span>
                <input className={inputClass} type="file" name="resume" accept=".pdf,.doc,.docx" />
              </label>
              <label>
                <span className={labelClass}>Other documents</span>
                <input className={inputClass} type="file" name="other_document" accept=".pdf,.doc,.docx,image/*" />
              </label>
            </div>
          </div>
        </section>

        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-br from-violet-600 to-violet-800 px-5 py-2.5 text-sm font-semibold text-white shadow-md disabled:opacity-60"
          >
            <i className="bi bi-check-lg" aria-hidden />
            {saving ? 'Saving…' : editing ? 'Update staff' : 'Add staff'}
          </button>
          <Link
            to="/management/teachers"
            className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:border-teal-600 hover:text-teal-800"
          >
            <i className="bi bi-x-lg" aria-hidden />
            {editing ? 'Cancel' : 'Discard'}
          </Link>
        </div>
      </form>
    </div>
  )
}
