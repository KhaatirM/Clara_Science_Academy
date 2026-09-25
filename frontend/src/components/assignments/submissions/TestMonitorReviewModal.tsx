import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  deleteTestRecordings,
  fetchTestMonitor,
  testSnapshotUrl,
  unlockTestSession,
  type TestMonitorEvent,
  type TestMonitorResponse,
} from '../../../api/assignmentWorkspace'
import type { AssignmentWorkspaceScope } from '../../../utils/assignmentWorkspaceScope'

type Props = {
  assignmentId: number
  sessionId: number
  scope: AssignmentWorkspaceScope
  onClose: () => void
  onChanged: () => void
}

const TRAIL_WINDOW_MS = 10_000

const EVENT_LABELS: Record<string, string> = {
  start: 'Test started',
  blur: 'Window lost focus',
  visibility: 'Tab visibility changed',
  violation: 'Locked',
  paste: 'Pasted text',
  copy: 'Copied text',
}

function ts(iso: string | null | undefined): number {
  if (!iso) return 0
  const n = Date.parse(iso)
  return Number.isNaN(n) ? 0 : n
}

function clock(ms: number) {
  const s = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

function MouseTrail({ events, endMs }: { events: TestMonitorEvent[]; endMs: number }) {
  const ref = useRef<HTMLCanvasElement | null>(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const W = canvas.width
    const H = canvas.height
    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = '#f8fafc'
    ctx.fillRect(0, 0, W, H)
    const windowEvents = events.filter(
      (e) => (e.type === 'm' || e.type === 'c') && e.t <= endMs && e.t >= endMs - TRAIL_WINDOW_MS,
    )
    const pt = (e: TestMonitorEvent) => ({
      x: ((e.x ?? 0) / Math.max(1, e.w ?? 1)) * W,
      y: ((e.y ?? 0) / Math.max(1, e.h ?? 1)) * H,
    })
    const moves = windowEvents.filter((e) => e.type === 'm')
    ctx.lineWidth = 2
    for (let i = 1; i < moves.length; i++) {
      const a = pt(moves[i - 1])
      const b = pt(moves[i])
      const age = (endMs - moves[i].t) / TRAIL_WINDOW_MS
      ctx.strokeStyle = `rgba(13, 148, 136, ${Math.max(0.15, 1 - age)})`
      ctx.beginPath()
      ctx.moveTo(a.x, a.y)
      ctx.lineTo(b.x, b.y)
      ctx.stroke()
    }
    for (const c of windowEvents.filter((e) => e.type === 'c')) {
      const p = pt(c)
      ctx.fillStyle = 'rgba(220, 38, 38, 0.8)'
      ctx.beginPath()
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2)
      ctx.fill()
    }
    const last = moves[moves.length - 1]
    if (last) {
      const p = pt(last)
      ctx.fillStyle = '#0f766e'
      ctx.beginPath()
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2)
      ctx.fill()
    }
  }, [events, endMs])
  return <canvas ref={ref} width={480} height={300} className="w-full rounded-lg border border-slate-200" />
}

export function TestMonitorReviewModal({ assignmentId, sessionId, scope, onClose, onChanged }: Props) {
  const [data, setData] = useState<TestMonitorResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      setData(await fetchTestMonitor(assignmentId, sessionId, scope))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load recording')
    }
  }, [assignmentId, sessionId, scope])

  useEffect(() => {
    void load()
  }, [load])

  const screens = useMemo(() => (data?.snapshots || []).filter((s) => s.kind === 'screen'), [data])
  const cameras = useMemo(() => (data?.snapshots || []).filter((s) => s.kind === 'camera'), [data])
  const frames = screens.length ? screens : cameras
  const current = frames[Math.min(frame, Math.max(0, frames.length - 1))] || null
  const currentMs = current ? ts(current.captured_at) : ts(data?.session.started_at)
  const nearest = (list: typeof cameras) => {
    if (!list.length || !current) return null
    let best = list[0]
    for (const s of list) {
      if (Math.abs(ts(s.captured_at) - currentMs) < Math.abs(ts(best.captured_at) - currentMs)) best = s
    }
    return best
  }
  const screenShot = screens.length ? current : null
  const cameraShot = nearest(cameras)
  const startMs = ts(data?.session.started_at)

  useEffect(() => {
    if (!playing || frames.length < 2) return
    const timer = window.setInterval(() => {
      setFrame((f) => {
        if (f >= frames.length - 1) {
          setPlaying(false)
          return f
        }
        return f + 1
      })
    }, 800)
    return () => window.clearInterval(timer)
  }, [playing, frames.length])

  const keyEvents = useMemo(
    () => (data?.events || []).filter((e) => e.type !== 'm' && e.type !== 'c'),
    [data],
  )
  const firstEventMs = data?.events?.[0]?.t ?? startMs

  const doUnlock = async () => {
    if (!window.confirm('Unlock this test? The student will be able to take it one more time.')) return
    setBusy(true)
    try {
      const res = await unlockTestSession(assignmentId, sessionId, scope)
      setMessage(res.message)
      onChanged()
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unlock failed')
    } finally {
      setBusy(false)
    }
  }

  const doDelete = async () => {
    if (!window.confirm('Delete all screen/camera images and activity logs for this attempt? This cannot be undone.')) return
    setBusy(true)
    try {
      const res = await deleteTestRecordings(assignmentId, sessionId, scope)
      setMessage(res.message)
      setFrame(0)
      onChanged()
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setBusy(false)
    }
  }

  const s = data?.session
  return (
    <div
      className="fixed inset-0 z-[1100] flex items-center justify-center bg-black/60 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="flex max-h-[94vh] w-full max-w-6xl flex-col overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl md:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-bold text-slate-900">
              <i className="bi bi-camera-reels" aria-hidden /> Test monitoring
              {data ? <span className="text-slate-500">· {data.student.name}</span> : null}
            </h2>
            {s ? (
              <p className="mt-1 text-sm text-slate-600">
                Started {s.started_at ? new Date(s.started_at).toLocaleString() : '—'}
                {s.ended_at ? ` · Ended ${new Date(s.ended_at).toLocaleString()}` : ''}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {s?.status === 'locked' ? (
              <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-800">
                <i className="bi bi-lock-fill me-1" />
                Locked: {s.lock_reason_label || 'Left the test'}
              </span>
            ) : s?.status === 'unlocked' ? (
              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">
                Unlocked ({s.lock_reason_label || 'was locked'})
              </span>
            ) : s?.status === 'submitted' ? (
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-900">Submitted normally</span>
            ) : s?.status === 'active' ? (
              <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-sky-900">In progress</span>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Close
            </button>
          </div>
        </div>

        {error ? <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div> : null}
        {message ? <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{message}</div> : null}

        {!data && !error ? <p className="py-10 text-center text-sm text-slate-500">Loading recording…</p> : null}

        {data ? (
          <div className="space-y-4">
            {frames.length ? (
              <>
                <div className="grid gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
                  <figure className="overflow-hidden rounded-xl border border-slate-200 bg-slate-900">
                    {screenShot ? (
                      <img
                        src={testSnapshotUrl(assignmentId, sessionId, screenShot.id, scope)}
                        alt="Student screen"
                        className="aspect-video w-full object-contain"
                      />
                    ) : (
                      <div className="flex aspect-video items-center justify-center text-sm text-slate-400">No screen image</div>
                    )}
                    <figcaption className="bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white">Screen</figcaption>
                  </figure>
                  <div className="space-y-3">
                    <figure className="overflow-hidden rounded-xl border border-slate-200 bg-slate-900">
                      {cameraShot ? (
                        <img
                          src={testSnapshotUrl(assignmentId, sessionId, cameraShot.id, scope)}
                          alt="Student camera"
                          className="aspect-[4/3] w-full object-cover"
                        />
                      ) : (
                        <div className="flex aspect-[4/3] items-center justify-center text-sm text-slate-400">No camera image</div>
                      )}
                      <figcaption className="bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white">Camera</figcaption>
                    </figure>
                    <div>
                      <p className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-500">
                        Mouse on test page (last 10s)
                      </p>
                      <MouseTrail events={data.events} endMs={currentMs} />
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    className="rounded-lg bg-teal-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal-800"
                    onClick={() => {
                      if (frame >= frames.length - 1) setFrame(0)
                      setPlaying((p) => !p)
                    }}
                  >
                    <i className={`bi ${playing ? 'bi-pause-fill' : 'bi-play-fill'} me-1`} />
                    {playing ? 'Pause' : 'Play'}
                  </button>
                  <input
                    type="range"
                    min={0}
                    max={Math.max(0, frames.length - 1)}
                    value={Math.min(frame, frames.length - 1)}
                    onChange={(e) => {
                      setPlaying(false)
                      setFrame(Number(e.target.value))
                    }}
                    className="min-w-[12rem] flex-1"
                    aria-label="Recording position"
                  />
                  <span className="text-sm font-semibold tabular-nums text-slate-700">
                    {clock(currentMs - startMs)} · frame {Math.min(frame, frames.length - 1) + 1} / {frames.length}
                  </span>
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                No screen or camera images were saved for this attempt (they may have been deleted).
              </div>
            )}

            <div>
              <h3 className="mb-2 text-sm font-bold text-slate-900">Activity timeline</h3>
              {keyEvents.length ? (
                <ol className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
                  {keyEvents.map((e, i) => (
                    <li key={`${e.t}-${i}`} className="flex gap-3">
                      <span className="w-14 shrink-0 font-mono text-xs text-slate-500">{clock(e.t - firstEventMs)}</span>
                      <span className={e.type === 'violation' ? 'font-bold text-red-700' : 'text-slate-800'}>
                        {EVENT_LABELS[e.type] || e.type}
                        {e.type === 'visibility' && e.state ? ` (${e.state})` : ''}
                        {e.type === 'violation' && e.reason ? ` - ${e.reason.replace(/_/g, ' ')}` : ''}
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-slate-500">No activity recorded.</p>
              )}
            </div>

            <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
              {s?.status === 'locked' ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void doUnlock()}
                  className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-bold text-white hover:bg-amber-600 disabled:opacity-50"
                >
                  <i className="bi bi-unlock-fill me-1" />
                  Unlock (grant one retake)
                </button>
              ) : null}
              <button
                type="button"
                disabled={busy || !data.snapshots.length && !data.events.length}
                onClick={() => void doDelete()}
                className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                <i className="bi bi-trash me-1" />
                Delete recordings
              </button>
              <p className="self-center text-xs text-slate-500">Recordings are deleted automatically after 60 days.</p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
