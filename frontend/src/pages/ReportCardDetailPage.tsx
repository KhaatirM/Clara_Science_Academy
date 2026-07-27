import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  approveReportCard,
  fetchReportCardDetail,
  reportCardPdfUrl,
  revokeReportCard,
} from '../api/reportCards'
import { StandardsChecklistCallout } from '../components/reportCards/StandardsChecklistCallout'
import type { ReportCardDetailResponse } from '../types/reportCards'

function gradeStatusClass(percentage: number): string {
  if (percentage >= 90) return 'bg-emerald-100 text-emerald-800'
  if (percentage >= 80) return 'bg-sky-100 text-sky-800'
  if (percentage >= 70) return 'bg-amber-100 text-amber-800'
  return 'bg-red-100 text-red-800'
}

function gradeStatusLabel(percentage: number): string {
  if (percentage >= 90) return 'Excellent'
  if (percentage >= 80) return 'Good'
  if (percentage >= 70) return 'Average'
  return 'Needs improvement'
}

export default function ReportCardDetailPage() {
  const { reportCardId = '' } = useParams()
  const id = Number(reportCardId)

  const [data, setData] = useState<ReportCardDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchReportCardDetail(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load report card.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  async function handleApprove() {
    if (!window.confirm('Approve this report card for the Family Portal?')) return
    setActionBusy(true)
    try {
      const result = await approveReportCard(id)
      setActionMessage(result.message)
      await load()
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Approval failed.')
    } finally {
      setActionBusy(false)
    }
  }

  async function handleRevoke() {
    if (!window.confirm('Remove this report card from the Family Portal?')) return
    setActionBusy(true)
    try {
      const result = await revokeReportCard(id)
      setActionMessage(result.message)
      await load()
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Revoke failed.')
    } finally {
      setActionBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-hub-muted">
        Loading report card…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
        <p>{error || 'Report card not found.'}</p>
        <Link to="/management/report-cards" className="mt-4 inline-block underline">
          Back to report cards
        </Link>
      </div>
    )
  }

  const { report_card: rc, student, school_year: sy } = data

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      {rc.is_official ? (
        rc.director_approved ? (
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4">
            <div>
              <p className="font-bold text-emerald-900">
                <i className="bi bi-check-circle-fill mr-2" aria-hidden />
                Published to Family Portal
              </p>
              {rc.approved_at_display ? (
                <p className="mt-1 text-sm text-emerald-800">
                  Approved {rc.approved_at_display}
                  {rc.approved_by ? ` by ${rc.approved_by}` : ''}
                </p>
              ) : null}
            </div>
            {data.is_director ? (
              <button
                type="button"
                disabled={actionBusy}
                onClick={() => void handleRevoke()}
                className="rounded-xl border border-red-300 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
              >
                Revoke parent access
              </button>
            ) : null}
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4">
            <div>
              <p className="font-bold text-amber-900">Awaiting Director approval</p>
              <p className="mt-1 text-sm text-amber-800">
                Not visible to parents until the Director confirms the final version.
              </p>
            </div>
            {data.is_director ? (
              <button
                type="button"
                disabled={actionBusy}
                onClick={() => void handleApprove()}
                className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
              >
                Approve for parents
              </button>
            ) : (
              <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold">
                Director review required
              </span>
            )}
          </div>
        )
      ) : rc.report_type === 'unofficial' ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-sm text-hub-muted">
          Unofficial copy — not eligible for Family Portal release.
        </div>
      ) : null}

      {actionMessage ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">{actionMessage}</div>
      ) : null}

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            to="/management/report-cards"
            className="text-sm font-semibold text-violet-700 hover:underline"
          >
            <i className="bi bi-arrow-left mr-1" aria-hidden />
            Back to report cards
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-hub-text">Report card details</h1>
          {student ? (
            <p className="text-sm text-hub-muted">
              {student.first_name} {student.last_name} · Grade {student.grade_display}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={reportCardPdfUrl(rc.id)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-800"
          >
            <i className="bi bi-download" aria-hidden />
            Download PDF
          </a>
          {data.urls.history ? (
            <Link
              to={data.urls.history}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold"
            >
              <i className="bi bi-clock-history" aria-hidden />
              History
            </Link>
          ) : null}
        </div>
      </header>

      <StandardsChecklistCallout
        checklist={data.standards_checklist}
        marksSummary={data.standards_marks_summary}
      />

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <p className="text-xs font-bold uppercase text-hub-muted">School year</p>
            <p className="mt-1 font-semibold">{sy?.name || 'N/A'}</p>
            <p className="mt-4 text-xs font-bold uppercase text-hub-muted">Quarter</p>
            <p className="mt-1 font-semibold">{rc.quarter}</p>
            {rc.generated_at_display ? (
              <>
                <p className="mt-4 text-xs font-bold uppercase text-hub-muted">Generated</p>
                <p className="mt-1 text-sm">{rc.generated_at_display}</p>
              </>
            ) : null}
          </div>
          <div>
            <p className="text-xs font-bold uppercase text-hub-muted">Selected classes</p>
            {data.classes.length ? (
              <ul className="mt-2 space-y-2">
                {data.classes.map((c) => (
                  <li key={c.id} className="text-sm">
                    <span className="font-semibold">{c.name}</span>
                    {c.subject ? (
                      <span className="block text-xs text-hub-muted">{c.subject}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-hub-muted">All enrolled classes</p>
            )}
          </div>
        </div>
      </div>

      {data.grades.length ? (
        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-slate-200 px-6 py-4">
            <h2 className="font-bold text-hub-text">
              <i className="bi bi-graph-up mr-2 text-violet-700" aria-hidden />
              Academic performance
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-hub-muted">
                <tr>
                  <th className="px-6 py-3">Subject / class</th>
                  <th className="px-6 py-3 text-center">Grade</th>
                  <th className="px-6 py-3 text-center">Percentage</th>
                  <th className="px-6 py-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.grades.map((row) => (
                  <tr key={row.subject} className="border-t border-slate-100">
                    <td className="px-6 py-3 font-semibold">{row.subject}</td>
                    <td className="px-6 py-3 text-center">
                      <span className="rounded-full bg-violet-100 px-3 py-1 font-bold text-violet-800">
                        {row.letter_grade}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-center font-bold">{row.percentage.toFixed(1)}%</td>
                    <td className="px-6 py-3 text-center">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${gradeStatusClass(row.percentage)}`}
                      >
                        {gradeStatusLabel(row.percentage)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {data.include_attendance && data.attendance.length ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-bold text-hub-text">
            <i className="bi bi-calendar-check mr-2 text-violet-700" aria-hidden />
            Attendance summary
          </h2>
          <div className="mt-4 space-y-6">
            {data.attendance.map((att) => (
              <div key={att.class_name} className="border-b border-slate-100 pb-4 last:border-0">
                <h3 className="font-semibold">{att.class_name}</h3>
                <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ['Present', att.present, 'text-emerald-700'],
                    ['Unexcused', att.unexcused, 'text-red-700'],
                    ['Excused', att.excused, 'text-amber-700'],
                    ['Tardy', att.tardy, 'text-sky-700'],
                  ].map(([label, value, tone]) => (
                    <div key={label} className="rounded-xl bg-slate-50 px-3 py-2">
                      <p className={`text-xl font-bold ${tone}`}>{value}</p>
                      <p className="text-xs text-hub-muted">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {data.include_comments && data.comments.length ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-bold text-hub-text">
            <i className="bi bi-chat-text mr-2 text-violet-700" aria-hidden />
            Teacher comments
          </h2>
          <div className="mt-4 space-y-4">
            {data.comments.map((c, i) => (
              <div key={`${c.class_name}-${i}`} className="rounded-xl bg-slate-50 p-4">
                <p className="text-sm font-semibold text-hub-text">{c.class_name}</p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-hub-muted">{c.comment}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
