import { Link } from 'react-router-dom'

/** Placeholder until K–8 transcript consolidation ships. */
export default function ReportCardsTranscriptsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <span className="inline-flex rounded-full bg-slate-900 px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
          Under development
        </span>
        <h1 className="mt-4 text-2xl font-extrabold text-hub-text">K–8 student transcripts</h1>
        <p className="mt-3 text-sm text-hub-muted">
          Transcripts will consolidate each school year’s final grades from report cards for students
          in middle school and below who have been with Clara Science Academy. This workspace is not
          available yet.
        </p>
        <Link
          to="/management/report-cards"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-800"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          Back to report cards
        </Link>
      </div>
    </div>
  )
}
