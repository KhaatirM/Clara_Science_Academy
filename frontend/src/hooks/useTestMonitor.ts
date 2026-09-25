import { useEffect, useRef } from 'react'
import { reportTestViolation, sendTestEvents, uploadTestSnapshot } from '../api/studentTest'

export type TestViolationReason =
  | 'tab_hidden'
  | 'window_blur'
  | 'page_closed'
  | 'screen_share_ended'
  | 'camera_ended'

type MonitorEvent = Record<string, number | string>

const SNAPSHOT_MS = 10_000
const EVENTS_FLUSH_MS = 5_000
const MOUSE_SAMPLE_MS = 100
const MAX_SNAPSHOT_BYTES = 150 * 1024

function captureFrame(video: HTMLVideoElement, maxWidth: number, maxHeight: number): Promise<Blob | null> {
  const vw = video.videoWidth
  const vh = video.videoHeight
  if (!vw || !vh) return Promise.resolve(null)
  const scale = Math.min(1, maxWidth / vw, maxHeight / vh)
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(vw * scale)
  canvas.height = Math.round(vh * scale)
  const ctx = canvas.getContext('2d')
  if (!ctx) return Promise.resolve(null)
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  const encode = (quality: number) =>
    new Promise<Blob | null>((resolve) => canvas.toBlob((b) => resolve(b), 'image/jpeg', quality))
  return encode(0.5).then((blob) => {
    if (blob && blob.size > MAX_SNAPSHOT_BYTES) return encode(0.3)
    return blob
  })
}

function videoFor(stream: MediaStream): HTMLVideoElement {
  const video = document.createElement('video')
  video.muted = true
  video.playsInline = true
  video.srcObject = stream
  void video.play().catch(() => undefined)
  return video
}

/**
 * Runs while a lockdown test is in progress: periodic screen/camera snapshots, mouse + focus event log,
 * and violation detection (leaving the tab, clicking outside the window, closing, or stopping a share).
 */
export function useTestMonitor({
  sessionId,
  screenStream,
  cameraStream,
  getAnswers,
  isPaused,
  onViolation,
}: {
  sessionId: number | null
  screenStream: MediaStream | null
  cameraStream: MediaStream | null
  getAnswers: () => Record<string, string>
  isPaused: () => boolean
  onViolation: (reason: TestViolationReason) => void
}) {
  const getAnswersRef = useRef(getAnswers)
  const isPausedRef = useRef(isPaused)
  const onViolationRef = useRef(onViolation)
  getAnswersRef.current = getAnswers
  isPausedRef.current = isPaused
  onViolationRef.current = onViolation

  useEffect(() => {
    if (!sessionId || !screenStream || !cameraStream) return
    let stopped = false
    let violated = false
    const buffer: MonitorEvent[] = []
    const now = () => Date.now()
    const push = (e: MonitorEvent) => {
      if (buffer.length < 4000) buffer.push(e)
    }

    const screenVideo = videoFor(screenStream)
    const cameraVideo = videoFor(cameraStream)

    const flushEvents = () => {
      if (stopped || violated) return
      const batch = buffer.splice(0, buffer.length)
      void sendTestEvents(sessionId, batch, getAnswersRef.current()).catch(() => undefined)
    }

    const snapshot = async () => {
      if (stopped || violated) return
      const [screenBlob, cameraBlob] = await Promise.all([
        captureFrame(screenVideo, 960, 600),
        captureFrame(cameraVideo, 320, 240),
      ])
      if (stopped || violated) return
      if (screenBlob) void uploadTestSnapshot(sessionId, 'screen', screenBlob).catch(() => undefined)
      if (cameraBlob) void uploadTestSnapshot(sessionId, 'camera', cameraBlob).catch(() => undefined)
    }

    const violate = (reason: TestViolationReason) => {
      if (violated || stopped || isPausedRef.current()) return
      violated = true
      push({ t: now(), type: 'violation', reason })
      const batch = buffer.splice(0, buffer.length)
      if (batch.length) void sendTestEvents(sessionId, batch, getAnswersRef.current()).catch(() => undefined)
      void reportTestViolation(sessionId, reason, getAnswersRef.current())
      onViolationRef.current(reason)
    }

    let lastMouse = 0
    const onMouseMove = (e: MouseEvent) => {
      const t = now()
      if (t - lastMouse < MOUSE_SAMPLE_MS) return
      lastMouse = t
      push({ t, type: 'm', x: e.clientX, y: e.clientY, w: window.innerWidth, h: window.innerHeight })
    }
    const onClick = (e: MouseEvent) => {
      push({ t: now(), type: 'c', x: e.clientX, y: e.clientY, w: window.innerWidth, h: window.innerHeight })
    }
    const onPaste = () => push({ t: now(), type: 'paste' })
    const onCopy = () => push({ t: now(), type: 'copy' })
    const onVisibility = () => {
      push({ t: now(), type: 'visibility', state: document.visibilityState })
      if (document.visibilityState === 'hidden') violate('tab_hidden')
    }
    const onBlur = () => {
      push({ t: now(), type: 'blur' })
      violate('window_blur')
    }
    const onPageHide = () => violate('page_closed')
    const onScreenEnded = () => violate('screen_share_ended')
    const onCameraEnded = () => violate('camera_ended')

    push({ t: now(), type: 'start', w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('mousemove', onMouseMove, { passive: true })
    window.addEventListener('click', onClick, true)
    window.addEventListener('paste', onPaste, true)
    window.addEventListener('copy', onCopy, true)
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', onBlur)
    window.addEventListener('pagehide', onPageHide)
    screenStream.getVideoTracks().forEach((t) => t.addEventListener('ended', onScreenEnded))
    cameraStream.getVideoTracks().forEach((t) => t.addEventListener('ended', onCameraEnded))

    const firstShot = window.setTimeout(() => void snapshot(), 1500)
    const shotTimer = window.setInterval(() => void snapshot(), SNAPSHOT_MS)
    const flushTimer = window.setInterval(flushEvents, EVENTS_FLUSH_MS)

    return () => {
      stopped = true
      window.clearTimeout(firstShot)
      window.clearInterval(shotTimer)
      window.clearInterval(flushTimer)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('click', onClick, true)
      window.removeEventListener('paste', onPaste, true)
      window.removeEventListener('copy', onCopy, true)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('blur', onBlur)
      window.removeEventListener('pagehide', onPageHide)
      screenStream.getVideoTracks().forEach((t) => t.removeEventListener('ended', onScreenEnded))
      cameraStream.getVideoTracks().forEach((t) => t.removeEventListener('ended', onCameraEnded))
      screenVideo.srcObject = null
      cameraVideo.srcObject = null
    }
  }, [sessionId, screenStream, cameraStream])
}

export function stopStreams(...streams: Array<MediaStream | null | undefined>) {
  for (const s of streams) s?.getTracks().forEach((t) => t.stop())
}
