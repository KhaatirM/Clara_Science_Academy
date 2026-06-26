import { useCallback, useEffect, useState } from 'react'

import { Link, useOutletContext } from 'react-router-dom'



import { deleteReportCard, fetchReportCardsHub, reportCardPdfUrl } from '../api/reportCards'
import PendingApprovalNotifier from '../components/reportCards/PendingApprovalNotifier'
import { spaRoute } from '../utils/spaRoute'
import type { ManagementOutletContext } from '../types/layout'
import type { ReportCardCategoryCard, ReportCardItem, ReportCardsHubResponse } from '../types/reportCards'

const GRADE1_STANDARDS_URL = '/management/report-cards/standards/grade1'
const GRADE3_STANDARDS_URL = '/management/report-cards/standards/grade3'

function QuickActionLink({
  to,
  icon,
  label,
  primary,
}: {
  to: string
  icon: string
  label: string
  primary?: boolean
}) {
  return (
    <Link
      to={spaRoute(to)}
      className={[
        'flex min-h-[5.5rem] flex-col items-center justify-center gap-2 rounded-xl border px-3 py-4 text-center text-sm font-semibold transition',
        primary
          ? 'border-violet-700 bg-violet-700 text-white hover:bg-violet-800'
          : 'border-slate-200 bg-slate-50 text-hub-text hover:bg-white',
      ].join(' ')}
    >
      <i className={`bi ${icon} text-2xl ${primary ? 'text-white' : 'text-violet-700'}`} aria-hidden />
      <span>{label}</span>
    </Link>
  )
}

function QuickActionsPanel({ hub }: { hub: ReportCardsHubResponse }) {
  const grade1Url = hub.urls.grade1_standards || GRADE1_STANDARDS_URL
  const grade3Url = hub.urls.grade3_standards || GRADE3_STANDARDS_URL

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-bold text-hub-text">
        <i className="bi bi-lightning-fill mr-2 text-violet-700" aria-hidden />
        Quick actions
      </h2>

      <div className="mt-4 space-y-5">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">Report cards</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <QuickActionLink to={hub.urls.generate_form} icon="bi-plus-circle-fill" label="Generate new" primary />
            {hub.categories.map((category) => (
              <QuickActionLink
                key={category.slug}
                to={category.path}
                icon={category.icon}
                label={`${category.title} roster`}
              />
            ))}
            <QuickActionLink to={grade1Url} icon="bi-check2-square" label="1st grade standards" />
            <QuickActionLink to={grade3Url} icon="bi-check2-square" label="3rd grade standards" />
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">Related</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <QuickActionLink to={hub.urls.students} icon="bi-people" label="Students" />
            <QuickActionLink to={hub.urls.grades} icon="bi-clipboard-data" label="Grades" />
            <QuickActionLink to={hub.urls.attendance} icon="bi-calendar-check" label="Attendance" />
            <QuickActionLink to={hub.urls.home} icon="bi-house-door" label="Home" />
          </div>
        </div>
      </div>
    </section>
  )
}

function StatCard({

  icon,

  value,

  label,

  featured,

}: {

  icon: string

  value: number

  label: string

  featured?: boolean

}) {

  return (

    <div

      className={[

        'flex items-start gap-3 rounded-2xl border p-4 shadow-sm',

        featured

          ? 'border-violet-200 bg-gradient-to-br from-violet-50 to-white'

          : 'border-white/90 bg-white/95',

      ].join(' ')}

      role="listitem"

    >

      <span

        className={[

          'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-base',

          featured ? 'bg-violet-100 text-violet-800' : 'bg-slate-100 text-slate-700',

        ].join(' ')}

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



function PublishStatus({ report }: { report: ReportCardItem }) {

  if (report.publish_status === 'unofficial') return null

  if (report.publish_status === 'published') {

    return (

      <span className="mt-1 inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">

        Published to parents

      </span>

    )

  }

  return (

    <span className="mt-1 inline-flex rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-900">

      Awaiting Director approval

    </span>

  )

}



function CategoryCard({ category }: { category: ReportCardCategoryCard }) {

  const toneClasses: Record<string, string> = {

    emerald: 'border-emerald-200 bg-gradient-to-br from-emerald-50 to-white',

    amber: 'border-amber-200 bg-gradient-to-br from-amber-50 to-white',

    sky: 'border-sky-200 bg-gradient-to-br from-sky-50 to-white',

  }



  return (

    <article

      className={[

        'flex h-full flex-col rounded-2xl border p-5 shadow-sm',

        toneClasses[category.tone] || toneClasses.emerald,

      ].join(' ')}

    >

      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-white/80 text-xl text-violet-700 shadow-sm">

        <i className={`bi ${category.icon}`} aria-hidden />

      </div>

      <h3 className="text-lg font-bold text-hub-text">{category.title}</h3>

      <p className="text-sm font-medium text-hub-muted">{category.range_label}</p>

      <p className="mt-2 text-sm text-hub-muted">

        {category.student_count} student{category.student_count === 1 ? '' : 's'} enrolled

      </p>

      <p className="mt-2 flex-1 text-sm text-hub-muted">{category.description}</p>

      <Link

        to={category.path}

        className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-violet-800 hover:text-violet-950"

      >

        Open {category.title.toLowerCase()}

        <i className="bi bi-arrow-right-short text-lg" aria-hidden />

      </Link>

    </article>

  )

}



function RecentReportRow({

  report,

  onDelete,

  busy,

}: {

  report: ReportCardItem

  onDelete: (id: number) => void

  busy: number | null

}) {

  return (

    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center">

      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-violet-100 text-sm font-bold text-violet-800">

        {report.student?.initials || '?'}

      </span>

      <div className="min-w-0 flex-1">

        <h3 className="font-bold text-hub-text">

          {report.student ? `${report.student.first_name} ${report.student.last_name}` : 'Unknown student'}

        </h3>

        <p className="text-sm text-hub-muted">

          Grade {report.student?.grade_display || '—'} · {report.school_year?.name || 'N/A'} ·{' '}

          <span className="font-semibold text-hub-text">{report.quarter}</span>

        </p>

        <p className="text-xs text-hub-muted">{report.generated_at_display || 'Date unavailable'}</p>

        <PublishStatus report={report} />

      </div>

      <div className="flex flex-wrap gap-2">

        {report.urls.history ? (

          <Link

            to={report.urls.history}

            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-hub-text hover:bg-slate-50"

            title="View history"

          >

            <i className="bi bi-clock-history" aria-hidden />

          </Link>

        ) : null}

        <Link

          to={report.urls.view}

          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-hub-text hover:bg-slate-50"

          title="View details"

        >

          <i className="bi bi-eye" aria-hidden />

        </Link>

        <a

          href={reportCardPdfUrl(report.id)}

          target="_blank"

          rel="noopener noreferrer"

          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-hub-text hover:bg-slate-50"

          title="Download PDF"

        >

          <i className="bi bi-file-pdf" aria-hidden />

        </a>

        <button

          type="button"

          disabled={busy === report.id}

          onClick={() => {

            if (window.confirm('Delete this report card? This cannot be undone.')) {

              onDelete(report.id)

            }

          }}

          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 disabled:opacity-60"

          title="Delete"

        >

          <i className="bi bi-trash" aria-hidden />

        </button>

      </div>

    </article>

  )

}



export default function ReportCardsPage() {

  const { user } = useOutletContext<ManagementOutletContext>()

  const [hub, setHub] = useState<ReportCardsHubResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState<string | null>(null)

  const [message, setMessage] = useState<string | null>(null)

  const [busyId, setBusyId] = useState<number | null>(null)



  const isDirector = user.role_canonical === 'Director'



  const load = useCallback(async () => {

    setLoading(true)

    setError(null)

    try {

      setHub(await fetchReportCardsHub())

    } catch (err) {

      setError(err instanceof Error ? err.message : 'Failed to load report cards')

    } finally {

      setLoading(false)

    }

  }, [])



  useEffect(() => {

    void load()

  }, [load])



  async function handleDelete(reportCardId: number) {

    setBusyId(reportCardId)

    setMessage(null)

    setError(null)

    try {

      const result = await deleteReportCard(reportCardId)

      setMessage(result.message)

      await load()

    } catch (err) {

      setError(err instanceof Error ? err.message : 'Failed to delete report card')

    } finally {

      setBusyId(null)

    }

  }



  return (

    <div className="mx-auto max-w-7xl space-y-6 px-1 pb-10 pt-2">

      <header className="rounded-3xl border border-white/80 bg-gradient-to-br from-violet-900 via-violet-800 to-indigo-900 p-6 text-white shadow-lg md:p-8">

        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">

          <div>

            <p className="text-xs font-bold uppercase tracking-[0.2em] text-violet-100/90">Academic reporting</p>

            <h1 className="mt-1 text-3xl font-extrabold tracking-tight">Report cards</h1>

            <p className="mt-2 flex items-center gap-2 text-sm text-violet-50/90">

              <i className="bi bi-file-earmark-text" aria-hidden />

              Generate and manage student report cards by grade category

            </p>

          </div>

          <div className="flex flex-wrap items-center gap-2">

            {isDirector ? (

              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">

                <i className="bi bi-award-fill" aria-hidden />

                Director

              </span>

            ) : (

              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">

                <i className="bi bi-shield-fill" aria-hidden />

                Administrator

              </span>

            )}

            <Link

              to="/management"

              className="inline-flex items-center gap-2 rounded-xl border border-white/30 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"

            >

              <i className="bi bi-house-door" aria-hidden />

              Home

            </Link>

          </div>

        </div>

      </header>



      {(error || message) && (

        <div

          className={[

            'rounded-2xl border px-4 py-3 text-sm font-medium',

            error ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800',

          ].join(' ')}

        >

          {error || message}

        </div>

      )}



      {loading && !hub ? (

        <div className="py-16 text-center text-hub-muted">Loading report cards…</div>

      ) : null}



      {hub ? (

        <>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="list">

            <StatCard icon="bi-people-fill" value={hub.stats.total_students} label="Total students" featured />

            <StatCard icon="bi-file-earmark-check-fill" value={hub.stats.total_reports} label="Report cards generated" />

            {isDirector && hub.stats.pending_parent_approval > 0 ? (

              <StatCard

                icon="bi-hourglass-split"

                value={hub.stats.pending_parent_approval}

                label="Awaiting parent release"

              />

            ) : null}

            <StatCard icon="bi-calendar-range" value={hub.stats.school_years_count} label="School years" />

          </div>



          <section className="space-y-4">

            <div>

              <h2 className="text-xl font-bold text-hub-text">

                <i className="bi bi-grid-3x3-gap-fill mr-2 text-violet-700" aria-hidden />

                Select grade category

              </h2>

              <p className="mt-1 text-sm text-hub-muted">

                Choose a grade band to view students and generate report cards for that range.

              </p>

            </div>

            <div className="grid gap-4 lg:grid-cols-3">

              {hub.categories.map((category) => (

                <CategoryCard key={category.slug} category={category} />

              ))}

            </div>

          </section>



          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">

            <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

              <h2 className="text-base font-bold text-hub-text">

                <i className="bi bi-info-circle-fill mr-2 text-violet-700" aria-hidden />

                Generation workflow

              </h2>

              <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-hub-muted">

                <li>Select a grade category above</li>

                <li>Choose a student from the roster</li>

                <li>Pick school year, classes, and quarters</li>

                <li>Review and generate the PDF report card</li>

                <li>Director approves the official card for the Family Portal</li>

              </ol>

              <ul className="mt-4 space-y-2 text-sm text-hub-text">

                {['Custom class selection', 'Attendance statistics', 'Teacher comments', 'Official or unofficial copies', 'K–3 standards checklists on PDF (1st & 3rd grade)'].map(

                  (item) => (

                    <li key={item} className="flex items-center gap-2">

                      <i className="bi bi-check2-circle text-emerald-600" aria-hidden />

                      {item}

                    </li>

                  ),

                )}

              </ul>

            </aside>



            <QuickActionsPanel hub={hub} />

          </div>



          <section className="space-y-4">

            <div className="flex items-center justify-between gap-3">

              <h2 className="text-xl font-bold text-hub-text">

                <i className="bi bi-clock-history mr-2 text-violet-700" aria-hidden />

                Recently generated

              </h2>

              <span className="text-sm text-hub-muted">Last 10 report cards</span>

            </div>

            {hub.recent_reports.length ? (

              <div className="space-y-3">

                {hub.recent_reports.map((report) => (

                  <RecentReportRow key={report.id} report={report} onDelete={handleDelete} busy={busyId} />

                ))}

              </div>

            ) : (

              <div className="rounded-2xl border border-dashed border-slate-200 px-6 py-14 text-center text-hub-muted">

                <i className="bi bi-inbox mb-2 block text-4xl text-slate-300" aria-hidden />

                <p className="font-semibold text-hub-text">No report cards generated yet</p>

                <p className="mt-1 text-sm">Select a grade category above to get started.</p>

              </div>

            )}

          </section>

        </>

      ) : null}



      <PendingApprovalNotifier enabled={isDirector} />

    </div>

  )

}


