import { useCallback, useState } from 'react'

const STORAGE_KEY = 'teachersStaffRecordsView'

export type StaffRecordsView = 'table' | 'cards'

export function useStaffRecordsView() {
  const [view, setView] = useState<StaffRecordsView>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'cards' ? 'cards' : 'table'
  })

  const setRecordsView = useCallback((next: StaffRecordsView) => {
    setView(next)
    localStorage.setItem(STORAGE_KEY, next)
  }, [])

  return { view, setRecordsView }
}
