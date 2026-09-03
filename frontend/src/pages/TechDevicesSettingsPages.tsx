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

function ticketCodeOf(ticket: { ticket_code?: string; id?: number }) {
  if (ticket.ticket_code) return ticket.ticket_code
  if (ticket.id != null) return `RT-${String(ticket.id).padStart(4, '0')}`
  return 'RT-????'
}

function severityStripeClass(severity: string) {
  switch (severity) {
    case 'critical':
      return 'bg-red-500'
    case 'high':
      return 'bg-orange-500'
    case 'low':
      return 'bg-slate-400'
    default:
      return 'bg-amber-400'
  }
}

function creatorLabel(person: { name?: string; username?: string } | null | undefined) {
  if (!person) return null
  return (person.name || person.username || '').trim() || null
}

const ACTIVE_LANES = [
  {
    key: 'open',
    label: 'Open',
    hint: 'Needs triage',
    tone: 'border-rose-200/80 bg-rose-50/40',
  },
  {
    key: 'in_progress',
    label: 'In progress',
    hint: 'On the bench',
    tone: 'border-sky-200/80 bg-sky-50/40',
  },
  {
    key: 'repaired',
    label: 'Ready',
    hint: 'Fixed — awaiting close',
    tone: 'border-emerald-200/80 bg-emerald-50/40',
  },
] as const

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
      label: 'Repair desk',
      icon: 'bi-wrench-adjustable',
      hint: 'Student ticket IDs, active bench, and a separate closed archive.',
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
                    Color
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
                    <td className="px-4 py-3 align-top text-hub-muted">
                      {String(row.device_type).toLowerCase() === 'laptop'
                        ? row.color_label || row.color || '—'
                        : '—'}
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
  const [board, setBoard] = useState<'active' | 'closed'>('active')
  const [category, setCategory] = useState('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)
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
  const [viewTicket, setViewTicket] = useState<any | null>(null)
  const [savingTicketId, setSavingTicketId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchTechRepairTickets({
        board,
        category,
        q,
      })
      setData(payload)
      const seeded: Record<number, string> = {}
      for (const ticket of payload?.tickets || []) {
        seeded[ticket.id] = ticket.resolution_notes || ''
      }
      setStatusNotes(seeded)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load repair tickets')
    } finally {
      setLoading(false)
    }
  }, [board, category, q])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (prefillDeviceId) {
      setShowForm(true)
      setBoard('active')
      setForm((prev) => ({ ...prev, device_id: String(prefillDeviceId) }))
    }
  }, [prefillDeviceId])

  const tickets = (data?.tickets || []) as any[]
  const devices = (data?.devices || []) as any[]
  const counts = data?.counts || {}

  const activeTickets = useMemo(
    () => tickets.filter((t) => t.status !== 'closed'),
    [tickets],
  )
  const closedTickets = useMemo(
    () => tickets.filter((t) => t.status === 'closed'),
    [tickets],
  )
  const visibleTickets = board === 'closed' ? closedTickets : activeTickets

  const laneTickets = useMemo(() => {
    const map: Record<string, any[]> = {
      open: [],
      in_progress: [],
      repaired: [],
    }
    for (const ticket of activeTickets) {
      const key = ticket.status in map ? ticket.status : 'open'
      map[key].push(ticket)
    }
    return map
  }, [activeTickets])

  const deviceOptions = useMemo(() => {
    return devices.map((d) => ({
      id: d.id,
      label: `${d.asset_name}${d.student?.name ? ` · ${d.student.name}` : ''}`,
    }))
  }, [devices])

  async function copyTicketCode(code: string) {
    try {
      await navigator.clipboard.writeText(code)
      setCopiedCode(code)
      window.setTimeout(() => setCopiedCode((prev) => (prev === code ? null : prev)), 1600)
    } catch {
      setMessage(`Ticket ID: ${code}`)
    }
  }

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
      const code = ticketCodeOf(res.ticket || {})
      setMessage(
        res.ticket
          ? `Ticket ${code} created — give this ID to the student.`
          : res.message || 'Repair ticket created.',
      )
      setForm({
        device_id: '',
        title: '',
        description: '',
        category: 'hardware',
        severity: 'medium',
      })
      setShowForm(false)
      onClearPrefill()
      setBoard('active')
      if (res.ticket) setViewTicket(res.ticket)
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not create ticket')
    } finally {
      setSaving(false)
    }
  }

  async function persistTicket(
    ticketId: number,
    nextStatus: string,
    notesOverride?: string,
  ) {
    setSavingTicketId(ticketId)
    setMessage(null)
    try {
      const notes =
        notesOverride !== undefined
          ? notesOverride.trim()
          : (statusNotes[ticketId] || '').trim()
      const res = await updateTechRepairTicketStatus(ticketId, {
        status: nextStatus,
        resolution_notes: notes,
      })
      setMessage(res.message || 'Ticket updated.')
      if (viewTicket?.id === ticketId && res.ticket) {
        setViewTicket(res.ticket)
      }
      if (nextStatus === 'closed') setBoard('closed')
      else if (board === 'closed' && nextStatus !== 'closed') setBoard('active')
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not update ticket')
    } finally {
      setSavingTicketId(null)
    }
  }

  async function saveResolutionNotes(ticket: any, notesValue?: string) {
    const notes = (notesValue ?? statusNotes[ticket.id] ?? '').trim()
    const previous = (ticket.resolution_notes || '').trim()
    if (notes === previous) return
    await persistTicket(ticket.id, ticket.status, notes)
  }

  function renderTicketCard(ticket: any) {
    const code = ticketCodeOf(ticket)
    const busy = savingTicketId === ticket.id
    return (
      <article
        key={ticket.id}
        className="group relative overflow-hidden rounded-2xl border border-[color-mix(in_srgb,var(--spa-mgmt-border)_85%,transparent)] bg-[var(--spa-mgmt-surface)] shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
      >
        <div
          className={`absolute inset-y-0 left-0 w-1.5 ${severityStripeClass(ticket.severity)}`}
          aria-hidden
        />
        <div className="space-y-3 p-3.5 pl-4">
          <div className="flex items-start justify-between gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-2.5 py-1 font-mono text-xs font-bold tracking-wide text-amber-300 shadow-sm transition hover:bg-slate-800"
              title="Copy ticket ID for the student"
              onClick={() => void copyTicketCode(code)}
            >
              <i className="bi bi-ticket-perforated" aria-hidden />
              {code}
              <i
                className={`bi ${copiedCode === code ? 'bi-check-lg text-emerald-300' : 'bi-clipboard'} text-[0.7rem] opacity-80`}
                aria-hidden
              />
            </button>
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide ${severityBadgeClass(ticket.severity)}`}
            >
              {ticket.severity}
            </span>
          </div>

          <div>
            <h3 className="line-clamp-2 text-sm font-bold leading-snug text-hub-text">
              {ticket.title}
            </h3>
            <p className="mt-1 text-xs text-hub-muted">
              <span className="font-semibold text-hub-text">
                {ticket.device?.asset_name || 'Device'}
              </span>
              {ticket.device?.student?.name ? ` · ${ticket.device.student.name}` : ''}
            </p>
          </div>

          <div className="flex flex-wrap gap-1.5">
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-[0.65rem] font-bold ${categoryBadgeClass(ticket.category)}`}
            >
              {ticket.category === 'software' ? 'Software' : 'Hardware'}
            </span>
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-[0.65rem] font-bold capitalize ${statusBadgeClass(ticket.status)}`}
            >
              {String(ticket.status || '').replace('_', ' ')}
            </span>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="spa-mgmt-btn-ghost flex-1 px-2.5 py-2 text-xs"
              onClick={() => setViewTicket(ticket)}
            >
              <i className="bi bi-eye me-1" aria-hidden />
              Open
            </button>
            <select
              className={`${fieldClass} flex-[1.4] py-2 text-xs`}
              value={ticket.status}
              disabled={busy}
              aria-label={`Status for ${code}`}
              onChange={(e) => void persistTicket(ticket.id, e.target.value)}
            >
              {REPAIR_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </article>
    )
  }

  return (
    <>
      <section className="relative mb-5 overflow-hidden rounded-3xl border border-[color-mix(in_srgb,var(--spa-mgmt-accent)_28%,var(--spa-mgmt-border))] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--spa-mgmt-accent-soft)_70%,#fff)_0%,var(--spa-mgmt-surface)_48%,color-mix(in_srgb,#0f172a_6%,var(--spa-mgmt-surface))_100%)] p-5 shadow-sm sm:p-6">
        <div
          className="pointer-events-none absolute -right-8 -top-10 h-40 w-40 rounded-full bg-[color-mix(in_srgb,var(--spa-mgmt-accent)_18%,transparent)] blur-2xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute bottom-0 left-8 h-24 w-56 opacity-[0.12]"
          style={{
            backgroundImage:
              'repeating-linear-gradient(-45deg, transparent, transparent 8px, currentColor 8px, currentColor 9px)',
            color: 'var(--spa-mgmt-accent-deep)',
          }}
          aria-hidden
        />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-1 text-[0.7rem] font-bold uppercase tracking-[0.2em] text-[var(--spa-mgmt-accent-deep)]">
              Tech repair desk
            </p>
            <h2 className="mb-1 text-2xl font-bold tracking-tight text-hub-text">
              Hand students a ticket ID
            </h2>
            <p className="mb-0 max-w-xl text-sm text-hub-muted">
              Every repair gets a code like{' '}
              <span className="rounded bg-slate-900 px-1.5 py-0.5 font-mono text-xs font-bold text-amber-300">
                RT-0042
              </span>
              . Active work stays on the bench; closed tickets live in the archive.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
              onClick={() => setShowForm(true)}
            >
              <i className="bi bi-plus-lg" aria-hidden />
              New ticket
            </button>
          </div>
        </div>
        <div className="relative mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { key: 'active', label: 'On the bench', value: counts.active ?? activeTickets.length },
            { key: 'open', label: 'Open', value: counts.open ?? 0 },
            { key: 'in_progress', label: 'In progress', value: counts.in_progress ?? 0 },
            { key: 'closed', label: 'Closed archive', value: counts.closed ?? 0 },
          ].map((stat) => (
            <div
              key={stat.key}
              className="rounded-2xl border border-white/70 bg-white/70 px-4 py-3 backdrop-blur-[2px]"
            >
              <div className="text-2xl font-bold tabular-nums text-hub-text">{stat.value}</div>
              <div className="text-[0.7rem] font-bold uppercase tracking-wide text-hub-muted">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div
          className="inline-flex rounded-2xl border border-[var(--spa-mgmt-border)] bg-[var(--spa-mgmt-surface)] p-1 shadow-sm"
          role="tablist"
          aria-label="Repair board"
        >
          <button
            type="button"
            role="tab"
            aria-selected={board === 'active'}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              board === 'active'
                ? 'bg-[var(--spa-mgmt-accent)] text-white shadow-sm'
                : 'text-hub-muted hover:text-hub-text'
            }`}
            onClick={() => setBoard('active')}
          >
            <i className="bi bi-kanban me-1" aria-hidden />
            Active bench
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={board === 'closed'}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              board === 'closed'
                ? 'bg-slate-800 text-white shadow-sm'
                : 'text-hub-muted hover:text-hub-text'
            }`}
            onClick={() => setBoard('closed')}
          >
            <i className="bi bi-archive me-1" aria-hidden />
            Closed archive
            {(counts.closed ?? 0) > 0 ? (
              <span className="ms-1.5 inline-flex min-w-[1.25rem] justify-center rounded-full bg-white/20 px-1.5 text-[0.7rem] tabular-nums">
                {counts.closed}
              </span>
            ) : null}
          </button>
        </div>
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
          <label className="flex min-w-[14rem] flex-[2] flex-col gap-1.5">
            <span className={labelClass}>Search</span>
            <input
              className={fieldClass}
              placeholder="Ticket ID (RT-0042), asset, student, or title…"
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

      {showForm ? (
        <form
          onSubmit={(e) => void submitTicket(e)}
          className="spa-mgmt-card mb-4 space-y-3 overflow-hidden p-0 shadow-sm"
        >
          <div className="spa-mgmt-accent-bar" />
          <div className="space-y-3 p-4">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 className="text-base font-bold text-hub-text">New repair ticket</h2>
                <p className="mb-0 text-xs text-hub-muted">
                  After save, copy the ticket ID and give it to the student.
                </p>
              </div>
            </div>
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
                rows={3}
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
          </div>
        </form>
      ) : null}

      {loading ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">
          Loading repair desk…
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : visibleTickets.length === 0 ? (
        <div className="spa-mgmt-card border-dashed px-6 py-12 text-center shadow-sm">
          <i
            className={`bi ${board === 'closed' ? 'bi-archive' : 'bi-wrench-adjustable'} mb-2 text-2xl text-hub-muted`}
            aria-hidden
          />
          <p className="mb-1 text-base font-semibold text-hub-text">
            {board === 'closed' ? 'No closed tickets' : 'Bench is clear'}
          </p>
          <p className="mb-4 text-sm text-hub-muted">
            {board === 'closed'
              ? 'Closed repairs will appear here, separate from active work.'
              : 'Create a ticket when a device needs repair, or adjust your filters.'}
          </p>
          {board === 'active' ? (
            <button
              type="button"
              className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
              onClick={() => setShowForm(true)}
            >
              New ticket
            </button>
          ) : null}
        </div>
      ) : board === 'active' ? (
        <div className="grid gap-4 xl:grid-cols-3">
          {ACTIVE_LANES.map((lane) => (
            <section
              key={lane.key}
              className={`rounded-3xl border p-3 ${lane.tone}`}
            >
              <header className="mb-3 flex items-baseline justify-between gap-2 px-1">
                <div>
                  <h3 className="mb-0 text-sm font-bold text-hub-text">{lane.label}</h3>
                  <p className="mb-0 text-[0.7rem] text-hub-muted">{lane.hint}</p>
                </div>
                <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs font-bold tabular-nums text-hub-text shadow-sm">
                  {laneTickets[lane.key]?.length || 0}
                </span>
              </header>
              <div className="flex max-h-[70vh] flex-col gap-3 overflow-y-auto pe-1">
                {(laneTickets[lane.key] || []).map((ticket) => renderTicketCard(ticket))}
                {(laneTickets[lane.key] || []).length === 0 ? (
                  <p className="rounded-2xl border border-dashed border-black/10 bg-white/40 px-3 py-6 text-center text-xs text-hub-muted">
                    Nothing here
                  </p>
                ) : null}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {closedTickets.map((ticket) => renderTicketCard(ticket))}
        </div>
      )}

      {viewTicket ? (
        <div
          className="fixed inset-0 z-[1600] flex items-center justify-center bg-slate-900/55 p-4 backdrop-blur-[2px]"
          onClick={() => setViewTicket(null)}
        >
          <div
            className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-[var(--spa-mgmt-surface)] shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby={`repair-ticket-${viewTicket.id}-title`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-[var(--spa-mgmt-border)] px-5 py-4">
              <div className="min-w-0">
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-2.5 py-1 font-mono text-xs font-bold tracking-wide text-amber-300"
                  onClick={() => void copyTicketCode(ticketCodeOf(viewTicket))}
                >
                  <i className="bi bi-ticket-perforated" aria-hidden />
                  {ticketCodeOf(viewTicket)}
                  <i
                    className={`bi ${
                      copiedCode === ticketCodeOf(viewTicket)
                        ? 'bi-check-lg text-emerald-300'
                        : 'bi-clipboard'
                    } text-[0.7rem] opacity-80`}
                    aria-hidden
                  />
                </button>
                <p className="mt-2 mb-0 text-xs text-hub-muted">
                  Give this ID to the student · click to copy
                </p>
                <h2
                  id={`repair-ticket-${viewTicket.id}-title`}
                  className="mt-2 text-lg font-bold text-hub-text"
                >
                  {viewTicket.title}
                </h2>
              </div>
              <button
                type="button"
                className="spa-mgmt-btn-ghost shrink-0 px-3 py-2 text-sm"
                onClick={() => setViewTicket(null)}
                aria-label="Close"
              >
                <i className="bi bi-x-lg" aria-hidden />
              </button>
            </div>
            <div className="space-y-4 overflow-y-auto px-5 py-4 text-sm">
              <div className="flex flex-wrap gap-2">
                <span
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold ${categoryBadgeClass(viewTicket.category)}`}
                >
                  {viewTicket.category_label || viewTicket.category}
                </span>
                <span
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold capitalize ${severityBadgeClass(viewTicket.severity)}`}
                >
                  {viewTicket.severity}
                </span>
                <span
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold capitalize ${statusBadgeClass(viewTicket.status)}`}
                >
                  {String(viewTicket.status || '').replace('_', ' ')}
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <div className={labelClass}>Asset</div>
                  <div className="mt-1 font-semibold text-hub-text">
                    {viewTicket.device?.asset_name || '—'}
                  </div>
                  <div className="text-xs capitalize text-hub-muted">
                    {viewTicket.device?.device_type || ''}
                    {viewTicket.device?.color_label ? ` · ${viewTicket.device.color_label}` : ''}
                  </div>
                </div>
                <div>
                  <div className={labelClass}>Student</div>
                  <div className="mt-1 font-semibold text-hub-text">
                    {viewTicket.device?.student?.name || '—'}
                  </div>
                  {viewTicket.device?.student ? (
                    <div className="text-xs text-hub-muted">
                      Grade {viewTicket.device.student.grade_level ?? '—'}
                      {viewTicket.device.student.student_id
                        ? ` · ${viewTicket.device.student.student_id}`
                        : ''}
                    </div>
                  ) : null}
                </div>
              </div>
              <div>
                <div className={labelClass}>Description</div>
                <p className="mt-1 whitespace-pre-wrap text-hub-text">
                  {viewTicket.description || '—'}
                </p>
              </div>
              <label className="flex flex-col gap-1.5">
                <span className={labelClass}>Status</span>
                <select
                  className={fieldClass}
                  value={viewTicket.status}
                  disabled={savingTicketId === viewTicket.id}
                  onChange={(e) => void persistTicket(viewTicket.id, e.target.value)}
                >
                  {REPAIR_STATUSES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5">
                <span className={labelClass}>Resolution notes</span>
                <textarea
                  className={`${fieldClass} min-h-[5rem] resize-y`}
                  rows={3}
                  placeholder="What fixed it, parts used, follow-up…"
                  value={statusNotes[viewTicket.id] ?? ''}
                  disabled={savingTicketId === viewTicket.id}
                  onChange={(e) =>
                    setStatusNotes((prev) => ({
                      ...prev,
                      [viewTicket.id]: e.target.value,
                    }))
                  }
                  onBlur={(e) => {
                    void saveResolutionNotes(viewTicket, e.target.value)
                  }}
                />
              </label>
              <button
                type="button"
                className="spa-mgmt-btn-primary px-3 py-2 text-sm disabled:opacity-60"
                disabled={savingTicketId === viewTicket.id}
                onClick={() => void saveResolutionNotes(viewTicket)}
              >
                {savingTicketId === viewTicket.id ? 'Saving…' : 'Save notes'}
              </button>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <div className={labelClass}>Created</div>
                  <div className="mt-1 text-hub-text">{viewTicket.created_display || '—'}</div>
                  {creatorLabel(viewTicket.creator) ? (
                    <div className="text-xs text-hub-muted">
                      by {creatorLabel(viewTicket.creator)}
                    </div>
                  ) : null}
                </div>
                <div>
                  <div className={labelClass}>Resolved</div>
                  <div className="mt-1 text-hub-text">{viewTicket.resolved_display || '—'}</div>
                  {creatorLabel(viewTicket.resolver) ? (
                    <div className="text-xs text-hub-muted">
                      by {creatorLabel(viewTicket.resolver)}
                    </div>
                  ) : null}
                </div>
              </div>
              {viewTicket.updated_display ? (
                <div className="text-xs text-hub-muted">
                  Last updated {viewTicket.updated_display}
                </div>
              ) : null}
            </div>
            <div className="flex justify-end border-t border-[var(--spa-mgmt-border)] px-5 py-3">
              <button
                type="button"
                className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
                onClick={() => setViewTicket(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      ) : null}
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
    color: 'black',
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
          const dtype = data.device.device_type || 'laptop'
          setForm({
            device_type: dtype,
            asset_name: data.device.asset_name || '',
            device_name: data.device.device_name || '',
            color: dtype === 'laptop' ? data.device.color || 'black' : '',
            cord_number: data.device.cord_number || '',
            operating_system: data.device.operating_system || 'ChromeOS',
            student_id: String(data.device.student_id || ''),
          })
        } else if (prefillStudentId) {
          const match = (data.students || []).find(
            (s: any) => String(s.id) === String(prefillStudentId),
          )
          const nextType = match?.expected_device_type || 'laptop'
          setForm((prev) => ({
            ...prev,
            student_id: prefillStudentId,
            device_type: nextType,
            color: nextType === 'laptop' ? prev.color || 'black' : '',
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
              const payload: Record<string, unknown> = {
                device_type: form.device_type,
                asset_name: form.asset_name,
                device_name: form.device_name,
                cord_number: form.cord_number,
                operating_system: form.operating_system,
                student_id: studentId,
              }
              if (form.device_type === 'laptop') {
                payload.color = form.color
              }
              await saveTechDevice(payload, id)
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
                onChange={(e) => {
                  const nextType = e.target.value
                  setForm((f) => ({
                    ...f,
                    device_type: nextType,
                    color: nextType === 'laptop' ? f.color || 'black' : '',
                  }))
                }}
              >
                {(formMeta.device_types || ['laptop', 'tablet']).map((t: string) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            {form.device_type === 'laptop' ? (
              <label className="flex flex-col gap-1.5">
                <span className={labelClass}>Color</span>
                <select
                  className={fieldClass}
                  required
                  value={form.color}
                  onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))}
                >
                  <option value="">Select color…</option>
                  {(formMeta.device_colors || [
                    { value: 'black', label: 'Black' },
                    { value: 'silver', label: 'Silver' },
                    { value: 'black_carbon', label: 'Black Carbon' },
                  ]).map((opt: { value: string; label: string }) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
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
                    color:
                      (match?.expected_device_type || f.device_type) === 'laptop'
                        ? f.color || 'black'
                        : '',
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
