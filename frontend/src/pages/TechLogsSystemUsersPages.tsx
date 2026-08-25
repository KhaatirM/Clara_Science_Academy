import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  fetchTechUser,
  fetchTechUsers,
  impersonateTechUser,
  resetTechUserPassword,
} from '../api/tech'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import { btnMuted, btnPrimary } from './TechHomePage'

function portalStatusTone(status: string | null | undefined) {
  const s = (status || '').toLowerCase()
  if (s.includes('active') && !s.includes('inactive')) return 'bg-emerald-100 text-emerald-800'
  if (s.includes('former') || s.includes('inactive') || s.includes('closed')) {
    return 'bg-slate-100 text-slate-700'
  }
  return 'bg-amber-100 text-amber-900'
}

function userMatchesQuery(user: any, q: string) {
  if (!q) return true
  const hay = [user.username, user.role, user.login_id, user.portal_status, user.email]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return hay.includes(q)
}

function UserBucket({ title, users }: { title: string; users: any[] }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
        <h2 className="mb-0 text-sm font-bold text-slate-900">
          {title}{' '}
          <span className="font-normal text-hub-muted">({users.length})</span>
        </h2>
      </div>
      {users.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-hub-muted">None in this group</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-white">
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Username
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Role
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Login ID
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  Status
                </th>
                <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.row_key || u.id}
                  className="border-b border-slate-100 last:border-b-0 hover:bg-teal-50/40"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {u.username}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-700">{u.role}</td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">
                    {u.login_id || '—'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${portalStatusTone(u.portal_status)}`}
                    >
                      {u.portal_status || '—'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-end">
                    {u.can_view !== false && u.id != null ? (
                      <Link to={`/tech/users/${u.id}`} className={btnMuted}>
                        View
                      </Link>
                    ) : (
                      <span className="text-xs text-hub-muted">No portal login</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function TechUserManagementPage() {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  useEffect(() => {
    setLoading(true)
    void fetchTechUsers()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load users'))
      .finally(() => setLoading(false))
  }, [])

  const query = q.trim().toLowerCase()
  const buckets = data
    ? [
        {
          title: 'Students (current)',
          users: (data.students_current || []).filter((u: any) => userMatchesQuery(u, query)),
        },
        {
          title: 'Students (former)',
          users: (data.students_former || []).filter((u: any) => userMatchesQuery(u, query)),
        },
        {
          title: 'Parents',
          users: (data.parents || []).filter((u: any) => userMatchesQuery(u, query)),
        },
        {
          title: 'Staff (current)',
          users: (data.staff_current || []).filter((u: any) => userMatchesQuery(u, query)),
        },
        {
          title: 'Staff (former)',
          users: (data.staff_former || []).filter((u: any) => userMatchesQuery(u, query)),
        },
      ]
    : []

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <div>
            <h1 className="mb-0 text-2xl font-bold text-slate-900">User Management</h1>
            <p className="mb-0 mt-1 text-sm text-hub-muted">
              Portal accounts, password resets, and impersonation
            </p>
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-end">
            <label className="flex min-w-[14rem] flex-1 flex-col gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Search
              </span>
              <input
                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
                placeholder="Username, role, login ID, or status…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
              Loading users…
            </div>
          ) : error ? (
            <div className="alert alert-danger">{error}</div>
          ) : (
            <div className="space-y-4">
              {buckets.map((bucket) => (
                <UserBucket key={bucket.title} title={bucket.title} users={bucket.users} />
              ))}
            </div>
          )}
        </div>
      </div>
    </ManagementPageShell>
  )
}

export function TechUserDetailPage() {
  const { userId = '' } = useParams()
  const id = Number(userId)
  const [data, setData] = useState<any>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchTechUser(id)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load user'))
  }, [id])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <Link to="/tech/users" className={btnMuted}>
            ← Back to users
          </Link>
          {error ? <div className="alert alert-danger">{error}</div> : null}
          {message ? (
            <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
              {message}
            </div>
          ) : null}
          {!data ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
              Loading user…
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h1 className="mb-1 text-2xl font-bold text-slate-900">{data.user.username}</h1>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="text-hub-muted">{data.user.role}</span>
                    <span
                      className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${portalStatusTone(data.user.portal_status)}`}
                    >
                      {data.user.portal_status}
                    </span>
                  </div>
                </div>
              </div>

              {data.profile ? (
                <dl className="mb-5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Name
                    </dt>
                    <dd className="mb-0 mt-0.5 text-sm font-medium text-slate-900">
                      {data.profile.first_name} {data.profile.last_name}
                    </dd>
                  </div>
                  {data.profile.kind === 'student' ? (
                    <>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Student ID
                        </dt>
                        <dd className="mb-0 mt-0.5 font-mono text-sm text-slate-900">
                          {data.profile.student_id || '—'}
                        </dd>
                      </div>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Grade
                        </dt>
                        <dd className="mb-0 mt-0.5 text-sm text-slate-900">
                          {data.profile.grade_level ?? '—'}
                        </dd>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Staff ID
                        </dt>
                        <dd className="mb-0 mt-0.5 font-mono text-sm text-slate-900">
                          {data.profile.staff_id || '—'}
                        </dd>
                      </div>
                      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                        <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Position
                        </dt>
                        <dd className="mb-0 mt-0.5 text-sm text-slate-900">
                          {data.profile.position || 'Staff'}
                        </dd>
                      </div>
                    </>
                  )}
                  {data.profile.email ? (
                    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5 sm:col-span-2">
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Email
                      </dt>
                      <dd className="mb-0 mt-0.5 text-sm text-slate-900">{data.profile.email}</dd>
                    </div>
                  ) : null}
                </dl>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className={btnPrimary}
                  onClick={async () => {
                    try {
                      const res = await resetTechUserPassword(id)
                      setMessage(
                        `${res.message}${res.temporary_password ? ` Temp password: ${res.temporary_password}` : ''}`,
                      )
                    } catch (err) {
                      setMessage(err instanceof Error ? err.message : 'Reset failed')
                    }
                  }}
                >
                  Reset password
                </button>
                {data.can_impersonate ? (
                  <button
                    type="button"
                    className={btnMuted}
                    onClick={async () => {
                      if (!window.confirm(`Impersonate ${data.user.username}?`)) return
                      try {
                        const res = await impersonateTechUser(id)
                        window.location.assign(res.redirect || '/app')
                      } catch (err) {
                        setMessage(err instanceof Error ? err.message : 'Impersonate failed')
                      }
                    }}
                  >
                    Impersonate
                  </button>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>
    </ManagementPageShell>
  )
}
