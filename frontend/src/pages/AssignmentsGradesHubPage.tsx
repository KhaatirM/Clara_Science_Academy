import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { fetchAssignmentsHub } from '../api/assignments'
import type { ManagementOutletContext } from '../types/layout'
import type { ClassListItem, SchoolYearOption } from '../types/classes'
import {
  ASSIGNMENTS_HUB_SORT_OPTIONS,
  computeAssignmentsHubStats,
  defaultAssignmentsHubFilters,
  filterAssignmentsHubClasses,
  subjectOptionsForHub,
  type AssignmentsHubFilters,
} from '../utils/assignmentsHubFilters'
import { GRADE_FILTER_OPTIONS, itemsForSchoolYear, teacherOptions } from '../utils/classListFilters'

function FilterLabel({ children, htmlFor }: { children: string; htmlFor: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-[0.72rem] font-bold uppercase tracking-wide text-hub-muted">
      {children}
    </label>
  )
}

function FilterSelect({
  id,
  value,
  onChange,
  disabled,
  children,
}: {
  id: string
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  children: ReactNode
}) {
  return (
    <select
      id={id}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-semibold text-hub-text focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </select>
  )
}

function InsightCard({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-white/90 bg-white px-3 py-2.5 shadow-sm">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
        <i className={`bi ${icon} text-sm`} aria-hidden />
      </span>
      <div>
        <div className="text-lg font-extrabold leading-tight text-hub-text">{value}</div>
        <div className="text-[0.62rem] font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function HubClassCard({
  item,
  pendingProposals,
  onOpen,
}: {
  item: ClassListItem
  pendingProposals: number
  onOpen: () => void
}) {
  return (
    <article
      className="flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-teal-400 hover:shadow-md"
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className="border-b border-indigo-100 bg-gradient-to-r from-indigo-600 to-teal-700 px-4 py-3 text-white">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15">
            <i className="bi bi-book-fill" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-bold">{item.name}</h3>
            <p className="text-sm text-white/85">{item.subject}</p>
          </div>
          <span className="shrink-0 rounded-full bg-white/20 px-2 py-0.5 text-xs font-semibold">
            {item.assignment_count} assignments
          </span>
        </div>
      </div>
      <div className="flex-1 space-y-2 p-4 text-sm text-hub-muted">
        <p>
          <i className="bi bi-person-badge me-2 text-teal-600" aria-hidden />
          <strong className="text-hub-text">{item.teacher.display_name}</strong>
        </p>
        <p>
          <i className="bi bi-people-fill me-2 text-teal-600" aria-hidden />
          {item.enrollment_count} students
        </p>
        <p>
          <i className="bi bi-mortarboard me-2 text-teal-600" aria-hidden />
          {item.grade_levels_display || 'N/A'}
        </p>
        {pendingProposals > 0 ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-900">
            <i className="bi bi-stars" aria-hidden />
            {pendingProposals} proposal{pendingProposals !== 1 ? 's' : ''} pending
          </span>
        ) : null}
      </div>
      <div className="border-t border-slate-100 bg-slate-50 p-3">
        <button
          type="button"
          className="w-full rounded-xl bg-gradient-to-r from-indigo-700 to-teal-700 px-3 py-2 text-sm font-semibold text-white hover:brightness-105"
          onClick={(e) => {
            e.stopPropagation()
            onOpen()
          }}
        >
          <i className="bi bi-eye me-2" aria-hidden />
          Open Assignments & grades
        </button>
      </div>
    </article>
  )
}

export function AssignmentsGradesHubPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const navigate = useNavigate()
  const isDirector = user.role_canonical === 'Director'

  const [allItems, setAllItems] = useState<ClassListItem[]>([])
  const [schoolYears, setSchoolYears] = useState<SchoolYearOption[]>([])
  const [hubMeta, setHubMeta] = useState<{
    extension_request_count: number
    redo_request_count: number
    pending_assistant_by_class: Record<number, number>
    total_pending_assistant_proposals: number
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<AssignmentsHubFilters>(defaultAssignmentsHubFilters)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAssignmentsHub()
      setAllItems(data.items)
      setSchoolYears(data.school_years)
      setHubMeta(data.hub)
      setFilters((prev) => ({
        ...prev,
        schoolYearId: data.meta.default_school_year_id ?? prev.schoolYearId ?? '',
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load assignments hub')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const yearItems = useMemo(
    () => itemsForSchoolYear(allItems, filters.schoolYearId),
    [allItems, filters.schoolYearId],
  )
  const visibleItems = useMemo(() => filterAssignmentsHubClasses(allItems, filters), [allItems, filters])
  const stats = useMemo(() => computeAssignmentsHubStats(visibleItems), [visibleItems])
  const subjects = useMemo(() => subjectOptionsForHub(yearItems), [yearItems])
  const teacherChoices = useMemo(() => teacherOptions(yearItems), [yearItems])

  const yearChosen = !!filters.schoolYearId
  const filtersEnabled = yearChosen

  const patchFilter = <K extends keyof AssignmentsHubFilters>(key: K, value: AssignmentsHubFilters[K]) => {
    setFilters((prev) => {
      const next = { ...prev, [key]: value }
      if (key === 'schoolYearId') {
        next.subject = ''
        next.grade = ''
        next.teacherKey = ''
        next.enrollment = ''
        next.assignment = ''
      }
      return next
    })
  }

  const resetFilters = () => {
    setFilters({ ...defaultAssignmentsHubFilters, schoolYearId: '' })
  }

  return (
    <div
      className={`rounded-3xl p-5 md:p-6 ${
        isDirector
          ? 'bg-gradient-to-br from-violet-50 via-purple-50/70 to-slate-100'
          : 'bg-gradient-to-br from-indigo-50 via-slate-50 to-slate-100'
      }`}
    >
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Assignments & grades</p>
          <h1 className="mt-0.5 text-2xl font-extrabold tracking-tight text-hub-text">Assignments & grades</h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-hub-muted">
            <i className="bi bi-clipboard-data" aria-hidden />
            Pick a class to manage assignments and grades
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isDirector ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2.5 py-1 text-xs font-bold text-violet-900">
              <i className="bi bi-award-fill" aria-hidden />
              Director
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-1 text-xs font-bold text-teal-900">
              <i className="bi bi-shield-fill" aria-hidden />
              Administrator
            </span>
          )}
          <Link
            to="/management/redo"
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
          >
            <i className="bi bi-arrow-repeat" aria-hidden />
            Redo
            {hubMeta && hubMeta.redo_request_count > 0 ? (
              <span className="rounded-full bg-red-600 px-1.5 text-[0.65rem] text-white">{hubMeta.redo_request_count}</span>
            ) : null}
          </Link>
          <Link
            to="/management/extensions"
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
          >
            <i className="bi bi-clock-history" aria-hidden />
            Extensions
            {hubMeta && hubMeta.extension_request_count > 0 ? (
              <span className="rounded-full bg-red-600 px-1.5 text-[0.65rem] text-white">
                {hubMeta.extension_request_count}
              </span>
            ) : null}
          </Link>
          <Link
            to="/management/assignments/create"
            className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br from-rose-800 to-teal-900 px-3.5 py-2 text-[0.82rem] font-semibold text-white shadow-sm hover:brightness-105"
          >
            <i className="bi bi-plus-circle" aria-hidden />
            New assignment
          </Link>
        </div>
      </header>

      {hubMeta && hubMeta.total_pending_assistant_proposals > 0 ? (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <i className="bi bi-stars me-2" aria-hidden />
          <strong>{hubMeta.total_pending_assistant_proposals}</strong> student-assistant proposal(s) are waiting for
          approval. Open a class below, then use <strong>Assistant proposals</strong> in the toolbar.
        </div>
      ) : null}

      {error ? <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div> : null}

      {yearChosen ? (
        <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <InsightCard icon="bi-house-door-fill" value={stats.total_classes} label="In view" />
          <InsightCard icon="bi-journal-check" value={stats.total_assignments} label="Assignments" />
          <InsightCard icon="bi-people-fill" value={stats.total_enrollments} label="Enrollments" />
          <InsightCard icon="bi-person-badge" value={stats.unique_teachers} label="Teachers" />
        </div>
      ) : null}

      <section className="mb-4 overflow-hidden rounded-2xl border border-white/90 bg-white shadow-lg">
        <div className="p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-base font-extrabold text-hub-text">
              <i className="bi bi-funnel-fill" aria-hidden />
              Filters
            </h2>
            <button
              type="button"
              onClick={resetFilters}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <i className="bi bi-arrow-counterclockwise" aria-hidden />
              Reset
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-12 md:items-end">
            <div className="md:col-span-4">
              <FilterLabel htmlFor="asg-search">Search</FilterLabel>
              <div className="flex overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                <span className="flex items-center px-3 text-hub-muted" aria-hidden>
                  <i className="bi bi-search" />
                </span>
                <input
                  id="asg-search"
                  type="search"
                  value={filters.search}
                  onChange={(e) => patchFilter('search', e.target.value)}
                  placeholder="Class, subject, or teacher…"
                  disabled={!filtersEnabled}
                  className="min-w-0 flex-1 border-0 bg-transparent px-0 py-2.5 pr-3 text-sm focus:outline-none focus:ring-0 disabled:opacity-60"
                />
              </div>
            </div>
            <div className="md:col-span-4">
              <FilterLabel htmlFor="asg-year">School year</FilterLabel>
              <FilterSelect
                id="asg-year"
                value={filters.schoolYearId ? String(filters.schoolYearId) : ''}
                onChange={(v) => patchFilter('schoolYearId', v ? Number(v) : '')}
              >
                <option value="">No school year selected</option>
                {schoolYears.map((y) => (
                  <option key={y.id} value={y.id}>
                    {y.name}
                    {y.is_active ? ' (Active)' : ' (Closed)'}
                  </option>
                ))}
              </FilterSelect>
            </div>
            <div className="md:col-span-4">
              <FilterLabel htmlFor="asg-subject">Subject</FilterLabel>
              <FilterSelect
                id="asg-subject"
                value={filters.subject}
                disabled={!filtersEnabled}
                onChange={(v) => patchFilter('subject', v)}
              >
                <option value="">All subjects</option>
                {subjects.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </FilterSelect>
            </div>
          </div>

          <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 md:grid-cols-12 md:items-end">
            <div className="md:col-span-2">
              <FilterLabel htmlFor="asg-grade">Grade</FilterLabel>
              <FilterSelect
                id="asg-grade"
                value={filters.grade}
                disabled={!filtersEnabled}
                onChange={(v) => patchFilter('grade', v)}
              >
                {GRADE_FILTER_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </FilterSelect>
            </div>
            <div className="md:col-span-3">
              <FilterLabel htmlFor="asg-teacher">Teacher</FilterLabel>
              <FilterSelect
                id="asg-teacher"
                value={filters.teacherKey}
                disabled={!filtersEnabled}
                onChange={(v) => patchFilter('teacherKey', v)}
              >
                <option value="">All teachers</option>
                {teacherChoices.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </FilterSelect>
            </div>
            <div className="md:col-span-2">
              <FilterLabel htmlFor="asg-students">Students</FilterLabel>
              <FilterSelect
                id="asg-students"
                value={filters.enrollment}
                disabled={!filtersEnabled}
                onChange={(v) => patchFilter('enrollment', v as AssignmentsHubFilters['enrollment'])}
              >
                <option value="">Any</option>
                <option value="with">With students</option>
                <option value="empty">No students</option>
              </FilterSelect>
            </div>
            <div className="md:col-span-2">
              <FilterLabel htmlFor="asg-assignment-filter">Assignments</FilterLabel>
              <FilterSelect
                id="asg-assignment-filter"
                value={filters.assignment}
                disabled={!filtersEnabled}
                onChange={(v) => patchFilter('assignment', v as AssignmentsHubFilters['assignment'])}
              >
                <option value="">Any</option>
                <option value="with">Has assignments</option>
                <option value="none">No assignments yet</option>
              </FilterSelect>
            </div>
            <div className="md:col-span-3">
              <FilterLabel htmlFor="asg-sort">Sort by</FilterLabel>
              <FilterSelect
                id="asg-sort"
                value={filters.sort}
                disabled={!filtersEnabled}
                onChange={(v) => patchFilter('sort', v as AssignmentsHubFilters['sort'])}
              >
                {ASSIGNMENTS_HUB_SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </FilterSelect>
            </div>
          </div>

          {yearChosen ? (
            <p className="mt-4 inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-900">
              Showing <strong className="mx-1">{visibleItems.length}</strong> of{' '}
              <strong className="mx-1">{yearItems.length}</strong> classes
            </p>
          ) : (
            <p className="mt-4 text-sm text-hub-muted">Select a school year to browse classes.</p>
          )}
        </div>
      </section>

      {loading ? (
        <div className="rounded-2xl bg-white/90 p-12 text-center text-hub-muted shadow-lg">Loading classes…</div>
      ) : !yearChosen ? (
        <div className="rounded-2xl bg-white/90 p-12 text-center text-hub-muted shadow-lg">
          Select a school year in the filters above to view classes.
        </div>
      ) : visibleItems.length === 0 ? (
        <div className="rounded-2xl bg-white/90 p-12 text-center text-hub-muted shadow-lg">
          <i className="bi bi-inbox mb-2 block text-3xl text-slate-300" aria-hidden />
          <p className="font-semibold text-hub-text">No classes match that filter</p>
          <p className="mt-2 text-sm">Try adjusting your search or filters.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visibleItems.map((item) => (
            <HubClassCard
              key={item.id}
              item={item}
              pendingProposals={hubMeta?.pending_assistant_by_class[item.id] ?? 0}
              onOpen={() => navigate(`/management/assignments/${item.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
