import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { bulkReviewExtensionRequests, fetchExtensionsHub, reviewExtensionRequest } from '../api/extensions'
import type { ExtensionRequestItem } from '../types/extensions'

type StatusTab = 'pending' | 'approved' | 'rejected' | 'all'

function formatDate(iso: string | null) {
  if (!iso) return 'N/A'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'N/A'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function StatTab({
  active,
  tone,
  icon,
  count,
  label,
  onClick,
}: {
  active: boolean
  tone: string
  icon: string
  count: number
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-1 items-center gap-3 rounded-2xl border px-4 py-3 text-left transition ${
        active ? `border-teal-400 bg-white shadow-md ring-2 ring-teal-500/20` : 'border-slate-200 bg-white/80 hover:border-teal-300'
      }`}
    >
      <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${tone}`}>
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-2xl font-extrabold text-hub-text">{count}</div>
        <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </button>
  )
}

function ExtensionCard({
  item,
  selectable,
  selected,
  onToggle,
  onApprove,
  onReject,
}: {
  item: ExtensionRequestItem
  selectable?: boolean
  selected?: boolean
  onToggle?: () => void
  onApprove?: () => void
  onReject?: () => void
}) {
  const statusTone =
    item.status === 'Pending'
      ? 'bg-amber-100 text-amber-900'
      : item.status === 'Approved'
        ? 'bg-emerald-100 text-emerald-900'
        : 'bg-red-100 text-red-800'

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex gap-3">
        {selectable ? (
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-600"
            aria-label={`Select request for ${item.student.display_name}`}
          />
        ) : null}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="font-bold text-hub-text">
                <i className="bi bi-person-circle me-1 text-hub-muted" aria-hidden />
                {item.student.display_name}
              </div>
              <div className="mt-1 text-sm text-hub-muted">
                <i className="bi bi-journal-text me-1" aria-hidden />
                <strong className="text-hub-text">{item.assignment.title}</strong>
              </div>
              <div className="text-sm text-hub-muted">
                <i className="bi bi-book me-1" aria-hidden />
                {item.class.name}
              </div>
            </div>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${statusTone}`}>{item.status}</span>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div>
              <div className="text-[0.65rem] font-bold uppercase text-hub-muted">Current due</div>
              <div className="text-sm font-semibold text-hub-text">{formatDate(item.current_due_date)}</div>
            </div>
            <div>
              <div className="text-[0.65rem] font-bold uppercase text-hub-muted">Requested due</div>
              <div className="text-sm font-semibold text-teal-800">{formatDate(item.requested_due_date)}</div>
            </div>
            <div>
              <div className="text-[0.65rem] font-bold uppercase text-hub-muted">
                {item.status === 'Approved' ? 'Approved' : item.status === 'Rejected' ? 'Reviewed' : 'Submitted'}
              </div>
              <div className="text-sm font-semibold text-hub-text">
                {formatDate(item.status === 'Pending' ? item.requested_at : item.reviewed_at)}
              </div>
            </div>
          </div>

          {item.reason ? (
            <div className="mt-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-hub-muted">
              <strong className="block text-xs uppercase text-hub-muted">Student reason</strong>
              {item.reason}
            </div>
          ) : null}

          {item.review_notes ? (
            <div className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm text-emerald-950">
              <strong className="block text-xs uppercase">Review notes</strong>
              {item.review_notes}
            </div>
          ) : null}

          {onApprove && onReject ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={onApprove}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700"
              >
                <i className="bi bi-check-circle me-1" aria-hidden />
                Approve
              </button>
              <button
                type="button"
                onClick={onReject}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-700"
              >
                <i className="bi bi-x-circle me-1" aria-hidden />
                Reject
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </article>
  )
}

export function ExtensionRequestsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchExtensionsHub>> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<StatusTab>('pending')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [reviewModal, setReviewModal] = useState<{
    ids: number[]
    action: 'approve' | 'reject'
  } | null>(null)
  const [reviewNotes, setReviewNotes] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchExtensionsHub()
      setData(res)
      setSelected(new Set())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load extension requests')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const tabItems = useMemo(() => {
    if (!data) return []
    const base =
      tab === 'pending'
        ? data.pending
        : tab === 'approved'
          ? data.approved
          : tab === 'rejected'
            ? data.rejected
            : data.items
    const q = search.trim().toLowerCase()
    if (!q) return base
    return base.filter((i) => i.search_text.includes(q))
  }, [data, tab, search])

  const pendingVisible = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    return q ? data.pending.filter((i) => i.search_text.includes(q)) : data.pending
  }, [data, search])

  const submitReview = async () => {
    if (!reviewModal) return
    setBusy(true)
    setToast(null)
    try {
      const res =
        reviewModal.ids.length === 1
          ? await reviewExtensionRequest(reviewModal.ids[0], reviewModal.action, reviewNotes)
          : await bulkReviewExtensionRequests(reviewModal.ids, reviewModal.action, reviewNotes)
      setToast(res.message)
      setReviewModal(null)
      setReviewNotes('')
      await load()
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Review failed')
    } finally {
      setBusy(false)
    }
  }

  const toggleAllPending = (checked: boolean) => {
    setSelected(checked ? new Set(pendingVisible.map((i) => i.id)) : new Set())
  }

  return (
    <div className="rounded-3xl bg-gradient-to-br from-indigo-50 via-slate-50 to-slate-100 p-5 md:p-6">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="flex gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-teal-700 text-white shadow">
            <i className="bi bi-clock-history text-xl" aria-hidden />
          </span>
          <div>
            <h1 className="text-2xl font-extrabold text-hub-text">Extension requests</h1>
            <p className="text-sm text-hub-muted">
              Review student due-date extension requests
              {data?.meta.active_school_year_name ? ` for ${data.meta.active_school_year_name}` : ''}.
            </p>
          </div>
        </div>
        <Link
          to="/management/assignments"
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-teal-500"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          Assignments
        </Link>
      </header>

      {toast ? (
        <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-4 py-2.5 text-sm text-teal-900">{toast}</div>
      ) : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div>
      ) : null}

      {data ? (
        <div className="mb-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <StatTab
            active={tab === 'pending'}
            tone="bg-amber-100 text-amber-800"
            icon="bi-hourglass-split"
            count={data.stats.pending}
            label="Pending"
            onClick={() => setTab('pending')}
          />
          <StatTab
            active={tab === 'approved'}
            tone="bg-emerald-100 text-emerald-800"
            icon="bi-check-circle-fill"
            count={data.stats.approved}
            label="Approved"
            onClick={() => setTab('approved')}
          />
          <StatTab
            active={tab === 'rejected'}
            tone="bg-red-100 text-red-700"
            icon="bi-x-circle-fill"
            count={data.stats.rejected}
            label="Rejected"
            onClick={() => setTab('rejected')}
          />
          <StatTab
            active={tab === 'all'}
            tone="bg-slate-100 text-slate-700"
            icon="bi-inboxes"
            count={data.stats.total}
            label="All requests"
            onClick={() => setTab('all')}
          />
        </div>
      ) : null}

      <section className="mb-4 rounded-2xl border border-white/90 bg-white p-4 shadow-lg">
        <div className="flex overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
          <span className="flex items-center px-3 text-hub-muted" aria-hidden>
            <i className="bi bi-search" />
          </span>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search student, assignment, or class…"
            className="min-w-0 flex-1 border-0 bg-transparent py-2.5 pr-3 text-sm focus:outline-none"
          />
        </div>
        <p className="mt-2 text-xs text-hub-muted">
          Showing <strong>{tabItems.length}</strong> in this view
        </p>
      </section>

      {tab === 'pending' && pendingVisible.length > 0 ? (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
          <label className="flex items-center gap-2 text-sm font-semibold text-amber-950">
            <input
              type="checkbox"
              checked={selected.size > 0 && selected.size === pendingVisible.length}
              onChange={(e) => toggleAllPending(e.target.checked)}
            />
            Select all
          </label>
          <span className="text-sm text-amber-900">{selected.size} selected</span>
          <div className="ms-auto flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selected.size || busy}
              onClick={() => setReviewModal({ ids: [...selected], action: 'approve' })}
              className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Approve selected
            </button>
            <button
              type="button"
              disabled={!selected.size || busy}
              onClick={() => setReviewModal({ ids: [...selected], action: 'reject' })}
              className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Reject selected
            </button>
          </div>
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl bg-white p-12 text-center text-hub-muted shadow-lg">Loading…</div>
      ) : !data?.meta.has_active_school_year ? (
        <div className="rounded-2xl bg-white p-12 text-center text-hub-muted shadow-lg">No active school year.</div>
      ) : tabItems.length === 0 ? (
        <div className="rounded-2xl bg-white p-12 text-center text-hub-muted shadow-lg">
          <i className="bi bi-inbox mb-2 block text-3xl text-slate-300" aria-hidden />
          No extension requests in this view.
        </div>
      ) : (
        <div className="space-y-3">
          {tabItems.map((item) => (
            <ExtensionCard
              key={item.id}
              item={item}
              selectable={tab === 'pending' && item.status === 'Pending'}
              selected={selected.has(item.id)}
              onToggle={() =>
                setSelected((prev) => {
                  const next = new Set(prev)
                  if (next.has(item.id)) next.delete(item.id)
                  else next.add(item.id)
                  return next
                })
              }
              onApprove={
                item.status === 'Pending'
                  ? () => setReviewModal({ ids: [item.id], action: 'approve' })
                  : undefined
              }
              onReject={
                item.status === 'Pending'
                  ? () => setReviewModal({ ids: [item.id], action: 'reject' })
                  : undefined
              }
            />
          ))}
        </div>
      )}

      {reviewModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
            <h2 className="text-lg font-bold text-hub-text">
              {reviewModal.action === 'approve' ? 'Approve' : 'Reject'}{' '}
              {reviewModal.ids.length > 1 ? `${reviewModal.ids.length} requests` : 'request'}
            </h2>
            <label className="mt-3 block text-sm font-semibold text-hub-muted" htmlFor="review-notes">
              Notes (optional)
            </label>
            <textarea
              id="review-notes"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setReviewModal(null)}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void submitReview()}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold text-white ${
                  reviewModal.action === 'approve' ? 'bg-emerald-600' : 'bg-red-600'
                }`}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
