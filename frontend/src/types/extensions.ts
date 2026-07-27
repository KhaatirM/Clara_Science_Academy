export interface ExtensionRequestItem {
  id: number
  status: 'Pending' | 'Approved' | 'Rejected' | string
  reason: string
  review_notes: string
  requested_at: string | null
  reviewed_at: string | null
  requested_due_date: string | null
  current_due_date: string | null
  student: { id: number | null; display_name: string }
  assignment: { id: number | null; title: string }
  class: { id: number | null; name: string }
  search_text: string
}

export interface ExtensionsHubResponse {
  items: ExtensionRequestItem[]
  pending: ExtensionRequestItem[]
  approved: ExtensionRequestItem[]
  rejected: ExtensionRequestItem[]
  stats: {
    total: number
    pending: number
    approved: number
    rejected: number
  }
  meta: {
    active_school_year_id: number | null
    active_school_year_name: string | null
    has_active_school_year: boolean
  }
}

export interface ApiActionResponse {
  success: boolean
  message: string
  processed_count?: number
  failed?: unknown[]
}
