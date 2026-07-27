import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { deleteReportCard, fetchReportCardHistory, reportCardPdfUrl } from '../api/reportCards'
import type {
  ReportCardHistoryResponse,
  ReportCardHistoryYearGroup,
  ReportCardItem,
} from '../types/reportCards'

function PublishBadge({ report }: { report: ReportCardItem }) {
  if (report.publish_status === 'unofficial') {
    return <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold">Unofficial</span>
  }
  if (report.publish_status === 'published') {
    return (
      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
        Published
      </span>
    )
  }
  return (
    <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
      Pending approval
    </span>
  )
}

function YearReportTable({
  group,
  studentId,
  deletingId,
  onDelete,
}: {
  group: ReportCardHistoryYearGroup
  studentId: number
  deletingId: number | null
  onDelete: (report: ReportCardItem, yearName: string) => void
}) {
  if (!group.report_cards.length) return null

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-bold text-hub-text">
              <i className="bi bi-calendar3 mr-2 text-violet-700" aria-hidden />
              {group.school_year}
            </h3>
            {group.grade_display ? (
              <p className="mt-1 text-sm text-hub-muted">Grade {group.grade_display} that year</p>
            ) : null}
          </div>
          {group.school_year_id ? (
            <Link
              to={`/management/report-cards/generate/${studentId}?school_year_id=${group.school_year_id}`}
              className="inline-flex items-center gap-2 rounded-xl border border-violet-200 px-3 py-2 text-sm font-semibold text-violet-800 hover:bg-violet-50"
            >
              <i className="bi bi-plus-circle" aria-hidden />
              Generate for this year
            </Link>
          ) : null}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-hub-muted">
            <tr>
              <th className="px-6 py-3">Quarter</th>
              <th className="px-6 py-3">Generated</th>
              <th className="px-6 py-3">Classes</th>
              <th className="px-6 py-3">Family Portal</th>
              <th className="px-6 py-3 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {group.report_cards.map((rc) => (
              <tr key={rc.id} className="border-t border-slate-100">
                <td className="px-6 py-4">
                  <span className="rounded-full bg-sky-100 px-3 py-1 font-semibold text-sky-800">
                    {rc.quarter}
                  </span>
                </td>
                <td className="px-6 py-4 text-hub-muted">{rc.generated_at_long || 'N/A'}</td>
                <td className="px-6 py-4">{rc.class_count_label}</td>
                <td className="px-6 py-4">
                  <PublishBadge report={rc} />
                </td>
                <td className="px-6 py-4">
                  <div className="flex justify-center gap-2">
                    <Link
                      to={rc.urls.view}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 hover:bg-slate-50"
                      title="View details"
                    >
                      <i className="bi bi-eye" aria-hidden />
                    </Link>
                    <a
                      href={reportCardPdfUrl(rc.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 hover:bg-slate-50"
                      title="Download PDF"
                    >
                      <i className="bi bi-download" aria-hidden />
                    </a>
                    <button
                      type="button"
                      disabled={deletingId === rc.id}
                      onClick={() => void onDelete(rc, group.school_year)}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-50"
                      title="Delete"
                    >
                      <i className="bi bi-trash" aria-hidden />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default function ReportCardHistoryPage() {
  const { studentId = '' } = useParams()
  const id = Number(studentId)

  const [data, setData] = useState<ReportCardHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchReportCardHistory(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load history.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  async function handleDelete(report: ReportCardItem, yearName: string) {
    const label = `${report.quarter} report card from ${yearName}`
    if (!window.confirm(`Delete ${label}? This cannot be undone.`)) return
    setDeletingId(report.id)
    try {
      await deleteReportCard(report.id)
      await load()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Delete failed.')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-hub-muted">
        Loading report card history…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
        <p>{error || 'Student not found.'}</p>
        <Link to="/management/report-cards" className="mt-4 inline-block underline">
          Back to report cards
        </Link>
      </div>
    )
  }

  const { student } = data
  const yearsWithoutCards = data.school_years.filter((year) => year.report_count === 0)

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            to="/management/report-cards"
            className="text-sm font-semibold text-violet-700 hover:underline"
          >
            <i className="bi bi-arrow-left mr-1" aria-hidden />
            Back to all report cards
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-hub-text">Report card history</h1>
          <p className="text-sm text-hub-muted">
            All report cards for {student.first_name} {student.last_name}
          </p>
        </div>
        <Link
          to={data.urls.generate}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          <i className="bi bi-plus-circle" aria-hidden />
          Generate new report card
        </Link>
      </header>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-violet-100 text-lg font-bold text-violet-800">
              {student.initials}
            </span>
            <div>
              <h2 className="text-xl font-bold text-hub-text">
                {student.first_name} {student.last_name}
              </h2>
              <p className="text-sm text-hub-muted">
                ID: {student.student_id || 'N/A'} · Current grade {student.grade_display}
              </p>
            </div>
          </div>
          <span className="rounded-full bg-violet-100 px-4 py-2 text-sm font-bold text-violet-800">
            {data.total_count} report card{data.total_count !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {data.school_years.length ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-hub-text">School years with this student</h2>
          <p className="mt-1 text-sm text-hub-muted">
            Generate or review report cards for each year the student was enrolled.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {data.school_years.map((year) => (
              <article
                key={year.id}
                className="rounded-xl border border-slate-200 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-hub-text">{year.name}</p>
                    <p className="text-sm text-hub-muted">
                      Grade {year.grade_display} · {year.class_count} class
                      {year.class_count !== 1 ? 'es' : ''} · {year.report_count} report card
                      {year.report_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <span
                    className={[
                      'rounded-full px-2.5 py-1 text-xs font-semibold',
                      year.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700',
                    ].join(' ')}
                  >
                    {year.status_label}
                  </span>
                </div>
                <Link
                  to={year.generate_url}
                  className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-violet-700 hover:underline"
                >
                  <i className="bi bi-file-earmark-text" aria-hidden />
                  {year.report_count ? 'Generate another' : 'Generate report card'}
                </Link>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {yearsWithoutCards.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-hub-muted">
          {yearsWithoutCards.length} enrolled year{yearsWithoutCards.length !== 1 ? 's have' : ' has'}{' '}
          no report cards yet. Use Generate above to create one.
        </div>
      ) : null}

      {data.report_cards_by_year.length ? (
        data.report_cards_by_year.map((group) => (
          <YearReportTable
            key={group.school_year}
            group={group}
            studentId={student.id}
            deletingId={deletingId}
            onDelete={handleDelete}
          />
        ))
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-hub-muted">
          No report cards yet for this student.
        </div>
      )}
    </div>
  )
}
