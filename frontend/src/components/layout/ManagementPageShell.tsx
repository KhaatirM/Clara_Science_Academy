import type { ReactNode } from 'react'

import { useManagementDirector } from '../../hooks/useManagementDirector'

type ManagementPageShellProps = {
  children: ReactNode
  /** Override director styling (defaults to session role). */
  director?: boolean
  className?: string
  shellClassName?: string
}

export function ManagementPageShell({
  children,
  director,
  className,
  shellClassName,
}: ManagementPageShellProps) {
  const isDirector = useManagementDirector()
  const useDirector = director ?? isDirector

  return (
    <div
      className={['spa-mgmt', useDirector ? 'spa-mgmt--director' : '', className]
        .filter(Boolean)
        .join(' ')}
    >
      <div className={['spa-mgmt-shell', shellClassName].filter(Boolean).join(' ')}>{children}</div>
    </div>
  )
}

type ManagementPageHeroProps = {
  children: ReactNode
  className?: string
}

export function ManagementPageHero({ children, className }: ManagementPageHeroProps) {
  return <header className={['spa-mgmt-hero', className].filter(Boolean).join(' ')}>{children}</header>
}
