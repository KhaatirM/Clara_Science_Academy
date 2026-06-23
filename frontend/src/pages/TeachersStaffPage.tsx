import { useCallback, useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { fetchStaffDetail, fetchStaffList, removeStaff } from '../api/staff'
import { StaffCard } from '../components/staff/StaffCard'
import { StaffDetailModal } from '../components/staff/StaffDetailModal'
import { StaffPageHeader } from '../components/staff/StaffPageHeader'
import { useStaffRecordsView } from '../hooks/useStaffRecordsView'
import type { ManagementOutletContext } from '../types/layout'
import type { StaffDetail, StaffFilters, StaffListItem } from '../types/staff'

const DEPARTMENTS = [
  '',
  'Mathematics',
  'Science',
  'English',
  'History & Social Studies',
  'Physical Education & Health',
  'Music & Arts',
  'Computer Science & Technology',
  'Administration',
  'Counseling',
  'Special Education',
  'Foreign Language',
  'Business',
]

const ROLES = [
  '',
  'Director',
  'School Administrator',
  'Teacher',
  'Substitute',
  'Counselor',
  'IT Support',
  'Other Staff',
]

const defaultFilters: StaffFilters = {
  search: '',
  search_type: 'all',
  department: '',
  role: '',
  employment: '',
  sort: 'name',
  order: 'asc',
}

function statusClasses(tone: StaffListItem['status_tone']) {
  switch (tone) {
    case 'success':
      return 'bg-emerald-100 text-emerald-800'
    case 'warning':
      return 'bg-amber-100 text-amber-900'
    case 'danger':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-slate-100 text-slate-700'
  }
}

function roleBadgeClass(bootstrapClass: string) {
  if (bootstrapClass.includes('primary')) return 'bg-indigo-100 text-indigo-800'
  if (bootstrapClass.includes('success')) return 'bg-emerald-100 text-emerald-800'
  if (bootstrapClass.includes('warning')) return 'bg-amber-100 text-amber-900'
  if (bootstrapClass.includes('danger')) return 'bg-red-100 text-red-800'
  if (bootstrapClass.includes('info')) return 'bg-sky-100 text-sky-800'
  return 'bg-slate-100 text-slate-700'
}

export function TeachersStaffPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const { view, setRecordsView } = useStaffRecordsView()
  const isDirector = user.role_canonical === 'Director'
  const [filters, setFilters] = useState<StaffFilters>(defaultFilters)
  const [draft, setDraft] = useState<StaffFilters>(defaultFilters)
  const [items, setItems] = useState<StaffListItem[]>([])
  const [stats, setStats] = useState({ total: 0, with_accounts: 0, without_accounts: 0, full_time: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<StaffDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const load = useCallback(async (active: StaffFilters) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchStaffList(active)
      setItems(data.items)
      setStats(data.stats)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load staff')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(filters)
  }, [filters, load])

  const applyFilters = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ ...draft })
  }

  const resetFilters = () => {
    setDraft(defaultFilters)
    setFilters(defaultFilters)
  }

  const openDetail = async (id: number) => {
    setDetailLoading(true)
    setDetail({ id } as StaffDetail)
    try {
      const data = await fetchStaffDetail(id)
      setDetail(data)
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Could not load details')
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleRemove = async (staff: StaffListItem) => {
    const ok = window.confirm(
      `Remove ${staff.display_name}? Their account will be deleted but historical work is preserved.`,
    )
    if (!ok) return
    try {
      const result = await removeStaff(staff.id)
      setActionMessage(result.message)
      void load(filters)
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Remove failed')
    }
  }

  return (
    <div
      className={[
        'rounded-3xl p-5 md:p-8',
        isDirector
          ? 'bg-gradient-to-br from-violet-50 via-violet-50/80 to-indigo-100'
          : 'bg-gradient-to-br from-emerald-50 via-teal-50/80 to-cyan-50',
      ].join(' ')}
    >
      <StaffPageHeader user={user} mode="manage" />

      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" role="list">
        <StatCard label="Total staff" value={stats.total} icon="bi-people-fill" />
        <StatCard label="With accounts" value={stats.with_accounts} icon="bi-person-check-fill" />
        <StatCard label="Without accounts" value={stats.without_accounts} icon="bi-person-x-fill" />
        <StatCard label="Full time" value={stats.full_time} icon="bi-calendar-check" />
      </div>

      <section className="mb-5 overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
        <div className="bg-gradient-to-br from-emerald-400 to-cyan-300 px-5 py-4 text-white">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <i className="bi bi-search" aria-hidden />
            Search &amp; filter staff
          </h2>
        </div>
        <form onSubmit={applyFilters} className="grid gap-3 p-5 md:grid-cols-2 lg:grid-cols-4">
          <label className="block md:col-span-2">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Search</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.search}
              onChange={(e) => setDraft({ ...draft, search: e.target.value })}
              placeholder="Name, email, role, department…"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Search in</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.search_type}
              onChange={(e) => setDraft({ ...draft, search_type: e.target.value })}
            >
              <option value="all">All fields</option>
              <option value="name">Name</option>
              <option value="contact">Contact</option>
              <option value="role">Role</option>
              <option value="department">Department</option>
              <option value="staff_id">Staff ID</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Department</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.department}
              onChange={(e) => setDraft({ ...draft, department: e.target.value })}
            >
              <option value="">All departments</option>
              {DEPARTMENTS.filter(Boolean).map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Role</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.role}
              onChange={(e) => setDraft({ ...draft, role: e.target.value })}
            >
              <option value="">All roles</option>
              {ROLES.filter(Boolean).map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Employment</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.employment}
              onChange={(e) => setDraft({ ...draft, employment: e.target.value })}
            >
              <option value="">All types</option>
              <option value="Full Time">Full time</option>
              <option value="Part Time">Part time</option>
            </select>
          </label>
          <div className="flex flex-wrap items-end gap-2 md:col-span-2">
            <button
              type="submit"
              className="rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-300 px-4 py-2 text-sm font-semibold text-white hover:brightness-105"
            >
              <i className="bi bi-search me-1" /> Search
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-muted hover:bg-slate-50"
            >
              Reset
            </button>
          </div>
        </form>
      </section>

      {actionMessage ? (
        <div className="mb-5 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
          {actionMessage}
          <button
            type="button"
            className="ms-3 font-semibold underline"
            onClick={() => setActionMessage(null)}
          >
            Dismiss
          </button>
        </div>
      ) : null}

      <section className="overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
        <div className="flex flex-col items-center gap-3 bg-gradient-to-br from-emerald-400 to-cyan-300 px-5 py-5 text-center text-white">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <i className="bi bi-table" aria-hidden />
            Staff Records
          </h2>
          <div className="flex flex-wrap justify-center gap-2">
            <button
              type="button"
              onClick={() => setRecordsView('table')}
              className={[
                'rounded-lg border-2 border-white px-4 py-1.5 text-sm font-semibold transition',
                view === 'table'
                  ? 'bg-white text-emerald-500'
                  : 'bg-white/20 text-white hover:bg-white/30',
              ].join(' ')}
            >
              <i className="bi bi-table" aria-hidden /> Table
            </button>
            <button
              type="button"
              onClick={() => setRecordsView('cards')}
              className={[
                'rounded-lg border-2 border-white px-4 py-1.5 text-sm font-semibold transition',
                view === 'cards'
                  ? 'bg-white text-emerald-500'
                  : 'bg-white/20 text-white hover:bg-white/30',
              ].join(' ')}
            >
              <i className="bi bi-grid-3x3-gap-fill" aria-hidden /> Cards
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-10 text-center text-hub-muted">Loading staff…</div>
        ) : error ? (
          <div className="p-10 text-center text-red-700">{error}</div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-hub-muted">
            <i className="bi bi-inbox mb-3 block text-5xl text-slate-300" aria-hidden />
            No staff found matching your criteria.
          </div>
        ) : view === 'table' ? (
          <div className="overflow-x-auto p-5 pt-0">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-800 text-white">
                <tr>
                  <th className="px-4 py-3 font-semibold">Name</th>
                  <th className="px-4 py-3 font-semibold">Role</th>
                  <th className="px-4 py-3 font-semibold">Department</th>
                  <th className="px-4 py-3 font-semibold">Email</th>
                  <th className="px-4 py-3 font-semibold">Employment</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((staff) => (
                  <tr key={staff.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {staff.image_url ? (
                          <img
                            src={staff.image_url}
                            alt=""
                            className="h-10 w-10 rounded-full object-cover"
                          />
                        ) : (
                          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-200 text-slate-500">
                            <i className="bi bi-person-fill" />
                          </div>
                        )}
                        <div>
                          <div className="font-semibold text-hub-text">{staff.display_name}</div>
                          {staff.staff_id ? (
                            <div className="text-xs text-hub-muted">ID: {staff.staff_id}</div>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {staff.role_badges.map((b) => (
                          <span
                            key={b.label}
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${roleBadgeClass(b.class)}`}
                          >
                            {b.label}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-hub-muted">{staff.department || '—'}</td>
                    <td className="px-4 py-3 text-hub-muted">{staff.email}</td>
                    <td className="px-4 py-3">{staff.employment_type || '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusClasses(staff.status_tone)}`}
                      >
                        {staff.status_display}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button
                          type="button"
                          title="View"
                          onClick={() => void openDetail(staff.id)}
                          className="rounded-lg bg-teal-700 px-2.5 py-1.5 text-white hover:bg-teal-800"
                        >
                          <i className="bi bi-eye" />
                        </button>
                        <Link
                          title="Edit"
                          to={`/management/teachers/${staff.id}/edit`}
                          className="rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-300 px-2.5 py-1.5 text-white"
                        >
                          <i className="bi bi-pencil" />
                        </Link>
                        <button
                          type="button"
                          title="Remove"
                          onClick={() => void handleRemove(staff)}
                          className="rounded-lg bg-gradient-to-br from-pink-400 to-rose-500 px-2.5 py-1.5 text-white"
                        >
                          <i className="bi bi-trash" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((staff) => (
              <StaffCard
                key={staff.id}
                staff={staff}
                roleBadgeClass={roleBadgeClass}
                statusClasses={statusClasses}
                onView={(id) => void openDetail(id)}
                onRemove={(s) => void handleRemove(s)}
              />
            ))}
          </div>
        )}
      </section>

      <StaffDetailModal detail={detail} loading={detailLoading} onClose={() => setDetail(null)} />
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="rounded-2xl border border-white/90 bg-white/95 p-4 shadow-md" role="listitem">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
          <i className={`bi ${icon}`} aria-hidden />
        </span>
        <div>
          <div className="text-2xl font-bold text-hub-text">{value}</div>
          <div className="text-sm text-hub-muted">{label}</div>
        </div>
      </div>
    </div>
  )
}
