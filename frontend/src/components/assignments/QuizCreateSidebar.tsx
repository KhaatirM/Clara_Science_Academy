import { Link } from 'react-router-dom'
import type { QuizBlock } from './QuizAuthoringBlocksEditor'

const QUESTION_TYPES = [
  {
    icon: 'bi-list-ul',
    iconClass: 'text-blue-600',
    title: 'Multiple Choice',
    description: 'One correct answer from multiple options',
  },
  {
    icon: 'bi-check2-square',
    iconClass: 'text-emerald-600',
    title: 'True/False',
    description: 'Simple true or false questions',
  },
  {
    icon: 'bi-chat-text',
    iconClass: 'text-amber-500',
    title: 'Short Answer',
    description: 'Brief text responses',
  },
  {
    icon: 'bi-file-text',
    iconClass: 'text-rose-600',
    title: 'Essay',
    description: 'Longer, detailed responses',
  },
] as const

export function quizBlockStats(blocks: QuizBlock[]) {
  const questions = blocks.filter((b) => b.kind === 'question')
  const totalPoints = questions.reduce((sum, b) => {
    if (b.kind !== 'question') return sum
    return sum + (Number.parseFloat(b.question.points) || 0)
  }, 0)
  return {
    questionCount: questions.length,
    totalPoints: Math.round(totalPoints * 10) / 10,
  }
}

export function QuizCreateSidebar({
  blocks,
  googleFormLinked = false,
  submitting = false,
  saveAction,
  formError,
  backTo,
  onPublish,
  onSaveDraft,
}: {
  blocks: QuizBlock[]
  googleFormLinked?: boolean
  submitting?: boolean
  saveAction?: 'publish' | 'draft'
  formError?: string | null
  backTo: string
  onPublish: () => void
  onSaveDraft: () => void
}) {
  const stats = quizBlockStats(blocks)

  return (
    <aside className="space-y-4 self-start lg:sticky lg:top-4 lg:z-10">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="bg-gradient-to-r from-slate-600 to-slate-700 px-4 py-3 text-white">
          <h3 className="m-0 text-sm font-bold">
            <i className="bi bi-lightbulb me-2" aria-hidden />
            Question Types Guide
          </h3>
        </header>
        <div className="space-y-3 p-4">
          {QUESTION_TYPES.map((type) => (
            <div key={type.title} className="flex items-start gap-2.5">
              <i className={`bi ${type.icon} mt-0.5 text-lg ${type.iconClass}`} aria-hidden />
              <div>
                <div className="text-sm font-bold text-hub-text">{type.title}</div>
                <p className="m-0 text-xs text-hub-muted">{type.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="bg-gradient-to-r from-slate-800 to-slate-900 px-4 py-3 text-white">
          <h3 className="m-0 text-sm font-bold">
            <i className="bi bi-graph-up me-2" aria-hidden />
            Quiz Stats
          </h3>
        </header>
        <div className="grid grid-cols-2 divide-x divide-slate-200 p-4 text-center">
          <div className="px-2">
            <div className="text-2xl font-extrabold text-blue-600">
              {googleFormLinked ? '—' : stats.questionCount}
            </div>
            <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
              Questions
            </div>
          </div>
          <div className="px-2">
            <div className="text-2xl font-extrabold text-emerald-600">
              {googleFormLinked ? '—' : stats.totalPoints}
            </div>
            <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">
              Total Points
            </div>
          </div>
        </div>
        {googleFormLinked ? (
          <p className="border-t border-slate-100 px-4 py-3 text-xs text-hub-muted">
            Native question stats are hidden while a Google Form is linked.
          </p>
        ) : null}
      </section>

      <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
        {formError ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{formError}</p>
        ) : null}
        <button
          type="button"
          disabled={submitting}
          onClick={onPublish}
          className="w-full rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-3 text-sm font-bold text-white shadow-md transition hover:from-emerald-600 hover:to-teal-700 disabled:opacity-60"
        >
          {submitting && saveAction === 'publish' ? 'Publishing…' : 'Publish quiz'}
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={onSaveDraft}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-60"
        >
          {submitting && saveAction === 'draft' ? 'Saving…' : 'Save draft'}
        </button>
        <Link
          to={backTo}
          className="block w-full rounded-xl px-4 py-2.5 text-center text-sm font-semibold text-slate-500 transition hover:bg-slate-50 hover:text-slate-700"
        >
          Cancel
        </Link>
      </section>
    </aside>
  )
}
