import { useEffect, useRef } from 'react'
import { showAppToasts } from '../../utils/appToast'

const ACTIVITY_EVENTS: Array<keyof WindowEventMap> = [
  'mousemove',
  'mousedown',
  'keydown',
  'touchstart',
  'scroll',
  'click',
]

let idleHolds = 0

/**
 * Suspend idle logout (e.g. while a student is taking a quiz or test).
 * Returns a release function; the page must also keep the server session alive.
 */
export function holdIdleLogout(): () => void {
  idleHolds += 1
  let released = false
  return () => {
    if (released) return
    released = true
    idleHolds = Math.max(0, idleHolds - 1)
  }
}

function logoutForIdle() {
  window.location.href = '/logout?reason=idle'
}

/**
 * Client-side companion to server idle session timeout.
 * Signs out after `timeoutMinutes` without pointer/keyboard activity.
 */
export function IdleSessionGuard({ timeoutMinutes }: { timeoutMinutes: number }) {
  const lastActivityRef = useRef(Date.now())
  const warnedRef = useRef(false)
  const minutes = Math.max(5, timeoutMinutes || 30)
  const timeoutMs = minutes * 60_000
  const warnMs = Math.max(60_000, timeoutMs - 2 * 60_000)

  useEffect(() => {
    const onActivity = () => {
      lastActivityRef.current = Date.now()
      warnedRef.current = false
    }

    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, onActivity, { passive: true })
    }

    const timer = window.setInterval(() => {
      if (idleHolds > 0) {
        onActivity()
        return
      }
      const idleFor = Date.now() - lastActivityRef.current
      if (idleFor >= timeoutMs) {
        logoutForIdle()
        return
      }
      if (!warnedRef.current && idleFor >= warnMs) {
        warnedRef.current = true
        showAppToasts([
          {
            tone: 'warning',
            message: 'You will be signed out soon due to inactivity. Move the mouse or press a key to stay signed in.',
          },
        ])
      }
    }, 15_000)

    return () => {
      window.clearInterval(timer)
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, onActivity)
      }
    }
  }, [timeoutMs, warnMs])

  return null
}
