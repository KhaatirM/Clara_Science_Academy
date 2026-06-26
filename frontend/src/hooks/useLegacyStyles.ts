import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
  BOOTSTRAP_SCOPED_CSS,
  CALENDAR_LEGACY_CSS,
  CLOSURE_LEGACY_CSS,
  HOME_LEGACY_CSS,
  isLegacyMgmtPath,
  SHARED_CALENDAR_CSS,
  SCHOOL_YEARS_LEGACY_CSS,
  STUDENTS_LEGACY_CSS,
} from '../config/legacyPages'

/** All legacy management page styles — kept mounted while inside the legacy shell. */
const LEGACY_MGMT_STYLE_SHEETS = [
  HOME_LEGACY_CSS,
  SHARED_CALENDAR_CSS,
  CALENDAR_LEGACY_CSS,
  SCHOOL_YEARS_LEGACY_CSS,
  CLOSURE_LEGACY_CSS,
  STUDENTS_LEGACY_CSS,
] as const

const legacySheetRefs = new Map<string, number>()
const legacySheetLinks = new Map<string, HTMLLinkElement>()

function acquireLegacyStyles(hrefs: readonly string[]): void {
  for (const href of hrefs) {
    const next = (legacySheetRefs.get(href) ?? 0) + 1
    legacySheetRefs.set(href, next)
    if (next === 1) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = href
      link.dataset.spaLegacyStyle = '1'
      document.head.appendChild(link)
      legacySheetLinks.set(href, link)
    }
  }
}

function releaseLegacyStyles(hrefs: readonly string[]): void {
  for (const href of hrefs) {
    const current = legacySheetRefs.get(href) ?? 0
    if (current <= 1) {
      legacySheetRefs.delete(href)
      legacySheetLinks.get(href)?.remove()
      legacySheetLinks.delete(href)
    } else {
      legacySheetRefs.set(href, current - 1)
    }
  }
}

/**
 * @deprecated Styles are loaded by `useLegacyMgmtShell` for all legacy routes.
 * Kept for API compatibility; no-op.
 */
export function useLegacyStyles(_hrefs: string[]) {
  /* centralized in useLegacyMgmtShell */
}

let scopedBootstrapLink: HTMLLinkElement | null = null
let scopedBootstrapRefs = 0

function mountScopedBootstrap(): void {
  if (scopedBootstrapLink) return
  scopedBootstrapLink = document.createElement('link')
  scopedBootstrapLink.id = 'spa-scoped-bootstrap'
  scopedBootstrapLink.rel = 'stylesheet'
  scopedBootstrapLink.href = BOOTSTRAP_SCOPED_CSS
  document.head.appendChild(scopedBootstrapLink)
}

function unmountScopedBootstrap(): void {
  if (scopedBootstrapRefs > 0) return
  scopedBootstrapLink?.remove()
  scopedBootstrapLink = null
}

/** Toggle document shell classes, scoped Bootstrap, and legacy page CSS. */
export function useLegacyMgmtShell(): boolean {
  const { pathname } = useLocation()
  const active = isLegacyMgmtPath(pathname)

  useEffect(() => {
    document.documentElement.classList.toggle('spa-legacy-mgmt-shell', active)
    document.body.classList.toggle('spa-legacy-mgmt-shell', active)

    if (!active) return

    scopedBootstrapRefs += 1
    mountScopedBootstrap()
    acquireLegacyStyles(LEGACY_MGMT_STYLE_SHEETS)

    return () => {
      scopedBootstrapRefs = Math.max(0, scopedBootstrapRefs - 1)
      unmountScopedBootstrap()
      releaseLegacyStyles(LEGACY_MGMT_STYLE_SHEETS)
      document.documentElement.classList.remove('spa-legacy-mgmt-shell')
      document.body.classList.remove('spa-legacy-mgmt-shell')
    }
  }, [active])

  return active
}
