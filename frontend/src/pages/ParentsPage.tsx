import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { fetchParentsHub, provisionAllParentLogins } from '../api/parents'
import type { ManagementOutletContext } from '../types/layout'
import type { ParentAccountItem, ParentsHubStats } from '../types/parents'

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
          ? 'border-rose-200 bg-gradient-to-br from-rose-50 to-white'
          : 'border-white/90 bg-white/95',
      ].join(' ')}
      role="listitem"
    >
      <span
        className={[
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-base',
          featured ? 'bg-rose-100 text-rose-700' : 'bg-teal-100 text-teal-800',
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

function WorkflowStep({ num, title, body }: { num: number; title: string; body: string }) {
  return (
    <div className="flex gap-3 rounded-xl border border-slate-200 bg-white/80 p-4">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-700 text-sm font-bold text-white">
        {num}
      </span>
      <div>
        <strong className="text-sm text-hub-text">{title}</strong>
        <p className="mt-1 text-sm text-hub-muted">{body}</p>
      </div>
    </div>
  )
}

function ParentAccountsTable({ items }: { items: ParentAccountItem[] }) {
  if (!items.length) {
    return (
      <div className="px-6 py-12 text-center text-hub-muted">
        <i className="bi bi-people mb-2 block text-3xl text-slate-300" aria-hidden />
        <p className="font-semibold text-hub-text">No parent portal accounts yet</p>
        <p className="mt-1 text-sm">
          Use <em>Provision all parent logins</em> or provision from a student record under Family portal
          access.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
            <th className="px-5 py-3">Account</th>
            <th className="px-5 py-3">Email</th>
            <th className="px-5 py-3">Linked children</th>
            <th className="px-5 py-3 text-right">Links</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/80">
              <td className="px-5 py-3">
                <div className="flex items-center gap-3">
                  <span
                    className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-rose-500 to-orange-400 text-sm font-bold text-white"
                    aria-hidden
                  >
                    {row.initial}
                  </span>
                  <div>
                    <code className="text-sm font-semibold text-hub-text">{row.username}</code>
                    <div className="text-xs text-hub-muted">Parent</div>
                  </div>
                </div>
              </td>
              <td className="px-5 py-3 text-hub-muted">{row.email || '—'}</td>
              <td className="px-5 py-3">
                {row.children.length ? (
                  <div className="flex flex-wrap gap-1.5">
                    {row.children.map((child) => (
                      <span
                        key={child.id}
                        className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-900"
                      >
                        <i className="bi bi-person text-[0.65rem]" aria-hidden />
                        {child.display_name}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-hub-muted">None linked</span>
                )}
              </td>
              <td className="px-5 py-3 text-right">
                <span className="inline-flex min-w-[1.75rem] justify-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-700">
                  {row.link_count}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ParentsPage() {
  const { user } = useOutletContext<ManagementOutletContext>()
  const navigate = useNavigate()
  const isDirector = user.role_canonical === 'Director'
  const [items, setItems] = useState<ParentAccountItem[]>([])
  const [stats, setStats] = useState<ParentsHubStats>({
    parent_accounts: 0,
    students_with_parent_email: 0,
    total_child_links: 0,
    students_not_linked: 0,
  })
  const [canProvision, setCanProvision] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [provisioning, setProvisioning] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchParentsHub()
      setItems(data.items)
      setStats(data.stats)
      setCanProvision(data.meta.can_provision)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load Family Portal data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleProvisionAll = async () => {
    if (
      !window.confirm(
        'Create parent accounts for all students with parent emails on file? Existing accounts will be linked where possible.',
      )
    ) {
      return
    }
    setProvisioning(true)
    setActionMessage(null)
    try {
      const result = await provisionAllParentLogins()
      let msg = result.message || 'Provisioning complete.'
      if (result.errors?.length) {
        msg += ` Warnings: ${result.errors.join('; ')}`
      }
      setActionMessage(msg)
      void load()
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Provisioning failed')
    } finally {
      setProvisioning(false)
    }
  }

  return (
    <div className="rounded-3xl bg-gradient-to-br from-rose-50 via-orange-50/70 to-amber-50 p-5 md:p-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.14em] text-hub-muted">Management</p>
          <h1 className="mt-1 flex items-center gap-2 text-3xl font-extrabold tracking-tight text-hub-text">
            <i className="bi bi-heart-fill text-rose-500" aria-hidden />
            Family Portal
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-hub-muted">
            Provision parent logins, link guardians to students, and release report cards to families.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isDirector ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-bold text-indigo-800">
              <i className="bi bi-shield-fill" aria-hidden />
              Administrator
            </span>
          ) : null}
          {canProvision ? (
            <button
              type="button"
              onClick={() => void handleProvisionAll()}
              disabled={provisioning}
              className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br from-rose-500 to-orange-400 px-3.5 py-2 text-[0.82rem] font-semibold text-white shadow-sm hover:brightness-105 disabled:opacity-60"
            >
              <i className="bi bi-person-plus" aria-hidden />
              {provisioning ? 'Provisioning…' : 'Provision all parent logins'}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => navigate('/management')}
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-[0.82rem] font-semibold text-slate-700 hover:border-teal-600 hover:text-teal-800"
          >
            <i className="bi bi-house-door" aria-hidden />
            Dashboard
          </button>
        </div>
      </header>

      {actionMessage ? (
        <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          {actionMessage}
        </div>
      ) : null}

      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" role="list">
        <StatCard icon="bi-people-fill" value={stats.parent_accounts} label="Parent accounts" featured />
        <StatCard
          icon="bi-envelope-check"
          value={stats.students_with_parent_email}
          label="Students with parent email"
        />
        <StatCard icon="bi-link-45deg" value={stats.total_child_links} label="Parent–child links" />
        <StatCard icon="bi-hourglass-split" value={stats.students_not_linked} label="Awaiting first link" />
      </div>

      <section className="mb-5 grid gap-3 md:grid-cols-3">
        <WorkflowStep
          num={1}
          title="Add parent emails"
          body="Enter Parent 1 / Parent 2 contact info on each student record."
        />
        <WorkflowStep
          num={2}
          title="Provision logins"
          body="Create accounts from a student profile or use bulk provision above."
        />
        <WorkflowStep
          num={3}
          title="Release report cards"
          body="Director approves official cards on the report card detail page for family download."
        />
      </section>

      <section className="overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-teal-100 bg-slate-50 px-5 py-3">
          <h2 className="flex items-center gap-2 text-base font-bold text-hub-text">
            <i className="bi bi-table text-teal-700" aria-hidden />
            Parent accounts
          </h2>
          <span className="rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
            {items.length} account{items.length === 1 ? '' : 's'}
          </span>
        </div>
        {loading ? (
          <div className="px-6 py-12 text-center text-hub-muted">Loading parent accounts…</div>
        ) : (
          <ParentAccountsTable items={items} />
        )}
      </section>

      <p className="mt-4 text-center text-sm text-hub-muted">
        To provision a single family, open a{' '}
        <Link to="/management/students" className="font-semibold text-hub-accent hover:underline">
          student record
        </Link>{' '}
        and use Family portal access in the edit view.
      </p>
    </div>
  )
}
