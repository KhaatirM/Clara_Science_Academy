import type { GradeStudentRow } from '../../../api/assignmentWorkspace'
import type { GradeRowDraft } from './PdfPaperGradeCard'
import {
  bucketFromDraft,
  letterFromPercent,
  percentFromScore,
  type GradeBucket,
} from './gradeUtils'

export type GradePrintPayload = {
  title: string
  className: string
  subject?: string | null
  dueDate?: string | null
  quarter?: string | null
  description?: string
  totalPoints: number
  rows: GradeStudentRow[]
  drafts: Record<string, GradeRowDraft>
}

const BUCKET_PRINT: Record<GradeBucket, { bg: string; text: string; label: string }> = {
  A: { bg: '#10b981', text: '#065f46', label: 'A' },
  B: { bg: '#0ea5e9', text: '#075985', label: 'B' },
  C: { bg: '#f59e0b', text: '#92400e', label: 'C' },
  D: { bg: '#f97316', text: '#9a3412', label: 'D' },
  F: { bg: '#ef4444', text: '#991b1b', label: 'F' },
  ungraded: { bg: '#cbd5e1', text: '#475569', label: 'Not entered' },
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function formatDue(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function submissionLabel(type: string) {
  if (type === 'in_person') return 'Submitted (Paper/In-Person)'
  if (type === 'online') return 'Submitted (Online)'
  return 'Not Submitted'
}

function notesLabel(draft: GradeRowDraft) {
  if (draft.submission_notes_type === 'Other') {
    return draft.submission_notes.trim() || 'Other'
  }
  return draft.submission_notes_type || 'On-Time'
}

function buildSpreadCounts(payload: GradePrintPayload) {
  const counts: Record<GradeBucket, number> = { A: 0, B: 0, C: 0, D: 0, F: 0, ungraded: 0 }
  for (const row of payload.rows) {
    if (row.grade.is_voided) continue
    const draft = payload.drafts[String(row.student.id)]
    if (!draft) continue
    const bucket = bucketFromDraft(draft.score, payload.totalPoints, false)
    counts[bucket] += 1
  }
  return counts
}

function buildPrintHtml(payload: GradePrintPayload) {
  const counts = buildSpreadCounts(payload)
  const gradedTotal = counts.A + counts.B + counts.C + counts.D + counts.F
  const barTotal = gradedTotal + counts.ungraded || 1
  const printedAt = new Date().toLocaleString()

  const spreadPills = (['A', 'B', 'C', 'D', 'F', 'ungraded'] as GradeBucket[])
    .map((b) => {
      const style = BUCKET_PRINT[b]
      return `<span class="pill" style="background:${style.bg}22;color:${style.text}">${style.label} <strong>${counts[b]}</strong></span>`
    })
    .join('')

  const spreadBar = (['A', 'B', 'C', 'D', 'F', 'ungraded'] as GradeBucket[])
    .map((b) => {
      const w = (counts[b] / barTotal) * 100
      if (w <= 0) return ''
      return `<div class="bar-seg" style="width:${w}%;background:${BUCKET_PRINT[b].bg}"></div>`
    })
    .join('')

  const studentCards = payload.rows
    .map((row) => {
      const key = String(row.student.id)
      const draft = payload.drafts[key]
      if (!draft) return ''
      const voided = row.grade.is_voided
      const pct = percentFromScore(draft.score, payload.totalPoints)
      const bucket = voided ? 'ungraded' : bucketFromDraft(draft.score, payload.totalPoints, false)
      const borderColor = voided ? '#94a3b8' : BUCKET_PRINT[bucket].bg

      const scoreBlock = voided
        ? '<div class="muted">Voided</div>'
        : pct != null
          ? `<div class="score">${escapeHtml(draft.score)} / ${payload.totalPoints}</div>
             <div class="muted">(${pct}%) ${letterFromPercent(pct)}</div>`
          : '<div class="muted">Not entered</div>'

      return `
        <article class="card" style="border-color:${borderColor}">
          <header class="card-head">
            <div>
              <div class="name">${escapeHtml(row.student.display_name)}</div>
              <div class="email">${escapeHtml(row.student.email || 'No email')}</div>
            </div>
            <div class="badge">${escapeHtml(voided ? 'Voided' : submissionLabel(draft.submission_type))}</div>
          </header>
          <div class="card-grid">
            <div><span class="lbl">Submission status</span><div>${escapeHtml(submissionLabel(draft.submission_type))}</div></div>
            <div><span class="lbl">Submission notes</span><div>${escapeHtml(notesLabel(draft))}</div></div>
            <div><span class="lbl">Points earned</span>${scoreBlock}</div>
            <div class="feedback"><span class="lbl">Feedback</span><div>${escapeHtml(draft.comment.trim() || '—')}</div></div>
          </div>
        </article>`
    })
    .join('')

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(payload.title)} — Gradebook</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; color: #1e293b; margin: 0.5in; font-size: 11pt; }
    h1 { margin: 0 0 0.25rem; font-size: 20pt; }
    .subtitle { color: #64748b; margin: 0 0 1rem; font-size: 10pt; }
    .section { border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 14px; break-inside: avoid; }
    .section-title { font-size: 11pt; font-weight: 700; margin: 0 0 10px; color: #334155; }
    .details-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    .detail-label { font-size: 8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b; }
    .detail-value { font-weight: 600; margin-top: 2px; }
    .desc { margin-top: 10px; padding-top: 10px; border-top: 1px solid #f1f5f9; color: #475569; font-size: 10pt; }
    .pills { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
    .pill { padding: 3px 10px; border-radius: 999px; font-size: 9pt; font-weight: 600; }
    .bar { display: flex; height: 10px; border-radius: 999px; overflow: hidden; background: #f1f5f9; }
    .bar-seg { height: 100%; }
    .footnote { font-size: 8.5pt; color: #64748b; margin: 8px 0 0; }
    .card { border: 2px solid #e2e8f0; border-radius: 10px; margin-bottom: 12px; break-inside: avoid; page-break-inside: avoid; }
    .card-head { display: flex; justify-content: space-between; gap: 12px; padding: 12px 14px; border-bottom: 1px solid #f1f5f9; }
    .name { font-weight: 700; font-size: 11pt; }
    .email { font-size: 9pt; color: #64748b; }
    .badge { font-size: 9pt; font-weight: 700; padding: 4px 10px; border-radius: 999px; background: #f1f5f9; white-space: nowrap; }
    .card-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; padding: 12px 14px; }
    .feedback { grid-column: 1 / -1; }
    .lbl { display: block; font-size: 8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b; margin-bottom: 2px; }
    .score { font-size: 14pt; font-weight: 800; color: #047857; }
    .muted { color: #64748b; font-size: 10pt; }
    @media print {
      body { margin: 0.35in; }
      .section, .card { box-shadow: none; }
    }
  </style>
</head>
<body>
  <h1>${escapeHtml(payload.title)}</h1>
  <p class="subtitle">${escapeHtml(payload.className)} · Printed ${escapeHtml(printedAt)}</p>

  <section class="section">
    <h2 class="section-title">Assignment details</h2>
    <div class="details-grid">
      <div><div class="detail-label">Class</div><div class="detail-value">${escapeHtml(payload.className)}</div></div>
      <div><div class="detail-label">Due date</div><div class="detail-value">${escapeHtml(formatDue(payload.dueDate))}</div></div>
      <div><div class="detail-label">Quarter</div><div class="detail-value">${escapeHtml(payload.quarter || '—')}</div></div>
      <div><div class="detail-label">Subject</div><div class="detail-value">${escapeHtml(payload.subject || 'N/A')}</div></div>
    </div>
    ${payload.description ? `<div class="desc"><strong>Description:</strong> ${escapeHtml(payload.description)}</div>` : ''}
  </section>

  <section class="section">
    <h2 class="section-title">Grade spread</h2>
    <div class="pills">${spreadPills}</div>
    <div class="bar">${spreadBar}</div>
    <p class="footnote">Entering 0 is a real grade (F). Blank means not entered. Voided students are excluded.</p>
  </section>

  <section>
    <h2 class="section-title">Student grades</h2>
    ${studentCards}
  </section>
</body>
</html>`
}

export function printAssignmentGradebook(payload: GradePrintPayload) {
  const html = buildPrintHtml(payload)
  const printWindow = window.open('', '_blank', 'width=900,height=700')
  if (!printWindow) {
    window.alert('Pop-up blocked. Allow pop-ups to print the gradebook.')
    return
  }
  printWindow.document.write(html)
  printWindow.document.close()
  printWindow.focus()
  window.setTimeout(() => {
    printWindow.print()
    printWindow.close()
  }, 300)
}
