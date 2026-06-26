import { Link } from 'react-router-dom'

import type { ReportCardStandardsChecklist, ReportCardStandardsLegendItem } from '../../types/reportCards'
import { spaRoute } from '../../utils/spaRoute'

export function StandardsChecklistCallout({
  checklist,
  marksSummary,
}: {
  checklist: ReportCardStandardsChecklist | null | undefined
  marksSummary?: {
    language_arts: { marked: number; total: number }
    math: { marked: number; total: number }
  } | null
}) {
  if (!checklist) return null

  return (
    <div className="rounded-2xl border border-sky-200 bg-gradient-to-br from-sky-50 to-white p-5 shadow-sm">
      <h3 className="flex items-center gap-2 text-base font-bold text-hub-text">
        <i className="bi bi-check2-square text-sky-700" aria-hidden />
        {checklist.title}
      </h3>
      <p className="mt-2 text-sm text-hub-muted">{checklist.description}</p>

      {checklist.pdf_pages?.length ? (
        <p className="mt-3 text-xs text-hub-muted">
          <span className="font-semibold text-hub-text">PDF layout:</span>{' '}
          {checklist.pdf_pages.join(' · ')}
        </p>
      ) : null}

      {marksSummary ? (
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-white px-3 py-1 font-semibold text-hub-text ring-1 ring-sky-200">
            Language Arts: {marksSummary.language_arts.marked}/{marksSummary.language_arts.total} standards marked
          </span>
          <span className="rounded-full bg-white px-3 py-1 font-semibold text-hub-text ring-1 ring-sky-200">
            Math: {marksSummary.math.marked}/{marksSummary.math.total} standards marked
          </span>
        </div>
      ) : null}

      {checklist.legend?.length ? (
        <dl className="mt-4 grid gap-2 sm:grid-cols-2">
          {checklist.legend.map((item: ReportCardStandardsLegendItem) => (
            <div key={item.code} className="text-xs text-hub-muted">
              <dt className="inline font-bold text-hub-text">{item.code}</dt>
              <dd className="inline"> — {item.label}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {checklist.editor_url ? (
        checklist.editor_url.startsWith('/management/') ? (
          <Link
            to={spaRoute(checklist.editor_url)}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800"
          >
            <i className="bi bi-pencil-square" aria-hidden />
            Open standards checklist editor
          </Link>
        ) : (
          <a
            href={checklist.editor_url}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800"
          >
            <i className="bi bi-pencil-square" aria-hidden />
            Open standards checklist editor
          </a>
        )
      ) : null}
    </div>
  )
}
