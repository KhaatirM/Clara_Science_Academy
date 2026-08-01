import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  deleteTechDevice,
  fetchTechDeviceForm,
  fetchTechDevices,
  fetchTechSettingsHub,
  saveTechDevice,
  updateTechTheme,
} from '../api/tech'
import {
  ManagementPageHero,
  ManagementPageShell,
} from '../components/layout/ManagementPageShell'
import { applyUserTheme } from '../utils/userTheme'

const fieldClass =
  'w-full rounded-xl border border-[color-mix(in_srgb,var(--spa-mgmt-accent)_22%,var(--spa-mgmt-border))] bg-[var(--spa-mgmt-surface)] px-3 py-2.5 text-sm text-hub-text shadow-sm outline-none transition focus:border-[var(--spa-mgmt-accent)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--spa-mgmt-accent)_25%,transparent)]'
const labelClass = 'text-xs font-semibold uppercase tracking-wide text-hub-muted'

const OS_OPTIONS = ['ChromeOS', 'Windows', 'macOS', 'iPadOS', 'Android', 'Linux']

function withCurrentOption(options: string[], current: string | null | undefined) {
  const value = (current || '').trim()
  if (value && !options.includes(value)) return [value, ...options]
  return options
}

export function TechDevicesPage() {
  const [data, setData] = useState<any>(null)
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTechDevices({ type, q }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load devices')
    } finally {
      setLoading(false)
    }
  }, [type, q])

  useEffect(() => {
    void load()
  }, [load])

  const records = (data?.records || []) as any[]
  const laptopCount = records.filter((r) => String(r.device_type).toLowerCase() === 'laptop').length
  const tabletCount = records.filter((r) => String(r.device_type).toLowerCase() === 'tablet').length

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
              Tech · Inventory
            </p>
            <h1 className="mb-0 text-3xl font-bold tracking-tight">Devices</h1>
            <p className="mb-0 mt-2 max-w-xl text-sm spa-mgmt-hero-muted">
              Student laptop and tablet assignments across the academy.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href="/tech/devices/csv-template?legacy=1"
              className="inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-sm font-semibold text-white no-underline hover:bg-white/25"
            >
              <i className="bi bi-filetype-csv" aria-hidden />
              CSV template
            </a>
            <Link
              to="/tech/devices/new"
              className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-[var(--spa-mgmt-accent-deep)] no-underline hover:bg-white/90"
            >
              <i className="bi bi-plus-lg" aria-hidden />
              Assign device
            </Link>
          </div>
        </div>
      </ManagementPageHero>

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-hub-text">{records.length}</div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Shown</div>
        </article>
        <article className="spa-mgmt-stat flex items-center gap-3 p-4 shadow-sm">
          <span className="spa-mgmt-avatar h-9 w-9 text-sm">
            <i className="bi bi-laptop" aria-hidden />
          </span>
          <div>
            <div className="text-2xl font-bold tabular-nums text-hub-text">{laptopCount}</div>
            <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Laptops</div>
          </div>
        </article>
        <article className="spa-mgmt-stat flex items-center gap-3 p-4 shadow-sm">
          <span className="spa-mgmt-avatar h-9 w-9 text-sm">
            <i className="bi bi-tablet" aria-hidden />
          </span>
          <div>
            <div className="text-2xl font-bold tabular-nums text-hub-text">{tabletCount}</div>
            <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">Tablets</div>
          </div>
        </article>
      </div>

      <section className="spa-mgmt-card mb-4 overflow-hidden shadow-sm">
        <div className="spa-mgmt-accent-bar" />
        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="flex min-w-[9rem] flex-1 flex-col gap-1.5 sm:max-w-[11rem]">
            <span className={labelClass}>Device type</span>
            <select className={fieldClass} value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">All types</option>
              <option value="laptop">Laptop</option>
              <option value="tablet">Tablet</option>
            </select>
          </label>
          <label className="flex min-w-[14rem] flex-[2] flex-col gap-1.5">
            <span className={labelClass}>Search</span>
            <input
              className={fieldClass}
              placeholder="Student name, ID, asset, or cord…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void load()
              }}
            />
          </label>
          <button
            type="button"
            className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
            onClick={() => void load()}
          >
            <i className="bi bi-search" aria-hidden />
            Search
          </button>
        </div>
      </section>

      {message ? (
        <div className="spa-mgmt-insight mb-4 px-4 py-3 text-sm font-medium">{message}</div>
      ) : null}

      {loading ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading devices…</div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : records.length === 0 ? (
        <div className="spa-mgmt-card border-dashed px-6 py-12 text-center shadow-sm">
          <i className="bi bi-laptop mb-2 text-2xl text-hub-muted" aria-hidden />
          <p className="mb-1 text-base font-semibold text-hub-text">No devices found</p>
          <p className="mb-4 text-sm text-hub-muted">
            Assign a laptop or tablet to a student, or adjust your filters.
          </p>
          <Link to="/tech/devices/new" className="spa-mgmt-btn-primary px-4 py-2.5 text-sm no-underline">
            Assign device
          </Link>
        </div>
      ) : (
        <div className="spa-mgmt-card overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[56rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--spa-mgmt-border)] bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_55%,var(--spa-mgmt-surface))]">
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Type
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Asset
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Student
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Cord #
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    OS
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {records.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-[color-mix(in_srgb,var(--spa-mgmt-border)_70%,transparent)] last:border-b-0 hover:bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_40%,transparent)]"
                  >
                    <td className="px-4 py-3 align-top">
                      <span className="spa-mgmt-badge capitalize">{row.device_type}</span>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="font-semibold text-hub-text">{row.asset_name}</div>
                      {row.device_name ? (
                        <div className="mt-0.5 text-xs text-hub-muted">{row.device_name}</div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 align-top">
                      {row.student ? (
                        <>
                          <div className="font-semibold text-hub-text">{row.student.name}</div>
                          <div className="mt-0.5 text-xs text-hub-muted">
                            Grade {row.student.grade_level ?? '—'}
                            {row.student.student_id ? ` · ID ${row.student.student_id}` : ''}
                          </div>
                        </>
                      ) : (
                        <span className="text-hub-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 align-top text-hub-muted">{row.cord_number || '—'}</td>
                    <td className="px-4 py-3 align-top text-hub-muted">
                      {row.operating_system || '—'}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="flex flex-wrap gap-2">
                        <Link
                          to={`/tech/devices/${row.id}/edit`}
                          className="spa-mgmt-btn-ghost px-3 py-1.5 text-xs no-underline"
                        >
                          Edit
                        </Link>
                        <button
                          type="button"
                          className="spa-mgmt-btn-ghost px-3 py-1.5 text-xs"
                          onClick={async () => {
                            if (!window.confirm('Remove this device assignment?')) return
                            try {
                              const res = await deleteTechDevice(row.id)
                              setMessage(res.message)
                              await load()
                            } catch (err) {
                              setMessage(err instanceof Error ? err.message : 'Delete failed')
                            }
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </ManagementPageShell>
  )
}

export function TechDeviceFormPage() {
  const { deviceId } = useParams()
  const id = deviceId ? Number(deviceId) : undefined
  const navigate = useNavigate()
  const [formMeta, setFormMeta] = useState<any>(null)
  const [form, setForm] = useState({
    device_type: 'laptop',
    asset_name: '',
    device_name: '',
    cord_number: '',
    operating_system: 'ChromeOS',
    student_id: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void fetchTechDeviceForm(id)
      .then((data) => {
        setFormMeta(data)
        if (data.device) {
          setForm({
            device_type: data.device.device_type || 'laptop',
            asset_name: data.device.asset_name || '',
            device_name: data.device.device_name || '',
            cord_number: data.device.cord_number || '',
            operating_system: data.device.operating_system || 'ChromeOS',
            student_id: String(data.device.student_id || ''),
          })
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load form'))
  }, [id])

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
              Tech · Devices
            </p>
            <h1 className="mb-0 text-3xl font-bold tracking-tight">
              {id ? 'Edit device' : 'Assign device'}
            </h1>
            <p className="mb-0 mt-2 text-sm spa-mgmt-hero-muted">
              Link a laptop or tablet asset to a student record.
            </p>
          </div>
          <Link
            to="/tech/devices"
            className="inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-sm font-semibold text-white no-underline hover:bg-white/25"
          >
            <i className="bi bi-arrow-left" aria-hidden />
            Back to devices
          </Link>
        </div>
      </ManagementPageHero>

      {error ? <div className="alert alert-danger mb-4">{error}</div> : null}

      {!formMeta ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading…</div>
      ) : (
        <form
          className="spa-mgmt-card mx-auto max-w-2xl overflow-hidden shadow-sm"
          onSubmit={async (e) => {
            e.preventDefault()
            setBusy(true)
            setError(null)
            try {
              await saveTechDevice(
                {
                  ...form,
                  student_id: Number(form.student_id),
                },
                id,
              )
              navigate('/tech/devices')
            } catch (err) {
              setError(err instanceof Error ? err.message : 'Save failed')
              setBusy(false)
            }
          }}
        >
          <div className="spa-mgmt-accent-bar" />
          <div className="space-y-4 p-5 md:p-6">
            <label className="flex flex-col gap-1.5">
              <span className={labelClass}>Device type</span>
              <select
                className={`${fieldClass} capitalize`}
                value={form.device_type}
                onChange={(e) => setForm((f) => ({ ...f, device_type: e.target.value }))}
              >
                {(formMeta.device_types || ['laptop', 'tablet']).map((t: string) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className={labelClass}>Asset name</span>
              <input
                className={fieldClass}
                required
                placeholder="e.g. CSA-Laptop-12"
                value={form.asset_name}
                onChange={(e) => setForm((f) => ({ ...f, asset_name: e.target.value }))}
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className={labelClass}>Device name</span>
              <input
                className={fieldClass}
                placeholder="Optional display name"
                value={form.device_name}
                onChange={(e) => setForm((f) => ({ ...f, device_name: e.target.value }))}
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5">
                <span className={labelClass}>Cord #</span>
                <input
                  className={fieldClass}
                  value={form.cord_number}
                  onChange={(e) => setForm((f) => ({ ...f, cord_number: e.target.value }))}
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className={labelClass}>Operating system</span>
                <select
                  className={fieldClass}
                  value={form.operating_system}
                  onChange={(e) => setForm((f) => ({ ...f, operating_system: e.target.value }))}
                >
                  <option value="">Select OS…</option>
                  {withCurrentOption(OS_OPTIONS, form.operating_system).map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="flex flex-col gap-1.5">
              <span className={labelClass}>Student</span>
              <select
                className={fieldClass}
                required
                value={form.student_id}
                onChange={(e) => setForm((f) => ({ ...f, student_id: e.target.value }))}
              >
                <option value="">Select a student…</option>
                {(formMeta.students || []).map((s: any) => (
                  <option key={s.id} value={s.id}>
                    {s.name} (Grade {s.grade_level ?? '?'}) · {s.student_id}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              className="spa-mgmt-btn-primary px-4 py-2.5 text-sm disabled:opacity-60"
              disabled={busy}
            >
              <i className="bi bi-check2-circle" aria-hidden />
              {busy ? 'Saving…' : 'Save device'}
            </button>
          </div>
        </form>
      )}
    </ManagementPageShell>
  )
}

export function TechSettingsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<'account' | 'preferences'>('account')
  const [data, setData] = useState<any>(null)
  const [theme, setTheme] = useState('default')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    void fetchTechSettingsHub()
      .then((hub) => {
        setData(hub)
        setTheme(hub.preferences?.saved_theme || 'default')
        applyUserTheme(hub.preferences?.theme || 'default')
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load settings'))
  }, [])

  const themeGroups = useMemo(() => {
    const groups = new Map<string, any[]>()
    for (const option of data?.preferences?.theme_options || []) {
      const list = groups.get(option.group) || []
      list.push(option)
      groups.set(option.group, list)
    }
    return groups
  }, [data])

  const tabMeta = {
    account: {
      label: 'Account',
      icon: 'bi-person',
      hint: 'Your tech portal identity and password.',
    },
    preferences: {
      label: 'Preferences',
      icon: 'bi-palette',
      hint: 'Personal theme for the tech portal interface.',
    },
  } as const

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
              Tech · Settings
            </p>
            <h1 className="mb-0 text-3xl font-bold tracking-tight">Settings</h1>
            <p className="mb-0 mt-2 max-w-xl text-sm spa-mgmt-hero-muted">{tabMeta[tab].hint}</p>
          </div>
          {data?.account?.username ? (
            <span className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold text-white">
              <i className="bi bi-person-badge" aria-hidden />
              {data.account.username}
              {data.account.role ? ` · ${data.account.role}` : ''}
            </span>
          ) : null}
        </div>
      </ManagementPageHero>

      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Settings sections">
        {(['account', 'preferences'] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={`spa-mgmt-tab ${tab === t ? 'is-active' : ''}`}
            onClick={() => {
              setTab(t)
              if (t === 'account') navigate('/tech/settings')
            }}
          >
            <i className={`bi ${tabMeta[t].icon}`} aria-hidden />
            {tabMeta[t].label}
          </button>
        ))}
      </div>

      {error ? <div className="alert alert-danger mb-4">{error}</div> : null}
      {message ? (
        <div className="spa-mgmt-insight mb-4 px-4 py-3 text-sm font-medium">{message}</div>
      ) : null}

      {!data ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading settings…</div>
      ) : tab === 'account' ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="spa-mgmt-card overflow-hidden shadow-sm">
            <div className="spa-mgmt-accent-bar" />
            <div className="p-5">
              <div className="mb-4 flex items-start gap-3">
                <span className="spa-mgmt-avatar h-11 w-11 text-lg">
                  <i className="bi bi-person" aria-hidden />
                </span>
                <div>
                  <h2 className="mb-0 text-lg font-bold text-hub-text">Account</h2>
                  <p className="mb-0 mt-1 text-sm text-hub-muted">
                    Signed-in profile for this tech session.
                  </p>
                </div>
              </div>
              <dl className="grid gap-3 sm:grid-cols-2">
                <div className="spa-mgmt-stat p-3">
                  <dt className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
                    Username
                  </dt>
                  <dd className="mb-0 mt-1 text-sm font-semibold text-hub-text">
                    {data.account?.username || '—'}
                  </dd>
                </div>
                <div className="spa-mgmt-stat p-3">
                  <dt className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
                    Role
                  </dt>
                  <dd className="mb-0 mt-1 text-sm font-semibold text-hub-text">
                    {data.account?.role || '—'}
                  </dd>
                </div>
                {data.account?.email ? (
                  <div className="spa-mgmt-stat p-3 sm:col-span-2">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
                      Email
                    </dt>
                    <dd className="mb-0 mt-1 text-sm font-semibold text-hub-text">
                      {data.account.email}
                    </dd>
                  </div>
                ) : null}
              </dl>
            </div>
          </section>

          <section className="spa-mgmt-card overflow-hidden shadow-sm">
            <div className="spa-mgmt-accent-bar" />
            <div className="p-5">
              <div className="mb-4 flex items-start gap-3">
                <span className="spa-mgmt-avatar h-11 w-11 text-lg">
                  <i className="bi bi-shield-lock" aria-hidden />
                </span>
                <div>
                  <h2 className="mb-0 text-lg font-bold text-hub-text">Security</h2>
                  <p className="mb-0 mt-1 text-sm text-hub-muted">
                    Update your password when rotating credentials.
                  </p>
                </div>
              </div>
              <a href="/change-password" className="spa-mgmt-btn-primary px-4 py-2.5 text-sm no-underline">
                <i className="bi bi-key" aria-hidden />
                Change password
              </a>
            </div>
          </section>
        </div>
      ) : (
        <section className="spa-mgmt-card overflow-hidden shadow-sm">
          <div className="spa-mgmt-accent-bar" />
          <div className="p-5 md:p-6">
            <div className="mb-4 flex items-start gap-3">
              <span className="spa-mgmt-avatar h-11 w-11 text-lg">
                <i className="bi bi-palette" aria-hidden />
              </span>
              <div>
                <h2 className="mb-0 text-lg font-bold text-hub-text">Theme preferences</h2>
                <p className="mb-0 mt-1 text-sm text-hub-muted">
                  Preview and save the look of your tech portal. Accents update with the theme.
                </p>
              </div>
            </div>

            {data.preferences?.theme_locked ? (
              <div className="mb-4 rounded-2xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-sm text-amber-950">
                Theme is locked by a site-wide Tech override. Clear it under System → Config to allow
                personal themes again.
              </div>
            ) : null}

            <div className="space-y-5">
              {[...themeGroups.entries()].map(([group, options]) => (
                <div key={group}>
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    {group}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {options.map((opt) => {
                      const selected = theme === opt.value
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          disabled={Boolean(data.preferences?.theme_locked)}
                          className={
                            selected
                              ? 'spa-mgmt-tab is-active disabled:opacity-60'
                              : 'spa-mgmt-tab disabled:opacity-60'
                          }
                          onClick={() => {
                            setTheme(opt.value)
                            if (!data.preferences?.theme_locked) applyUserTheme(opt.value)
                          }}
                        >
                          {opt.label}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              className="spa-mgmt-btn-primary mt-5 px-4 py-2.5 text-sm disabled:opacity-60"
              disabled={saving || Boolean(data.preferences?.theme_locked)}
              onClick={async () => {
                setSaving(true)
                setMessage(null)
                try {
                  const res = await updateTechTheme(theme)
                  setMessage(res.message || 'Theme saved')
                  applyUserTheme(theme)
                } catch (err) {
                  setMessage(err instanceof Error ? err.message : 'Could not save theme')
                } finally {
                  setSaving(false)
                }
              }}
            >
              <i className="bi bi-check2-circle" aria-hidden />
              {saving ? 'Saving…' : 'Save theme'}
            </button>
          </div>
        </section>
      )}
    </ManagementPageShell>
  )
}
