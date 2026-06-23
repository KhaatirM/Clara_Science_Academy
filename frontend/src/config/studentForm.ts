export { US_STATES } from './staffForm'

/** Grade labels for the add-student form (POST field `grade_level`). */
export const STUDENT_GRADES_FOR_ADD = [
  'Kindergarten',
  '1st',
  '2nd',
  '3rd',
  '4th',
  '5th',
  '6th',
  '7th',
  '8th',
  '9th',
  '10th',
  '11th',
  '12th',
] as const

/** Grade options for edit (numeric values match backend `parse_grade_level_for_policy`). */
export const STUDENT_GRADE_OPTIONS = [
  { value: '0', label: 'Kindergarten' },
  { value: '1', label: '1st Grade' },
  { value: '2', label: '2nd Grade' },
  { value: '3', label: '3rd Grade' },
  { value: '4', label: '4th Grade' },
  { value: '5', label: '5th Grade' },
  { value: '6', label: '6th Grade' },
  { value: '7', label: '7th Grade' },
  { value: '8', label: '8th Grade' },
  { value: '9', label: '9th Grade' },
  { value: '10', label: '10th Grade' },
  { value: '11', label: '11th Grade' },
  { value: '12', label: '12th Grade' },
] as const

export const STUDENT_GENDERS = [
  'Male',
  'Female',
  'Non-binary',
  'Prefer not to say',
  'Other',
] as const

export const PARENT_RELATIONSHIPS = ['Mother', 'Father'] as const

export const EMERGENCY_RELATIONSHIPS = [
  'Parent',
  'Guardian',
  'Grandparent',
  'Aunt/Uncle',
  'Sibling',
  'Other',
] as const

export function buildEntranceSchoolYearOptions(startYear = 2020): string[] {
  const now = new Date()
  const currentStartYear = now.getMonth() >= 6 ? now.getFullYear() : now.getFullYear() - 1
  const options: string[] = []
  for (let y = currentStartYear; y >= startYear; y -= 1) {
    options.push(`${y}-${y + 1}`)
  }
  return options
}
