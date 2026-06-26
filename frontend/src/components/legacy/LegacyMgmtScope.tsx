import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'

const LegacyMgmtPortalContext = createContext<HTMLElement | null>(null)

export function useLegacyMgmtPortal(): HTMLElement | null {
  return useContext(LegacyMgmtPortalContext)
}

/** Wrap legacy management pages so scoped Bootstrap only applies inside this subtree. */
export function LegacyMgmtScope({ children }: { children: ReactNode }) {
  const portalRef = useRef<HTMLDivElement>(null)
  const [portalEl, setPortalEl] = useState<HTMLElement | null>(null)

  useEffect(() => {
    setPortalEl(portalRef.current)
  }, [])

  return (
    <LegacyMgmtPortalContext.Provider value={portalEl}>
      <div className="legacy-mgmt-bootstrap">
        {children}
        <div ref={portalRef} className="legacy-mgmt-portal" aria-hidden={!portalEl} />
      </div>
    </LegacyMgmtPortalContext.Provider>
  )
}
