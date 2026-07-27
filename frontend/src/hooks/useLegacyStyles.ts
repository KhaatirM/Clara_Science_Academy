import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { stylesForMgmtPath } from '../config/legacyPages'

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

/** Load page-specific mgmt-* CSS (and scoped Bootstrap when needed) for the current route. */
export function useMgmtPageStyles(): void {
  const { pathname } = useLocation()
  const sheets = stylesForMgmtPath(pathname)

  useEffect(() => {
    if (!sheets.length) return
    acquireLegacyStyles(sheets)
    return () => releaseLegacyStyles(sheets)
  }, [pathname, sheets.join('|')])
}

/** @deprecated Styles are loaded by `useMgmtPageStyles`. */
export function useLegacyStyles(_hrefs: string[]) {
  /* no-op */
}

/** Whether the main content area should use legacy padding (none — themed shell everywhere). */
export function useLegacyMgmtShell(): boolean {
  useMgmtPageStyles()
  return false
}
