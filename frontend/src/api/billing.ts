import { apiFetch } from './client'
import type { BillingActionResponse, BillingHubResponse } from '../types/billing'

export async function fetchBillingHub(): Promise<BillingHubResponse> {
  return apiFetch<BillingHubResponse>('/api/spa/billing/hub')
}

export async function billingAddInvoicePlaceholder(): Promise<BillingActionResponse> {
  return apiFetch<BillingActionResponse>('/api/spa/billing/add-invoice', { method: 'POST' })
}

export async function billingRecordPaymentPlaceholder(): Promise<BillingActionResponse> {
  return apiFetch<BillingActionResponse>('/api/spa/billing/record-payment', { method: 'POST' })
}
