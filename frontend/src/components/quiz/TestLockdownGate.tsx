import { useEffect, useRef, useState } from 'react'
import { startTest } from '../../api/studentTest'
import { stopStreams } from '../../hooks/useTestMonitor'

export type TestStarted = {
  sessionId: number
  screenStream: MediaStream
  cameraStream: MediaStream
  timeLimitSeconds: number | null
}

const btnPrimary =
  'inline-flex items-center justify-center gap-2 rounded-xl border border-red-700 bg-gradient-to-br from-red-700 to-rose-600 px-5 py-2.5 text-sm font-bold text-white shadow-md transition hover:from-red-800 hover:to-rose-700 disabled:cursor-not-allowed disabled:opacity-50'
const btnMuted =
  'inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50'

function monitoringSupported(): boolean {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices) return false
  const md = navigator.mediaDevices as Partial<MediaDevices>
  return typeof md.getUserMedia === 'function' && typeof md.getDisplayMedia === 'function'
}

function StreamPreview({ stream, label }: { stream: MediaStream; label: string }) {
  const ref = useRef<HTMLVideoElement | null>(null)
  useEffect(() => {
    if (ref.current) ref.current.srcObject = stream
  }, [stream])
  return (
    <figure className="overflow-hidden rounded-xl border border-slate-200 bg-slate-900">
      <video ref={ref} autoPlay muted playsInline className="aspect-video w-full object-contain" />
      <figcaption className="bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white">{label}</figcaption>
    </figure>
  )
}

export function TestLockedPanel({ reasonLabel, backTo }: { reasonLabel: string | null; backTo: string }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-red-200 bg-white shadow-sm">
      <div className="bg-gradient-to-br from-red-700 to-rose-600 px-5 py-5 text-white">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <i className="bi bi-lock-fill" aria-hidden /> This test is locked
        </h2>
        <p className="mt-1 text-sm text-white/90">
          {reasonLabel ? `Reason: ${reasonLabel}.` : 'The test was closed during your attempt.'} Your answers up to that
          point were submitted.
        </p>
      </div>
      <div className="space-y-3 px-5 py-4 text-sm text-slate-700">
        <p>Your teacher has been notified and can review the recording. If this was a mistake, ask them to unlock it.</p>
        <a href={backTo} className={btnMuted}>
          Back to assignments
        </a>
      </div>
    </section>
  )
}

export function TestLockdownGate({
  assignmentId,
  timeLimitMinutes,
  onStarted,
}: {
  assignmentId: number
  timeLimitMinutes: number | null | undefined
  onStarted: (started: TestStarted) => void
}) {
  const [agreed, setAgreed] = useState(false)
  const [camera, setCamera] = useState<MediaStream | null>(null)
  const [screen, setScreen] = useState<MediaStream | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const handedOff = useRef(false)
  const streamsRef = useRef<{ camera: MediaStream | null; screen: MediaStream | null }>({ camera: null, screen: null })
  streamsRef.current = { camera, screen }

  useEffect(() => {
    return () => {
      if (!handedOff.current) stopStreams(streamsRef.current.camera, streamsRef.current.screen)
    }
  }, [])

  useEffect(() => {
    const tracks = [...(camera?.getVideoTracks() || []), ...(screen?.getVideoTracks() || [])]
    const onEnded = () => {
      if (handedOff.current) return
      setError('Sharing stopped. Turn on your camera and share your entire screen again to begin.')
      if (camera?.getVideoTracks().some((t) => t.readyState === 'ended')) setCamera(null)
      if (screen?.getVideoTracks().some((t) => t.readyState === 'ended')) setScreen(null)
    }
    tracks.forEach((t) => t.addEventListener('ended', onEnded))
    return () => tracks.forEach((t) => t.removeEventListener('ended', onEnded))
  }, [camera, screen])

  if (!monitoringSupported()) {
    return (
      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950">
        <h2 className="text-lg font-bold">Take this test on a computer</h2>
        <p className="mt-1 text-sm">
          This test requires camera and screen monitoring, which only works in Chrome, Edge, or Firefox on a laptop or
          desktop computer. Phones and tablets are not supported.
        </p>
      </section>
    )
  }

  const enableCamera = async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      })
      setCamera(stream)
    } catch {
      setError('Camera access was blocked. Allow camera access in your browser (the icon in the address bar) and try again.')
    }
  }

  const enableScreen = async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'monitor', frameRate: { ideal: 5, max: 10 } } as MediaTrackConstraints,
        audio: false,
      })
      const track = stream.getVideoTracks()[0]
      const surface = (track?.getSettings() as MediaTrackSettings & { displaySurface?: string }).displaySurface
      if (surface && surface !== 'monitor') {
        stopStreams(stream)
        setError('Please choose "Entire screen" (not a window or tab) when sharing.')
        return
      }
      setScreen(stream)
    } catch {
      setError('Screen sharing was cancelled. Choose "Entire screen" and click Share to continue.')
    }
  }

  const begin = async () => {
    if (!camera || !screen) return
    setBusy(true)
    setError(null)
    try {
      const res = await startTest(assignmentId)
      handedOff.current = true
      onStarted({
        sessionId: res.session.id,
        screenStream: screen,
        cameraStream: camera,
        timeLimitSeconds: res.time_limit_seconds,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start the test')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-red-200 bg-white shadow-sm">
      <div className="bg-gradient-to-br from-slate-900 via-red-900 to-rose-800 px-5 py-5 text-white">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <i className="bi bi-shield-lock-fill" aria-hidden /> Lockdown test
        </h2>
        <p className="mt-1 text-sm text-white/85">Read this before you begin.</p>
      </div>
      <div className="space-y-4 px-5 py-5">
        <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="flex items-center gap-2 font-bold">
            <i className="bi bi-camera-video-fill" aria-hidden /> Your camera will be turned on to monitor you during this
            test.
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Your camera and your entire screen will be recorded as images about every 10 seconds.</li>
            <li>Your mouse movements and clicks on this page will be recorded.</li>
            <li>Your teacher can review these recordings later.</li>
          </ul>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
          <p className="font-bold">The test locks immediately if you:</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>switch tabs, open another window or app, or click outside this browser window</li>
            <li>close or reload this page</li>
            <li>stop sharing your screen or turn off your camera</li>
          </ul>
          <p className="mt-2">When it locks, your answers so far are submitted and only your teacher can unlock it.</p>
          {timeLimitMinutes ? <p className="mt-2 font-semibold">Time limit: {timeLimitMinutes} minutes.</p> : null}
        </div>

        <label className="flex items-start gap-2 text-sm font-semibold text-slate-800">
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-slate-300"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
          />
          I understand my camera, screen, and mouse will be monitored and recorded during this test.
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <button type="button" className={btnMuted} disabled={!agreed || Boolean(camera)} onClick={() => void enableCamera()}>
              <i className={`bi ${camera ? 'bi-check-circle-fill text-emerald-600' : 'bi-camera-video'}`} aria-hidden />
              {camera ? 'Camera on' : '1. Turn on camera'}
            </button>
            {camera ? <StreamPreview stream={camera} label="Camera preview" /> : null}
          </div>
          <div className="space-y-2">
            <button type="button" className={btnMuted} disabled={!agreed || Boolean(screen)} onClick={() => void enableScreen()}>
              <i className={`bi ${screen ? 'bi-check-circle-fill text-emerald-600' : 'bi-display'}`} aria-hidden />
              {screen ? 'Screen shared' : '2. Share entire screen'}
            </button>
            {screen ? <StreamPreview stream={screen} label="Screen preview" /> : null}
          </div>
        </div>

        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
        ) : null}

        <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
          <button type="button" className={btnPrimary} disabled={!agreed || !camera || !screen || busy} onClick={() => void begin()}>
            <i className="bi bi-play-fill" aria-hidden />
            {busy ? 'Starting…' : 'Start test'}
          </button>
          <p className="text-xs text-hub-muted">
            After you click Start, stay on this page until you submit.
          </p>
        </div>
      </div>
    </section>
  )
}

export function CameraMonitorBadge({ stream }: { stream: MediaStream }) {
  const ref = useRef<HTMLVideoElement | null>(null)
  useEffect(() => {
    if (ref.current) ref.current.srcObject = stream
  }, [stream])
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[1200] w-44 overflow-hidden rounded-xl border-2 border-red-500 bg-slate-900 shadow-2xl">
      <video ref={ref} autoPlay muted playsInline className="aspect-[4/3] w-full object-cover" />
      <div className="flex items-center gap-1.5 bg-red-600 px-2 py-1 text-[11px] font-bold text-white">
        <span className="h-2 w-2 animate-pulse rounded-full bg-white" aria-hidden />
        Camera on - you are being monitored
      </div>
    </div>
  )
}
