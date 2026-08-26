/** Match backend `_normalize_assignment_type` / `_is_pdf_paper_type`. */
export function normalizeAssignmentType(type: string | null | undefined): string {
  return (type || '').toLowerCase().replace(/\//g, '_').replace(/\s+/g, '_')
}

export function isPdfPaperAssignmentType(type: string | null | undefined): boolean {
  const normalized = normalizeAssignmentType(type)
  return !normalized || normalized === 'pdf' || normalized === 'paper' || normalized === 'pdf_paper'
}
