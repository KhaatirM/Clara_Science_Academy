export interface ParentLinkedChild {
  id: number
  display_name: string
}

export interface ParentAccountItem {
  id: number
  username: string
  email: string
  initial: string
  children: ParentLinkedChild[]
  link_count: number
}

export interface ParentsHubStats {
  parent_accounts: number
  students_with_parent_email: number
  total_child_links: number
  students_not_linked: number
}

export interface ParentsHubResponse {
  items: ParentAccountItem[]
  stats: ParentsHubStats
  meta: {
    can_provision: boolean
  }
}

export interface ParentProvisionCredential {
  slot?: number
  student_id?: number
  student_name?: string
  parent_name?: string
  email?: string
  username?: string
  portal_password?: string
  created_new?: boolean
  password_reissued?: boolean
}

export interface ParentProvisionAllResponse {
  success: boolean
  message?: string
  linked?: number
  created?: number
  reissued?: number
  skipped?: number
  errors?: string[]
  credentials?: ParentProvisionCredential[]
  emails_sent?: number
}
