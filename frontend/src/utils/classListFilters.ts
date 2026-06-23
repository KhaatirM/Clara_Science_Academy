import type { ClassListItem } from '../types/classes'

export type ClassSortKey =
  | 'name_asc'
  | 'name_desc'
  | 'teacher_asc'
  | 'students_desc'
  | 'assignments_desc'

export interface ClassFilters {
  search: string
  schoolYearId: number | ''
  subject: string
  status: '' | 'active' | 'inactive'
  grade: string
  teacherKey: string
  enrollment: '' | 'with' | 'empty'
  assignment: '' | 'with' | 'none'
  sort: ClassSortKey
}

export const defaultClassFilters: ClassFilters = {
  search: '',
  schoolYearId: '',
  subject: '',
  status: '',
  grade: '',
  teacherKey: '',
  enrollment: '',
  assignment: '',
  sort: 'name_asc',
}

export function teacherKeyForItem(item: ClassListItem): string {
  return item.teacher.display_name.trim().toLowerCase()
}

export function itemsForSchoolYear(items: ClassListItem[], schoolYearId: number | ''): ClassListItem[] {
  if (!schoolYearId) return []
  return items.filter((item) => item.school_year_id === schoolYearId)
}

export function subjectOptions(items: ClassListItem[]): string[] {
  const subjects = new Set<string>()
  items.forEach((item) => {
    const subj = (item.subject || '').trim()
    if (subj) subjects.add(subj)
  })
  return Array.from(subjects).sort((a, b) => a.localeCompare(b))
}

export function teacherOptions(
  items: ClassListItem[],
): { value: string; label: string }[] {
  const teachers = new Map<string, string>()
  items.forEach((item) => {
    const key = teacherKeyForItem(item)
    const label = item.teacher.display_name.trim()
    if (key && label && label !== 'N/A') teachers.set(key, label)
  })
  return Array.from(teachers.entries())
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([value, label]) => ({ value, label }))
}

export function filterAndSortClasses(items: ClassListItem[], filters: ClassFilters): ClassListItem[] {
  if (!filters.schoolYearId) return []

  const search = filters.search.trim().toLowerCase()
  let result = items.filter((item) => {
    if (item.school_year_id !== filters.schoolYearId) return false
    if (search && !item.search_text.includes(search)) return false
    if (filters.subject && item.subject !== filters.subject) return false
    if (filters.status === 'active' && !item.is_active) return false
    if (filters.status === 'inactive' && item.is_active) return false
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
    const teacherA = a.teacher.display_name.toLowerCase()
    const teacherB = b.teacher.display_name.toLowerCase()
    switch (filters.sort) {
      case 'name_desc':
        return nameB.localeCompare(nameA)
      case 'teacher_asc':
        return teacherA.localeCompare(teacherB) || nameA.localeCompare(nameB)
      case 'students_desc':
        return b.enrollment_count - a.enrollment_count || nameA.localeCompare(nameB)
      case 'assignments_desc':
        return b.assignment_count - a.assignment_count || nameA.localeCompare(nameB)
      default:
        return nameA.localeCompare(nameB)
    }
  })

  return result
}

export function computeClassStats(items: ClassListItem[]) {
  const teacherKeys = new Set(
    items
      .map(teacherKeyForItem)
      .filter((k) => k && k !== 'n/a'),
  )
  return {
    total_classes: items.length,
    total_enrollments: items.reduce((sum, i) => sum + i.enrollment_count, 0),
    unique_teachers: teacherKeys.size,
    total_assignments: items.reduce((sum, i) => sum + i.assignment_count, 0),
  }
}

export function exportClassesCsv(items: ClassListItem[]) {
  const header = ['Class', 'Subject', 'Teacher', 'Grades', 'Students', 'Assignments', 'Status', 'Room', 'Schedule']
  const rows = items.map((item) => [
    item.name,
    item.subject,
    item.teacher.display_name,
    item.grade_levels_display,
    String(item.enrollment_count),
    String(item.assignment_count),
    item.is_active ? 'Active' : 'Inactive',
    item.room_number || '',
    item.schedule || '',
  ])
  const escape = (cell: string) => `"${cell.replace(/"/g, '""')}"`
  const csv = [header, ...rows].map((row) => row.map(escape).join(',')).join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `classes-export-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export const GRADE_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All grades' },
  { value: '0', label: 'Kindergarten' },
  ...Array.from({ length: 8 }, (_, i) => {
    const g = i + 1
    const suffix = g === 1 ? 'st' : g === 2 ? 'nd' : g === 3 ? 'rd' : 'th'
    return { value: String(g), label: `${g}${suffix} Grade` }
  }),
]

export const SORT_OPTIONS: { value: ClassSortKey; label: string }[] = [
  { value: 'name_asc', label: 'Class name (A–Z)' },
  { value: 'name_desc', label: 'Class name (Z–A)' },
  { value: 'teacher_asc', label: 'Teacher (A–Z)' },
  { value: 'students_desc', label: 'Most students' },
  { value: 'assignments_desc', label: 'Most assignments' },
]
