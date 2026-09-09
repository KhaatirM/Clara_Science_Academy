/** Match backend `_normalize_assignment_type` / `_is_pdf_paper_type`. */
export function normalizeAssignmentType(type: string | null | undefined): string {
  return (type || '').toLowerCase().replace(/\//g, '_').replace(/\s+/g, '_')
}

export function isPdfPaperAssignmentType(type: string | null | undefined): boolean {
  const normalized = normalizeAssignmentType(type)
  return !normalized || normalized === 'pdf' || normalized === 'paper' || normalized === 'pdf_paper'
}

export function assignmentTypeLabel(type: string | null | undefined): string {
  const t = normalizeAssignmentType(type)
  if (t === 'quiz') return 'Quiz'
  if (t === 'discussion') return 'Discussion'
  if (t === 'group' || t === 'group_assignment') return 'Group'
  if (isPdfPaperAssignmentType(type)) return 'PDF / Paper'
  if (!t) return 'Assignment'
  return t.replace(/_/g, ' ')
}

export function assignmentTypeTone(type: string | null | undefined): string {
  const t = normalizeAssignmentType(type)
  if (t === 'quiz') return 'bg-violet-100 text-violet-800'
  if (t === 'discussion') return 'bg-sky-100 text-sky-800'
  if (isPdfPaperAssignmentType(type)) return 'bg-amber-100 text-amber-900'
  return 'bg-slate-100 text-slate-700'
}
