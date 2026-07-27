import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { approveReportCard, deleteReportCard, fetchPendingReportCards, reportCardPdfUrl } from '../../api/reportCards'
import type { ReportCardItem } from '../../types/reportCards'

export default function PendingApprovalNotifier({ enabled }: { enabled: boolean }) {
  const [total, setTotal] = useState(0)
  const [reports, setReports] = useState<ReportCardItem[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!enabled) return
    try {
      const data = await fetchPendingReportCards()
      setTotal(data.total)
      setReports(data.report_cards)
    } catch {
      /* ignore — notifier is non-blocking */
    }
  }, [enabled])

  useEffect(() => {
    void load()
  }, [load])

  async function handleApprove(reportCardId: number) {
    if (!window.confirm('Approve this report card for the Family Portal?')) return
    setBusyId(reportCardId)
    setMessage(null)
    setError(null)
    try {
      const result = await approveReportCard(reportCardId)
      setMessage(result.message)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve report card')
    } finally {
      setBusyId(null)
    }
  }

  async function handleDelete(reportCardId: number) {
    if (!window.confirm('Delete this report card? This cannot be undone.')) return
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

  if (!enabled || total <= 0) return null

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex max-w-xs items-center gap-3 rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-white px-4 py-3 text-left shadow-lg transition hover:shadow-xl"
        aria-label={`${total} report card${total === 1 ? '' : 's'} pending approval. Open queue.`}
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white shadow-sm">
          <i className="bi bi-hourglass-split text-lg" aria-hidden />
        </span>
        <span className="min-w-0">
          <span className="block text-sm font-bold text-amber-950">Pending approval</span>
          <span className="block text-xs text-amber-800">
            {total} official report card{total === 1 ? '' : 's'} awaiting release
          </span>
        </span>
        <i className="bi bi-chevron-up ml-1 text-amber-700" aria-hidden />
      </button>

      {modalOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center"
          onClick={() => setModalOpen(false)}
        >
          <div
            className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
            role="dialog"
            aria-modal
            aria-labelledby="pending-approval-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-amber-50 px-5 py-4">
              <div>
                <h2 id="pending-approval-title" className="text-lg font-bold text-hub-text">
                  <i className="bi bi-hourglass-split mr-2 text-amber-700" aria-hidden />
                  Pending approval
                </h2>
                <p className="mt-1 text-sm text-hub-muted">
                  Official report cards awaiting Director approval before Family Portal release.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-hub-muted hover:bg-white"
                aria-label="Close"
              >
                <i className="bi bi-x-lg" aria-hidden />
              </button>
            </div>

            {(error || message) && (
              <div
                className={[
                  'mx-5 mt-4 rounded-xl border px-4 py-2 text-sm',
                  error ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800',
                ].join(' ')}
              >
                {error || message}
              </div>
            )}

            <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
              {reports.length ? (
                reports.map((report) => (
                  <article
                    key={report.id}
                    className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-4 sm:flex-row sm:items-center"
                  >
                    <div className="min-w-0 flex-1">
                      <h3 className="font-bold text-hub-text">
                        {report.student
                          ? `${report.student.first_name} ${report.student.last_name}`
                          : 'Unknown student'}
                      </h3>
                      <p className="text-sm text-hub-muted">
                        {report.school_year?.name || 'N/A'} · {report.quarter} · Grade{' '}
                        {report.student?.grade_display || '—'}
                      </p>
                      <p className="text-xs text-hub-muted">{report.generated_at_display || 'Date unavailable'}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={busyId === report.id}
                        onClick={() => void handleApprove(report.id)}
                        className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800 disabled:opacity-60"
                      >
                        <i className="bi bi-check-circle-fill" aria-hidden />
                        Approve
                      </button>
                      <Link
                        to={report.urls.view}
                        onClick={() => setModalOpen(false)}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white hover:bg-slate-50"
                        title="View details"
                      >
                        <i className="bi bi-eye" aria-hidden />
                      </Link>
                      <a
                        href={reportCardPdfUrl(report.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white hover:bg-slate-50"
                        title="PDF"
                      >
                        <i className="bi bi-file-pdf" aria-hidden />
                      </a>
                      <button
                        type="button"
                        disabled={busyId === report.id}
                        onClick={() => void handleDelete(report.id)}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-rose-200 bg-white text-rose-700 hover:bg-rose-50 disabled:opacity-60"
                        title="Delete"
                      >
                        <i className="bi bi-trash" aria-hidden />
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <p className="py-8 text-center text-sm text-hub-muted">No report cards pending approval.</p>
              )}
            </div>

            <div className="border-t border-slate-200 px-5 py-3 text-right">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
