import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { BOOTSTRAP_LEGACY_CSS, isLegacyMgmtPath } from '../config/legacyPages'

/** Load legacy management CSS sheets (served by Flask at /static/css/...). */
export function useLegacyStyles(hrefs: string[], options?: { includeBootstrap?: boolean }) {
  const includeBootstrap = options?.includeBootstrap ?? true

  useEffect(() => {
    const sheets = includeBootstrap ? [BOOTSTRAP_LEGACY_CSS, ...hrefs] : hrefs
    const links = sheets.map((href) => {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = href
      document.head.appendChild(link)
      return link
    })
    return () => {
      links.forEach((link) => link.remove())
    }
  }, [hrefs, includeBootstrap])
}

/** Toggle document + main-area classes for legacy management pages. */
export function useLegacyMgmtShell(): boolean {
  const { pathname } = useLocation()
  const active = isLegacyMgmtPath(pathname)

  useEffect(() => {
    document.documentElement.classList.toggle('spa-legacy-mgmt-shell', active)
    document.body.classList.toggle('spa-legacy-mgmt-shell', active)
    return () => {
      document.documentElement.classList.remove('spa-legacy-mgmt-shell')
      document.body.classList.remove('spa-legacy-mgmt-shell')
    }
  }, [active])

  return active
}
