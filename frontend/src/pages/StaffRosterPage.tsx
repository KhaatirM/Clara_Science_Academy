import { useCallback, useEffect, useState } from 'react'
import { Navigate, useOutletContext, useSearchParams } from 'react-router-dom'
import { fetchStaffDetail, fetchStaffRoster } from '../api/staff'
import { StaffDetailModal } from '../components/staff/StaffDetailModal'
import { StaffPageHeader } from '../components/staff/StaffPageHeader'
import type { ManagementOutletContext } from '../types/layout'
import type { StaffDetail, StaffRosterItem, StaffRosterTab } from '../types/staff'

function statusClasses(tone: StaffRosterItem['status_tone']) {
  switch (tone) {
    case 'success':
      return 'bg-emerald-100 text-emerald-800'
    case 'warning':
      return 'bg-amber-100 text-amber-900'
    case 'danger':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-slate-200 text-slate-700'
  }
}

export function StaffRosterPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const [searchParams, setSearchParams] = useSearchParams()
  const isDirector = user.role_canonical === 'Director'
  const initialTab = searchParams.get('tab') === 'former' ? 'former' : 'current'
  const initialQ = searchParams.get('q') ?? ''
  const [tab, setTab] = useState<StaffRosterTab>(initialTab)
  const [draftQ, setDraftQ] = useState(initialQ)
  const [q, setQ] = useState(initialQ)
  const [items, setItems] = useState<StaffRosterItem[]>([])
  const [counts, setCounts] = useState({ current: 0, former: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<StaffDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(async (activeTab: StaffRosterTab, search: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchStaffRoster(activeTab, search)
      setItems(data.items)
      setCounts(data.counts)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load roster')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(tab, q)
  }, [tab, q, load])

  useEffect(() => {
    const params = new URLSearchParams()
    if (tab !== 'current') params.set('tab', tab)
    if (q) params.set('q', q)
    setSearchParams(params, { replace: true })
  }, [tab, q, setSearchParams])

  const switchTab = (next: StaffRosterTab) => {
    setTab(next)
  }

  const applySearch = (search: string) => {
    setQ(search)
  }

  const openDetail = async (id: number) => {
    setDetailLoading(true)
    setDetail({ id } as StaffDetail)
    try {
      const data = await fetchStaffDetail(id)
      setDetail(data)
    } catch {
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  if (!user.management_entry) {
    return <Navigate to="/management/teachers" replace />
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
      <StaffPageHeader user={user} mode="roster" />

      <section className="mb-5 overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3 bg-gradient-to-br from-emerald-400 to-cyan-300 px-5 py-4 text-white">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <i className="bi bi-funnel" aria-hidden />
            Show
          </h2>
          <span className="text-sm text-white/90">
            {counts.current} current · {counts.former} former
          </span>
        </div>
        <div className="space-y-4 p-5">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => switchTab('current')}
              className={[
                'inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold',
                tab === 'current'
                  ? 'bg-teal-100 text-teal-900'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
              ].join(' ')}
            >
              <i className="bi bi-person-check-fill" aria-hidden />
              Current
            </button>
            <button
              type="button"
              onClick={() => switchTab('former')}
              className={[
                'inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold',
                tab === 'former'
                  ? 'bg-teal-100 text-teal-900'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
              ].join(' ')}
            >
              <i className="bi bi-person-x-fill" aria-hidden />
              Former
            </button>
          </div>
          <form
            className="flex flex-wrap items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              applySearch(draftQ.trim())
            }}
          >
            <label className="min-w-[220px] flex-1">
              <span className="mb-1 block text-sm font-medium text-hub-muted">Search this list</span>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={draftQ}
                onChange={(e) => setDraftQ(e.target.value)}
                placeholder="Name, email, staff ID…"
              />
            </label>
            <button
              type="submit"
              className="rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-300 px-4 py-2 text-sm font-semibold text-white"
            >
              <i className="bi bi-search me-1" aria-hidden />
              Search
            </button>
            {q ? (
              <button
                type="button"
                onClick={() => {
                  setDraftQ('')
                  applySearch('')
                }}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-muted hover:bg-slate-50"
              >
                Clear
              </button>
            ) : null}
          </form>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
        <div className="bg-gradient-to-br from-emerald-400 to-cyan-300 px-5 py-4 text-center text-white">
          <h2 className="flex items-center justify-center gap-2 text-base font-bold">
            <i className="bi bi-table" aria-hidden />
            {tab === 'current' ? 'Current employees' : 'Former employees'}
          </h2>
        </div>

        {loading ? (
          <div className="p-10 text-center text-hub-muted">Loading roster…</div>
        ) : error ? (
          <div className="p-10 text-center text-red-700">{error}</div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-hub-muted">No rows match.</div>
        ) : (
          <div className="overflow-x-auto p-5">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-800 text-white">
                <tr>
                  <th className="px-4 py-3 font-semibold">Name</th>
                  <th className="px-4 py-3 font-semibold">Role</th>
                  <th className="px-4 py-3 font-semibold">Department</th>
                  <th className="px-4 py-3 font-semibold">Email</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr
                    key={row.id}
                    className={[
                      'border-t border-slate-100 hover:bg-slate-50/80',
                      row.is_deleted ? 'bg-slate-50/60' : '',
                    ].join(' ')}
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-hub-text">{row.display_name}</div>
                      {row.staff_id ? (
                        <div className="text-xs text-hub-muted">ID: {row.staff_id}</div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      {row.has_account && row.role_display ? (
                        <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-900">
                          {row.role_display}
                        </span>
                      ) : (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                          No Account
                        </span>
                      )}
                      {row.assigned_role &&
                      (!row.role_display || row.assigned_role !== row.role_display) ? (
                        <div className="mt-1 text-xs text-hub-muted">{row.assigned_role}</div>
                      ) : null}
                    </td>
                    <td className="max-w-[180px] px-4 py-3 text-hub-muted">
                      {row.department
                        ? row.department.length > 80
                          ? `${row.department.slice(0, 80)}…`
                          : row.department
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-hub-muted">{row.email || '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusClasses(row.status_tone)}`}
                      >
                        {row.status_display}
                      </span>
                      {row.deleted_at ? (
                        <div className="mt-1 text-xs text-hub-muted">{row.deleted_at}</div>
                      ) : null}
                      {row.marked_for_removal ? (
                        <span className="ms-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">
                          Marked
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        title="View"
                        onClick={() => void openDetail(row.id)}
                        className="rounded-lg bg-teal-700 px-2.5 py-1.5 text-white hover:bg-teal-800"
                      >
                        <i className="bi bi-eye" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <StaffDetailModal detail={detail} loading={detailLoading} onClose={() => setDetail(null)} />
    </div>
  )
}
