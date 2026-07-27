export type BillingMetrics = {
  total_revenue: number
  total_payments: number
  outstanding_balance: number
  student_count: number
  active_invoices: number
  pending_invoices: number
}

export type BillingHubResponse = {
  role_canonical: string
  is_director: boolean
  metrics: BillingMetrics
  invoices: unknown[]
  pending_invoices: unknown[]
  coming_soon: boolean
  urls: {
    home: string
    payment_policy?: string
  }
}

export type BillingActionResponse = {
  success: boolean
  message: string
}
