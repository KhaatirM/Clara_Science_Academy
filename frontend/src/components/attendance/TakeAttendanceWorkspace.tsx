import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { apiFetch } from '../../api/client'

export interface TakeAttendanceRow {
  student_id: number
  display_name: string
  grade_level: number | null
  status: string
  notes: string
  school_day_status: string | null
}

export interface TakeAttendanceResponse {
  class: { id: number; name: string; subject: string | null }
  date: string
  statuses: string[]
  rows: TakeAttendanceRow[]
  stats: Record<string, number>
  urls: {
    attendance_hub: string
    class_view: string
    records?: string
    csv_template?: string
    csv_upload?: string
  }
}

const STATUS_STYLES: Record<string, { base: string; active: string; short: string }> = {
  Present: {
    base: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    active: 'border-emerald-600 bg-emerald-600 text-white',
    short: 'Present',
  },
  'Unexcused Absence': {
    base: 'border-rose-200 bg-rose-50 text-rose-800',
    active: 'border-rose-600 bg-rose-600 text-white',
    short: 'Absent',
  },
  Late: {
    base: 'border-amber-200 bg-amber-50 text-amber-900',
    active: 'border-amber-500 bg-amber-500 text-white',
    short: 'Late',
  },
  'Excused Absence': {
    base: 'border-sky-200 bg-sky-50 text-sky-800',
    active: 'border-sky-600 bg-sky-600 text-white',
    short: 'Excused',
  },
  Suspended: {
    base: 'border-slate-300 bg-slate-100 text-slate-800',
    active: 'border-slate-700 bg-slate-700 text-white',
    short: 'Suspended',
  },
}

function studentInitials(name: string) {
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] || '?') + (parts[parts.length - 1]?.[0] || '')).toUpperCase()
}

type Props = {
  classId: number
  apiBase: string
  hubPath: string
  classViewPath: string
  recordsPath?: string
  shell?: 'teacher' | 'management'
}

export function TakeAttendanceWorkspace({
  classId,
  apiBase,
  hubPath,
  classViewPath,
  recordsPath,
  shell = 'management',
}: Props) {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [data, setData] = useState<TakeAttendanceResponse | null>(null)
  const [drafts, setDrafts] = useState<Record<number, { status: string; notes: string }>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [csvOpen, setCsvOpen] = useState(false)
  const [csvUploading, setCsvUploading] = useState(false)
  const [csvFile, setCsvFile] = useState<File | null>(null)

  const load = useCallback(async () => {
    if (!classId) return
    setLoading(true)
    setError(null)
    try {
      const date = searchParams.get('date') || ''
      const qs = date ? `?date=${encodeURIComponent(date)}` : ''
      const payload = await apiFetch<TakeAttendanceResponse>(`${apiBase}${qs}`)
      setData(payload)
      const next: Record<number, { status: string; notes: string }> = {}
      for (const row of payload.rows) {
        next[row.student_id] = { status: row.status || '', notes: row.notes || '' }
      }
      setDrafts(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load attendance.')
    } finally {
      setLoading(false)
    }
  }, [apiBase, classId, searchParams])

  useEffect(() => {
    void load()
  }, [load])

  const liveStats = useMemo(() => {
    if (!data) return { present: 0, late: 0, absent: 0, unmarked: 0, rate: 0 }
    let present = 0
    let late = 0
    let absent = 0
    let unmarked = 0
    for (const row of data.rows) {
      const status = drafts[row.student_id]?.status || ''
      if (!status) unmarked += 1
      else if (status === 'Present') present += 1
      else if (status === 'Late') late += 1
      else absent += 1
    }
    const marked = data.rows.length - unmarked
    const rate = marked > 0 ? Math.round((present / marked) * 100) : 0
    return { present, late, absent, unmarked, rate }
  }, [data, drafts])

  function setDate(nextDate: string) {
    const params = new URLSearchParams(searchParams)
    if (nextDate) params.set('date', nextDate)
    else params.delete('date')
    setSearchParams(params)
  }

  function setAllStatus(status: string) {
    if (!data) return
    const next = { ...drafts }
    for (const row of data.rows) {
      next[row.student_id] = { status, notes: next[row.student_id]?.notes || '' }
    }
    setDrafts(next)
  }

  function clearAll() {
    if (!data) return
    const next = { ...drafts }
    for (const row of data.rows) {
      next[row.student_id] = { status: '', notes: '' }
    }
    setDrafts(next)
  }

  async function markAllPresent() {
    if (!data) return
    setSaving(true)
    setMessage(null)
    try {
      const markUrl = apiBase.includes('/teacher/')
        ? `/api/spa/teacher/attendance/take/${classId}/mark-all-present`
        : `/api/spa/attendance/class/${classId}/mark-all-present`
      await apiFetch(markUrl, {
        method: 'POST',
        body: JSON.stringify({ date: data.date }),
      })
      setMessage('All students marked present.')
      void load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not mark all present.')
    } finally {
      setSaving(false)
    }
  }

  async function onSave() {
    if (!data) return
    setSaving(true)
    setMessage(null)
    try {
      const entries = data.rows.map((row) => ({
        student_id: row.student_id,
        status: drafts[row.student_id]?.status || '',
        notes: drafts[row.student_id]?.notes || '',
      }))
      const result = await apiFetch<{ success: boolean; message: string; redirect_url?: string }>(
        apiBase,
        { method: 'POST', body: JSON.stringify({ date: data.date, entries }) },
      )
      setMessage(result.message)
      if (result.redirect_url) {
        navigate(result.redirect_url.replace(/^\/app/, ''))
      } else {
        void load()
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  async function uploadCsv() {
    if (!data?.urls.csv_upload || !csvFile) return
    setCsvUploading(true)
    setMessage(null)
    try {
      const form = new FormData()
      form.append('attendance_file', csvFile)
      const res = await fetch(data.urls.csv_upload, {
        method: 'POST',
        body: form,
        credentials: 'include',
      })
      const body = (await res.json()) as { success?: boolean; message?: string }
      if (!res.ok || !body.success) throw new Error(body.message || 'Upload failed')
      setMessage(body.message || 'CSV uploaded.')
      setCsvOpen(false)
      setCsvFile(null)
      void load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'CSV upload failed.')
    } finally {
      setCsvUploading(false)
    }
  }

  const heroClass =
    shell === 'teacher'
      ? 'rounded-2xl bg-gradient-to-br from-violet-700 via-indigo-700 to-slate-800 p-6 text-white shadow-lg'
      : 'spa-mgmt-hero mb-4'

  if (loading) {
    return <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">Loading attendance…</div>
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">{error || 'Could not load attendance.'}</p>
        <Link to={hubPath} className="mt-4 inline-block font-semibold text-teal-700">
          Back to attendance
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <header className={heroClass}>
        <p className="text-sm font-semibold uppercase tracking-wide text-white/80">Class period attendance</p>
        <h1 className="text-2xl font-bold">{data.class.name}</h1>
        <p className="text-sm text-white/90">
          {data.class.subject || 'General'} · {data.rows.length} students · {data.date}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link
            to={hubPath}
            className={
              shell === 'teacher'
                ? 'rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-sm font-semibold text-white'
                : 'spa-mgmt-btn spa-mgmt-btn--ghost text-sm'
            }
          >
            Back to hub
          </Link>
          <Link
            to={classViewPath}
            className={
              shell === 'teacher'
                ? 'rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-sm font-semibold text-white'
                : 'spa-mgmt-btn spa-mgmt-btn--ghost text-sm'
            }
          >
            Class view
          </Link>
          {recordsPath || data.urls.records ? (
            <Link
              to={(recordsPath || data.urls.records || '').replace(/^\/app/, '')}
              className={
                shell === 'teacher'
                  ? 'rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-sm font-semibold text-white'
                  : 'spa-mgmt-btn spa-mgmt-btn--ghost text-sm'
              }
            >
              Records
            </Link>
          ) : null}
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { label: 'Present', value: liveStats.present, icon: 'bi-check-circle-fill', tone: 'text-emerald-700' },
          { label: 'Late', value: liveStats.late, icon: 'bi-clock-fill', tone: 'text-amber-700' },
          { label: 'Absent', value: liveStats.absent, icon: 'bi-x-circle-fill', tone: 'text-rose-700' },
          { label: 'Unmarked', value: liveStats.unmarked, icon: 'bi-dash-circle', tone: 'text-slate-600' },
          { label: 'Rate', value: `${liveStats.rate}%`, icon: 'bi-graph-up', tone: 'text-teal-700' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className={`text-xl font-extrabold ${stat.tone}`}>
              <i className={`bi ${stat.icon} me-2`} />
              {stat.value}
            </div>
            <div className="text-xs font-bold uppercase tracking-wide text-hub-muted">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm font-semibold text-hub-muted" htmlFor="attendance-date">
            Date
          </label>
          <input
            id="attendance-date"
            type="date"
            value={data.date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void markAllPresent()}
            disabled={saving}
            className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-900"
          >
            All present
          </button>
          <button
            type="button"
            onClick={() => setAllStatus('Unexcused Absence')}
            className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-900"
          >
            All absent
          </button>
          <button
            type="button"
            onClick={clearAll}
            className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700"
          >
            Clear
          </button>
          {data.urls.csv_template ? (
            <a
              href={data.urls.csv_template}
              className="rounded-lg border border-teal-300 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-900"
            >
              CSV template
            </a>
          ) : null}
          {data.urls.csv_upload ? (
            <button
              type="button"
              onClick={() => setCsvOpen(true)}
              className="rounded-lg border border-indigo-300 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-900"
            >
              Bulk CSV
            </button>
          ) : null}
        </div>
      </div>

      {message ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-900">
          {message}
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        {data.rows.map((row) => {
          const draft = drafts[row.student_id] || { status: '', notes: '' }
          return (
            <div
              key={row.student_id}
              className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md"
            >
              <div className="mb-3 flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal-600 to-emerald-700 text-sm font-bold text-white">
                  {studentInitials(row.display_name)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-hub-text">{row.display_name}</div>
                  <div className="text-xs text-hub-muted">
                    Grade {row.grade_level ?? '—'}
                    {row.school_day_status ? (
                      <span className="ms-2 rounded-full bg-slate-100 px-2 py-0.5">
                        School day: {row.school_day_status}
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.statuses.map((status) => {
                  const styles = STATUS_STYLES[status] || STATUS_STYLES.Present
                  const selected = draft.status === status
                  return (
                    <button
                      key={status}
                      type="button"
                      onClick={() =>
                        setDrafts((prev) => ({
                          ...prev,
                          [row.student_id]: { ...draft, status },
                        }))
                      }
                      className={`rounded-full border px-2.5 py-1 text-xs font-semibold transition ${
                        selected ? styles.active : styles.base
                      }`}
                    >
                      {styles.short}
                    </button>
                  )
                })}
              </div>
              <input
                type="text"
                value={draft.notes}
                onChange={(e) =>
                  setDrafts((prev) => ({
                    ...prev,
                    [row.student_id]: { ...draft, notes: e.target.value },
                  }))
                }
                placeholder="Notes (optional)"
                className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
          )
        })}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          disabled={saving}
          onClick={() => void onSave()}
          className="rounded-xl bg-teal-700 px-6 py-3 text-sm font-bold text-white shadow hover:bg-teal-800 disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save attendance'}
        </button>
      </div>

      {csvOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-hub-text">Bulk CSV upload</h3>
            <p className="mt-2 text-sm text-hub-muted">
              Upload a CSV with Date, Student ID, Status, and optional Notes. Download the template first if needed.
            </p>
            <input
              type="file"
              accept=".csv"
              className="mt-4 block w-full text-sm"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
            />
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setCsvOpen(false)} className="text-sm font-semibold text-slate-600">
                Cancel
              </button>
              <button
                type="button"
                disabled={!csvFile || csvUploading}
                onClick={() => void uploadCsv()}
                className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {csvUploading ? 'Uploading…' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
