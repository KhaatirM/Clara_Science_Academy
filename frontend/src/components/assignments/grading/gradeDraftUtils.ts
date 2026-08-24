import type { GradeStudentRow } from '../../../api/assignmentWorkspace'
import type { GradeRowDraft } from './PdfPaperGradeCard'

export function isPdfPaperAssignmentType(assignmentType: string | null | undefined): boolean {
  const t = (assignmentType || '').toLowerCase().replace(/[/\s-]+/g, '_')
  return !t || t === 'pdf' || t === 'paper' || t === 'pdf_paper' || t === 'file' || t === 'homework'
}

export function draftFromGradeRow(row: GradeStudentRow): GradeRowDraft {
  const score = row.grade.score ?? row.grade.points_earned
  const sub = row.submission
  let submissionNotesType = sub?.submission_notes_type || 'On-Time'
  let submissionNotes = ''
  const rawNotes = sub?.submission_notes || row.submission_notes || ''

  if (!sub?.submission_notes_type) {
    if (rawNotes === 'On-Time' || rawNotes === 'Late') {
      submissionNotesType = rawNotes
    } else if (rawNotes) {
      submissionNotesType = 'Other'
      submissionNotes = rawNotes
    }
  } else if (submissionNotesType === 'Other') {
    submissionNotes = sub?.submission_notes_other || rawNotes
  }

  return {
    score: score != null ? String(score) : '',
    comment: row.grade.comment || '',
    submission_type: sub?.submission_type || row.submission_type || 'not_submitted',
    submission_notes_type: submissionNotesType,
    submission_notes: submissionNotes,
  }
}

export function gradeHistoryUrl(
  gradeId: number | null | undefined,
  scope: 'management' | 'teacher',
): string | null {
  if (!gradeId) return null
  const base = scope === 'teacher' ? '/teacher' : '/management'
  return `${base}/grades/history/${gradeId}`
}
