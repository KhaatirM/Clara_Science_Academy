import type { ClassPeriodItem, ClassPeriodStats } from '../types/attendance'

export type ClassPeriodCompletionFilter = '' | 'completed' | 'pending'

export type ClassPeriodSortKey = 'name_asc' | 'teacher_asc' | 'pending_first' | 'students_desc'

export interface ClassPeriodFilters {
  search: string
  subject: string
  teacherKey: string
  grade: string
  completion: ClassPeriodCompletionFilter
  sort: ClassPeriodSortKey
}

export const defaultClassPeriodFilters: ClassPeriodFilters = {
  search: '',
  subject: '',
  teacherKey: '',
  grade: '',
  completion: '',
  sort: 'name_asc',
}

export function teacherKeyForPeriod(item: ClassPeriodItem): string {
  return (item.teacher_name || '').trim().toLowerCase()
}

export function subjectOptionsForPeriod(items: ClassPeriodItem[]): string[] {
  const subjects = new Set<string>()
  items.forEach((item) => {
    const subject = (item.subject || '').trim()
    if (subject) subjects.add(subject)
  })
  return Array.from(subjects).sort((a, b) => a.localeCompare(b))
}

export function teacherOptionsForPeriod(
  items: ClassPeriodItem[],
): { value: string; label: string }[] {
  const teachers = new Map<string, string>()
  items.forEach((item) => {
    const key = teacherKeyForPeriod(item)
    const label = (item.teacher_name || '').trim()
    if (key && label && label.toLowerCase() !== 'n/a') teachers.set(key, label)
  })
  return Array.from(teachers.entries())
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([value, label]) => ({ value, label }))
}

function matchesGrade(display: string, grade: string): boolean {
  if (!grade) return true
  const normalized = (display || '').trim()
  if (!normalized) return false
  const tokens = normalized.split(/[,/]+/).map((part) => part.replace(/\D/g, '') || part.trim())
  return tokens.includes(grade) || new RegExp(`\\b${grade}\\b`).test(normalized)
}

export function filterAndSortClassPeriods(
  items: ClassPeriodItem[],
  filters: ClassPeriodFilters,
): ClassPeriodItem[] {
  const search = filters.search.trim().toLowerCase()
  let result = items.filter((item) => {
    if (search) {
      const haystack = [
        item.name,
        item.subject,
        item.teacher_name,
        item.grade_levels_display,
      ]
        .join(' ')
        .toLowerCase()
      if (!haystack.includes(search)) return false
    }
    if (filters.subject && item.subject !== filters.subject) return false
    if (filters.teacherKey && teacherKeyForPeriod(item) !== filters.teacherKey) return false
    if (filters.grade && !matchesGrade(item.grade_levels_display, filters.grade)) return false
    if (filters.completion === 'completed' && !item.attendance_taken) return false
    if (filters.completion === 'pending' && item.attendance_taken) return false
    return true
  })

  result = [...result].sort((a, b) => {
    const nameA = a.name.toLowerCase()
    const nameB = b.name.toLowerCase()
    const teacherA = a.teacher_name.toLowerCase()
    const teacherB = b.teacher_name.toLowerCase()
    switch (filters.sort) {
      case 'teacher_asc':
        return teacherA.localeCompare(teacherB) || nameA.localeCompare(nameB)
      case 'pending_first':
        if (a.attendance_taken !== b.attendance_taken) {
          return a.attendance_taken ? 1 : -1
        }
        return nameA.localeCompare(nameB)
      case 'students_desc':
        return b.student_count - a.student_count || nameA.localeCompare(nameB)
      default:
        return nameA.localeCompare(nameB)
    }
  })

  return result
}

export function computeClassPeriodStats(items: ClassPeriodItem[]): ClassPeriodStats {
  const classes_completed = items.filter((item) => item.attendance_taken).length
  const pending_classes = items.length - classes_completed
  const totalRecords = items.reduce(
    (sum, item) => sum + (item.attendance_taken ? item.today_present + item.today_absent : 0),
    0,
  )
  const presentRecords = items.reduce(
    (sum, item) => sum + (item.attendance_taken ? item.today_present : 0),
    0,
  )
  const overall_rate =
    totalRecords > 0 ? Math.round((presentRecords / totalRecords) * 1000) / 10 : 0
  return { classes_completed, pending_classes, overall_rate }
}

export function classPeriodFiltersActive(filters: ClassPeriodFilters): boolean {
  return Boolean(
    filters.search.trim()
      || filters.subject
      || filters.teacherKey
      || filters.grade
      || filters.completion,
  )
}

export const CLASS_PERIOD_GRADE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All grades' },
  { value: '0', label: 'Kindergarten' },
  ...Array.from({ length: 8 }, (_, i) => {
    const g = i + 1
    const suffix = g === 1 ? 'st' : g === 2 ? 'nd' : g === 3 ? 'rd' : 'th'
    return { value: String(g), label: `${g}${suffix} Grade` }
  }),
]

export const CLASS_PERIOD_SORT_OPTIONS: { value: ClassPeriodSortKey; label: string }[] = [
  { value: 'name_asc', label: 'Class name (A–Z)' },
  { value: 'teacher_asc', label: 'Teacher (A–Z)' },
  { value: 'pending_first', label: 'Pending first' },
  { value: 'students_desc', label: 'Most students' },
]
