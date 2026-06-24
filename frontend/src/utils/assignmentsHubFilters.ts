import type { ClassListItem } from '../types/classes'
import { teacherKeyForItem } from './classListFilters'

export type AssignmentsHubSort =
  | 'name_asc'
  | 'name_desc'
  | 'assignments_desc'
  | 'students_desc'

export interface AssignmentsHubFilters {
  search: string
  schoolYearId: number | ''
  subject: string
  grade: string
  teacherKey: string
  enrollment: '' | 'with' | 'empty'
  assignment: '' | 'with' | 'none'
  sort: AssignmentsHubSort
}

export const defaultAssignmentsHubFilters: AssignmentsHubFilters = {
  search: '',
  schoolYearId: '',
  subject: '',
  grade: '',
  teacherKey: '',
  enrollment: '',
  assignment: '',
  sort: 'name_asc',
}

export const ASSIGNMENTS_HUB_SORT_OPTIONS: { value: AssignmentsHubSort; label: string }[] = [
  { value: 'name_asc', label: 'Class name (A–Z)' },
  { value: 'name_desc', label: 'Class name (Z–A)' },
  { value: 'assignments_desc', label: 'Most assignments' },
  { value: 'students_desc', label: 'Most students' },
]

export function subjectOptionsForHub(items: ClassListItem[]): string[] {
  const subjects = new Set<string>()
  for (const item of items) {
    const subj = (item.subject || '').trim()
    if (subj) subjects.add(subj)
  }
  return Array.from(subjects).sort((a, b) => a.localeCompare(b))
}

export function filterAssignmentsHubClasses(
  items: ClassListItem[],
  filters: AssignmentsHubFilters,
): ClassListItem[] {
  if (!filters.schoolYearId) return []

  const search = filters.search.trim().toLowerCase()
  let result = items.filter((item) => {
    if (item.school_year_id !== filters.schoolYearId) return false
    if (search && !item.search_text.includes(search)) return false
    if (filters.subject && item.subject !== filters.subject) return false
    if (filters.grade && !item.grade_levels.map(String).includes(filters.grade)) return false
    if (filters.teacherKey && teacherKeyForItem(item) !== filters.teacherKey) return false
    if (filters.enrollment === 'with' && item.enrollment_count <= 0) return false
    if (filters.enrollment === 'empty' && item.enrollment_count > 0) return false
    if (filters.assignment === 'with' && item.assignment_count <= 0) return false
    if (filters.assignment === 'none' && item.assignment_count > 0) return false
    return true
  })

  result = [...result].sort((a, b) => {
    const nameA = a.name.toLowerCase()
    const nameB = b.name.toLowerCase()
    switch (filters.sort) {
      case 'name_desc':
        return nameB.localeCompare(nameA)
      case 'assignments_desc':
        return b.assignment_count - a.assignment_count || nameA.localeCompare(nameB)
      case 'students_desc':
        return b.enrollment_count - a.enrollment_count || nameA.localeCompare(nameB)
      default:
        return nameA.localeCompare(nameB)
    }
  })

  return result
}

export function computeAssignmentsHubStats(items: ClassListItem[]) {
  const teacherKeys = new Set(
    items
      .map((i) => i.teacher.display_name.trim().toLowerCase())
      .filter((k) => k && k !== 'n/a'),
  )
  return {
    total_classes: items.length,
    total_assignments: items.reduce((sum, i) => sum + i.assignment_count, 0),
    total_enrollments: items.reduce((sum, i) => sum + i.enrollment_count, 0),
    unique_teachers: teacherKeys.size,
  }
}
