import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchTechDashboard, postTechSystemAction } from '../api/tech'
import {
  ManagementPageHero,
  ManagementPageShell,
} from '../components/layout/ManagementPageShell'

const btnPrimary =
  'inline-flex items-center justify-center rounded-xl border border-teal-700 bg-gradient-to-br from-teal-700 to-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-md hover:from-teal-800'
const btnMuted =
  'inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50'

export function TechHomePage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTechDashboard())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function runQuick(action: string) {
    if (!window.confirm(`Run ${action.replace('_', ' ')}?`)) return
    setBusy(true)
    setMessage(null)
    try {
      const path =
        action === 'backup' ? 'backup' : action === 'integrity' ? 'integrity' : 'clear-cache'
      const res = await postTechSystemAction(path)
      setMessage(res.message || 'Done')
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  const maintenanceOn = Boolean(data?.maintenance?.is_active)

  return (
    <ManagementPageShell>
      {loading && !data ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading tech home…</div>
      ) : error && !data ? (
        <div className="alert alert-danger">{error}</div>
      ) : data ? (
        <>
          <ManagementPageHero className="mb-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
                  Tech · Home
                </p>
                <h1 className="mb-0 text-3xl font-bold tracking-tight">Tech portal</h1>
                <p className="mb-0 mt-2 max-w-xl text-sm spa-mgmt-hero-muted">
                  Welcome, {data.username}. Manage devices, logs, bugs, and system health.
                </p>
              </div>
              <span
                className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${
                  maintenanceOn ? 'bg-amber-300 text-amber-950' : 'bg-emerald-300/90 text-emerald-950'
                }`}
              >
                <i className={`bi ${maintenanceOn ? 'bi-tools' : 'bi-check-circle'}`} aria-hidden />
                {maintenanceOn ? 'Maintenance on' : 'Portal online'}
              </span>
            </div>
          </ManagementPageHero>

          {maintenanceOn ? (
            <div className="mb-4 rounded-2xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-amber-950">
              <strong>Maintenance mode active.</strong>{' '}
              {data.maintenance.maintenance_message || data.maintenance.reason}
              {data.maintenance.end_display ? ` · Ends ${data.maintenance.end_display}` : ''}
              <div className="mt-2">
                <Link
                  to="/tech/system"
                  className="text-sm font-semibold text-amber-950 underline-offset-2 hover:underline"
                >
                  Open System → Maintenance
                </Link>
              </div>
            </div>
          ) : null}

          {message ? (
            <div className="spa-mgmt-insight mb-4 px-4 py-3 text-sm font-medium">{message}</div>
          ) : null}

          <section className="spa-mgmt-card mb-5 overflow-hidden shadow-sm">
            <div className="spa-mgmt-accent-bar" />
            <div className="p-4 md:p-5">
              <div className="mb-3 flex items-center gap-3">
                <span className="spa-mgmt-avatar h-9 w-9 text-sm">
                  <i className="bi bi-lightning-charge" aria-hidden />
                </span>
                <div>
                  <h2 className="mb-0 text-base font-bold text-hub-text">Quick actions</h2>
                  <p className="mb-0 text-sm text-hub-muted">Common server tasks without leaving Home.</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {(data.quick_actions || []).map((a: any) => (
                  <button
                    key={a.id}
                    type="button"
                    className="spa-mgmt-btn-ghost px-4 py-2.5 text-sm disabled:opacity-60"
                    disabled={busy}
                    onClick={() => void runQuick(a.action)}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {(data.cards || []).map((card: any) => (
              <Link
                key={card.id}
                to={String(card.url || '').replace(/^\/app/, '')}
                className="spa-mgmt-card group overflow-hidden text-hub-text no-underline shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="spa-mgmt-accent-bar" />
                <div className="p-4">
                  <span className="spa-mgmt-avatar mb-3 h-10 w-10 text-base">
                    <i className={`bi ${card.icon}`} aria-hidden />
                  </span>
                  <h3 className="mb-1 text-base font-bold">{card.title}</h3>
                  <p className="mb-0 text-sm text-hub-muted">{card.blurb}</p>
                </div>
              </Link>
            ))}
          </div>
        </>
      ) : null}
    </ManagementPageShell>
  )
}

export { btnPrimary, btnMuted }
