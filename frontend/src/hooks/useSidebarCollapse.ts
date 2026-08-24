import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'sidebarCollapsed'
/** Match Jinja/Bootstrap xs breakpoint used by the legacy dashboard drawer. */
export const DRAWER_MAX_WIDTH_PX = 575.98
export const SIDEBAR_WIDTH_EXPANDED = 256
export const SIDEBAR_WIDTH_COLLAPSED = 80

function readCollapsedFromStorage(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function matchesDrawerQuery(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia(`(max-width: ${DRAWER_MAX_WIDTH_PX}px)`).matches
}

export function useSidebarCollapse() {
  const [collapsed, setCollapsed] = useState(readCollapsedFromStorage)
  const [isDrawerMode, setIsDrawerMode] = useState(matchesDrawerQuery)
  const [mobileOpen, setMobileOpen] = useState(false)

  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(STORAGE_KEY, String(next))
      } catch {
        /* ignore quota / private mode */
      }
      return next
    })
  }, [])

  const openMobile = useCallback(() => setMobileOpen(true), [])
  const closeMobile = useCallback(() => setMobileOpen(false), [])
  const toggleMobile = useCallback(() => setMobileOpen((prev) => !prev), [])

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) {
        setCollapsed(event.newValue === 'true')
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return
    }
    const media = window.matchMedia(`(max-width: ${DRAWER_MAX_WIDTH_PX}px)`)
    const sync = () => {
      const next = media.matches
      setIsDrawerMode(next)
      // Entering phone layout: always start closed so content gets full width.
      if (next) setMobileOpen(false)
    }
    sync()
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', sync)
      return () => media.removeEventListener('change', sync)
    }
    media.addListener(sync)
    return () => media.removeListener(sync)
  }, [])

  // Desktop rail width; phone drawer uses full expanded width when open, 0 spacer.
  const railCollapsed = !isDrawerMode && collapsed
  const width = isDrawerMode
    ? SIDEBAR_WIDTH_EXPANDED
    : railCollapsed
      ? SIDEBAR_WIDTH_COLLAPSED
      : SIDEBAR_WIDTH_EXPANDED
  const spacerWidth = isDrawerMode ? 0 : width

  return {
    collapsed: railCollapsed,
    toggle,
    width,
    spacerWidth,
    isDrawerMode,
    mobileOpen,
    openMobile,
    closeMobile,
    toggleMobile,
  }
}
