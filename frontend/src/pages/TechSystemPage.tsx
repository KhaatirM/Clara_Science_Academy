import { useCallback, useEffect, useState } from 'react'
import { fetchTechSystem, postTechSystemAction } from '../api/tech'
import {
  ManagementPageHero,
  ManagementPageShell,
} from '../components/layout/ManagementPageShell'

const SYSTEM_CONFIG_FIELDS: Record<string, { label: string; options: string[] }> = {
  debug_mode: {
    label: 'Server mode',
    options: ['Development Server', 'Production Server'],
  },
  database_path: {
    label: 'Database path',
    options: ['instance/app.db'],
  },
  max_upload_size: {
    label: 'Max upload size',
    options: ['8 MB', '16 MB', '32 MB', '64 MB', '128 MB'],
  },
  session_timeout: {
    label: 'Session timeout',
    options: ['1 hour', '4 hours', '8 hours', '24 hours', '48 hours', '7 days'],
  },
  backup_location: {
    label: 'Backup location',
    options: ['backups/'],
  },
  log_level: {
    label: 'Log level',
    options: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
  },
}

const SCHOOL_TIMEZONE_OPTIONS = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Phoenix',
  'America/Anchorage',
  'Pacific/Honolulu',
]

const MAINT_DURATION_OPTIONS = [
  { value: '15', label: '15 minutes' },
  { value: '30', label: '30 minutes' },
  { value: '60', label: '1 hour' },
  { value: '90', label: '1.5 hours' },
  { value: '120', label: '2 hours' },
  { value: '180', label: '3 hours' },
  { value: '240', label: '4 hours' },
  { value: '360', label: '6 hours' },
  { value: '480', label: '8 hours' },
  { value: '720', label: '12 hours' },
  { value: '1440', label: '24 hours' },
  { value: '2880', label: '2 days' },
  { value: '10080', label: '7 days' },
]

const MAINT_REASON_OPTIONS = [
  'Scheduled maintenance',
  'System upgrade',
  'Database maintenance',
  'Security update',
  'Emergency maintenance',
  'Performance tuning',
]

const MAINT_MESSAGE_OPTIONS = [
  'System is under maintenance. Please check back later.',
  'We are performing scheduled updates. The portal will return shortly.',
  'Clara Science Academy portal is temporarily unavailable for maintenance.',
  'Emergency maintenance is in progress. Thank you for your patience.',
]

function withCurrentOption(options: string[], current: string | null | undefined) {
  const value = (current || '').trim()
  if (value && !options.includes(value)) return [value, ...options]
  return options
}

function formatUptime(raw: unknown) {
  if (raw == null || raw === '') return '—'
  const text = String(raw)
  return text.replace(/\.\d+$/, '') || text
}

function ResourceMeter({
  label,
  icon,
  percent,
  detail,
}: {
  label: string
  icon: string
  percent: number | null | undefined
  detail?: string
}) {
  const pct =
    percent == null || Number.isNaN(Number(percent))
      ? null
      : Math.max(0, Math.min(100, Number(percent)))
  const barTone =
    pct == null
      ? 'bg-[var(--spa-mgmt-accent)]'
      : pct >= 90
        ? 'bg-red-500'
        : pct >= 75
          ? 'bg-amber-500'
          : 'bg-[var(--spa-mgmt-accent)]'

  return (
    <article className="spa-mgmt-card overflow-hidden shadow-sm">
      <div className="spa-mgmt-accent-bar" />
      <div className="p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <p className="mb-0 text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</p>
            <p className="mb-0 mt-1 text-2xl font-bold tabular-nums text-hub-text">
              {pct == null ? '—' : `${pct.toFixed(pct % 1 === 0 ? 0 : 1)}%`}
            </p>
          </div>
          <span className="spa-mgmt-avatar h-10 w-10 text-base">
            <i className={`bi ${icon}`} aria-hidden />
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-black/5">
          <div
            className={`h-full rounded-full transition-all ${barTone}`}
            style={{ width: `${pct ?? 0}%` }}
          />
        </div>
        {detail ? <p className="mb-0 mt-2 text-xs text-hub-muted">{detail}</p> : null}
      </div>
    </article>
  )
}

function PortalStat({
  label,
  value,
  icon,
}: {
  label: string
  value: string | number
  icon: string
}) {
  return (
    <article className="spa-mgmt-stat flex items-center gap-3 p-4 shadow-sm">
      <span className="spa-mgmt-avatar h-9 w-9 shrink-0 text-sm">
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div className="min-w-0">
        <div className="truncate text-lg font-bold tabular-nums text-hub-text">{value}</div>
        <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
      </div>
    </article>
  )
}

export function TechSystemPage() {
  const [tab, setTab] = useState<'status' | 'config' | 'maintenance'>('status')
  const [data, setData] = useState<any>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<Record<string, string>>({})
  const [tz, setTz] = useState('')
  const [theme, setTheme] = useState('')
  const [maint, setMaint] = useState({
    duration_minutes: '60',
    reason: MAINT_REASON_OPTIONS[0],
    maintenance_message: MAINT_MESSAGE_OPTIONS[0],
  })

  const load = useCallback(async () => {
    setError(null)
    try {
      const payload = await fetchTechSystem()
      setData(payload)
      setConfig(payload.config || {})
      setTz(payload.school_timezone?.db_raw || payload.school_timezone?.effective || '')
      setTheme(payload.site_theme_override || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load system')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function run(path: Parameters<typeof postTechSystemAction>[0], body?: Record<string, unknown>) {
    setMessage(null)
    try {
      const res = await postTechSystemAction(path, body)
      setMessage(res.message || 'Done')
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Action failed')
    }
  }

  const fieldClass =
    'w-full rounded-xl border border-[color-mix(in_srgb,var(--spa-mgmt-accent)_22%,var(--spa-mgmt-border))] bg-[var(--spa-mgmt-surface)] px-3 py-2.5 text-sm text-hub-text shadow-sm outline-none transition focus:border-[var(--spa-mgmt-accent)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--spa-mgmt-accent)_25%,transparent)]'
  const labelClass = 'text-xs font-semibold uppercase tracking-wide text-hub-muted'

  const tabMeta = {
    status: { label: 'Status', icon: 'bi-speedometer2', hint: 'Health, capacity, and server actions' },
    config: { label: 'Config', icon: 'bi-sliders', hint: 'Approved server, timezone, and theme settings' },
    maintenance: { label: 'Maintenance', icon: 'bi-tools', hint: 'Control the public maintenance window' },
  } as const

  const status = data?.status || {}
  const maintenanceOn = Boolean(status.is_maintenance_mode || data?.maintenance?.is_active)

  return (
    <ManagementPageShell>
      <ManagementPageHero className="mb-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.18em] spa-mgmt-hero-muted">
              Tech · Server
            </p>
            <h1 className="mb-0 text-3xl font-bold tracking-tight">System</h1>
            <p className="mb-0 mt-2 max-w-xl text-sm spa-mgmt-hero-muted">{tabMeta[tab].hint}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold text-white">
              <i className="bi bi-clock" aria-hidden />
              {data?.school_timezone?.now_sample || 'School time —'}
            </span>
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${
                maintenanceOn ? 'bg-amber-300 text-amber-950' : 'bg-emerald-300/90 text-emerald-950'
              }`}
            >
              <i className={`bi ${maintenanceOn ? 'bi-tools' : 'bi-check-circle'}`} aria-hidden />
              {maintenanceOn ? 'Maintenance on' : 'Portal online'}
            </span>
          </div>
        </div>
      </ManagementPageHero>

      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="System sections">
        {(['status', 'config', 'maintenance'] as const).map((t) => (
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

      {message ? (
        <div className="spa-mgmt-insight mb-4 px-4 py-3 text-sm font-medium">{message}</div>
      ) : null}
      {error ? <div className="alert alert-danger mb-4">{error}</div> : null}

      {!data ? (
        <div className="spa-mgmt-card p-8 text-center text-hub-muted shadow-sm">Loading system…</div>
      ) : tab === 'status' ? (
        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-3">
            <ResourceMeter
              label="CPU"
              icon="bi-cpu"
              percent={status.cpu_percent}
              detail="Processor utilization"
            />
            <ResourceMeter
              label="Memory"
              icon="bi-memory"
              percent={status.memory_percent}
              detail={
                status.memory_used_gb != null && status.memory_total_gb != null
                  ? `${status.memory_used_gb} / ${status.memory_total_gb} GB used`
                  : undefined
              }
            />
            <ResourceMeter
              label="Disk"
              icon="bi-device-hdd"
              percent={status.disk_percent}
              detail={
                status.disk_used_gb != null && status.disk_total_gb != null
                  ? `${status.disk_used_gb} / ${status.disk_total_gb} GB used`
                  : undefined
              }
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <PortalStat label="Users" value={status.total_users ?? '—'} icon="bi-people" />
            <PortalStat label="Students" value={status.total_students ?? '—'} icon="bi-mortarboard" />
            <PortalStat label="Teachers" value={status.total_teachers ?? '—'} icon="bi-person-workspace" />
            <PortalStat label="Open bugs" value={status.open_bugs ?? '—'} icon="bi-bug" />
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            <article className="spa-mgmt-card p-4 shadow-sm lg:col-span-2">
              <h2 className="mb-3 text-sm font-bold text-hub-text">Server snapshot</h2>
              <dl className="grid gap-3 sm:grid-cols-2">
                <div>
                  <dt className={labelClass}>Uptime</dt>
                  <dd className="mb-0 mt-1 text-sm font-semibold text-hub-text">
                    {formatUptime(status.uptime)}
                  </dd>
                </div>
                <div>
                  <dt className={labelClass}>School time</dt>
                  <dd className="mb-0 mt-1 text-sm font-semibold text-hub-text">
                    {data.school_timezone?.now_sample || '—'}
                  </dd>
                </div>
                <div>
                  <dt className={labelClass}>Activity (24h)</dt>
                  <dd className="mb-0 mt-1 text-sm font-semibold text-hub-text">
                    {status.recent_activities ?? '—'} events · {status.recent_errors ?? 0} errors
                  </dd>
                </div>
                <div>
                  <dt className={labelClass}>Runtime</dt>
                  <dd className="mb-0 mt-1 text-sm font-semibold text-hub-text">
                    {data.system_info?.python_version
                      ? `Python ${data.system_info.python_version}`
                      : '—'}
                    {data.system_info?.flask_version
                      ? ` · Flask ${data.system_info.flask_version}`
                      : ''}
                    {data.system_info?.server ? ` · ${data.system_info.server}` : ''}
                  </dd>
                </div>
              </dl>
            </article>

            <article className="spa-mgmt-card p-4 shadow-sm">
              <h2 className="mb-3 text-sm font-bold text-hub-text">Quick actions</h2>
              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  className="spa-mgmt-btn-ghost justify-start px-3 py-2.5 text-sm"
                  onClick={() => void run('backup')}
                >
                  <i className="bi bi-database-down" aria-hidden />
                  Backup database
                </button>
                <button
                  type="button"
                  className="spa-mgmt-btn-ghost justify-start px-3 py-2.5 text-sm"
                  onClick={() => void run('integrity')}
                >
                  <i className="bi bi-shield-check" aria-hidden />
                  Integrity check
                </button>
                <button
                  type="button"
                  className="spa-mgmt-btn-ghost justify-start px-3 py-2.5 text-sm"
                  onClick={() => void run('clear-cache')}
                >
                  <i className="bi bi-trash3" aria-hidden />
                  Clear cache
                </button>
              </div>
            </article>
          </div>
        </div>
      ) : tab === 'config' ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <section className="spa-mgmt-card overflow-hidden shadow-sm">
            <div className="spa-mgmt-accent-bar" />
            <div className="p-5">
              <div className="mb-4 flex items-start gap-3">
                <span className="spa-mgmt-avatar h-10 w-10 text-base">
                  <i className="bi bi-gear" aria-hidden />
                </span>
                <div>
                  <h2 className="mb-0 text-base font-bold text-hub-text">App configuration</h2>
                  <p className="mb-0 mt-1 text-sm text-hub-muted">
                    Pick from approved values only — no free typing.
                  </p>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {Object.keys(SYSTEM_CONFIG_FIELDS).map((key) => {
                  const meta = SYSTEM_CONFIG_FIELDS[key]
                  const current = config[key] || ''
                  const options = withCurrentOption(meta.options, current)
                  return (
                    <label key={key} className="flex flex-col gap-1.5">
                      <span className={labelClass}>{meta.label}</span>
                      <select
                        className={fieldClass}
                        value={current}
                        onChange={(e) => setConfig((c) => ({ ...c, [key]: e.target.value }))}
                      >
                        {options.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    </label>
                  )
                })}
              </div>
              <button
                type="button"
                className="spa-mgmt-btn-primary mt-5 px-4 py-2.5 text-sm"
                onClick={() => void run('config', config)}
              >
                <i className="bi bi-check2-circle" aria-hidden />
                Save config
              </button>
            </div>
          </section>

          <div className="space-y-4">
            <section className="spa-mgmt-card overflow-hidden shadow-sm">
              <div className="spa-mgmt-accent-bar" />
              <div className="p-5">
                <div className="mb-4 flex items-start gap-3">
                  <span className="spa-mgmt-avatar h-10 w-10 text-base">
                    <i className="bi bi-globe-americas" aria-hidden />
                  </span>
                  <div>
                    <h2 className="mb-0 text-base font-bold text-hub-text">School timezone</h2>
                    <p className="mb-0 mt-1 text-sm text-hub-muted">
                      {data.school_timezone?.source_label || '—'}
                    </p>
                  </div>
                </div>
                <label className="flex flex-col gap-1.5">
                  <span className={labelClass}>Timezone</span>
                  <select className={fieldClass} value={tz} onChange={(e) => setTz(e.target.value)}>
                    {withCurrentOption(SCHOOL_TIMEZONE_OPTIONS, tz).map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="mb-0 mt-2 text-xs text-hub-muted">
                  Current sample: {data.school_timezone?.now_sample || '—'}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
                    onClick={() => void run('timezone', { action: 'set', school_timezone: tz })}
                  >
                    Set timezone
                  </button>
                  <button
                    type="button"
                    className="spa-mgmt-btn-ghost px-4 py-2.5 text-sm"
                    onClick={() => void run('timezone', { action: 'clear' })}
                  >
                    Clear override
                  </button>
                </div>
              </div>
            </section>

            <section className="spa-mgmt-card overflow-hidden shadow-sm">
              <div className="spa-mgmt-accent-bar" />
              <div className="p-5">
                <div className="mb-4 flex items-start gap-3">
                  <span className="spa-mgmt-avatar h-10 w-10 text-base">
                    <i className="bi bi-palette" aria-hidden />
                  </span>
                  <div>
                    <h2 className="mb-0 text-base font-bold text-hub-text">Site theme override</h2>
                    <p className="mb-0 mt-1 text-sm text-hub-muted">
                      Forces one portal theme for everyone until cleared.
                    </p>
                  </div>
                </div>
                <label className="flex max-w-xs flex-col gap-1.5">
                  <span className={labelClass}>Theme</span>
                  <select
                    className={fieldClass}
                    value={theme}
                    onChange={(e) => setTheme(e.target.value)}
                  >
                    <option value="">(none)</option>
                    {(data.theme_choices || []).map((t: string) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="spa-mgmt-btn-primary mt-4 px-4 py-2.5 text-sm"
                  onClick={() => void run('site-theme', { theme })}
                >
                  Save site theme
                </button>
              </div>
            </section>
          </div>
        </div>
      ) : (
        <section className="spa-mgmt-card mx-auto max-w-3xl overflow-hidden shadow-sm">
          <div className="spa-mgmt-accent-bar" />
          <div className="p-5 md:p-6">
            {data.maintenance?.is_active ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-amber-300/70 bg-amber-50 px-4 py-4 text-amber-950">
                  <p className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wide">
                    <i className="bi bi-exclamation-triangle-fill" aria-hidden />
                    Maintenance active
                  </p>
                  <p className="mb-0 text-base font-semibold">
                    {data.maintenance.reason || 'No reason provided'}
                  </p>
                  {data.maintenance.maintenance_message ? (
                    <p className="mb-0 mt-2 text-sm opacity-90">
                      {data.maintenance.maintenance_message}
                    </p>
                  ) : null}
                  {data.maintenance.end_display ? (
                    <p className="mb-0 mt-3 text-sm font-medium">
                      Ends {data.maintenance.end_display}
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
                  onClick={() => void run('maintenance/stop')}
                >
                  <i className="bi bi-stop-circle" aria-hidden />
                  Stop maintenance
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="flex items-start gap-3">
                  <span className="spa-mgmt-avatar h-11 w-11 text-lg">
                    <i className="bi bi-tools" aria-hidden />
                  </span>
                  <div>
                    <h2 className="mb-0 text-lg font-bold text-hub-text">Start maintenance window</h2>
                    <p className="mb-0 mt-1 text-sm text-hub-muted">
                      Blocks non-tech sign-ins and shows the public maintenance page. Dual-role staff
                      can still open Tech; School management stays unavailable until you stop.
                    </p>
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>Duration</span>
                    <select
                      className={fieldClass}
                      value={maint.duration_minutes}
                      onChange={(e) =>
                        setMaint((m) => ({ ...m, duration_minutes: e.target.value }))
                      }
                    >
                      {MAINT_DURATION_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className={labelClass}>Reason</span>
                    <select
                      className={fieldClass}
                      value={maint.reason}
                      onChange={(e) => setMaint((m) => ({ ...m, reason: e.target.value }))}
                    >
                      {withCurrentOption(MAINT_REASON_OPTIONS, maint.reason).map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5 sm:col-span-2">
                    <span className={labelClass}>Message shown to users</span>
                    <select
                      className={fieldClass}
                      value={maint.maintenance_message}
                      onChange={(e) =>
                        setMaint((m) => ({ ...m, maintenance_message: e.target.value }))
                      }
                    >
                      {withCurrentOption(MAINT_MESSAGE_OPTIONS, maint.maintenance_message).map(
                        (opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                </div>
                <button
                  type="button"
                  className="spa-mgmt-btn-primary px-4 py-2.5 text-sm"
                  onClick={() =>
                    void run('maintenance/start', {
                      duration_minutes: Number(maint.duration_minutes),
                      reason: maint.reason,
                      maintenance_message: maint.maintenance_message,
                    })
                  }
                >
                  <i className="bi bi-play-circle" aria-hidden />
                  Start maintenance
                </button>
              </div>
            )}
          </div>
        </section>
      )}
    </ManagementPageShell>
  )
}
