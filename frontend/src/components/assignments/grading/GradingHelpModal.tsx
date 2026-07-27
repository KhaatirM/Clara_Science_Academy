import { useState, type ReactNode } from 'react'

export const GRADING_HELP_DISMISS_KEY = 'clara:disableGradingHelpModal'

type Props = {
  open: boolean
  onClose: () => void
  allowExtraCredit?: boolean
  assignmentType?: string | null
}

function Section({
  icon,
  title,
  children,
}: {
  icon: string
  title: string
  children: ReactNode
}) {
  return (
    <div className="mb-4">
      <h3 className="mb-1.5 text-sm font-bold text-hub-text">
        <i className={`bi ${icon} me-2 text-violet-600`} />
        {title}
      </h3>
      <div className="text-sm leading-relaxed text-hub-muted">{children}</div>
    </div>
  )
}

export function GradingHelpModal({ open, onClose, allowExtraCredit, assignmentType }: Props) {
  const [dontShowAgain, setDontShowAgain] = useState(
    () => localStorage.getItem(GRADING_HELP_DISMISS_KEY) === '1',
  )

  if (!open) return null

  function handleClose() {
    localStorage.setItem(GRADING_HELP_DISMISS_KEY, dontShowAgain ? '1' : '0')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={handleClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between bg-violet-700 px-5 py-4 text-white">
          <h2 className="text-lg font-bold">
            <i className="bi bi-question-circle me-2" />
            Grading Fields Guide
          </h2>
          <button type="button" onClick={handleClose} className="text-white/80 hover:text-white">
            <i className="bi bi-x-lg" />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          <p className="mb-4 text-sm text-hub-muted">
            Use this guide to record grades correctly and avoid accidental zeros.
          </p>

          <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="flex gap-3">
              <i className="bi bi-exclamation-triangle-fill shrink-0 text-lg text-amber-500" />
              <div>
                <div className="font-semibold text-amber-950">Important</div>
                <p className="mt-1 text-sm text-amber-900">
                  Leaving points <strong>blank</strong> means &ldquo;not entered yet.&rdquo; Entering{' '}
                  <strong>0</strong> is a real grade (F). Students <strong>voided</strong> for this
                  assignment are excluded from the grade spread and will not be updated.
                </p>
              </div>
            </div>
          </div>

          <Section icon="bi-clipboard-check" title="Submission Status">
            <p className="mb-1">
              <strong>Not Submitted</strong> — Use when nothing was turned in yet.
            </p>
            <p className="mb-1">
              <strong>Submitted (Paper/In-Person)</strong> — Use when a student hands in paper or work
              is collected in class.
            </p>
            <p>
              <strong>Submitted (Online)</strong> — Use when the student submits digitally through
              the app.
            </p>
          </Section>

          <Section icon="bi-sticky" title="Submission Notes">
            Optional notes such as <strong>On-Time</strong>, <strong>Late</strong>, or{' '}
            <strong>Other</strong>. If late penalties are enabled for this assignment, choosing{' '}
            <strong>Late</strong> can apply the penalty. Use bulk actions above the student list to
            update many students at once.
          </Section>

          <Section icon="bi-star" title="Points Earned">
            Points the student earned out of the total.
            {allowExtraCredit ? (
              <>
                {' '}
                Extra credit is enabled — you can enter points above the base total (up to the
                assignment&apos;s extra credit limit).
              </>
            ) : null}{' '}
            Letter buttons set a percentage of total points; number presets set exact points. Use{' '}
            <strong>0</strong> only when you truly mean a zero.
          </Section>

          <Section icon="bi-lightning-charge" title="Save All">
            Changes are kept in the form until you click <strong>Save all</strong> at the top of the
            page. If save fails, check submission status and required fields for the affected
            students.
          </Section>

          {assignmentType === 'quiz' ? (
            <Section icon="bi-hourglass-split" title="Quiz grading (auto + manual)">
              Multiple choice / true-false questions are auto-graded on submission. Short answer /
              essay questions require manual grading on the Submissions page. Students may see{' '}
              <strong>Grade Pending</strong> until you finalize the score.
            </Section>
          ) : null}

          <Section icon="bi-chat-left-text" title="Feedback">
            Optional comment visible to the student. Add constructive feedback to help them improve
            (up to 500 characters).
          </Section>

          <Section icon="bi-check2-square" title="Bulk selection">
            Select individual students or use <strong>Select all</strong>, then mark many as
            submitted (online or in-person) or set submission notes (On-Time, Late, Other) in one
            step before saving.
          </Section>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-5 py-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-hub-muted">
            <input
              type="checkbox"
              checked={dontShowAgain}
              onChange={(e) => setDontShowAgain(e.target.checked)}
              className="rounded border-slate-300"
            />
            Don&apos;t show this automatically again
          </label>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-full bg-violet-700 px-6 py-2 text-sm font-semibold text-white hover:bg-violet-800"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  )
}
