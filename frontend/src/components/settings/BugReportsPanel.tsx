import { useCallback, useEffect, useState } from 'react'

import { fetchBugReports, submitBugReport, updateBugReportStatus } from '../../api/settings'
import type { BugReportItem, BugReportsResponse } from '../../types/settings'

const SEVERITY_CLASS: Record<string, string> = {
  low: 'bg-slate-100 text-slate-700',
  medium: 'bg-sky-100 text-sky-800',
  high: 'bg-amber-100 text-amber-900',
  critical: 'bg-red-100 text-red-800',
}

const STATUS_CLASS: Record<string, string> = {
  open: 'bg-red-100 text-red-800',
  in_progress: 'bg-amber-100 text-amber-900',
  resolved: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-slate-100 text-slate-700',
}

export function BugReportsPanel() {
  const [data, setData] = useState<BugReportsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    title: '',
    description: '',
    contact_email: '',
    severity: 'medium',
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchBugReports())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load bug reports.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      const result = await submitBugReport({
        ...form,
        page_url: window.location.href,
      })
      setMessage(result.message)
      setShowForm(false)
      setForm({ title: '', description: '', contact_email: '', severity: 'medium' })
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not submit bug report.')
    } finally {
      setBusy(false)
    }
  }

  async function handleStatusChange(report: BugReportItem, status: string) {
    setBusy(true)
    try {
      await updateBugReportStatus(report.id, status)
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not update status.')
    } finally {
      setBusy(false)
    }
  }

  if (loading && !data) {
    return <div className="text-sm text-hub-muted">Loading bug reports…</div>
  }

  if (error) {
    return <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
  }

  if (!data) return null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-hub-text">Bug reports</h2>
          <p className="text-sm text-hub-muted">Submit issues and track reports you have filed.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm((open) => !open)}
          className="inline-flex items-center gap-2 rounded-xl bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800"
        >
          <i className="bi bi-bug" aria-hidden />
          Report a bug
        </button>
      </div>

      {message ? (
        <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">{message}</div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-4">
        {[
          ['Total', data.summary.total],
          ['Open', data.summary.open],
          ['In progress', data.summary.in_progress],
          ['Resolved', data.summary.resolved],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xl font-bold text-hub-text">{value}</div>
            <div className="text-sm text-hub-muted">{label}</div>
          </div>
        ))}
      </div>

      {showForm ? (
        <form onSubmit={(e) => void handleSubmit(e)} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="font-bold text-hub-text">New bug report</h3>
          <div className="mt-4 grid gap-3">
            <input
              required
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="Short title"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            />
            <textarea
              required
              rows={4}
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Describe what happened and how to reproduce it"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm((prev) => ({ ...prev, contact_email: e.target.value }))}
                placeholder="Contact email (optional)"
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              />
              <select
                value={form.severity}
                onChange={(e) => setForm((prev) => ({ ...prev, severity: e.target.value }))}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="low">Low severity</option>
                <option value="medium">Medium severity</option>
                <option value="high">High severity</option>
                <option value="critical">Critical severity</option>
              </select>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-xl bg-violet-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              Submit report
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-hub-text"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-hub-muted">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Submitted</th>
              {data.can_manage ? <th className="px-4 py-3">Reporter</th> : null}
            </tr>
          </thead>
          <tbody>
            {data.reports.length ? (
              data.reports.map((report) => (
                <tr key={report.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-hub-text">{report.title}</div>
                    <div className="mt-1 max-w-md truncate text-xs text-hub-muted">{report.description}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${SEVERITY_CLASS[report.severity] || SEVERITY_CLASS.medium}`}
                    >
                      {report.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {data.can_manage ? (
                      <select
                        value={report.status}
                        disabled={busy}
                        onChange={(e) => void handleStatusChange(report, e.target.value)}
                        className="rounded-lg border border-slate-200 px-2 py-1 text-xs"
                      >
                        <option value="open">Open</option>
                        <option value="in_progress">In progress</option>
                        <option value="resolved">Resolved</option>
                        <option value="closed">Closed</option>
                      </select>
                    ) : (
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-semibold ${STATUS_CLASS[report.status] || STATUS_CLASS.open}`}
                      >
                        {report.status.replace('_', ' ')}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-hub-muted">
                    {report.created_at ? new Date(report.created_at).toLocaleString() : '—'}
                  </td>
                  {data.can_manage ? (
                    <td className="px-4 py-3 text-hub-muted">{report.reporter_username || '—'}</td>
                  ) : null}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={data.can_manage ? 5 : 4} className="px-4 py-8 text-center text-hub-muted">
                  No bug reports yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
