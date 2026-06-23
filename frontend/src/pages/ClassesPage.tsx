import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { useNavigate, useOutletContext, useSearchParams, Link } from 'react-router-dom'

import { fetchClassList } from '../api/classes'

import { ClassCard } from '../components/classes/ClassCard'

import { CreateClassModal } from '../components/classes/CreateClassModal'

import { LinkGoogleClassroomModal } from '../components/classes/LinkGoogleClassroomModal'

import type { ManagementOutletContext } from '../types/layout'

import type { ClassListItem, SchoolYearOption } from '../types/classes'

import {

  GRADE_FILTER_OPTIONS,

  SORT_OPTIONS,

  computeClassStats,

  defaultClassFilters,

  exportClassesCsv,

  filterAndSortClasses,

  itemsForSchoolYear,

  subjectOptions,

  teacherOptions,

  type ClassFilters,

} from '../utils/classListFilters'



function FilterLabel({ children, htmlFor }: { children: string; htmlFor: string }) {

  return (

    <label

      htmlFor={htmlFor}

      className="mb-1 block text-[0.72rem] font-bold uppercase tracking-wide text-hub-muted"

    >

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



function StatCard({

  icon,

  value,

  label,

  iconClass,

}: {

  icon: string

  value: number

  label: string

  iconClass: string

}) {

  return (

    <div

      className="flex items-start gap-3 rounded-2xl border border-white/90 bg-white/95 p-4 shadow-sm"

      role="listitem"

    >

      <span

        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-base ${iconClass}`}

      >

        <i className={`bi ${icon}`} aria-hidden />

      </span>

      <div>

        <div className="text-2xl font-extrabold text-hub-text">{value}</div>

        <div className="text-[0.72rem] font-semibold uppercase tracking-wide text-hub-muted">{label}</div>

      </div>

    </div>

  )

}



export function ClassesPage() {

  const { user } = useOutletContext<ManagementOutletContext>()

  const navigate = useNavigate()

  const [searchParams, setSearchParams] = useSearchParams()

  const isDirector = user.role_canonical === 'Director'



  const shellBg = isDirector

    ? 'bg-gradient-to-br from-violet-50 via-purple-50/80 to-slate-100'

    : 'bg-gradient-to-br from-emerald-50 via-teal-50/70 to-slate-100'

  const primaryBtn = isDirector

    ? 'bg-gradient-to-br from-violet-600 to-purple-700'

    : 'bg-gradient-to-br from-teal-600 to-teal-800'

  const ghostHover = isDirector ? 'hover:border-violet-500 hover:text-violet-800' : 'hover:border-teal-500 hover:text-teal-800'

  const accentRing = isDirector ? 'focus:border-violet-500 focus:ring-violet-500/20' : 'focus:border-teal-500 focus:ring-teal-500/20'

  const exportBtn = isDirector

    ? 'bg-gradient-to-br from-violet-600 to-purple-700'

    : 'bg-gradient-to-br from-teal-600 to-teal-800'

  const gridAccent = isDirector ? 'border-violet-500' : 'border-amber-400'

  const statIcons = isDirector

    ? ['bg-violet-100 text-violet-800', 'bg-purple-100 text-purple-800', 'bg-fuchsia-100 text-fuchsia-800', 'bg-violet-100 text-violet-700']

    : ['bg-emerald-100 text-emerald-800', 'bg-teal-100 text-teal-800', 'bg-cyan-100 text-cyan-800', 'bg-teal-100 text-teal-700']



  const [allItems, setAllItems] = useState<ClassListItem[]>([])

  const [schoolYears, setSchoolYears] = useState<SchoolYearOption[]>([])

  const [filters, setFilters] = useState<ClassFilters>(defaultClassFilters)

  const [canAdminUi, setCanAdminUi] = useState(false)

  const [canCreate, setCanCreate] = useState(false)

  const [hasActiveSchoolYear, setHasActiveSchoolYear] = useState(true)

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState<string | null>(null)

  const [showCreate, setShowCreate] = useState(false)

  const [linkGoogle, setLinkGoogle] = useState<{ id: number; name: string } | null>(null)



  const load = useCallback(async () => {

    setLoading(true)

    setError(null)

    try {

      const data = await fetchClassList()

      setAllItems(data.items)

      setSchoolYears(data.school_years)

      setCanAdminUi(data.meta.can_admin_ui)

      setCanCreate(data.meta.can_create)

      setHasActiveSchoolYear(data.meta.has_active_school_year)

      setFilters((prev) => ({

        ...prev,

        schoolYearId: data.meta.default_school_year_id ?? prev.schoolYearId ?? '',

      }))

    } catch (err) {

      setError(err instanceof Error ? err.message : 'Could not load classes')

    } finally {

      setLoading(false)

    }

  }, [])



  useEffect(() => {

    void load()

  }, [load])



  useEffect(() => {

    if (searchParams.get('open') === 'create' && canCreate) {

      setShowCreate(true)

      const next = new URLSearchParams(searchParams)

      next.delete('open')

      setSearchParams(next, { replace: true })

    }

  }, [canCreate, searchParams, setSearchParams])



  const yearItems = useMemo(

    () => itemsForSchoolYear(allItems, filters.schoolYearId),

    [allItems, filters.schoolYearId],

  )



  const subjectChoices = useMemo(() => subjectOptions(yearItems), [yearItems])

  const teacherChoices = useMemo(() => teacherOptions(yearItems), [yearItems])



  const visibleItems = useMemo(() => filterAndSortClasses(allItems, filters), [allItems, filters])

  const stats = useMemo(() => computeClassStats(visibleItems), [visibleItems])



  const yearChosen = !!filters.schoolYearId

  const filtersEnabled = yearChosen



  const patchFilter = <K extends keyof ClassFilters>(key: K, value: ClassFilters[K]) => {

    setFilters((prev) => {

      const next = { ...prev, [key]: value }

      if (key === 'schoolYearId') {

        next.subject = ''

        next.teacherKey = ''

        next.status = ''

        next.grade = ''

        next.enrollment = ''

        next.assignment = ''

      }

      return next

    })

  }



  const resetFilters = () => {

    setFilters({

      ...defaultClassFilters,

      schoolYearId: '',

    })

  }



  return (

    <div className={`rounded-3xl p-5 md:p-8 ${shellBg}`}>

      <header className="mb-5 flex flex-wrap items-start justify-between gap-4">

        <div>

          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Course catalog</p>

          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-hub-text">Classes</h1>

          <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-hub-muted">

            <i className="bi bi-book" aria-hidden />

            Manage classes, schedules, and enrollments

          </p>

        </div>

        <div className="flex flex-wrap items-center gap-2">

          {isDirector ? (

            <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2.5 py-1 text-xs font-bold text-violet-900">

              <i className="bi bi-award-fill" aria-hidden />

              Director

            </span>

          ) : canAdminUi ? (

            <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-1 text-xs font-bold text-teal-900">

              <i className="bi bi-shield-fill" aria-hidden />

              Administrator

            </span>

          ) : null}

          {canCreate ? (

            <Link

              to="/management/classes/core-setup"

              className={`inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 ${ghostHover}`}

            >

              <i className="bi bi-journal-check" aria-hidden />

              Core class setup

            </Link>

          ) : null}

          {canCreate ? (

            <button

              type="button"

              onClick={() => setShowCreate(true)}

              className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[0.82rem] font-semibold text-white shadow-sm hover:brightness-105 ${primaryBtn}`}

            >

              <i className="bi bi-plus-circle" aria-hidden />

              Create class

            </button>

          ) : null}

          <button

            type="button"

            onClick={() => navigate('/management')}

            className={`inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 ${ghostHover}`}

          >

            <i className="bi bi-house-door" aria-hidden />

            Dashboard

          </button>

        </div>

      </header>



      {!hasActiveSchoolYear ? (

        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">

          No active school year is set. Class creation and some actions may be limited until a school year is active.

        </div>

      ) : null}



      {error ? (

        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>

      ) : null}



      {yearChosen ? (

        <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" role="list" aria-live="polite">

          <StatCard icon="bi-house-door-fill" value={stats.total_classes} label="Total classes" iconClass={statIcons[0]} />

          <StatCard icon="bi-people-fill" value={stats.total_enrollments} label="Enrollments" iconClass={statIcons[1]} />

          <StatCard icon="bi-person-badge" value={stats.unique_teachers} label="Teachers" iconClass={statIcons[2]} />

          <StatCard icon="bi-journal-check" value={stats.total_assignments} label="Assignments" iconClass={statIcons[3]} />

        </div>

      ) : null}



      <section className="mb-5 overflow-hidden rounded-2xl border border-white/90 bg-white shadow-lg">

        <div className="p-5">

          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">

            <h2 className="flex items-center gap-2 text-base font-extrabold text-hub-text">

              <i className="bi bi-funnel-fill" aria-hidden />

              Filters

            </h2>

            <div className="flex flex-wrap gap-2">

              <button

                type="button"

                onClick={resetFilters}

                className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"

              >

                <i className="bi bi-arrow-counterclockwise" aria-hidden />

                Reset

              </button>

              <button

                type="button"

                disabled={!visibleItems.length}

                onClick={() => exportClassesCsv(visibleItems)}

                className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-semibold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-50 ${exportBtn}`}

              >

                <i className="bi bi-download" aria-hidden />

                Export

              </button>

            </div>

          </div>



          <div className="grid gap-3 md:grid-cols-12 md:items-end">

            <div className="md:col-span-4">

              <FilterLabel htmlFor="classSearch">Search</FilterLabel>

              <div className="flex overflow-hidden rounded-xl border border-slate-200 bg-slate-50">

                <span className="flex items-center px-3 text-hub-muted" aria-hidden>

                  <i className="bi bi-search" />

                </span>

                <input

                  id="classSearch"

                  type="search"

                  value={filters.search}

                  onChange={(e) => patchFilter('search', e.target.value)}

                  placeholder="Class, teacher, subject…"

                  disabled={!filtersEnabled}

                  className={`min-w-0 flex-1 border-0 bg-transparent px-0 py-2.5 pr-3 text-sm focus:outline-none focus:ring-0 disabled:opacity-60 ${accentRing}`}

                />

              </div>

            </div>

            <div className="md:col-span-3">

              <FilterLabel htmlFor="schoolYearFilter">School year</FilterLabel>

              <FilterSelect

                id="schoolYearFilter"

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

            <div className="md:col-span-3">

              <FilterLabel htmlFor="subjectFilter">Subject</FilterLabel>

              <FilterSelect

                id="subjectFilter"

                value={filters.subject}

                disabled={!filtersEnabled}

                onChange={(v) => patchFilter('subject', v)}

              >

                <option value="">All subjects</option>

                {subjectChoices.map((s) => (

                  <option key={s} value={s}>

                    {s}

                  </option>

                ))}

              </FilterSelect>

            </div>

            <div className="md:col-span-2">

              <FilterLabel htmlFor="statusFilter">Status</FilterLabel>

              <FilterSelect

                id="statusFilter"

                value={filters.status}

                disabled={!filtersEnabled}

                onChange={(v) => patchFilter('status', v as ClassFilters['status'])}

              >

                <option value="">All</option>

                <option value="active">Active</option>

                <option value="inactive">Inactive</option>

              </FilterSelect>

            </div>

          </div>



          <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 md:grid-cols-12 md:items-end">

            <div className="md:col-span-2">

              <FilterLabel htmlFor="gradeFilter">Grade</FilterLabel>

              <FilterSelect

                id="gradeFilter"

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

              <FilterLabel htmlFor="teacherFilter">Teacher</FilterLabel>

              <FilterSelect

                id="teacherFilter"

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

              <FilterLabel htmlFor="enrollmentFilter">Students</FilterLabel>

              <FilterSelect

                id="enrollmentFilter"

                value={filters.enrollment}

                disabled={!filtersEnabled}

                onChange={(v) => patchFilter('enrollment', v as ClassFilters['enrollment'])}

              >

                <option value="">Any</option>

                <option value="with">With students</option>

                <option value="empty">No students</option>

              </FilterSelect>

            </div>

            <div className="md:col-span-2">

              <FilterLabel htmlFor="assignmentFilter">Assignments</FilterLabel>

              <FilterSelect

                id="assignmentFilter"

                value={filters.assignment}

                disabled={!filtersEnabled}

                onChange={(v) => patchFilter('assignment', v as ClassFilters['assignment'])}

              >

                <option value="">Any</option>

                <option value="with">Has assignments</option>

                <option value="none">No assignments</option>

              </FilterSelect>

            </div>

            <div className="md:col-span-3">

              <FilterLabel htmlFor="sortFilter">Sort by</FilterLabel>

              <FilterSelect

                id="sortFilter"

                value={filters.sort}

                disabled={!filtersEnabled}

                onChange={(v) => patchFilter('sort', v as ClassFilters['sort'])}

              >

                {SORT_OPTIONS.map((opt) => (

                  <option key={opt.value} value={opt.value}>

                    {opt.label}

                  </option>

                ))}

              </FilterSelect>

            </div>

          </div>

        </div>

      </section>



      <div className={`mb-4 rounded-xl border border-slate-200 border-l-4 bg-white px-5 py-3 shadow-sm ${gridAccent}`}>

        <h2 className="flex flex-wrap items-center gap-2 text-base font-bold text-hub-text">

          <i className="bi bi-grid-3x3-gap-fill" aria-hidden />

          All Classes

          <span className="text-sm font-semibold text-hub-muted">

            {!yearChosen

              ? '(select a school year)'

              : `(${visibleItems.length} shown)`}

          </span>

        </h2>

      </div>



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

          {canCreate ? (

            <p className="mt-2 text-sm">

              Try adjusting filters or use <strong>Create class</strong> to add a new class.

            </p>

          ) : null}

        </div>

      ) : (

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">

          {visibleItems.map((item) => (

            <ClassCard

              key={item.id}

              item={item}

              canAdminUi={canAdminUi}

              canCreate={canCreate}

              accentClass={isDirector ? 'violet' : 'teal'}

              onLinkGoogle={(id, name) => setLinkGoogle({ id, name })}

              onChanged={() => void load()}

            />

          ))}

        </div>

      )}

      {showCreate ? (

        <CreateClassModal

          onClose={() => setShowCreate(false)}

          onCreated={(classId) => {

            setShowCreate(false)

            void load()

            navigate(`/management/classes/${classId}`)

          }}

        />

      ) : null}

      {linkGoogle ? (

        <LinkGoogleClassroomModal

          classId={linkGoogle.id}

          className={linkGoogle.name}

          onClose={() => setLinkGoogle(null)}

          onLinked={() => void load()}

        />

      ) : null}

    </div>

  )

}


