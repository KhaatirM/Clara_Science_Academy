import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { fetchTeacherAssignmentsHub } from '../api/teacherTabs'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { ClassListItem } from '../types/classes'
import type { TeacherAssignmentsClassItem, TeacherAssignmentsHubResponse } from '../types/teacherTabs'
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

function TeacherAssignmentsClassCard({ item }: { item: TeacherAssignmentsClassItem }) {
  return (
    <article className="teacher-class-card">
      <div className="teacher-class-card__header">
        <h3 className="teacher-class-card__title">{item.name}</h3>
        <span className="teacher-class-card__grade">{item.grade_levels_display}</span>
      </div>
      <div className="teacher-class-card__body">
        <div className="teacher-class-card__meta">
          <div className="teacher-class-card__meta-item">
            <span className="teacher-class-card__meta-icon bg-blue-100 text-blue-700">
              <i className="bi bi-book-fill" aria-hidden />
            </span>
            <div>
              <div className="teacher-class-card__meta-label">Subject</div>
              <div className="teacher-class-card__meta-value">{item.subject}</div>
            </div>
          </div>
          <div className="teacher-class-card__meta-item">
            <span className="teacher-class-card__meta-icon bg-emerald-100 text-emerald-700">
              <i className="bi bi-people-fill" aria-hidden />
            </span>
            <div>
              <div className="teacher-class-card__meta-label">Students</div>
              <div className="teacher-class-card__meta-value">{item.enrollment_count}</div>
            </div>
          </div>
          <div className="teacher-class-card__meta-item">
            <span className="teacher-class-card__meta-icon bg-amber-100 text-amber-700">
              <i className="bi bi-journal-check" aria-hidden />
            </span>
            <div>
              <div className="teacher-class-card__meta-label">Assignments</div>
              <div className="teacher-class-card__meta-value">{item.assignment_count}</div>
            </div>
          </div>
        </div>
        <div className="teacher-class-card__actions teacher-class-card__actions--pair">
          <Link to={`/teacher/assignments-and-grades/${item.id}`} className="teacher-class-card__btn teacher-class-card__btn--view">
            <i className="bi bi-journal-text" aria-hidden />
            Open class
          </Link>
          <Link
            to={`/teacher/assignments/create?class_id=${item.id}`}
            className="teacher-class-card__btn teacher-class-card__btn--assignment"
          >
            <i className="bi bi-plus-circle-fill" aria-hidden />
            New assignment
          </Link>
        </div>
      </div>
    </article>
  )
}

export function TeacherAssignmentsGradesPage() {
  const [data, setData] = useState<TeacherAssignmentsHubResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<AssignmentsHubFilters>(defaultAssignmentsHubFilters)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchTeacherAssignmentsHub()
      setData(payload)
      const defaultYearId =
        payload.meta?.default_school_year_id ?? payload.meta?.active_school_year_id ?? ''
      setFilters((prev) => ({
        ...prev,
        schoolYearId: defaultYearId,
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load assignments')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const allItems = data?.items ?? []
  const yearItems = useMemo(
    () => itemsForSchoolYear(allItems as ClassListItem[], filters.schoolYearId),
    [allItems, filters.schoolYearId],
  )
  const visibleItems = useMemo(
    () => filterAssignmentsHubClasses(allItems as ClassListItem[], filters) as TeacherAssignmentsClassItem[],
    [allItems, filters],
  )
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
    const defaultYearId = data?.meta?.default_school_year_id ?? data?.meta?.active_school_year_id ?? ''
    setFilters({ ...defaultAssignmentsHubFilters, schoolYearId: defaultYearId })
  }

  const canSelectSchoolYear = data?.meta?.can_select_school_year ?? false
  const activeSchoolYearName = data?.meta?.active_school_year_name
  const hub = data?.hub

  return (
    <ManagementPageShell>
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Assignments & grades</p>
              <h1 className="mt-0.5 text-2xl font-extrabold tracking-tight text-hub-text">Assignments & grades</h1>
              <p className="mt-1 flex items-center gap-1.5 text-sm text-hub-muted">
                <i className="bi bi-clipboard-data" aria-hidden />
                Select a class to view and manage assignments
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-1 text-xs font-bold text-teal-900">
                <i className="bi bi-mortarboard-fill" aria-hidden />
                Teacher
              </span>
              <Link
                to="/teacher/redo"
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
              >
                <i className="bi bi-arrow-repeat" aria-hidden />
                Redo
                {hub && hub.redo_request_count > 0 ? (
                  <span className="rounded-full bg-red-600 px-1.5 text-[0.65rem] text-white">
                    {hub.redo_request_count}
                  </span>
                ) : null}
              </Link>
              <Link
                to="/teacher/extensions"
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500"
              >
                <i className="bi bi-clock-history" aria-hidden />
                Extensions
                {hub && hub.extension_request_count > 0 ? (
                  <span className="rounded-full bg-red-600 px-1.5 text-[0.65rem] text-white">
                    {hub.extension_request_count}
                  </span>
                ) : null}
              </Link>
              <Link
                to="/teacher/assignments/create"
                className="spa-mgmt-btn-primary inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[0.82rem] shadow-sm hover:brightness-105"
              >
                <i className="bi bi-plus-circle" aria-hidden />
                New assignment
              </Link>
            </div>
          </header>

          {error ? (
            <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div>
          ) : null}

          {!loading && data && !data.meta.has_active_school_year ? (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              No active school year is set. Class lists may be empty until a school year is active.
            </div>
          ) : null}

          {yearChosen ? (
            <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <InsightCard icon="bi-house-door-fill" value={stats.total_classes} label="Classes" />
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
                  <FilterLabel htmlFor="teacher-asg-search">Search</FilterLabel>
                  <div className="flex overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                    <span className="flex items-center px-3 text-hub-muted" aria-hidden>
                      <i className="bi bi-search" />
                    </span>
                    <input
                      id="teacher-asg-search"
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
                  <FilterLabel htmlFor="teacher-asg-year">School year</FilterLabel>
                  {canSelectSchoolYear ? (
                    <FilterSelect
                      id="teacher-asg-year"
                      value={filters.schoolYearId ? String(filters.schoolYearId) : ''}
                      onChange={(v) => patchFilter('schoolYearId', v ? Number(v) : '')}
                    >
                      <option value="">No school year selected</option>
                      {(data?.school_years ?? []).map((y) => (
                        <option key={y.id} value={y.id}>
                          {y.name}
                          {y.is_active ? ' (Active)' : ' (Closed)'}
                        </option>
                      ))}
                    </FilterSelect>
                  ) : (
                    <div
                      id="teacher-asg-year"
                      className="flex min-h-[42px] w-full items-center rounded-xl border border-slate-200 bg-slate-100 px-3 py-2.5 text-sm font-semibold text-hub-text"
                    >
                      {activeSchoolYearName || 'No active school year'}
                      {data?.meta.has_active_school_year ? (
                        <span className="ms-2 rounded-full bg-emerald-100 px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-emerald-800">
                          Active
                        </span>
                      ) : null}
                    </div>
                  )}
                </div>
                <div className="md:col-span-4">
                  <FilterLabel htmlFor="teacher-asg-subject">Subject</FilterLabel>
                  <FilterSelect
                    id="teacher-asg-subject"
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
                  <FilterLabel htmlFor="teacher-asg-grade">Grade</FilterLabel>
                  <FilterSelect
                    id="teacher-asg-grade"
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
                  <FilterLabel htmlFor="teacher-asg-teacher">Teacher</FilterLabel>
                  <FilterSelect
                    id="teacher-asg-teacher"
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
                  <FilterLabel htmlFor="teacher-asg-students">Students</FilterLabel>
                  <FilterSelect
                    id="teacher-asg-students"
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
                  <FilterLabel htmlFor="teacher-asg-assignment-filter">Assignments</FilterLabel>
                  <FilterSelect
                    id="teacher-asg-assignment-filter"
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
                  <FilterLabel htmlFor="teacher-asg-sort">Sort by</FilterLabel>
                  <FilterSelect
                    id="teacher-asg-sort"
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
              ) : canSelectSchoolYear ? (
                <p className="mt-4 text-sm text-hub-muted">Select a school year to browse classes.</p>
              ) : null}
            </div>
          </section>

          {loading ? (
            <div className="rounded-2xl bg-white/90 p-12 text-center text-hub-muted shadow-lg">Loading classes…</div>
          ) : !yearChosen && canSelectSchoolYear ? (
            <div className="rounded-2xl bg-white/90 p-12 text-center text-hub-muted shadow-lg">
              Select a school year in the filters above to view classes.
            </div>
          ) : !yearChosen ? (
            <div className="rounded-2xl bg-white/90 p-12 text-center text-hub-muted shadow-lg">
              No active school year is set. Classes will appear here once a school year is active.
            </div>
          ) : visibleItems.length === 0 ? (
            <div className="rounded-2xl bg-white/90 p-12 text-center text-hub-muted shadow-lg">
              <i className="bi bi-inbox mb-2 block text-3xl text-slate-300" aria-hidden />
              <p className="font-semibold text-hub-text">No classes match that filter</p>
              <p className="mt-2 text-sm">Try adjusting your search or filters.</p>
            </div>
          ) : (
            <div className="teacher-classes-grid">
              {visibleItems.map((item) => (
                <TeacherAssignmentsClassCard key={item.id} item={item} />
              ))}
            </div>
          )}
    </ManagementPageShell>
  )
}
