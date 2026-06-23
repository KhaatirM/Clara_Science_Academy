import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import {
  fetchStudentDetail,
  fetchStudentList,
  markStudentsRepeating,
  removeStudent,
} from '../api/students'
import { getCsrfToken } from '../api/client'
import { StudentDetailModal } from '../components/students/StudentDetailModal'
import { StudentEditModal } from '../components/students/StudentEditModal'
import type { ManagementOutletContext } from '../types/layout'
import type {
  StudentDetail,
  StudentFilters,
  StudentListItem,
  StudentTone,
} from '../types/students'

type RecordsView = 'table' | 'cards' | 'grouped'
type ViewModeSelect = 'list' | 'grouped' | 'alerts_only'

const GRADE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All grades' },
  { value: '0', label: 'Kindergarten' },
  ...Array.from({ length: 12 }, (_, i) => ({
    value: String(i + 1),
    label: `${i + 1}${i === 0 ? 'st' : i === 1 ? 'nd' : i === 2 ? 'rd' : 'th'} grade`,
  })),
]

const defaultFilters: StudentFilters = {
  search: '',
  search_type: 'all',
  grade_level: '',
  status: '',
  alert_filter: '',
  sort: 'name',
  order: 'asc',
  page: 1,
}

function toneClasses(tone: StudentTone) {
  switch (tone) {
    case 'success':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200'
    case 'warning':
      return 'bg-amber-100 text-amber-900 border-amber-200'
    case 'danger':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'primary':
      return 'bg-sky-100 text-sky-800 border-sky-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

function gpaClasses(level: StudentListItem['alert_level']) {
  switch (level) {
    case 'critical':
      return 'bg-red-100 text-red-800'
    case 'warning':
      return 'bg-amber-100 text-amber-900'
    case 'excellent':
      return 'bg-emerald-100 text-emerald-800'
    default:
      return 'bg-slate-100 text-slate-700'
  }
}

function resolveAccountBadgeKind(
  student: Pick<
    StudentListItem,
    'account_badge_kind' | 'grade_level' | 'has_account' | 'is_deleted'
  >,
): StudentListItem['account_badge_kind'] {
  if (student.account_badge_kind) {
    return student.account_badge_kind
  }
  const young = student.grade_level != null && Number(student.grade_level) < 3
  if (student.is_deleted) return 'removed'
  if (student.has_account) return young ? 'has_young' : 'has_active'
  return young ? 'no_young' : 'no_active'
}

/** Legacy Bootstrap badge colors (#dc3545 danger, #fd7e14 warning, #198754 success). */
function accountBadgeClasses(kind: StudentListItem['account_badge_kind']) {
  switch (kind) {
    case 'removed':
    case 'no_active':
      return 'border-[#dc3545] bg-[#dc3545] text-white'
    case 'has_young':
    case 'no_young':
      return 'border-[#fd7e14] bg-[#fd7e14] text-[#212529]'
    case 'has_active':
      return 'border-[#198754] bg-[#198754] text-white'
    default:
      return 'border-slate-300 bg-slate-100 text-slate-700'
  }
}

function accountBadgeIcon(kind: StudentListItem['account_badge_kind']) {
  switch (kind) {
    case 'removed':
      return 'bi-archive'
    case 'has_young':
    case 'has_active':
      return 'bi-check-circle'
    case 'no_young':
      return 'bi-hourglass-split'
    case 'no_active':
      return 'bi-x-circle'
    default:
      return 'bi-person'
  }
}

export function StudentsPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const navigate = useNavigate()
  const isDirector = user.role_canonical === 'Director'
  const [filters, setFilters] = useState<StudentFilters>(defaultFilters)
  const [draft, setDraft] = useState<StudentFilters>(defaultFilters)
  const [viewModeSelect, setViewModeSelect] = useState<ViewModeSelect>('list')
  const [recordsView, setRecordsView] = useState<RecordsView>('table')
  const [showSearchTips, setShowSearchTips] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [items, setItems] = useState<StudentListItem[]>([])
  const [stats, setStats] = useState({
    total: 0,
    with_accounts: 0,
    without_accounts: 0,
    on_page: 0,
    high_gpa: 0,
  })
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 40,
    total: 0,
    pages: 1,
    has_next: false,
    has_prev: false,
  })
  const [canAdminUi, setCanAdminUi] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [detail, setDetail] = useState<StudentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [editStudentId, setEditStudentId] = useState<number | null>(null)

  const load = useCallback(async (active: StudentFilters) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchStudentList(active)
      setItems(data.items)
      setStats(data.stats)
      setPagination(data.pagination)
      setCanAdminUi(data.meta.can_admin_ui)
      setSelectedIds(new Set())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load students')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(filters)
  }, [filters, load])

  const applyFilters = (e: React.FormEvent) => {
    e.preventDefault()
    let alertFilter = draft.alert_filter
    let nextView = recordsView
    if (viewModeSelect === 'alerts_only') {
      alertFilter = 'critical'
      nextView = 'table'
    } else if (viewModeSelect === 'grouped') {
      nextView = 'grouped'
    } else {
      nextView = recordsView === 'grouped' ? 'table' : recordsView
    }
    setRecordsView(nextView)
    setFilters({ ...draft, alert_filter: alertFilter, page: 1 })
  }

  const resetFilters = () => {
    setDraft(defaultFilters)
    setFilters(defaultFilters)
    setViewModeSelect('list')
    setRecordsView('table')
  }

  const goToPage = (page: number) => {
    setFilters((prev) => ({ ...prev, page }))
    setDraft((prev) => ({ ...prev, page }))
  }

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(items.map((s) => s.id)))
    }
  }

  const handleMarkRepeating = async () => {
    const ids = [...selectedIds]
    if (!ids.length) {
      setActionMessage('Select at least one student first.')
      return
    }
    if (!window.confirm(`Mark ${ids.length} student(s) as repeating?`)) return
    try {
      const result = await markStudentsRepeating(ids)
      setActionMessage(result.message)
      void load(filters)
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Update failed')
    }
  }

  const handleRemove = async (student: StudentListItem) => {
    if (!window.confirm(`Remove ${student.display_name}? Their account will be deleted but records are preserved.`)) {
      return
    }
    try {
      const result = await removeStudent(student.id)
      setActionMessage(result.message)
      void load(filters)
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Remove failed')
    }
  }

  const openDetail = async (id: number) => {
    setDetailLoading(true)
    setDetail({ id } as StudentDetail)
    try {
      const data = await fetchStudentDetail(id)
      setDetail(data)
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Could not load student details')
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const groupedByGrade = useMemo(() => {
    const map = new Map<number, StudentListItem[]>()
    for (const s of items) {
      const g = s.grade_level ?? 0
      if (!map.has(g)) map.set(g, [])
      map.get(g)!.push(s)
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0])
  }, [items])

  const shellClass = isDirector
    ? 'bg-gradient-to-br from-violet-50 via-violet-50/80 to-indigo-100'
    : 'bg-gradient-to-br from-rose-50 via-orange-50/50 to-amber-50'

  const hasActiveFilters =
    Boolean(filters.search || filters.grade_level || filters.status || filters.alert_filter)

  return (
    <div className={`rounded-3xl p-5 md:p-8 ${shellClass}`}>
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">
            Student records
          </p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-hub-text">Students</h1>
          <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-hub-muted">
            <i className="bi bi-people-fill" aria-hidden />
            Manage enrollments, accounts, and academic records
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isDirector ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-gradient-to-br from-violet-100 to-violet-200 px-3.5 py-2 text-[0.82rem] font-bold text-violet-800">
              <i className="bi bi-award-fill" aria-hidden />
              Director
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-gradient-to-br from-teal-100 to-emerald-200 px-3.5 py-2 text-[0.82rem] font-bold text-teal-900">
              <i className="bi bi-shield-fill" aria-hidden />
              Administrator
            </span>
          )}
          {canAdminUi ? (
            <Link
              to="/management/students/new"
              className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br from-rose-500 to-orange-400 px-3.5 py-2 text-[0.82rem] font-semibold text-white shadow-sm hover:brightness-105"
            >
              <i className="bi bi-plus-circle" aria-hidden />
              Add student
            </Link>
          ) : null}
          <button
            type="button"
            onClick={() => navigate('/management')}
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 hover:border-teal-600 hover:text-teal-800"
          >
            <i className="bi bi-house-door" aria-hidden />
            Dashboard
          </button>
        </div>
      </header>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" role="list">
        <StatCard label="Total students" value={stats.total} icon="bi-people-fill" />
        <StatCard label="With accounts" value={stats.with_accounts} icon="bi-person-check-fill" />
        <StatCard label="Without accounts" value={stats.without_accounts} icon="bi-person-x-fill" />
        <StatCard label="On this page" value={stats.on_page} icon="bi-funnel" />
      </div>

      <section className="mb-5 overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-teal-100 bg-slate-50 px-5 py-3">
          <h2 className="flex items-center gap-2 text-base font-bold text-hub-text">
            <i className="bi bi-search text-teal-700" aria-hidden />
            Search &amp; filter students
          </h2>
          <AccountStatusLegend />
        </div>
        <form onSubmit={applyFilters} className="grid gap-3 p-5 md:grid-cols-2 lg:grid-cols-4">
          <label className="block md:col-span-2">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Search term</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.search}
              onChange={(e) => setDraft({ ...draft, search: e.target.value })}
              placeholder="Enter search term…"
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
              <option value="name">Student name</option>
              <option value="contact">Contact info</option>
              <option value="phone">Phone numbers</option>
              <option value="address">Address</option>
              <option value="parents">Parent names</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Grade level</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.grade_level}
              onChange={(e) => setDraft({ ...draft, grade_level: e.target.value })}
            >
              {GRADE_OPTIONS.map((g) => (
                <option key={g.value || 'all'} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Account status</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.status}
              onChange={(e) => setDraft({ ...draft, status: e.target.value })}
            >
              <option value="">All students</option>
              <option value="has_account">Has account</option>
              <option value="no_account">No account</option>
              {canAdminUi ? (
                <>
                  <option value="former">Former (removed)</option>
                  <option value="all">All (current + former)</option>
                </>
              ) : null}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Academic alert</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.alert_filter}
              onChange={(e) => setDraft({ ...draft, alert_filter: e.target.value })}
            >
              <option value="">All students</option>
              <option value="critical">Critical (&lt;2.0 GPA)</option>
              <option value="warning">Warning (2.0–2.9 GPA)</option>
              <option value="good">Good standing (3.0+)</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">Sort by</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={draft.sort}
              onChange={(e) => setDraft({ ...draft, sort: e.target.value })}
            >
              <option value="name">Name (A–Z)</option>
              <option value="grade">Grade level</option>
              <option value="id">Student ID</option>
              <option value="gpa">GPA (low to high)</option>
              <option value="gpa_desc">GPA (high to low)</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-hub-muted">View mode</span>
            <select
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={viewModeSelect}
              onChange={(e) => setViewModeSelect(e.target.value as ViewModeSelect)}
            >
              <option value="list">All students</option>
              <option value="grouped">Grouped by grade</option>
              <option value="alerts_only">Alerts only</option>
            </select>
          </label>
          <div className="flex flex-wrap items-end gap-2 md:col-span-2 lg:col-span-4">
            <button
              type="submit"
              className="rounded-xl bg-gradient-to-br from-teal-600 to-cyan-500 px-4 py-2 text-sm font-semibold text-white hover:brightness-105"
            >
              <i className="bi bi-search me-1" /> Search
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-muted hover:bg-slate-50"
            >
              <i className="bi bi-arrow-clockwise me-1" /> Reset
            </button>
            <button
              type="button"
              onClick={() => setShowSearchTips((v) => !v)}
              className="rounded-xl border border-teal-600 px-4 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50"
            >
              <i className="bi bi-info-circle me-1" /> Search tips
            </button>
          </div>
        </form>
        {showSearchTips ? <SearchTipsPanel /> : null}
      </section>

      {canAdminUi ? (
        <section className="mb-5 overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
          <div className="border-b border-slate-100 px-5 py-3">
            <h2 className="flex items-center gap-2 text-base font-bold text-hub-text">
              <i className="bi bi-arrow-repeat text-amber-600" aria-hidden />
              Repeat grade (bulk update)
            </h2>
          </div>
          <div className="p-5">
            <p className="mb-3 text-sm text-hub-muted">
              Select students in the table below, then mark them as repeating. This sets{' '}
              <code className="rounded bg-slate-100 px-1">is_repeating</code> and bumps{' '}
              <code className="rounded bg-slate-100 px-1">grad_year</code> by 1 when graduation year
              is known.
            </p>
            <button
              type="button"
              onClick={() => void handleMarkRepeating()}
              className="inline-flex items-center gap-1.5 rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600"
            >
              <i className="bi bi-arrow-repeat" aria-hidden />
              Mark selected as repeating
            </button>
          </div>
        </section>
      ) : null}

      {canAdminUi ? <CsvImportExportPanel /> : null}

      {hasActiveFilters ? (
        <div className="mb-5 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
          <i className="bi bi-info-circle me-1" aria-hidden />
          <strong>Search results:</strong> Found {stats.total} student(s)
          {filters.search ? ` matching "${filters.search}"` : ''}
        </div>
      ) : null}

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

      {error ? (
        <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <section className="overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
        <div className="flex flex-col items-center gap-3 bg-gradient-to-br from-teal-600 to-cyan-500 px-5 py-5 text-center text-white">
          <div className="flex flex-wrap items-center justify-center gap-2">
            <h2 className="flex items-center gap-2 text-base font-bold">
              <i className="bi bi-table" aria-hidden />
              Student records
            </h2>
            <span className="rounded-full bg-blue-500 px-2.5 py-0.5 text-xs font-bold">
              {stats.on_page} on this page
            </span>
            <span className="rounded-full bg-slate-600/80 px-2.5 py-0.5 text-xs font-bold">
              {stats.total} matching
            </span>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <ViewToggleButton
              active={recordsView === 'table'}
              icon="bi-table"
              label="Table"
              onClick={() => setRecordsView('table')}
            />
            <ViewToggleButton
              active={recordsView === 'cards'}
              icon="bi-grid-3x3-gap-fill"
              label="Cards"
              onClick={() => setRecordsView('cards')}
            />
            <ViewToggleButton
              active={recordsView === 'grouped'}
              icon="bi-grid"
              label="By grade"
              onClick={() => setRecordsView('grouped')}
            />
          </div>
        </div>

        {pagination.pages > 1 ? (
          <p className="border-b border-slate-100 px-5 py-2 text-xs text-hub-muted">
            <i className="bi bi-info-circle me-1" aria-hidden />
            List and card views show <strong>{pagination.per_page}</strong> students per page.
            Grouped-by-grade uses only the current page.
          </p>
        ) : null}

        {loading ? (
          <div className="p-10 text-center text-hub-muted">Loading students…</div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-hub-muted">
            <i className="bi bi-inbox mb-2 block text-3xl" aria-hidden />
            No students found.
          </div>
        ) : recordsView === 'table' ? (
          <StudentTable
            items={items}
            canAdminUi={canAdminUi}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onView={openDetail}
            onEdit={setEditStudentId}
            onRemove={handleRemove}
          />
        ) : recordsView === 'cards' ? (
          <StudentCards
            items={items}
            canAdminUi={canAdminUi}
            onView={openDetail}
            onEdit={setEditStudentId}
            onRemove={handleRemove}
          />
        ) : (
          <StudentGrouped
            groups={groupedByGrade}
            canAdminUi={canAdminUi}
            onView={openDetail}
            onEdit={setEditStudentId}
            onRemove={handleRemove}
          />
        )}

        {pagination.pages > 1 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-4">
            <p className="text-sm text-hub-muted">
              Page {pagination.page} of {pagination.pages} · {pagination.total} students
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={!pagination.has_prev}
                onClick={() => goToPage(pagination.page - 1)}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!pagination.has_next}
                onClick={() => goToPage(pagination.page + 1)}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <StudentDetailModal detail={detail} loading={detailLoading} onClose={() => setDetail(null)} />
      {editStudentId !== null ? (
        <StudentEditModal
          studentId={editStudentId}
          onClose={() => setEditStudentId(null)}
          onSaved={(message) => {
            setEditStudentId(null)
            setActionMessage(message)
            void load(filters)
          }}
        />
      ) : null}
    </div>
  )
}

function AccountStatusLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-hub-muted">
      <span className="font-semibold text-hub-text">Account status</span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#dc3545]" aria-hidden />
        Removed / No account
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#fd7e14]" aria-hidden />
        Too young / Not yet
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#198754]" aria-hidden />
        Grade 3+ active
      </span>
    </div>
  )
}

function SearchTipsPanel() {
  return (
    <div className="mx-5 mb-5 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-slate-700">
      <h3 className="mb-2 flex items-center gap-1.5 font-bold text-hub-text">
        <i className="bi bi-lightbulb text-amber-500" aria-hidden />
        Search tips
      </h3>
      <ul className="list-disc space-y-1 ps-5">
        <li>
          <strong>All fields:</strong> Search across names, contact info, addresses, and parents
        </li>
        <li>
          <strong>Student name:</strong> First or last name
        </li>
        <li>
          <strong>Contact info:</strong> Student or parent email addresses
        </li>
        <li>
          <strong>Phone numbers:</strong> Parent or emergency phone numbers
        </li>
        <li>
          <strong>Address:</strong> Street, city, state, or zip code
        </li>
        <li>
          <strong>Parent names:</strong> Parent or guardian first or last names
        </li>
      </ul>
    </div>
  )
}

function CsvImportExportPanel() {
  const csrf = getCsrfToken()
  return (
    <section className="mb-5 overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
      <div className="border-b border-slate-100 px-5 py-3">
        <h2 className="flex items-center gap-2 text-base font-bold text-hub-text">
          <i className="bi bi-file-earmark-spreadsheet text-teal-700" aria-hidden />
          CSV import/export
        </h2>
      </div>
      <div className="grid gap-5 p-5 md:grid-cols-3">
        <div>
          <h3 className="mb-1 flex items-center gap-1.5 text-sm font-bold">
            <i className="bi bi-download" aria-hidden /> Export students
          </h3>
          <p className="mb-2 text-xs text-hub-muted">Download all student data as a CSV file.</p>
          <a
            href="/management/students/download-csv"
            className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
          >
            <i className="bi bi-file-earmark-arrow-down" aria-hidden /> Download CSV
          </a>
        </div>
        <div>
          <h3 className="mb-1 flex items-center gap-1.5 text-sm font-bold">
            <i className="bi bi-file-earmark-text" aria-hidden /> CSV template
          </h3>
          <p className="mb-2 text-xs text-hub-muted">Download a template with example data.</p>
          <a
            href="/management/students/download-template"
            className="inline-flex items-center gap-1 rounded-lg bg-sky-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-600"
          >
            <i className="bi bi-file-earmark-text" aria-hidden /> Download template
          </a>
        </div>
        <div>
          <h3 className="mb-1 flex items-center gap-1.5 text-sm font-bold">
            <i className="bi bi-upload" aria-hidden /> Import students
          </h3>
          <p className="mb-2 text-xs text-hub-muted">Upload a CSV file to add or update students.</p>
          <form
            method="POST"
            action="/management/students/upload-csv"
            encType="multipart/form-data"
            className="flex flex-wrap gap-2"
          >
            {csrf ? <input type="hidden" name="csrf_token" value={csrf} /> : null}
            <input
              type="file"
              name="csv_file"
              accept=".csv"
              required
              className="max-w-[180px] text-xs"
            />
            <button
              type="submit"
              className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              <i className="bi bi-upload" aria-hidden /> Upload
            </button>
          </form>
        </div>
      </div>
      <div className="mx-5 mb-5 rounded-xl border border-sky-200 bg-sky-50 p-4 text-xs text-slate-700">
        <h3 className="mb-2 flex items-center gap-1.5 font-bold">
          <i className="bi bi-info-circle" aria-hidden /> CSV upload instructions
        </h3>
        <ul className="list-disc space-y-1 ps-5">
          <li>Download the template to see the required format and example data.</li>
          <li>
            <strong>Required fields:</strong> First name and last name.
          </li>
          <li>Student ID: leave blank to auto-generate (requires state and date of birth).</li>
          <li>Date format: MM/DD/YYYY (e.g. 01/15/2010).</li>
          <li>Update existing students by Student ID or first name + last name + DOB.</li>
        </ul>
      </div>
    </section>
  )
}

function ViewToggleButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean
  icon: string
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'inline-flex items-center gap-1.5 rounded-lg border-2 px-3 py-1.5 text-sm font-semibold transition',
        active
          ? 'border-white bg-white text-teal-600'
          : 'border-white/40 bg-white/15 text-white hover:bg-white/25',
      ].join(' ')}
    >
      <i className={`bi ${icon}`} aria-hidden />
      {label}
    </button>
  )
}

function AccountBadge({ student }: { student: StudentListItem }) {
  const kind = resolveAccountBadgeKind(student)
  return (
    <span
      className={[
        'inline-flex max-w-[150px] items-center gap-1 truncate rounded-full border px-2.5 py-0.5 text-xs font-semibold',
        accountBadgeClasses(kind),
      ].join(' ')}
      title={student.account_status}
    >
      <i className={`bi ${accountBadgeIcon(kind)}`} aria-hidden />
      {student.account_status}
    </span>
  )
}

function ActionButtons({
  student,
  canAdminUi,
  onView,
  onEdit,
  onRemove,
}: {
  student: StudentListItem
  canAdminUi: boolean
  onView: (id: number) => void
  onEdit: (id: number) => void
  onRemove: (s: StudentListItem) => void
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-lg shadow-sm">
      <button
        type="button"
        onClick={() => onView(student.id)}
        className="bg-teal-800 px-2.5 py-1.5 text-white hover:bg-teal-900"
        title="View details"
      >
        <i className="bi bi-eye" aria-hidden />
      </button>
      {canAdminUi ? (
        <>
          <button
            type="button"
            onClick={() => onEdit(student.id)}
            className="bg-teal-500 px-2.5 py-1.5 text-white hover:bg-teal-600"
            title="Edit student"
          >
            <i className="bi bi-pencil" aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => void onRemove(student)}
            className="bg-rose-500 px-2.5 py-1.5 text-white hover:bg-rose-600"
            title="Remove student"
          >
            <i className="bi bi-trash" aria-hidden />
          </button>
        </>
      ) : null}
    </div>
  )
}

function StudentTable({
  items,
  canAdminUi,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onView,
  onEdit,
  onRemove,
}: {
  items: StudentListItem[]
  canAdminUi: boolean
  selectedIds: Set<number>
  onToggleSelect: (id: number) => void
  onToggleSelectAll: () => void
  onView: (id: number) => void
  onEdit: (id: number) => void
  onRemove: (s: StudentListItem) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50/80 text-center text-xs font-semibold uppercase tracking-wide text-hub-muted">
            {canAdminUi ? (
              <th className="w-10 px-3 py-3">
                <input
                  type="checkbox"
                  checked={items.length > 0 && selectedIds.size === items.length}
                  onChange={onToggleSelectAll}
                  aria-label="Select all students on this page"
                />
              </th>
            ) : null}
            <th className="px-4 py-3 text-left">Name</th>
            <th className="px-3 py-3">Grade</th>
            <th className="px-3 py-3">Student ID</th>
            <th className="px-3 py-3">GPA</th>
            <th className="px-3 py-3">Academic status</th>
            <th className="px-3 py-3">Account</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((student) => (
            <tr
              key={student.id}
              className={[
                'border-b border-slate-100 text-center hover:bg-slate-50/60',
                student.alert_level === 'critical'
                  ? 'bg-red-50/40'
                  : student.alert_level === 'warning'
                    ? 'bg-amber-50/30'
                    : '',
              ].join(' ')}
            >
              {canAdminUi ? (
                <td className="px-3 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(student.id)}
                    onChange={() => onToggleSelect(student.id)}
                    aria-label={`Select ${student.display_name}`}
                  />
                </td>
              ) : null}
              <td className="px-4 py-3 text-left">
                <div className="flex items-center gap-2">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-teal-100 text-xs font-bold text-teal-800">
                    {student.initials}
                  </span>
                  <span className="font-semibold text-hub-text">{student.display_name}</span>
                </div>
              </td>
              <td className="px-3 py-3">
                <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-semibold">
                  Grade {student.grade_display}
                </span>
              </td>
              <td className="px-3 py-3">
                <code className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                  {student.student_id || 'N/A'}
                </code>
              </td>
              <td className="px-3 py-3">
                {student.gpa != null ? (
                  <span
                    className={[
                      'inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold',
                      gpaClasses(student.alert_level),
                    ].join(' ')}
                  >
                    {student.gpa.toFixed(2)}
                  </span>
                ) : (
                  <span className="text-hub-muted">N/A</span>
                )}
              </td>
              <td className="px-3 py-3">
                <span
                  className={[
                    'inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold',
                    toneClasses(student.academic_tone),
                  ].join(' ')}
                >
                  {student.academic_status}
                </span>
              </td>
              <td className="px-3 py-3">
                <AccountBadge student={student} />
              </td>
              <td className="px-4 py-3">
                <ActionButtons
                  student={student}
                  canAdminUi={canAdminUi}
                  onView={onView}
                  onEdit={onEdit}
                  onRemove={onRemove}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StudentCards({
  items,
  canAdminUi,
  onView,
  onEdit,
  onRemove,
}: {
  items: StudentListItem[]
  canAdminUi: boolean
  onView: (id: number) => void
  onEdit: (id: number) => void
  onRemove: (s: StudentListItem) => void
}) {
  return (
    <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((student) => (
        <article
          key={student.id}
          className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
        >
          <div className="flex items-center gap-3 border-b border-slate-100 bg-slate-50 px-4 py-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-teal-100 text-teal-800">
              <i className="bi bi-person-fill" aria-hidden />
            </span>
            <div>
              <h3 className="font-bold text-hub-text">{student.display_name}</h3>
              <p className="text-xs text-hub-muted">ID: {student.student_id || 'N/A'}</p>
            </div>
          </div>
          <div className="space-y-2 px-4 py-3 text-sm text-hub-muted">
            <p>
              <i className="bi bi-mortarboard me-2" aria-hidden />
              Grade {student.grade_display}
            </p>
            <p>
              <i className="bi bi-calendar3 me-2" aria-hidden />
              DOB: {student.dob || 'N/A'}
            </p>
            <p className="flex items-center gap-2">
              <i className="bi bi-trophy me-2" aria-hidden />
              GPA:{' '}
              {student.gpa != null ? (
                <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${gpaClasses(student.alert_level)}`}>
                  {student.gpa.toFixed(2)}
                </span>
              ) : (
                'N/A'
              )}
            </p>
            <p className="flex flex-wrap items-center gap-2">
              <i className="bi bi-person-circle me-1" aria-hidden />
              Account: <AccountBadge student={student} />
            </p>
          </div>
          <div className="flex flex-wrap gap-2 border-t border-slate-100 px-4 py-3">
            <button
              type="button"
              onClick={() => onView(student.id)}
              className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-semibold hover:bg-slate-50"
            >
              <i className="bi bi-eye me-1" aria-hidden />
              View
            </button>
            {canAdminUi ? (
              <>
                <button
                  type="button"
                  onClick={() => onEdit(student.id)}
                  className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-semibold hover:bg-slate-50"
                >
                  <i className="bi bi-pencil me-1" aria-hidden />
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => void onRemove(student)}
                  className="rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-700 hover:bg-red-50"
                >
                  <i className="bi bi-trash me-1" aria-hidden />
                  Remove
                </button>
              </>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  )
}

function StudentGrouped({
  groups,
  canAdminUi,
  onView,
  onEdit,
  onRemove,
}: {
  groups: [number, StudentListItem[]][]
  canAdminUi: boolean
  onView: (id: number) => void
  onEdit: (id: number) => void
  onRemove: (s: StudentListItem) => void
}) {
  return (
    <div className="space-y-4 p-5">
      {groups.map(([grade, students]) => (
        <details key={grade} open className="rounded-xl border border-slate-200 bg-slate-50/50">
          <summary className="cursor-pointer px-4 py-3 font-bold text-hub-text">
            Grade {grade === 0 ? 'K' : grade}{' '}
            <span className="text-sm font-normal text-hub-muted">({students.length})</span>
          </summary>
          <ul className="divide-y divide-slate-100 border-t border-slate-200">
            {students.map((student) => (
              <li
                key={student.id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm"
              >
                <div>
                  <span className="font-semibold text-hub-text">{student.display_name}</span>
                  <span className="ms-2 text-hub-muted">{student.student_id || 'N/A'}</span>
                </div>
                <div className="flex items-center gap-3">
                  <AccountBadge student={student} />
                  <ActionButtons
                    student={student}
                    canAdminUi={canAdminUi}
                    onView={onView}
                    onEdit={onEdit}
                    onRemove={onRemove}
                  />
                </div>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <article className="flex items-start gap-3 rounded-2xl border border-white/90 bg-white/95 p-4 shadow-sm">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-700">
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-xl font-extrabold text-hub-text">{value}</div>
        <div className="text-[0.72rem] font-semibold uppercase tracking-wide text-hub-muted">
          {label}
        </div>
      </div>
    </article>
  )
}
