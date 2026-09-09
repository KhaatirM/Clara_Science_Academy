import { apiFetch } from './client'
import type { PendingGradesResponse } from '../types/pendingGrades'

export async function fetchPendingGrades(scope: 'management' | 'teacher') {
  return apiFetch<PendingGradesResponse>(`/api/spa/pending-grades?scope=${scope}`)
}

export const PENDING_GRADES_OPEN_EVENT = 'clara:open-pending-grades'

export function openPendingGradesModal() {
  window.dispatchEvent(new CustomEvent(PENDING_GRADES_OPEN_EVENT))
}
