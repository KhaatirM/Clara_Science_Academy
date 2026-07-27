import { useOutletContext } from 'react-router-dom'

import type { ManagementOutletContext } from '../types/layout'

export function useManagementDirector(): boolean {
  const { user } = useOutletContext<ManagementOutletContext>()
  return user.role_canonical === 'Director'
}
