export type GradeDisplayValue = string | number

/** Letter band a grade falls in; 'none' covers voided, missing, and unparseable grades. */
export type GradeTone = 'A' | 'B' | 'C' | 'D' | 'F' | 'none'

type GradeToneClasses = {
  /** Soft pill/badge: border + background + text. */
  badge: string
  /** Filled badge for high-contrast corner tags. */
  solid: string
  /** Text-only, for large score numbers. */
  text: string
  /** Progress/meter fill. */
  bar: string
  /** Panel surface used by the grade section in the view popup. */
  panel: string
}

export const GRADE_TONES: Record<GradeTone, GradeToneClasses> = {
  A: {
    badge: 'border-emerald-300 bg-emerald-50 text-emerald-900',
    solid: 'bg-emerald-600 text-white',
    text: 'text-emerald-700',
    bar: 'bg-emerald-500',
    panel: 'border-emerald-200 bg-gradient-to-br from-emerald-50 to-white',
  },
  B: {
    badge: 'border-sky-300 bg-sky-50 text-sky-900',
    solid: 'bg-sky-600 text-white',
    text: 'text-sky-700',
    bar: 'bg-sky-500',
    panel: 'border-sky-200 bg-gradient-to-br from-sky-50 to-white',
  },
  C: {
    badge: 'border-amber-300 bg-amber-50 text-amber-900',
    solid: 'bg-amber-500 text-white',
    text: 'text-amber-700',
    bar: 'bg-amber-500',
    panel: 'border-amber-200 bg-gradient-to-br from-amber-50 to-white',
  },
  D: {
    badge: 'border-orange-300 bg-orange-50 text-orange-900',
    solid: 'bg-orange-600 text-white',
    text: 'text-orange-700',
    bar: 'bg-orange-500',
    panel: 'border-orange-200 bg-gradient-to-br from-orange-50 to-white',
  },
  F: {
    badge: 'border-red-300 bg-red-50 text-red-800',
    solid: 'bg-red-600 text-white',
    text: 'text-red-700',
    bar: 'bg-red-500',
    panel: 'border-red-200 bg-gradient-to-br from-red-50 to-white',
  },
  none: {
    badge: 'border-slate-300 bg-slate-100 text-slate-700',
    solid: 'bg-slate-500 text-white',
    text: 'text-slate-700',
    bar: 'bg-slate-400',
    panel: 'border-slate-200 bg-gradient-to-br from-slate-50 to-white',
  },
}

export function gradeToneFromPercent(pct: number | null | undefined): GradeTone {
  if (pct == null || !Number.isFinite(pct)) return 'none'
  if (pct >= 90) return 'A'
  if (pct >= 80) return 'B'
  if (pct >= 70) return 'C'
  if (pct >= 60) return 'D'
  return 'F'
}

export function gradeToneFromLetter(letter: string | null | undefined): GradeTone {
  const first = (letter || '').trim().charAt(0).toUpperCase()
  if (first === 'A' || first === 'B' || first === 'C' || first === 'D') return first
  if (first === 'F' || first === 'E') return 'F'
  return 'none'
}

export function gradeTone(grade: GradeDisplayValue): GradeTone {
  if (
    grade === 'Voided' ||
    grade === 'Not Graded' ||
    grade === 'Not Assigned' ||
    grade === 'No Group'
  ) {
    return 'none'
  }
  if (grade === 'N/A') return 'F'
  const num = typeof grade === 'number' ? grade : Number.parseFloat(String(grade))
  if (Number.isNaN(num)) return 'none'
  return gradeToneFromPercent(num)
}

export function gradeBadgeClass(grade: GradeDisplayValue): string {
  return GRADE_TONES[gradeTone(grade)].badge
}

export function formatGradeLabel(grade: GradeDisplayValue): string {
  if (grade === 'Not Graded' || grade === 'Not Assigned' || grade === 'No Group' || grade === 'Voided' || grade === 'N/A') {
    return String(grade)
  }
  if (typeof grade === 'number') return String(grade)
  return String(grade)
}
