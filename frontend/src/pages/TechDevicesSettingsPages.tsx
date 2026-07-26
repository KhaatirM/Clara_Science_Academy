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
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import { applyUserTheme } from '../utils/userTheme'
import { btnMuted, btnPrimary } from './TechHomePage'

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

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="mb-0 text-2xl font-bold text-slate-900">Devices</h1>
              <p className="mb-0 mt-1 text-sm text-hub-muted">
                Student laptop and tablet assignments
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <a href="/tech/devices/csv-template?legacy=1" className={btnMuted}>
                CSV template
              </a>
              <Link to="/tech/devices/new" className={btnPrimary}>
                Assign device
              </Link>
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:flex-wrap sm:items-end">
            <label className="flex min-w-[9rem] flex-1 flex-col gap-1.5 sm:max-w-[11rem]">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Device type
              </span>
              <select
                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800"
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                <option value="">All types</option>
                <option value="laptop">Laptop</option>
                <option value="tablet">Tablet</option>
              </select>
            </label>
            <label className="flex min-w-[14rem] flex-[2] flex-col gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Search
              </span>
              <input
                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800"
                placeholder="Student name, ID, asset, or cord…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void load()
                }}
              />
            </label>
            <button type="button" className={btnMuted} onClick={() => void load()}>
              Search
            </button>
          </div>

          {message ? (
            <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
              {message}
            </div>
          ) : null}

          {loading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
              Loading devices…
            </div>
          ) : error ? (
            <div className="alert alert-danger">{error}</div>
          ) : records.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center shadow-sm">
              <p className="mb-1 text-base font-semibold text-slate-800">No devices found</p>
              <p className="mb-4 text-sm text-hub-muted">
                Assign a laptop or tablet to a student, or adjust your filters.
              </p>
              <Link to="/tech/devices/new" className={btnPrimary}>
                Assign device
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
              <table className="w-full min-w-[56rem] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      Type
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      Asset
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      Student
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      Cord #
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      OS
                    </th>
                    <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((row) => (
                    <tr
                      key={row.id}
                      className="border-b border-slate-100 last:border-b-0 hover:bg-teal-50/40"
                    >
                      <td className="px-4 py-3 align-top">
                        <span className="inline-flex rounded-lg bg-teal-100 px-2.5 py-1 text-xs font-semibold capitalize text-teal-900">
                          {row.device_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="font-semibold text-slate-900">{row.asset_name}</div>
                        {row.device_name ? (
                          <div className="mt-0.5 text-xs text-hub-muted">{row.device_name}</div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 align-top">
                        {row.student ? (
                          <>
                            <div className="font-semibold text-slate-900">{row.student.name}</div>
                            <div className="mt-0.5 text-xs text-hub-muted">
                              Grade {row.student.grade_level ?? '—'}
                              {row.student.student_id ? ` · ID ${row.student.student_id}` : ''}
                            </div>
                          </>
                        ) : (
                          <span className="text-hub-muted">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top text-slate-700">
                        {row.cord_number || '—'}
                      </td>
                      <td className="px-4 py-3 align-top text-slate-700">
                        {row.operating_system || '—'}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="flex flex-wrap gap-2">
                          <Link to={`/tech/devices/${row.id}/edit`} className={btnMuted}>
                            Edit
                          </Link>
                          <button
                            type="button"
                            className={btnMuted}
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
          )}
        </div>
      </div>
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
    operating_system: '',
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
            operating_system: data.device.operating_system || '',
            student_id: String(data.device.student_id || ''),
          })
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load form'))
  }, [id])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell mx-auto max-w-2xl space-y-4 px-1 pb-8 md:px-2">
          <Link to="/tech/devices" className={btnMuted}>
            ← Back
          </Link>
          <h1 className="text-2xl font-bold">{id ? 'Edit device' : 'Assign device'}</h1>
          {error ? <div className="alert alert-danger">{error}</div> : null}
          {!formMeta ? (
            <div className="text-muted">Loading…</div>
          ) : (
            <form
              className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              onSubmit={async (e) => {
                e.preventDefault()
                setBusy(true)
                setError(null)
                try {
                  const res = await saveTechDevice(
                    {
                      ...form,
                      student_id: Number(form.student_id),
                    },
                    id,
                  )
                  navigate('/tech/devices')
                  void res
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'Save failed')
                  setBusy(false)
                }
              }}
            >
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Device type
                </span>
                <select
                  className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm capitalize"
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
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Asset name
                </span>
                <input
                  className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                  required
                  placeholder="e.g. CSA-Laptop-12"
                  value={form.asset_name}
                  onChange={(e) => setForm((f) => ({ ...f, asset_name: e.target.value }))}
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Device name
                </span>
                <input
                  className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                  placeholder="Optional display name"
                  value={form.device_name}
                  onChange={(e) => setForm((f) => ({ ...f, device_name: e.target.value }))}
                />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Cord #
                  </span>
                  <input
                    className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                    value={form.cord_number}
                    onChange={(e) => setForm((f) => ({ ...f, cord_number: e.target.value }))}
                  />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Operating system
                  </span>
                  <input
                    className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                    placeholder="e.g. ChromeOS"
                    value={form.operating_system}
                    onChange={(e) => setForm((f) => ({ ...f, operating_system: e.target.value }))}
                  />
                </label>
              </div>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Student
                </span>
                <select
                  className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
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
              <button type="submit" className={btnPrimary} disabled={busy}>
                {busy ? 'Saving…' : 'Save device'}
              </button>
            </form>
          )}
        </div>
      </div>
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

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <h1 className="text-2xl font-bold">Settings</h1>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={tab === 'account' ? btnPrimary : btnMuted}
              onClick={() => {
                setTab('account')
                navigate('/tech/settings')
              }}
            >
              Account
            </button>
            <button
              type="button"
              className={tab === 'preferences' ? btnPrimary : btnMuted}
              onClick={() => setTab('preferences')}
            >
              Preferences
            </button>
          </div>
          {error ? <div className="alert alert-danger">{error}</div> : null}
          {message ? <div className="rounded-xl bg-teal-50 px-3 py-2 text-sm">{message}</div> : null}
          {!data ? (
            <div className="text-muted">Loading…</div>
          ) : tab === 'account' ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="mb-1">
                <strong>Username:</strong> {data.account?.username}
              </p>
              <p className="mb-3">
                <strong>Role:</strong> {data.account?.role}
              </p>
              <a href="/change-password" className={btnPrimary}>
                Change password
              </a>
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              {data.preferences?.theme_locked ? (
                <p className="text-amber-800">Theme is locked by a site-wide Tech override.</p>
              ) : null}
              {[...themeGroups.entries()].map(([group, options]) => (
                <div key={group} className="mb-3">
                  <h3 className="text-sm font-bold text-hub-muted">{group}</h3>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {options.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        className={theme === opt.value ? btnPrimary : btnMuted}
                        onClick={() => setTheme(opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              <button
                type="button"
                className={btnPrimary}
                onClick={async () => {
                  try {
                    const res = await updateTechTheme(theme)
                    setMessage(res.message || 'Theme saved')
                    applyUserTheme(theme)
                  } catch (err) {
                    setMessage(err instanceof Error ? err.message : 'Could not save theme')
                  }
                }}
              >
                Save theme
              </button>
            </div>
          )}
        </div>
      </div>
    </ManagementPageShell>
  )
}
