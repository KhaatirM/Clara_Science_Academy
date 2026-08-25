import { useEffect, useState } from 'react'
import type { AppVersionInfo } from '../../types/session'

const SESSION_KEY = 'spaUpdateModalShownAug25_2026_v7'

const LATEST_UPDATES: Array<{ title: string; body: string }> = [
  {
    title: 'Laptop color on devices',
    body: 'When adding or editing a laptop, choose Black, Silver, or Black Carbon. Tablets do not use a color field. Inventory lists show color for laptops, and CSV import includes color for laptops only.',
  },
  {
    title: 'Archived students stay off class lists',
    body: 'Graduated, withdrawn, and removed students no longer appear when grading, taking attendance, managing groups, picking assistants, or other day-to-day class work.',
  },
  {
    title: 'Student assistants: 2 per active year',
    body: 'A student may assist at most two classes in the active school year. Closed-year assignments do not count, and archived students cannot be selected.',
  },
  {
    title: 'Assignment create returns to Assignments',
    body: 'After creating an assignment (including multi-class), staff land on the Assignments hub instead of Home. PDF create also has clearer file drag-and-drop.',
  },
]

export function PortalUpdatesHost({ version }: { version?: AppVersionInfo | null }) {
  const [open, setOpen] = useState(false)
  const [versionOpen, setVersionOpen] = useState(false)

  const display = version?.display || 'v 2.516.1'
  const releaseLabel = version?.release_label || 'August 25, 2026'
  const origin = version?.origin || '0.0.0'
  const updatesEstimate = version?.updates_estimate ?? 2685
  const productName = version?.product_name || 'Clara Science Academy Portal'

  useEffect(() => {
    if (sessionStorage.getItem(SESSION_KEY)) return
    const timer = window.setTimeout(() => {
      setOpen(true)
      sessionStorage.setItem(SESSION_KEY, 'true')
    }, 600)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <>
      <button
        type="button"
        className="spa-version-badge fixed bottom-4 right-4 z-[1080] inline-flex items-center gap-2 rounded-full border border-teal-700/20 bg-teal-800 px-3.5 py-2 text-sm font-semibold text-white shadow-lg shadow-teal-900/25 transition hover:bg-teal-700"
        aria-label={`Portal version ${display}`}
        onClick={() => setVersionOpen(true)}
      >
        <i className="bi bi-layers-fill" aria-hidden />
        <span>{display}</span>
      </button>

      {versionOpen ? (
        <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-slate-900/45 p-4" role="presentation">
          <div
            className="w-full max-w-sm overflow-hidden rounded-2xl bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="spa-version-title"
          >
            <div className="bg-gradient-to-br from-teal-800 to-teal-600 px-5 py-4 text-white">
              <p className="mb-1 text-[0.7rem] font-bold uppercase tracking-[0.16em] text-teal-100">Release info</p>
              <h2 id="spa-version-title" className="text-lg font-extrabold">
                {productName}
              </h2>
            </div>
            <div className="space-y-3 px-5 py-4 text-sm text-slate-700">
              <div className="inline-flex rounded-full bg-teal-50 px-3 py-1 text-sm font-bold text-teal-900">
                {display}
              </div>
              <p className="mb-0">
                <span className="text-hub-muted">Started at</span> <strong>v {origin}</strong>
              </p>
              <p className="mb-0">
                <span className="text-hub-muted">Improvements</span>{' '}
                <strong>{updatesEstimate.toLocaleString()}+</strong> updates shipped
              </p>
              <p className="mb-0">
                <span className="text-hub-muted">Release window</span> <strong>{releaseLabel}</strong>
              </p>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">
              <button
                type="button"
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => setVersionOpen(false)}
              >
                Close
              </button>
              <button
                type="button"
                className="rounded-xl bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                onClick={() => {
                  setVersionOpen(false)
                  setOpen(true)
                }}
              >
                <i className="bi bi-megaphone me-1" aria-hidden />
                Latest changes
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {open ? (
        <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-slate-900/45 p-4" role="presentation">
          <div
            className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="spa-updates-title"
          >
            <div className="flex items-start justify-between gap-3 bg-gradient-to-br from-teal-800 to-teal-600 px-5 py-4 text-white">
              <div>
                <h2 id="spa-updates-title" className="text-lg font-extrabold">
                  System Updates
                </h2>
                <p className="mb-0 text-sm text-teal-100">
                  Latest improvements · {releaseLabel} · {display}
                </p>
              </div>
              <button
                type="button"
                className="rounded-lg p-1.5 text-white/80 hover:bg-white/10 hover:text-white"
                aria-label="Close"
                onClick={() => setOpen(false)}
              >
                <i className="bi bi-x-lg" aria-hidden />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
              <div className="rounded-2xl border border-teal-100 bg-teal-50/70 p-4">
                <h3 className="mb-2 text-sm font-bold text-teal-950">
                  Security, Reports &amp; Classroom – {releaseLabel}
                </h3>
                <p className="mb-0 text-sm text-teal-900/90">
                  Idle auto sign-out, grade-3 report PDF fix, grade-filtered class rosters, and
                  school-managed Google Classroom lifecycle.
                </p>
              </div>
              <ul className="m-0 list-none space-y-3 p-0">
                {LATEST_UPDATES.map((item) => (
                  <li key={item.title} className="rounded-xl border border-slate-200 bg-slate-50/80 px-3.5 py-3">
                    <p className="mb-1 flex items-start gap-2 text-sm font-semibold text-hub-text">
                      <i className="bi bi-check-circle-fill mt-0.5 text-teal-600" aria-hidden />
                      {item.title}
                    </p>
                    <p className="mb-0 pl-6 text-sm text-hub-muted">{item.body}</p>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex justify-end border-t border-slate-100 px-5 py-3">
              <button
                type="button"
                className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                onClick={() => setOpen(false)}
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
