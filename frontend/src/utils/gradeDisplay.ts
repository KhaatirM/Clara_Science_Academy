export type GradeDisplayValue = string | number

export function gradeBadgeClass(grade: GradeDisplayValue): string {
  if (grade === 'Voided' || grade === 'Not Graded' || grade === 'Not Assigned' || grade === 'No Group') {
    return 'border-slate-300 bg-slate-100 text-slate-700'
  }
  if (grade === 'N/A') {
    return 'border-red-300 bg-red-50 text-red-800'
  }
  const num = typeof grade === 'number' ? grade : Number.parseFloat(String(grade))
  if (Number.isNaN(num)) {
    return 'border-slate-300 bg-slate-100 text-slate-700'
  }
  if (num >= 90) return 'border-emerald-300 bg-emerald-50 text-emerald-900'
  if (num >= 80) return 'border-sky-300 bg-sky-50 text-sky-900'
  if (num >= 70) return 'border-amber-300 bg-amber-50 text-amber-900'
  return 'border-red-300 bg-red-50 text-red-800'
}

export function formatGradeLabel(grade: GradeDisplayValue): string {
  if (grade === 'Not Graded' || grade === 'Not Assigned' || grade === 'No Group' || grade === 'Voided' || grade === 'N/A') {
    return String(grade)
  }
  if (typeof grade === 'number') return String(grade)
  return String(grade)
}
