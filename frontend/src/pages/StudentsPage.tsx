import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useOutletContext, useSearchParams } from 'react-router-dom'
import {
  fetchStudentDetail,
  fetchStudentList,
  markStudentsRepeating,
  removeStudent,
  uploadStudentsCsv,
} from '../api/students'
import { LegacyMgmtScope } from '../components/legacy/LegacyMgmtScope'
import { StudentDetailModal } from '../components/students/StudentDetailModal'
import { StudentEditModal } from '../components/students/StudentEditModal'
import type { ManagementOutletContext } from '../types/layout'
import type {
  StudentDetail,
  StudentFilters,
  StudentListItem,
  StudentTone,
} from '../types/students'
import { canStudentAdminUi } from '../utils/studentAccess'

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

function accountBootstrapBadge(kind: StudentListItem['account_badge_kind']) {
  switch (kind) {
    case 'removed':
    case 'no_active':
      return 'bg-danger text-white border border-danger'
    case 'has_young':
    case 'no_young':
      return 'bg-warning text-dark border border-warning'
    case 'has_active':
      return 'bg-success text-white border border-success'
    default:
      return 'bg-secondary text-white'
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

function academicBadgeClass(tone: StudentTone) {
  switch (tone) {
    case 'success':
      return 'text-bg-success'
    case 'warning':
      return 'text-bg-warning'
    case 'danger':
      return 'text-bg-danger'
    case 'primary':
      return 'text-bg-primary'
    default:
      return 'text-bg-secondary'
  }
}

function academicBadgeIcon(tone: StudentTone) {
  switch (tone) {
    case 'success':
      return 'bi-trophy-fill'
    case 'primary':
      return 'bi-check-circle-fill'
    case 'warning':
      return 'bi-exclamation-circle-fill'
    case 'danger':
      return 'bi-exclamation-triangle-fill'
    default:
      return 'bi-dash-circle'
  }
}

function gradeGroupLabel(grade: number) {
  if (grade === 0) return 'Unassigned Grade'
  return `Grade ${grade}`
}

export function StudentsPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const isDirector = user.role_canonical === 'Director'
  const canEditStudents = canStudentAdminUi(user)
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
  const deepLinkHandled = useRef(false)

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

  const openDetail = useCallback(async (id: number) => {
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
  }, [])

  useEffect(() => {
    if (deepLinkHandled.current) return
    const fromQuery = searchParams.get('edit')
    const fromStorage = sessionStorage.getItem('clara_open_student_edit')
    const raw = fromQuery || fromStorage
    if (!raw) return

    deepLinkHandled.current = true
    const id = Number.parseInt(raw, 10)
    if (!Number.isFinite(id) || id <= 0) return

    if (fromQuery) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.delete('edit')
          return next
        },
        { replace: true },
      )
    }
    if (fromStorage) {
      sessionStorage.removeItem('clara_open_student_edit')
    }

    if (canEditStudents) {
      setEditStudentId(id)
    } else {
      setActionMessage('You do not have permission to edit students.')
      void openDetail(id)
    }
  }, [canEditStudents, searchParams, setSearchParams, openDetail])

  const groupedByGrade = useMemo(() => {
    const map = new Map<number, StudentListItem[]>()
    for (const s of items) {
      const g = s.grade_level ?? 0
      if (!map.has(g)) map.set(g, [])
      map.get(g)!.push(s)
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0])
  }, [items])

  const hasActiveFilters =
    Boolean(filters.search || filters.grade_level || filters.status || filters.alert_filter)

  const shellClass = isDirector ? 'mgmt-stu-shell mgmt-stu-shell--director' : 'mgmt-stu-shell'

  if (loading && items.length === 0 && !error) {
    return (
      <LegacyMgmtScope>
        <div className="mgmt-stu container-fluid px-0 px-md-1">
          <div className={shellClass}>
            <div className="p-5 text-center text-muted">Loading students…</div>
          </div>
        </div>
      </LegacyMgmtScope>
    )
  }

  return (
    <LegacyMgmtScope>
      <div className="mgmt-stu container-fluid px-0 px-md-1">
        <div className={shellClass}>
          <header className="mgmt-stu-hero">
            <div>
              <p className="mgmt-stu-eyebrow">Student records</p>
              <h1 className="mgmt-stu-title">Students</h1>
              <p className="mgmt-stu-subtitle">
                <i className="bi bi-people-fill" aria-hidden="true" />
                Manage enrollments, accounts, and academic records
              </p>
            </div>
            <div className="mgmt-stu-hero-actions">
              {isDirector ? (
                <span className="mgmt-stu-role-badge mgmt-stu-role-badge--director">
                  <i className="bi bi-award-fill" aria-hidden="true" /> Director
                </span>
              ) : (
                <span className="mgmt-stu-role-badge mgmt-stu-role-badge--admin">
                  <i className="bi bi-shield-fill" aria-hidden="true" /> Administrator
                </span>
              )}
              {canAdminUi ? (
                <Link to="/management/students/new" className="mgmt-stu-btn mgmt-stu-btn--primary">
                  <i className="bi bi-plus-circle" aria-hidden="true" /> Add student
                </Link>
              ) : null}
              <button
                type="button"
                onClick={() => navigate('/management')}
                className="mgmt-stu-btn mgmt-stu-btn--ghost"
              >
                <i className="bi bi-house-door" aria-hidden="true" /> Dashboard
              </button>
            </div>
          </header>

          <div className="mgmt-stu-insights" role="list">
            <div className="mgmt-stu-insight" role="listitem">
              <span className="mgmt-stu-insight-icon">
                <i className="bi bi-people-fill" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-stu-insight-value">{stats.total}</div>
                <div className="mgmt-stu-insight-label">Total students</div>
              </div>
            </div>
            <div className="mgmt-stu-insight" role="listitem">
              <span className="mgmt-stu-insight-icon">
                <i className="bi bi-person-check-fill" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-stu-insight-value">{stats.with_accounts}</div>
                <div className="mgmt-stu-insight-label">With accounts</div>
              </div>
            </div>
            <div className="mgmt-stu-insight" role="listitem">
              <span className="mgmt-stu-insight-icon">
                <i className="bi bi-person-x-fill" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-stu-insight-value">{stats.without_accounts}</div>
                <div className="mgmt-stu-insight-label">Without accounts</div>
              </div>
            </div>
            <div className="mgmt-stu-insight" role="listitem">
              <span className="mgmt-stu-insight-icon">
                <i className="bi bi-funnel" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-stu-insight-value">{stats.on_page}</div>
                <div className="mgmt-stu-insight-label">On this page</div>
              </div>
            </div>
            <div className="mgmt-stu-insight" role="listitem">
              <span className="mgmt-stu-insight-icon">
                <i className="bi bi-trophy-fill" aria-hidden="true" />
              </span>
              <div>
                <div className="mgmt-stu-insight-value">{stats.high_gpa}</div>
                <div className="mgmt-stu-insight-label">Honors</div>
              </div>
            </div>
          </div>

          <div className="mgmt-stu-content">
            <div className="students-search-card mb-4">
              <div className="students-search-header d-flex justify-content-between align-items-center flex-wrap gap-2">
                <h5 className="mb-0">
                  <i className="bi bi-search me-2" aria-hidden="true" />
                  Search &amp; Filter Students
                </h5>
                <AccountStatusLegend />
              </div>
              <div className="students-search-body">
                <form onSubmit={applyFilters} className="row g-3">
                  <div className="col-md-4">
                    <label htmlFor="search" className="form-label">
                      Search Term
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      id="search"
                      value={draft.search}
                      onChange={(e) => setDraft({ ...draft, search: e.target.value })}
                      placeholder="Enter search term..."
                      autoComplete="off"
                    />
                  </div>
                  <div className="col-md-2">
                    <label htmlFor="search_type" className="form-label">
                      Search In
                    </label>
                    <select
                      className="form-select"
                      id="search_type"
                      value={draft.search_type}
                      onChange={(e) => setDraft({ ...draft, search_type: e.target.value })}
                    >
                      <option value="all">All Fields</option>
                      <option value="name">Student Name</option>
                      <option value="contact">Contact Info</option>
                      <option value="phone">Phone Numbers</option>
                      <option value="address">Address</option>
                      <option value="parents">Parent Names</option>
                    </select>
                  </div>
                  <div className="col-md-2">
                    <label htmlFor="grade_level" className="form-label">
                      Grade Level
                    </label>
                    <select
                      className="form-select"
                      id="grade_level"
                      value={draft.grade_level}
                      onChange={(e) => setDraft({ ...draft, grade_level: e.target.value })}
                    >
                      {GRADE_OPTIONS.map((g) => (
                        <option key={g.value || 'all'} value={g.value}>
                          {g.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-md-2">
                    <label htmlFor="status" className="form-label">
                      Account Status
                    </label>
                    <select
                      className="form-select"
                      id="status"
                      value={draft.status}
                      onChange={(e) => setDraft({ ...draft, status: e.target.value })}
                    >
                      <option value="">All Students</option>
                      <option value="has_account">Has Account</option>
                      <option value="no_account">No Account</option>
                      {canAdminUi ? (
                        <>
                          <option value="former">Former (Removed)</option>
                          <option value="all">All (Current + Former)</option>
                        </>
                      ) : null}
                    </select>
                  </div>
                  <div className="col-md-2">
                    <label htmlFor="alert_filter" className="form-label">
                      Academic Alert
                    </label>
                    <select
                      className="form-select"
                      id="alert_filter"
                      value={draft.alert_filter}
                      onChange={(e) => setDraft({ ...draft, alert_filter: e.target.value })}
                    >
                      <option value="">All Students</option>
                      <option value="critical">Critical (&lt;2.0 GPA)</option>
                      <option value="warning">Warning (2.0–2.9 GPA)</option>
                      <option value="good">Good Standing (3.0+)</option>
                    </select>
                  </div>
                  <div className="col-md-2">
                    <label htmlFor="sort" className="form-label">
                      Sort By
                    </label>
                    <select
                      className="form-select"
                      id="sort"
                      value={draft.sort}
                      onChange={(e) => setDraft({ ...draft, sort: e.target.value })}
                    >
                      <option value="name">Name (A–Z)</option>
                      <option value="grade">Grade Level</option>
                      <option value="id">Student ID</option>
                      <option value="gpa">GPA (Low to High)</option>
                      <option value="gpa_desc">GPA (High to Low)</option>
                    </select>
                  </div>
                  <div className="col-md-2">
                    <label htmlFor="view_mode" className="form-label">
                      View Mode
                    </label>
                    <select
                      className="form-select"
                      id="view_mode"
                      value={viewModeSelect}
                      onChange={(e) => setViewModeSelect(e.target.value as ViewModeSelect)}
                    >
                      <option value="list">All Students</option>
                      <option value="grouped">Grouped by Grade</option>
                      <option value="alerts_only">Alerts Only</option>
                    </select>
                  </div>
                  <div className="col-12">
                    <div className="d-flex gap-2 flex-wrap">
                      <button type="submit" className="btn btn-students-search">
                        <i className="bi bi-search me-2" aria-hidden="true" />
                        Search
                      </button>
                      <button type="button" onClick={resetFilters} className="btn btn-students-reset">
                        <i className="bi bi-arrow-clockwise me-2" aria-hidden="true" />
                        Reset
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowSearchTips((v) => !v)}
                        className="btn btn-students-info"
                      >
                        <i className="bi bi-info-circle me-2" aria-hidden="true" />
                        Search Tips
                      </button>
                    </div>
                  </div>
                </form>
                {showSearchTips ? (
                  <div className="mt-3">
                    <SearchTipsPanel />
                  </div>
                ) : null}
              </div>
            </div>

            {canAdminUi ? (
              <div className="students-csv-card mb-4">
                <div className="students-csv-header">
                  <h5 className="mb-0">
                    <i className="bi bi-arrow-repeat me-2" aria-hidden="true" />
                    Repeat Grade (Bulk Update)
                  </h5>
                </div>
                <div className="students-csv-body">
                  <p className="text-muted small mb-2">
                    Select students below, then mark them as repeating. This will set{' '}
                    <code>is_repeating</code> and bump <code>grad_year</code> by 1 (when grad year is
                    known).
                  </p>
                  <button
                    type="button"
                    onClick={() => void handleMarkRepeating()}
                    className="btn btn-warning btn-sm"
                  >
                    <i className="bi bi-arrow-repeat me-1" aria-hidden="true" />
                    Mark Selected as Repeating
                  </button>
                </div>
              </div>
            ) : null}

            {canAdminUi ? (
              <CsvImportExportPanel
                onUploaded={(msg) => {
                  setActionMessage(msg)
                  void load(filters)
                }}
              />
            ) : null}

            {hasActiveFilters ? (
              <div className="students-results-banner mb-4">
                <i className="bi bi-info-circle me-2" aria-hidden="true" />
                <strong>Search Results:</strong> Found {stats.total} student(s)
                {filters.search ? ` matching "${filters.search}"` : ''}
              </div>
            ) : null}

            {actionMessage ? (
              <div className="alert alert-success d-flex align-items-center justify-content-between flex-wrap gap-2 mb-4" role="status">
                <span>{actionMessage}</span>
                <button
                  type="button"
                  className="btn-close"
                  aria-label="Dismiss"
                  onClick={() => setActionMessage(null)}
                />
              </div>
            ) : null}

            {error ? (
              <div className="alert alert-danger mb-4" role="alert">
                {error}
              </div>
            ) : null}

            <div className="students-table-card">
              {pagination.pages > 1 ? (
                <p className="text-muted small px-3 pt-3 mb-0">
                  <i className="bi bi-info-circle me-1" aria-hidden="true" />
                  List and card views show <strong>{pagination.per_page}</strong> students per page.
                  Grouped-by-grade uses only the current page.
                </p>
              ) : null}

              <div className="students-table-header">
                <h5 className="mb-0">
                  <i className="bi bi-table me-2" aria-hidden="true" />
                  Student Records
                  <span className="badge bg-primary ms-2">{stats.on_page} on this page</span>
                  <span className="badge bg-secondary ms-1">{stats.total} matching</span>
                </h5>
                <div className="students-table-view-toggle">
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
                    label="By Grade"
                    onClick={() => setRecordsView('grouped')}
                  />
                </div>
              </div>

              {loading ? (
                <div className="students-table-body p-5 text-center text-muted">Loading students…</div>
              ) : items.length === 0 ? (
                <div className="students-table-body text-center py-5 text-muted">
                  <i className="bi bi-inbox display-1 text-muted d-block mb-3" aria-hidden="true" />
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
                <div className="students-table-footer border-top px-3 py-3 d-flex flex-wrap justify-content-between align-items-center gap-2 bg-light bg-opacity-50">
                  <div className="text-muted small">
                    Page {pagination.page} of {pagination.pages} · {pagination.total} students
                  </div>
                  <nav aria-label="Students pagination">
                    <ul className="pagination pagination-sm mb-0">
                      <li className={`page-item${!pagination.has_prev ? ' disabled' : ''}`}>
                        <button
                          type="button"
                          className="page-link"
                          disabled={!pagination.has_prev}
                          onClick={() => goToPage(pagination.page - 1)}
                        >
                          Prev
                        </button>
                      </li>
                      <li className={`page-item${!pagination.has_next ? ' disabled' : ''}`}>
                        <button
                          type="button"
                          className="page-link"
                          disabled={!pagination.has_next}
                          onClick={() => goToPage(pagination.page + 1)}
                        >
                          Next
                        </button>
                      </li>
                    </ul>
                  </nav>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

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
    </LegacyMgmtScope>
  )
}

function AccountStatusLegend() {
  return (
    <div className="students-account-legend small text-muted">
      <span className="me-2 fw-semibold">Account status</span>
      <span className="d-inline-flex align-items-center gap-1 me-2">
        <span className="legend-dot legend-dot-danger" aria-hidden="true" />
        Removed / No account
      </span>
      <span className="d-inline-flex align-items-center gap-1 me-2">
        <span className="legend-dot legend-dot-warning" aria-hidden="true" />
        Too young / Not yet
      </span>
      <span className="d-inline-flex align-items-center gap-1">
        <span className="legend-dot legend-dot-success" aria-hidden="true" />
        Grade 3+ Active
      </span>
    </div>
  )
}

function SearchTipsPanel() {
  return (
    <div className="students-info-box">
      <h6>
        <i className="bi bi-lightbulb me-2" aria-hidden="true" />
        Search Tips:
      </h6>
      <ul className="mb-0">
        <li>
          <strong>All Fields:</strong> Search across student names, contact info, addresses, and
          parent information
        </li>
        <li>
          <strong>Student Name:</strong> Search by first or last name
        </li>
        <li>
          <strong>Contact Info:</strong> Search by student or parent email addresses
        </li>
        <li>
          <strong>Phone Numbers:</strong> Search by parent or emergency contact phone numbers
        </li>
        <li>
          <strong>Address:</strong> Search by street, city, state, or zip code
        </li>
        <li>
          <strong>Parent Names:</strong> Search by parent first or last names
        </li>
      </ul>
    </div>
  )
}

function CsvImportExportPanel({ onUploaded }: { onUploaded: (message: string) => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    try {
      const res = await uploadStudentsCsv(file)
      onUploaded(res.message)
      setFile(null)
    } catch (err) {
      onUploaded(err instanceof Error ? err.message : 'CSV upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="students-csv-card mb-4">
      <div className="students-csv-header">
        <h5 className="mb-0">
          <i className="bi bi-file-earmark-spreadsheet me-2" aria-hidden="true" />
          CSV Import/Export
        </h5>
      </div>
      <div className="students-csv-body">
        <div className="row g-3">
          <div className="col-md-4">
            <h6>
              <i className="bi bi-download me-2" aria-hidden="true" />
              Export Students
            </h6>
            <p className="text-muted small mb-2">Download all student data as a CSV file</p>
            <a href="/management/students/download-csv" className="btn btn-success btn-sm">
              <i className="bi bi-file-earmark-arrow-down me-1" aria-hidden="true" />
              Download CSV
            </a>
          </div>
          <div className="col-md-4">
            <h6>
              <i className="bi bi-file-earmark-text me-2" aria-hidden="true" />
              CSV Template
            </h6>
            <p className="text-muted small mb-2">Download a template with example data</p>
            <a href="/management/students/download-template" className="btn btn-info btn-sm">
              <i className="bi bi-file-earmark-text me-1" aria-hidden="true" />
              Download Template
            </a>
          </div>
          <div className="col-md-4">
            <h6>
              <i className="bi bi-upload me-2" aria-hidden="true" />
              Import Students
            </h6>
            <p className="text-muted small mb-2">Upload a CSV file to add/update students</p>
            <form onSubmit={(e) => void handleUpload(e)} className="d-inline">
              <div className="input-group input-group-sm">
                <input
                  type="file"
                  name="csv_file"
                  accept=".csv"
                  required
                  className="form-control"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <button type="submit" disabled={uploading || !file} className="btn btn-primary">
                  <i className="bi bi-upload me-1" aria-hidden="true" />
                  {uploading ? 'Uploading…' : 'Upload'}
                </button>
              </div>
            </form>
          </div>
        </div>
        <div className="mt-3">
          <div className="students-info-box mb-0">
            <h6>
              <i className="bi bi-info-circle me-2" aria-hidden="true" />
              CSV Upload Instructions:
            </h6>
            <ul className="mb-0 small">
              <li>
                <strong>Download the template</strong> to see the required format and example data
              </li>
              <li>
                <strong>Required fields:</strong> First Name and Last Name
              </li>
              <li>
                <strong>Student ID:</strong> Leave blank to auto-generate (requires State and Date of
                Birth)
              </li>
              <li>
                <strong>Date format:</strong> MM/DD/YYYY (e.g., 01/15/2010)
              </li>
              <li>
                <strong>Update existing students:</strong> Match by Student ID or by First Name +
                Last Name + Date of Birth
              </li>
              <li>
                <strong>Add new students:</strong> Simply omit Student ID or provide a unique one
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
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
      className={`btn btn-sm btn-students-view${active ? ' active' : ''}`}
    >
      <i className={`bi ${icon}`} aria-hidden="true" /> {label}
    </button>
  )
}

function AccountBadge({ student }: { student: StudentListItem }) {
  const kind = resolveAccountBadgeKind(student)
  return (
    <span
      className={`badge ${accountBootstrapBadge(kind)}`}
      style={{ fontWeight: 500 }}
      title={student.account_status}
    >
      <i className={`bi ${accountBadgeIcon(kind)} me-1`} aria-hidden="true" />
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
    <div className="students-action-group" role="group" aria-label={`Actions for ${student.display_name}`}>
      <button
        type="button"
        onClick={() => onView(student.id)}
        className="btn btn-students-action-view"
        title="View details"
      >
        <i className="bi bi-eye" aria-hidden="true" />
        <span>View</span>
      </button>
      {canAdminUi ? (
        <>
          <button
            type="button"
            onClick={() => onEdit(student.id)}
            className="btn btn-students-action-edit"
            title="Edit student"
          >
            <i className="bi bi-pencil" aria-hidden="true" />
            <span>Edit</span>
          </button>
          <button
            type="button"
            onClick={() => void onRemove(student)}
            className="btn btn-students-action-delete"
            title="Remove student"
          >
            <i className="bi bi-trash" aria-hidden="true" />
            <span>Remove</span>
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
    <div className="students-table-body">
      <div className="table-responsive">
        <table className="table table-hover align-middle">
          <thead>
            <tr>
              {canAdminUi ? (
                <th style={{ width: 38 }}>
                  <input
                    className="form-check-input"
                    type="checkbox"
                    checked={items.length > 0 && selectedIds.size === items.length}
                    onChange={onToggleSelectAll}
                    aria-label="Select all students on this page"
                  />
                </th>
              ) : null}
              <th>Name</th>
              <th>Grade Level</th>
              <th>Student ID</th>
              <th>GPA</th>
              <th>Academic Status</th>
              <th>Account</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((student) => (
              <tr
                key={student.id}
                className={`student-row student-alert-${student.alert_level}`}
              >
                {canAdminUi ? (
                  <td>
                    <input
                      className="form-check-input student-select"
                      type="checkbox"
                      checked={selectedIds.has(student.id)}
                      onChange={() => onToggleSelect(student.id)}
                      aria-label={`Select ${student.display_name}`}
                    />
                  </td>
                ) : null}
                <td>
                  <div className="d-flex align-items-center gap-2">
                    <div className="student-avatar-mini">{student.initials}</div>
                    <strong>{student.display_name}</strong>
                  </div>
                </td>
                <td>
                  <span className="badge bg-secondary bg-opacity-20 text-dark border">
                    Grade {student.grade_display}
                  </span>
                </td>
                <td>
                  <code className="student-id-code">{student.student_id || 'N/A'}</code>
                </td>
                <td>
                  {student.gpa != null ? (
                    <div className="gpa-display">
                      <span className={`gpa-badge gpa-${student.alert_level}`}>
                        {student.gpa.toFixed(2)}
                      </span>
                      <div className="gpa-progress-bar">
                        <div
                          className={`gpa-progress-fill gpa-progress-${student.alert_level}`}
                          style={{ width: `${Math.round((student.gpa / 4.0) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ) : (
                    <span className="badge bg-secondary">N/A</span>
                  )}
                </td>
                <td>
                  <span className={`badge ${academicBadgeClass(student.academic_tone)}`}>
                    <i className={`bi ${academicBadgeIcon(student.academic_tone)} me-1`} aria-hidden="true" />
                    {student.academic_status}
                  </span>
                </td>
                <td>
                  <AccountBadge student={student} />
                </td>
                <td>
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
    <div className="students-cards-body">
      <div className="row g-3">
        {items.map((student) => {
          const kind = resolveAccountBadgeKind(student)
          return (
            <div key={student.id} className="col-12 col-md-6 col-lg-4">
              <div className="student-card">
                <div className="student-card-header">
                  <div className="student-card-avatar">
                    <i className="bi bi-person-fill" aria-hidden="true" />
                  </div>
                  <div className="student-card-info">
                    <h6 className="student-card-name">{student.display_name}</h6>
                    <p className="student-card-id">ID: {student.student_id || 'N/A'}</p>
                  </div>
                </div>
                <div className="student-card-body">
                  <div className="student-card-detail">
                    <i className="bi bi-mortarboard me-2" aria-hidden="true" />
                    <span>Grade: {student.grade_display}</span>
                  </div>
                  <div className="student-card-detail">
                    <i className="bi bi-calendar3 me-2" aria-hidden="true" />
                    <span>DOB: {student.dob || 'N/A'}</span>
                  </div>
                  <div className="student-card-detail">
                    <i className="bi bi-trophy me-2" aria-hidden="true" />
                    <span>
                      GPA:{' '}
                      {student.gpa != null ? (
                        <span
                          className={`badge ${
                            student.gpa >= 3.5
                              ? 'bg-success'
                              : student.gpa >= 2.0
                                ? 'bg-warning'
                                : 'bg-danger'
                          }`}
                        >
                          {student.gpa.toFixed(2)}
                        </span>
                      ) : (
                        <span className="badge bg-secondary">N/A</span>
                      )}
                    </span>
                  </div>
                  <div className="student-card-detail">
                    <i className="bi bi-person-circle me-2" aria-hidden="true" />
                    <span>
                      Account:{' '}
                      <span className={`badge ${accountBootstrapBadge(kind)}`}>
                        {student.account_status}
                      </span>
                    </span>
                  </div>
                </div>
                <div className="student-card-footer">
                  <button
                    type="button"
                    onClick={() => onView(student.id)}
                    className="btn btn-sm btn-students-card-action"
                  >
                    <i className="bi bi-eye me-1" aria-hidden="true" />
                    View
                  </button>
                  {canAdminUi ? (
                    <>
                      <button
                        type="button"
                        onClick={() => onEdit(student.id)}
                        className="btn btn-sm btn-students-card-action"
                      >
                        <i className="bi bi-pencil me-1" aria-hidden="true" />
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => void onRemove(student)}
                        className="btn btn-sm btn-students-card-action-delete"
                      >
                        <i className="bi bi-trash me-1" aria-hidden="true" />
                        Remove
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
            </div>
          )
        })}
      </div>
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
  const [collapsedGrades, setCollapsedGrades] = useState<Set<number>>(new Set())

  const toggleGradeGroup = (grade: number) => {
    setCollapsedGrades((prev) => {
      const next = new Set(prev)
      if (next.has(grade)) next.delete(grade)
      else next.add(grade)
      return next
    })
  }

  return (
    <div className="students-grouped-body">
      {groups.map(([grade, students]) => {
        const collapsed = collapsedGrades.has(grade)
        return (
          <div key={grade} className="grade-group-section mb-4">
            <div
              className="grade-group-header"
              role="button"
              tabIndex={0}
              onClick={() => toggleGradeGroup(grade)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  toggleGradeGroup(grade)
                }
              }}
            >
              <div className="d-flex align-items-center gap-3">
                <div className="grade-group-icon">
                  <i className="bi bi-mortarboard-fill" aria-hidden="true" />
                </div>
                <div>
                  <h5 className="mb-0">{gradeGroupLabel(grade)}</h5>
                  <small className="text-muted">
                    {students.length} Student{students.length !== 1 ? 's' : ''}
                  </small>
                </div>
              </div>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={(e) => {
                  e.stopPropagation()
                  toggleGradeGroup(grade)
                }}
                aria-expanded={!collapsed}
              >
                <i
                  className={`bi ${collapsed ? 'bi-chevron-right' : 'bi-chevron-down'}`}
                  aria-hidden="true"
                />
              </button>
            </div>
            {!collapsed ? (
              <div className="grade-group-body">
                <div className="row g-3">
                  {students.map((student) => (
                    <div key={student.id} className="col-12 col-md-6 col-lg-4 col-xl-3">
                      <div
                        className={`student-grouped-card student-card-alert-${student.alert_level}`}
                      >
                        <div className="student-grouped-header">
                          <div className="student-grouped-avatar">{student.initials}</div>
                          <div className="student-grouped-info">
                            <h6 className="mb-0">{student.display_name}</h6>
                            <small className="text-muted">
                              ID: {student.student_id || 'N/A'}
                            </small>
                          </div>
                        </div>
                        <div className="student-grouped-stats">
                          <div className="grouped-stat-item">
                            <div className="grouped-stat-icon">
                              <i className="bi bi-trophy" aria-hidden="true" />
                            </div>
                            <div>
                              <div className="grouped-stat-value">
                                {student.gpa != null ? student.gpa.toFixed(2) : 'N/A'}
                              </div>
                              <div className="grouped-stat-label">GPA</div>
                            </div>
                          </div>
                          <div className="grouped-stat-item">
                            <div className="grouped-stat-icon">
                              <i className="bi bi-person-badge" aria-hidden="true" />
                            </div>
                            <div>
                              <div className="grouped-stat-value">
                                {student.has_account ? (
                                  student.grade_level != null && student.grade_level < 3 ? (
                                    <i className="bi bi-check-circle" style={{ color: '#fd7e14' }} aria-hidden="true" />
                                  ) : (
                                    <i className="bi bi-check-circle text-success" aria-hidden="true" />
                                  )
                                ) : (
                                  <i className="bi bi-x-circle text-danger" aria-hidden="true" />
                                )}
                              </div>
                              <div className="grouped-stat-label">Account</div>
                            </div>
                          </div>
                        </div>
                        <div className="student-grouped-footer text-center">
                          {canAdminUi ? (
                            <ActionButtons
                              student={student}
                              canAdminUi={canAdminUi}
                              onView={onView}
                              onEdit={onEdit}
                              onRemove={onRemove}
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() => onView(student.id)}
                              className="btn btn-students-action-view w-100"
                            >
                              <i className="bi bi-eye" aria-hidden="true" />
                              <span>View details</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
