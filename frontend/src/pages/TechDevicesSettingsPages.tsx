import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  createTechRepairTicket,
  deleteTechDevice,
  fetchTechDeviceForm,
  fetchTechDevices,
  fetchTechRepairTickets,
  fetchTechSettingsHub,
  saveTechDevice,
  updateTechRepairTicketStatus,
  updateTechTheme,
  uploadTechDevicesCsv,
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

const REPAIR_STATUSES = [
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'repaired', label: 'Repaired' },
  { value: 'closed', label: 'Closed' },
] as const

const REPAIR_CATEGORIES = [
  { value: 'hardware', label: 'Hardware Issues' },
  { value: 'software', label: 'Software Issues' },
] as const

function withCurrentOption(options: string[], current: string | null | undefined) {
  const value = (current || '').trim()
  if (value && !options.includes(value)) return [value, ...options]
  return options
}

function severityBadgeClass(severity: string) {
  switch (severity) {
    case 'critical':
      return 'bg-red-100 text-red-800'
    case 'high':
      return 'bg-orange-100 text-orange-800'
    case 'low':
      return 'bg-slate-100 text-slate-700'
    default:
      return 'bg-amber-100 text-amber-900'
  }
}

function categoryBadgeClass(category: string) {
  return category === 'software'
    ? 'bg-indigo-100 text-indigo-800'
    : 'bg-teal-100 text-teal-800'
}

function statusBadgeClass(status: string) {
  switch (status) {
    case 'in_progress':
      return 'bg-sky-100 text-sky-800'
    case 'repaired':
      return 'bg-emerald-100 text-emerald-800'
    case 'closed':
      return 'bg-slate-200 text-slate-700'
    default:
      return 'bg-rose-100 text-rose-800'
  }
}

export function TechDevicesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const tab: 'inventory' | 'repairs' = rawTab === 'repairs' ? 'repairs' : 'inventory'
  const prefillDeviceId = searchParams.get('device_id')

  function setTab(next: 'inventory' | 'repairs', extras?: { device_id?: number | null }) {
    const nextParams = new URLSearchParams(searchParams)
    if (next === 'inventory') {
      nextParams.delete('tab')
      nextParams.delete('device_id')
    } else {
      nextParams.set('tab', 'repairs')
      if (extras?.device_id != null) nextParams.set('device_id', String(extras.device_id))
      else if (extras && extras.device_id === null) nextParams.delete('device_id')
    }
    setSearchParams(nextParams, { replace: true })
  }

  const tabMeta = {
    inventory: {
      label: 'Inventory',
      icon: 'bi-laptop',
      hint: 'Assigned devices, unassigned stock, and students still waiting for a device.',
    },
    repairs: {
      label: 'Repair tickets',
      icon: 'bi-wrench-adjustable',
      hint: 'Hardware and software issues — open, in progress, or fixed.',
    },
  } as const

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
              Tech · Inventory
            </p>
            <h1 className="mb-0 text-3xl font-bold tracking-tight">Devices</h1>
            <p className="mb-0 mt-2 max-w-xl text-sm spa-mgmt-hero-muted">{tabMeta[tab].hint}</p>
          </div>
          {tab === 'inventory' ? (
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
                Add device
              </Link>
            </div>
          ) : null}
        </div>
      </ManagementPageHero>

      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Device sections">
        {(['inventory', 'repairs'] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={`spa-mgmt-tab ${tab === t ? 'is-active' : ''}`}
            onClick={() => setTab(t)}
          >
            <i className={`bi ${tabMeta[t].icon}`} aria-hidden />
            {tabMeta[t].label}
          </button>
        ))}
      </div>

      {tab === 'inventory' ? (
        <DevicesInventoryPanel
          onFileRepair={(deviceId) => setTab('repairs', { device_id: deviceId })}
        />
      ) : (
        <DevicesRepairTicketsPanel
          prefillDeviceId={prefillDeviceId ? Number(prefillDeviceId) : undefined}
          onClearPrefill={() => setTab('repairs', { device_id: null })}
        />
      )}
    </ManagementPageShell>
  )
}

function DevicesInventoryPanel({ onFileRepair }: { onFileRepair: (deviceId: number) => void }) {
  const [data, setData] = useState<any>(null)
  const [type, setType] = useState('')
  const [assignment, setAssignment] = useState('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTechDevices({ type, q, assignment }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load devices')
    } finally {
      setLoading(false)
    }
  }, [type, q, assignment])

  useEffect(() => {
    void load()
  }, [load])

  const records = (data?.records || []) as any[]
  const pendingStudents = (data?.pending_students || []) as any[]
  const counts = data?.counts || {}
  const laptopCount = records.filter((r) => String(r.device_type).toLowerCase() === 'laptop').length
  const tabletCount = records.filter((r) => String(r.device_type).toLowerCase() === 'tablet').length
  const unassignedCount = records.filter((r) => !r.student_id).length

  async function onCsvSelected(file: File | null) {
    if (!file) return
    setUploading(true)
    setMessage(null)
    setError(null)
    try {
      const res = await uploadTechDevicesCsv(file)
      const errList = (res.errors || []) as string[]
      setMessage(
        res.message ||
          `Imported ${res.created || 0} created, ${res.updated || 0} updated.` +
            (errList.length ? ` ${errList.length} row(s) skipped.` : ''),
      )
      if (errList.length) {
        setError(errList.slice(0, 5).join(' · '))
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'CSV upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
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
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-hub-text">
            {counts.unassigned ?? unassignedCount}
          </div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
            Unassigned stock
          </div>
        </article>
        <article className="spa-mgmt-stat p-4 shadow-sm">
          <div className="text-2xl font-bold tabular-nums text-hub-text">
            {counts.pending_students ?? pendingStudents.length}
          </div>
          <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
            Pending students
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
          <label className="flex min-w-[9rem] flex-1 flex-col gap-1.5 sm:max-w-[12rem]">
            <span className={labelClass}>Assignment</span>
            <select
              className={fieldClass}
              value={assignment}
              onChange={(e) => setAssignment(e.target.value)}
            >
              <option value="">All</option>
              <option value="assigned">Assigned</option>
              <option value="unassigned">Unassigned</option>
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
          <label className="spa-mgmt-btn-ghost cursor-pointer px-4 py-2.5 text-sm">
            <i className="bi bi-upload" aria-hidden />
            {uploading ? 'Uploading…' : 'Upload CSV'}
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const file = e.target.files?.[0] || null
                e.target.value = ''
                void onCsvSelected(file)
              }}
            />
          </label>
        </div>
      </section>

      {message ? (
        <div className="spa-mgmt-insight mb-4 px-4 py-3 text-sm font-medium">{message}</div>
      ) : null}

      {pendingStudents.length > 0 ? (
        <section className="spa-mgmt-card mb-4 overflow-hidden shadow-sm">
          <div className="border-b border-[var(--spa-mgmt-border)] px-4 py-3">
            <h2 className="mb-0 text-sm font-bold text-hub-text">
              Students pending a device{' '}
              <span className="font-normal text-hub-muted">({pendingStudents.length})</span>
            </h2>
            <p className="mb-0 mt-1 text-xs text-hub-muted">
              Active students on the roster who do not have a school device assigned yet.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--spa-mgmt-border)] bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_55%,var(--spa-mgmt-surface))]">
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Student
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Grade
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Expected
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {pendingStudents.slice(0, 40).map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-[color-mix(in_srgb,var(--spa-mgmt-border)_70%,transparent)] last:border-b-0"
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-hub-text">{s.name}</div>
                      <div className="mt-0.5 text-xs text-hub-muted">
                        {s.student_id ? `ID ${s.student_id}` : '—'}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-hub-muted">{s.grade_level ?? '—'}</td>
                    <td className="px-4 py-3 capitalize text-hub-muted">
                      {s.expected_device_type || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/tech/devices/new?student_id=${s.id}`}
                        className="spa-mgmt-btn-ghost px-3 py-1.5 text-xs no-underline"
                      >
                        Assign device
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {pendingStudents.length > 40 ? (
            <div className="border-t border-[var(--spa-mgmt-border)] px-4 py-2 text-xs text-hub-muted">
              Showing first 40 of {pendingStudents.length}. Use Assign / Add device to continue.
            </div>
          ) : null}
        </section>
      ) : null}

      {loading ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading devices…</div>
      ) : error && !records.length ? (
        <div className="alert alert-danger">{error}</div>
      ) : records.length === 0 ? (
        <div className="spa-mgmt-card border-dashed px-6 py-12 text-center shadow-sm">
          <i className="bi bi-laptop mb-2 text-2xl text-hub-muted" aria-hidden />
          <p className="mb-1 text-base font-semibold text-hub-text">No devices found</p>
          <p className="mb-4 text-sm text-hub-muted">
            Add inventory (assigned or unassigned), upload the CSV template, or adjust filters.
          </p>
          <Link to="/tech/devices/new" className="spa-mgmt-btn-primary px-4 py-2.5 text-sm no-underline">
            Add device
          </Link>
        </div>
      ) : (
        <div className="spa-mgmt-card overflow-hidden shadow-sm">
          {error ? <div className="alert alert-warning m-4 mb-0">{error}</div> : null}
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
                        <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-900">
                          Unassigned
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 align-top text-hub-muted">{row.cord_number || '—'}</td>
                    <td className="px-4 py-3 align-top text-hub-muted">
                      {row.operating_system || '—'}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="spa-mgmt-btn-ghost px-3 py-1.5 text-xs"
                          onClick={() => onFileRepair(row.id)}
                        >
                          File repair
                        </button>
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
                            if (!window.confirm('Remove this device from inventory?')) return
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
    </>
  )
}

function DevicesRepairTicketsPanel({
  prefillDeviceId,
  onClearPrefill,
}: {
  prefillDeviceId?: number
  onClearPrefill: () => void
}) {
  const [data, setData] = useState<any>(null)
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(Boolean(prefillDeviceId))
  const [form, setForm] = useState({
    device_id: prefillDeviceId ? String(prefillDeviceId) : '',
    title: '',
    description: '',
    category: 'hardware',
    severity: 'medium',
  })
  const [saving, setSaving] = useState(false)
  const [statusNotes, setStatusNotes] = useState<Record<number, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTechRepairTickets({ status, category, q }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load repair tickets')
    } finally {
      setLoading(false)
    }
  }, [status, category, q])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (prefillDeviceId) {
      setShowForm(true)
      setForm((prev) => ({ ...prev, device_id: String(prefillDeviceId) }))
    }
  }, [prefillDeviceId])

  const tickets = (data?.tickets || []) as any[]
  const devices = (data?.devices || []) as any[]
  const counts = data?.counts || {}

  const deviceOptions = useMemo(() => {
    return devices.map((d) => ({
      id: d.id,
      label: `${d.asset_name}${d.student?.name ? ` · ${d.student.name}` : ''}`,
    }))
  }, [devices])

  async function submitTicket(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const deviceId = Number(form.device_id)
      if (!deviceId) throw new Error('Select a device.')
      const res = await createTechRepairTicket({
        device_id: deviceId,
        title: form.title.trim(),
        description: form.description.trim(),
        category: form.category,
        severity: form.severity,
      })
      setMessage(res.message || 'Repair ticket created.')
      setForm({
        device_id: '',
        title: '',
        description: '',
        category: 'hardware',
        severity: 'medium',
      })
      setShowForm(false)
      onClearPrefill()
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not create ticket')
    } finally {
      setSaving(false)
    }
  }

  async function changeStatus(ticketId: number, nextStatus: string) {
    setMessage(null)
    try {
      const notes = (statusNotes[ticketId] || '').trim()
      const res = await updateTechRepairTicketStatus(ticketId, {
        status: nextStatus,
        resolution_notes: notes || undefined,
      })
      setMessage(res.message || 'Status updated.')
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not update status')
    }
  }

  return (
    <>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {[
          { key: 'total', label: 'Shown' },
          { key: 'hardware', label: 'Hardware' },
          { key: 'software', label: 'Software' },
          { key: 'open', label: 'Open' },
          { key: 'in_progress', label: 'In progress' },
          { key: 'repaired', label: 'Repaired' },
          { key: 'closed', label: 'Closed' },
        ].map((item) => (
          <article key={item.key} className="spa-mgmt-stat p-4 shadow-sm">
            <div className="text-2xl font-bold tabular-nums text-hub-text">
              {counts[item.key] ?? 0}
            </div>
            <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
              {item.label}
            </div>
          </article>
        ))}
      </div>

      <section className="spa-mgmt-card mb-4 overflow-hidden shadow-sm">
        <div className="spa-mgmt-accent-bar" />
        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="flex min-w-[9rem] flex-1 flex-col gap-1.5 sm:max-w-[12rem]">
            <span className={labelClass}>Category</span>
            <select
              className={fieldClass}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">All categories</option>
              {REPAIR_CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[9rem] flex-1 flex-col gap-1.5 sm:max-w-[12rem]">
            <span className={labelClass}>Status</span>
            <select className={fieldClass} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              {REPAIR_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[14rem] flex-[2] flex-col gap-1.5">
            <span className={labelClass}>Search</span>
            <input
              className={fieldClass}
              placeholder="Asset, student, or title…"
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
          <button
            type="button"
            className="spa-mgmt-btn-ghost px-4 py-2.5 text-sm"
            onClick={() => setShowForm((v) => !v)}
          >
            <i className="bi bi-plus-lg" aria-hidden />
            {showForm ? 'Hide form' : 'New ticket'}
          </button>
        </div>
      </section>

      {message ? (
        <div className="spa-mgmt-insight mb-4 px-4 py-3 text-sm font-medium">{message}</div>
      ) : null}

      {showForm ? (
        <form
          onSubmit={(e) => void submitTicket(e)}
          className="spa-mgmt-card mb-4 space-y-3 p-4 shadow-sm"
        >
          <h2 className="text-base font-bold text-hub-text">New repair ticket</h2>
          <label className="flex flex-col gap-1.5">
            <span className={labelClass}>Device</span>
            <select
              className={fieldClass}
              required
              value={form.device_id}
              onChange={(e) => setForm((prev) => ({ ...prev, device_id: e.target.value }))}
            >
              <option value="">Select device…</option>
              {deviceOptions.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className={labelClass}>Title</span>
            <input
              className={fieldClass}
              required
              maxLength={200}
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="e.g. Cracked screen / won’t charge"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className={labelClass}>Description</span>
            <textarea
              className={fieldClass}
              required
              rows={4}
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="What is wrong, when it started, and any troubleshooting tried…"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2 sm:max-w-xl">
            <label className="flex flex-col gap-1.5">
              <span className={labelClass}>Category</span>
              <select
                className={fieldClass}
                required
                value={form.category}
                onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}
              >
                {REPAIR_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className={labelClass}>Severity</span>
              <select
                className={fieldClass}
                value={form.severity}
                onChange={(e) => setForm((prev) => ({ ...prev, severity: e.target.value }))}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={saving}
              className="spa-mgmt-btn-primary px-4 py-2.5 text-sm disabled:opacity-60"
            >
              {saving ? 'Saving…' : 'Create ticket'}
            </button>
            <button
              type="button"
              className="spa-mgmt-btn-ghost px-4 py-2.5 text-sm"
              onClick={() => {
                setShowForm(false)
                onClearPrefill()
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {loading ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">
          Loading repair tickets…
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : tickets.length === 0 ? (
        <div className="spa-mgmt-card border-dashed px-6 py-12 text-center shadow-sm">
          <i className="bi bi-wrench-adjustable mb-2 text-2xl text-hub-muted" aria-hidden />
          <p className="mb-1 text-base font-semibold text-hub-text">No repair tickets</p>
          <p className="mb-4 text-sm text-hub-muted">
            Create a ticket when a device needs repair, or adjust your filters.
          </p>
          <button
            type="button"
            className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
            onClick={() => setShowForm(true)}
          >
            New ticket
          </button>
        </div>
      ) : (
        <div className="spa-mgmt-card overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[64rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--spa-mgmt-border)] bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_55%,var(--spa-mgmt-surface))]">
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Asset
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Student
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Title
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Category
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Severity
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Status
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Created
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-hub-muted">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((ticket) => (
                  <tr
                    key={ticket.id}
                    className="border-b border-[color-mix(in_srgb,var(--spa-mgmt-border)_70%,transparent)] last:border-b-0 hover:bg-[color-mix(in_srgb,var(--spa-mgmt-accent-soft)_40%,transparent)]"
                  >
                    <td className="px-4 py-3 align-top">
                      <div className="font-semibold text-hub-text">
                        {ticket.device?.asset_name || '—'}
                      </div>
                      <div className="mt-0.5 text-xs capitalize text-hub-muted">
                        {ticket.device?.device_type || ''}
                      </div>
                    </td>
                    <td className="px-4 py-3 align-top">
                      {ticket.device?.student ? (
                        <>
                          <div className="font-semibold text-hub-text">
                            {ticket.device.student.name}
                          </div>
                          <div className="mt-0.5 text-xs text-hub-muted">
                            Grade {ticket.device.student.grade_level ?? '—'}
                          </div>
                        </>
                      ) : (
                        <span className="text-hub-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="font-semibold text-hub-text">{ticket.title}</div>
                      <div className="mt-0.5 line-clamp-2 text-xs text-hub-muted">
                        {ticket.description}
                      </div>
                      {ticket.resolution_notes ? (
                        <div className="mt-1 text-xs text-emerald-800">
                          Notes: {ticket.resolution_notes}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold ${categoryBadgeClass(ticket.category)}`}
                      >
                        {ticket.category_label ||
                          (ticket.category === 'software'
                            ? 'Software Issues'
                            : 'Hardware Issues')}
                      </span>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold capitalize ${severityBadgeClass(ticket.severity)}`}
                      >
                        {ticket.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold capitalize ${statusBadgeClass(ticket.status)}`}
                      >
                        {String(ticket.status || '').replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 align-top text-hub-muted">
                      <div>{ticket.created_display || '—'}</div>
                      {ticket.creator?.username ? (
                        <div className="mt-0.5 text-xs">by {ticket.creator.username}</div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="flex min-w-[12rem] flex-col gap-2">
                        <select
                          className={fieldClass}
                          value={ticket.status}
                          onChange={(e) => void changeStatus(ticket.id, e.target.value)}
                        >
                          {REPAIR_STATUSES.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                        <input
                          className={fieldClass}
                          placeholder="Resolution notes…"
                          value={statusNotes[ticket.id] || ''}
                          onChange={(e) =>
                            setStatusNotes((prev) => ({ ...prev, [ticket.id]: e.target.value }))
                          }
                          onBlur={() => {
                            const notes = (statusNotes[ticket.id] || '').trim()
                            if (
                              notes &&
                              (ticket.status === 'repaired' || ticket.status === 'closed')
                            ) {
                              void changeStatus(ticket.id, ticket.status)
                            }
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

export function TechDeviceFormPage() {
  const { deviceId } = useParams()
  const id = deviceId ? Number(deviceId) : undefined
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const prefillStudentId = searchParams.get('student_id') || ''
  const [formMeta, setFormMeta] = useState<any>(null)
  const [form, setForm] = useState({
    device_type: 'laptop',
    asset_name: '',
    device_name: '',
    cord_number: '',
    operating_system: 'ChromeOS',
    student_id: prefillStudentId,
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
        } else if (prefillStudentId) {
          const match = (data.students || []).find(
            (s: any) => String(s.id) === String(prefillStudentId),
          )
          setForm((prev) => ({
            ...prev,
            student_id: prefillStudentId,
            device_type: match?.expected_device_type || prev.device_type,
          }))
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load form'))
  }, [id, prefillStudentId])

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
              Tech · Devices
            </p>
            <h1 className="mb-0 text-3xl font-bold tracking-tight">
              {id ? 'Edit device' : 'Add device'}
            </h1>
            <p className="mb-0 mt-2 text-sm spa-mgmt-hero-muted">
              Assign to a student now, or leave unassigned as stock inventory.
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
              const studentId = form.student_id ? Number(form.student_id) : null
              await saveTechDevice(
                {
                  device_type: form.device_type,
                  asset_name: form.asset_name,
                  device_name: form.device_name,
                  cord_number: form.cord_number,
                  operating_system: form.operating_system,
                  student_id: studentId,
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
              <span className={labelClass}>Student (optional)</span>
              <select
                className={fieldClass}
                value={form.student_id}
                onChange={(e) => {
                  const nextId = e.target.value
                  const match = (formMeta.students || []).find(
                    (s: any) => String(s.id) === nextId,
                  )
                  setForm((f) => ({
                    ...f,
                    student_id: nextId,
                    device_type: match?.expected_device_type || f.device_type,
                  }))
                }}
              >
                <option value="">Unassigned (stock inventory)</option>
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
