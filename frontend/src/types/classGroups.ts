import type { StudentBrief } from './classDetail'

export interface ClassGroupMember {
  student_id: number
  display_name: string
  is_leader: boolean
}

export interface ClassGroupItem {
  id: number
  name: string
  description: string
  max_students: number | null
  member_count: number
  members: ClassGroupMember[]
}

export interface ClassGroupsResponse {
  class: { id: number; name: string; subject: string | null }
  groups: ClassGroupItem[]
  enrolled_students: StudentBrief[]
  stats: {
    total_groups: number
    total_students: number
    avg_group_size: number
  }
  meta?: { can_admin_ui: boolean; can_create: boolean }
}

export type ClassGroupsAction =
  | { action: 'create'; name: string; description?: string; max_students?: number | null }
  | { action: 'update'; group_id: number; name?: string; description?: string; max_students?: number | null }
  | { action: 'delete'; group_id: number }
  | { action: 'add_members'; group_id: number; student_ids: number[]; leader_id?: number | null }
  | { action: 'remove_member'; group_id: number; student_id: number }
  | { action: 'set_leader'; group_id: number; student_id: number }
