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

export interface ParentProvisionAllResponse {
  success: boolean
  message?: string
  linked?: number
  created?: number
  skipped?: number
  errors?: string[]
}
