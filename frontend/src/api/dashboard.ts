import { apiFetch } from './client'
import type { DashboardHomeResponse } from '../types/dashboard'

export async function fetchDashboardHome(): Promise<DashboardHomeResponse> {
  return apiFetch<DashboardHomeResponse>('/api/spa/dashboard/home')
}
