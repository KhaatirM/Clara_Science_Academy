import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext, useParams, useSearchParams } from 'react-router-dom'

import { fetchReportCardsCategory, reportCardPdfUrl } from '../api/reportCards'
import PendingApprovalNotifier from '../components/reportCards/PendingApprovalNotifier'
import { spaRoute } from '../utils/spaRoute'
import type { ManagementOutletContext } from '../types/layout'
import type { ReportCardsCategoryResponse, ReportCardsCategoryStudent } from '../types/reportCards'

type SortOrder =
  | 'name-asc'
  | 'name-desc'
  | 'grade-asc'
  | 'grade-desc'
  | 'reports-desc'
  | 'reports-asc'

type ReportStatusFilter = 'all' | 'with-reports' | 'without-reports' | 'pending-approval'

function sortStudents(students: ReportCardsCategoryStudent[], sort: SortOrder) {
  const copy = [...students]
  copy.sort((a, b) => {
    switch (sort) {
      case 'name-desc':
        return b.name.localeCompare(a.name)
      case 'grade-asc':
        return a.grade_level - b.grade_level || a.name.localeCompare(b.name)
      case 'grade-desc':
        return b.grade_level - a.grade_level || a.name.localeCompare(b.name)
      case 'reports-desc':
        return b.report_count - a.report_count || a.name.localeCompare(b.name)
      case 'reports-asc':
        return a.report_count - b.report_count || a.name.localeCompare(b.name)
      default:
        return a.name.localeCompare(b.name)
    }
  })
  return copy
}

function StudentCard({
  student,
  highlight,
}: {
  student: ReportCardsCategoryStudent
  highlight: boolean
}) {
  const [recentOpen, setRecentOpen] = useState(highlight)

  return (
    <article
      className={[
        'rounded-2xl border bg-white shadow-sm',
        highlight ? 'border-violet-400 ring-2 ring-violet-200' : 'border-slate-200',
      ].join(' ')}
    >
      <div className="h-1 rounded-t-2xl bg-gradient-to-r from-violet-500 to-indigo-500" />
      <div className="space-y-4 p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-violet-100 text-sm font-bold text-violet-800">
            {student.initials}
          </span>
          <div className="min-w-0">
            <h3 className="truncate font-bold text-hub-text">{student.name}</h3>
            <p className="text-xs text-hub-muted">
              <i className="bi bi-card-text mr-1" aria-hidden />
              {student.student_id ? `ID ${student.student_id}` : 'No student ID'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">Grade</p>
            <p className="text-lg font-bold text-hub-text">{student.grade_display}</p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[0.65rem] font-bold uppercase tracking-wide text-hub-muted">Classes</p>
            <p className="text-lg font-bold text-hub-text">{student.enrollment_count}</p>
          </div>
        </div>

        <Link
          to={student.generate_url}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-800"
        >
          <i className="bi bi-file-earmark-text" aria-hidden />
          Generate report card
        </Link>

        {student.recent_reports.length ? (
          <div className="rounded-xl border border-slate-200">
            <button
              type="button"
              onClick={() => setRecentOpen((open) => !open)}
              className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-hub-text"
            >
              <span>
                <i className="bi bi-clock-history mr-1 text-violet-700" aria-hidden />
                Recent ({student.report_count})
              </span>
              <i className={`bi bi-chevron-${recentOpen ? 'up' : 'down'}`} aria-hidden />
            </button>
            {recentOpen ? (
              <div className="space-y-2 border-t border-slate-200 px-4 py-3">
                {student.recent_reports.map((report) => (
                  <div
                    key={report.id}
                    className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm"
                  >
                    <span className="min-w-0 truncate text-hub-muted">
                      {report.quarter} · {report.school_year?.name || 'N/A'}
                      {report.generated_at_display ? ` · ${report.generated_at_display.split(' · ')[0]}` : ''}
                    </span>
                    <span className="flex shrink-0 gap-1">
                      <Link
                        to={report.urls.view}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 hover:bg-white"
                        title="View"
                      >
                        <i className="bi bi-eye" aria-hidden />
                      </Link>
                      <a
                        href={reportCardPdfUrl(report.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 hover:bg-white"
                        title="PDF"
                      >
                        <i className="bi bi-file-pdf" aria-hidden />
                      </a>
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  )
}

export default function ReportCardsCategoryPage() {
  const { category = '' } = useParams()
  const { user } = useOutletContext<ManagementOutletContext>()
  const [searchParams] = useSearchParams()
  const highlightStudentId = Number(searchParams.get('highlight') || '') || null
  const reportSaved = searchParams.get('saved') === '1'

  const [data, setData] = useState<ReportCardsCategoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [gradeFilter, setGradeFilter] = useState<number | null>(null)
  const [reportStatusFilter, setReportStatusFilter] = useState<ReportStatusFilter>('all')
  const [sort, setSort] = useState<SortOrder>('name-asc')

  const isDirector = user.role_canonical === 'Director'

  const load = useCallback(async () => {
    if (!category) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchReportCardsCategory(category))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load category roster')
    } finally {
      setLoading(false)
    }
  }, [category])

  useEffect(() => {
    void load()
  }, [load])

  const visibleStudents = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    let result = data.students.filter((student) => {
      if (gradeFilter !== null && student.grade_level !== gradeFilter) return false
      if (reportStatusFilter === 'with-reports' && student.report_count <= 0) return false
      if (reportStatusFilter === 'without-reports' && student.report_count > 0) return false
      if (
        reportStatusFilter === 'pending-approval' &&
        !student.recent_reports.some((report) => report.publish_status === 'pending')
      ) {
        return false
      }
      if (!q) return true
      return (
        student.name.toLowerCase().includes(q) ||
        String(student.student_id).toLowerCase().includes(q)
      )
    })
    result = sortStudents(result, sort)
    return result
  }, [data, search, gradeFilter, reportStatusFilter, sort])

  if (loading && !data) {
    return <div className="py-16 text-center text-hub-muted">Loading roster…</div>
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-rose-700">{error || 'Category not found.'}</p>
        <Link to="/management/report-cards" className="mt-4 inline-block text-violet-700 underline">
          Back to report cards
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-1 pb-10 pt-2">
      {reportSaved ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          <i className="bi bi-check-circle-fill mr-2" aria-hidden />
          Report card saved. It is listed under <strong>Recent</strong> on the student card below.
        </div>
      ) : null}

      {(data.warnings.unfinalized_grades.length > 0) && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Some grade-level standards may still be unfinalized (grades{' '}
          {data.warnings.unfinalized_grades.join(', ')}). Review before generating official cards.
        </div>
      )}

      <header className="rounded-3xl border border-white/80 bg-gradient-to-br from-violet-900 via-violet-800 to-indigo-900 p-6 text-white shadow-lg md:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <nav className="mb-2 text-sm text-violet-100/90" aria-label="Breadcrumb">
              <Link to={data.urls.hub} className="hover:text-white">
                Report cards
              </Link>
              <span className="mx-2">›</span>
              <span>{data.category.short_name}</span>
            </nav>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-violet-100/90">Generate report cards</p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight">
              {data.category.name}
              <span className="ml-3 rounded-full bg-white/15 px-3 py-1 text-sm font-semibold">
                {data.category.short_name}
              </span>
            </h1>
            <p className="mt-2 text-sm text-violet-50/90">
              Pick a student to start their report card — search, filter, and skim recent activity below.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to={data.urls.hub}
              className="inline-flex items-center gap-2 rounded-xl border border-white/30 px-4 py-2 text-sm font-semibold text-white hover:bg-white/10"
            >
              <i className="bi bi-arrow-left" aria-hidden />
              Back to categories
            </Link>
            <a
              href={data.urls.generate_form}
              className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-violet-900 hover:bg-violet-50"
            >
              <i className="bi bi-plus-circle-fill" aria-hidden />
              Generate new
            </a>
          </div>
        </div>
      </header>

      {data.category.slug === 'elementary' && (data.urls.grade1_standards || data.urls.grade3_standards) ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50/80 p-4">
          <p className="text-sm font-semibold text-hub-text">
            <i className="bi bi-check2-square mr-2 text-sky-700" aria-hidden />
            K–3 report cards use standards checklists on the PDF. Teachers fill marks in the checklist editors before you generate.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.urls.grade1_standards ? (
              <Link
                to={spaRoute(data.urls.grade1_standards)}
                className="inline-flex items-center gap-2 rounded-xl border border-sky-300 bg-white px-4 py-2 text-sm font-semibold text-sky-900 hover:bg-sky-50"
              >
                1st grade standards editor
              </Link>
            ) : null}
            {data.urls.grade3_standards ? (
              <Link
                to={spaRoute(data.urls.grade3_standards)}
                className="inline-flex items-center gap-2 rounded-xl border border-sky-300 bg-white px-4 py-2 text-sm font-semibold text-sky-900 hover:bg-sky-50"
              >
                3rd grade standards editor
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}

      {data.students.length ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <i className="bi bi-funnel-fill text-violet-700" aria-hidden />
            <h2 className="text-sm font-bold uppercase tracking-wide text-hub-muted">Filter roster</h2>
          </div>
          <div className="flex flex-col gap-4">
            <div className="relative max-w-md">
              <i className="bi bi-search absolute left-3 top-1/2 -translate-y-1/2 text-hub-muted" aria-hidden />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or student ID…"
                className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-3 text-sm"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">Grade</span>
              <button
                type="button"
                onClick={() => setGradeFilter(null)}
                className={[
                  'rounded-full px-3 py-1.5 text-xs font-semibold',
                  gradeFilter === null ? 'bg-violet-700 text-white' : 'bg-slate-100 text-hub-muted',
                ].join(' ')}
              >
                All
              </button>
              {data.category.grade_levels.map((grade, index) => (
                <button
                  key={grade}
                  type="button"
                  onClick={() => setGradeFilter(grade)}
                  className={[
                    'rounded-full px-3 py-1.5 text-xs font-semibold',
                    gradeFilter === grade ? 'bg-violet-700 text-white' : 'bg-slate-100 text-hub-muted',
                  ].join(' ')}
                >
                  {data.category.grade_displays[index]}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">Report cards</span>
              {(
                [
                  ['all', 'All students'],
                  ['with-reports', 'Has report cards'],
                  ['without-reports', 'No report cards'],
                  ['pending-approval', 'Pending approval'],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setReportStatusFilter(value)}
                  className={[
                    'rounded-full px-3 py-1.5 text-xs font-semibold',
                    reportStatusFilter === value ? 'bg-violet-700 text-white' : 'bg-slate-100 text-hub-muted',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <label htmlFor="rc-sort" className="mb-1 block text-xs font-bold uppercase text-hub-muted">
                  Sort
                </label>
                <select
                  id="rc-sort"
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortOrder)}
                  className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="name-asc">Name (A → Z)</option>
                  <option value="name-desc">Name (Z → A)</option>
                  <option value="grade-asc">Grade (low → high)</option>
                  <option value="grade-desc">Grade (high → low)</option>
                  <option value="reports-desc">Most report cards</option>
                  <option value="reports-asc">Fewest report cards</option>
                </select>
              </div>
              {(search || gradeFilter !== null || reportStatusFilter !== 'all') && (
                <button
                  type="button"
                  onClick={() => {
                    setSearch('')
                    setGradeFilter(null)
                    setReportStatusFilter('all')
                  }}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { value: data.stats.total_students, label: 'Students' },
          { value: data.stats.grade_levels, label: 'Grade levels' },
          { value: data.stats.total_reports, label: 'Report cards on file' },
          { value: data.stats.students_without_reports, label: 'Students without a card' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-2xl border border-white/90 bg-white/95 p-4 shadow-sm">
            <div className="text-2xl font-extrabold text-hub-text">{stat.value}</div>
            <div className="text-[0.72rem] font-semibold uppercase tracking-wide text-hub-muted">{stat.label}</div>
          </div>
        ))}
      </div>

      {data.students.length ? (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-hub-text">
              <i className="bi bi-grid-3x3-gap-fill mr-2 text-violet-700" aria-hidden />
              Roster
            </h2>
            <span className="text-sm text-hub-muted">
              Showing <strong>{visibleStudents.length}</strong> of <strong>{data.stats.total_students}</strong>{' '}
              students
            </span>
          </div>

          {visibleStudents.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visibleStudents.map((student) => (
                <StudentCard
                  key={student.id}
                  student={student}
                  highlight={highlightStudentId === student.id}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 px-6 py-14 text-center text-hub-muted">
              No students match your search or filters.
            </div>
          )}
        </>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-200 px-6 py-14 text-center text-hub-muted">
          <p className="font-semibold text-hub-text">No students in this grade category</p>
        </div>
      )}
      <PendingApprovalNotifier enabled={isDirector} />
    </div>
  )
}
