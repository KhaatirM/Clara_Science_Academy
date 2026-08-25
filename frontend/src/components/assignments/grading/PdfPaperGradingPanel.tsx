import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { saveIndividualStudentGrade, type GradeStudentRow } from '../../../api/assignmentWorkspace'
import type { AssignmentWorkspaceScope } from '../../../utils/assignmentWorkspaceScope'
import { BulkGradingToolbar } from './BulkGradingToolbar'
import { GradeSpreadBar } from './GradeSpreadBar'
import { PdfPaperGradeCard, type GradeRowDraft } from './PdfPaperGradeCard'
import { draftFromGradeRow, gradeHistoryUrl } from './gradeDraftUtils'
import { bucketFromDraft, matchesSpreadFilter, type SpreadFilter } from './gradeUtils'

export type StudentSubmissionFile = {
  download_url: string
  file_name: string
}

type Props = {
  assignmentId: number
  rows: GradeStudentRow[]
  totalPoints: number
  allowExtraCredit?: boolean
  maxExtraCreditPoints?: number
  filesByStudent?: Record<number, StudentSubmissionFile>
  workspaceScope?: AssignmentWorkspaceScope
  onSaved?: () => void
}

function rowKey(studentId: number) {
  return String(studentId)
}

function draftsEqual(a: GradeRowDraft, b: GradeRowDraft): boolean {
  return (
    a.score === b.score &&
    a.comment === b.comment &&
    a.submission_type === b.submission_type &&
    a.submission_notes_type === b.submission_notes_type &&
    a.submission_notes === b.submission_notes
  )
}

export function PdfPaperGradingPanel({
  assignmentId,
  rows,
  totalPoints,
  allowExtraCredit = false,
  maxExtraCreditPoints = 0,
  filesByStudent = {},
  workspaceScope = 'management',
  onSaved,
}: Props) {
  const maxGradingPoints = totalPoints + (allowExtraCredit ? maxExtraCreditPoints : 0)
  const [drafts, setDrafts] = useState<Record<string, GradeRowDraft>>(() => {
    const init: Record<string, GradeRowDraft> = {}
    for (const row of rows) {
      init[rowKey(row.student.id)] = draftFromGradeRow(row)
    }
    return init
  })
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [spreadFilter, setSpreadFilter] = useState<SpreadFilter>('all')
  const [message, setMessage] = useState<string | null>(null)
  const [savingIds, setSavingIds] = useState<Set<number>>(new Set())
  const saveTimers = useRef<Record<number, ReturnType<typeof setTimeout>>>({})
  const rowsRef = useRef(rows)
  rowsRef.current = rows
  const draftsRef = useRef(drafts)
  draftsRef.current = drafts
  /** Students with local edits that haven't finished saving yet — preserve across row reloads. */
  const dirtyIdsRef = useRef<Set<number>>(new Set())
  const onSavedRef = useRef(onSaved)
  onSavedRef.current = onSaved
  const saveStudentRef = useRef<
    (studentId: number, silent?: boolean, reload?: boolean) => Promise<void>
  >(async () => undefined)

  useEffect(() => {
    setDrafts((prev) => {
      const next: Record<string, GradeRowDraft> = {}
      for (const row of rows) {
        const key = rowKey(row.student.id)
        const incoming = draftFromGradeRow(row)
        const existing = prev[key]
        if (
          existing &&
          dirtyIdsRef.current.has(row.student.id) &&
          !draftsEqual(existing, incoming)
        ) {
          // Keep in-progress typing while another row's save reloads the roster.
          next[key] = existing
        } else {
          next[key] = incoming
          dirtyIdsRef.current.delete(row.student.id)
        }
      }
      draftsRef.current = next
      return next
    })
  }, [rows])

  const selectableRows = useMemo(
    () => rows.filter((row) => !row.grade.is_voided),
    [rows],
  )

  const spreadDrafts = useMemo(() => {
    const out: Record<string, { score: string; isVoided: boolean }> = {}
    for (const row of rows) {
      const key = rowKey(row.student.id)
      const draft = drafts[key] || draftFromGradeRow(row)
      out[key] = { score: draft.score, isVoided: row.grade.is_voided }
    }
    return out
  }, [drafts, rows])

  const visibleRows = useMemo(() => {
    return selectableRows.filter((row) => {
      const draft = drafts[rowKey(row.student.id)] || draftFromGradeRow(row)
      const bucket = bucketFromDraft(draft.score, totalPoints, row.grade.is_voided)
      return matchesSpreadFilter(bucket, spreadFilter, draft.score, row.grade.is_voided)
    })
  }, [drafts, selectableRows, spreadFilter, totalPoints])

  const updateDraft = useCallback((studentId: number, patch: Partial<GradeRowDraft>) => {
    const key = rowKey(studentId)
    setDrafts((prev) => {
      const base =
        prev[key] ||
        draftFromGradeRow(rowsRef.current.find((r) => r.student.id === studentId)!)
      const nextDraft = { ...base, ...patch }
      const next = { ...prev, [key]: nextDraft }
      // Keep ref in sync immediately so auto-save timers never read a stale draft.
      draftsRef.current = next
      dirtyIdsRef.current.add(studentId)
      return next
    })
  }, [])

  const scheduleAutoSave = useCallback((studentId: number) => {
    const row = rowsRef.current.find((r) => r.student.id === studentId)
    if (!row || row.grade.is_voided) return
    const existing = saveTimers.current[studentId]
    if (existing) clearTimeout(existing)
    saveTimers.current[studentId] = setTimeout(() => {
      void saveStudentRef.current(studentId, true)
    }, 2000)
  }, [])

  const saveStudent = useCallback(
    async (studentId: number, silent = false, reload?: boolean) => {
      const row = rowsRef.current.find((r) => r.student.id === studentId)
      const draft = draftsRef.current[rowKey(studentId)]
      if (!row || !draft || row.grade.is_voided) return

      const shouldReload = reload ?? !silent
      const snapshot: GradeRowDraft = { ...draft }
      setSavingIds((prev) => new Set(prev).add(studentId))
      if (!silent) setMessage(null)
      try {
        await saveIndividualStudentGrade(
          assignmentId,
          studentId,
          {
            score: snapshot.score,
            comment: snapshot.comment,
            submission_type: snapshot.submission_type,
            submission_notes_type: snapshot.submission_notes_type,
            submission_notes: snapshot.submission_notes,
          },
          workspaceScope,
        )
        const current = draftsRef.current[rowKey(studentId)]
        if (current && draftsEqual(current, snapshot)) {
          dirtyIdsRef.current.delete(studentId)
        } else if (current) {
          // User kept typing during the request — save again with the latest draft.
          scheduleAutoSave(studentId)
        }
        if (!silent) {
          setMessage(`Saved grade for ${row.student.display_name}`)
        }
        // Full reload only when requested; dirty drafts are preserved across reloads.
        if (shouldReload) onSavedRef.current?.()
      } catch (e) {
        setMessage(e instanceof Error ? e.message : 'Save failed')
      } finally {
        setSavingIds((prev) => {
          const next = new Set(prev)
          next.delete(studentId)
          return next
        })
      }
    },
    [assignmentId, scheduleAutoSave, workspaceScope],
  )
  saveStudentRef.current = saveStudent

  useEffect(() => {
    return () => {
      for (const timer of Object.values(saveTimers.current)) {
        clearTimeout(timer)
      }
    }
  }, [])

  const handleDraftChange = (studentId: number, patch: Partial<GradeRowDraft>) => {
    updateDraft(studentId, patch)
    scheduleAutoSave(studentId)
  }

  const toggleSelect = (studentId: number, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (checked) next.add(studentId)
      else next.delete(studentId)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === selectableRows.length) {
      setSelected(new Set())
      return
    }
    setSelected(new Set(selectableRows.map((r) => r.student.id)))
  }

  const applyBulk = (patch: Partial<GradeRowDraft>) => {
    if (!selected.size) return
    setDrafts((prev) => {
      const next = { ...prev }
      for (const id of selected) {
        const key = rowKey(id)
        const row = rowsRef.current.find((r) => r.student.id === id)
        if (!row) continue
        next[key] = { ...(next[key] || draftFromGradeRow(row)), ...patch }
        dirtyIdsRef.current.add(id)
        scheduleAutoSave(id)
      }
      draftsRef.current = next
      return next
    })
  }

  const saveAll = async () => {
    setMessage(null)
    // Flush any pending auto-save timers so we save the latest drafts once.
    for (const timer of Object.values(saveTimers.current)) {
      clearTimeout(timer)
    }
    saveTimers.current = {}

    const targets = selectableRows.filter((row) => {
      const draft = draftsRef.current[rowKey(row.student.id)]
      return draft && draft.score.trim() !== ''
    })
    if (!targets.length) {
      setMessage('Enter at least one score before saving.')
      return
    }
    for (const row of targets) {
      // Skip per-row reload; refresh once after the batch.
      await saveStudent(row.student.id, true, false)
    }
    setMessage(`Saved grades for ${targets.length} student(s)`)
    onSavedRef.current?.()
  }

  return (
    <div className="space-y-4">
      {message ? (
        <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          {message}
        </div>
      ) : null}

      {savingIds.size > 0 ? (
        <div className="text-xs font-semibold text-violet-700">
          <i className="bi bi-arrow-repeat me-1 animate-spin" />
          Saving…
        </div>
      ) : null}

      <GradeSpreadBar
        drafts={spreadDrafts}
        totalPoints={totalPoints}
        filter={spreadFilter}
        onFilterChange={setSpreadFilter}
      />

      <BulkGradingToolbar
        totalSelectable={selectableRows.length}
        selectedCount={selected.size}
        allSelected={selected.size > 0 && selected.size === selectableRows.length}
        onToggleSelectAll={toggleSelectAll}
        onMarkSubmitted={(type) => applyBulk({ submission_type: type })}
        onMarkNotes={(notes) =>
          applyBulk({
            submission_notes_type: notes,
            submission_notes: notes === 'Other' ? '' : '',
          })
        }
        onClearSelection={() => setSelected(new Set())}
      />

      <div className="flex justify-end print:hidden">
        <button
          type="button"
          onClick={() => void saveAll()}
          className="rounded-full bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800"
        >
          Save all grades
        </button>
      </div>

      <div className="space-y-4">
        {visibleRows.map((row) => {
          const studentId = row.student.id
          const key = rowKey(studentId)
          const draft = drafts[key] || draftFromGradeRow(row)
          const file = filesByStudent[studentId]
          return (
            <div key={key} className="space-y-2">
              {file ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100 text-red-700">
                        <i className="bi bi-file-earmark-pdf text-lg" />
                      </div>
                      <div>
                        <div className="font-semibold text-hub-text">{file.file_name}</div>
                        <div className="text-xs text-hub-muted">Student submission</div>
                      </div>
                    </div>
                    <a
                      href={file.download_url}
                      className="inline-flex items-center gap-2 rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                    >
                      <i className="bi bi-download" />
                      Download
                    </a>
                  </div>
                </div>
              ) : null}
              <PdfPaperGradeCard
                row={row}
                draft={draft}
                totalPoints={totalPoints}
                maxGradingPoints={maxGradingPoints}
                disabled={row.grade.is_voided}
                selected={selected.has(studentId)}
                onSelectChange={(checked) => toggleSelect(studentId, checked)}
                onChange={(patch) => handleDraftChange(studentId, patch)}
                gradeHistoryUrl={gradeHistoryUrl(row.grade.grade_id, workspaceScope)}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
