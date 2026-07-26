import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchTechDashboard, postTechSystemAction } from '../api/tech'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'

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

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading tech home…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <>
              <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-teal-800 via-teal-700 to-cyan-600 px-4 py-6 text-white shadow-sm md:px-6">
                <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Tech portal</h1>
                <p className="mb-0 mt-1 text-teal-50/90">
                  Welcome, {data.username}. Manage devices, logs, and system health.
                </p>
              </section>

              {data.maintenance?.is_active ? (
                <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-amber-950">
                  <strong>Maintenance mode active.</strong>{' '}
                  {data.maintenance.maintenance_message || data.maintenance.reason}
                  {data.maintenance.end_display ? ` · Ends ${data.maintenance.end_display}` : ''}
                </div>
              ) : null}

              {message ? (
                <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
                  {message}
                </div>
              ) : null}

              <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="mb-3 text-base font-bold">Quick actions</h2>
                <div className="flex flex-wrap gap-2">
                  {(data.quick_actions || []).map((a: any) => (
                    <button
                      key={a.id}
                      type="button"
                      className={btnMuted}
                      disabled={busy}
                      onClick={() => void runQuick(a.action)}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              </section>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {(data.cards || []).map((card: any) => (
                  <Link
                    key={card.id}
                    to={String(card.url || '').replace(/^\/app/, '')}
                    className="rounded-2xl border border-slate-200 bg-white p-4 text-slate-900 no-underline shadow-sm transition hover:border-teal-300 hover:shadow-md"
                  >
                    <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-teal-700 text-white">
                      <i className={`bi ${card.icon}`} aria-hidden />
                    </div>
                    <h3 className="mb-1 text-base font-bold">{card.title}</h3>
                    <p className="mb-0 text-sm text-hub-muted">{card.blurb}</p>
                  </Link>
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

export { btnPrimary, btnMuted }
