import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { fetchGradeStandardsHub } from '../api/gradeStandards'
import type { GradeLevelRoute } from '../api/gradeStandards'
import type { GradeStandardsClassCard, GradeStandardsHubResponse } from '../types/gradeStandards'
import { spaRoute } from '../utils/spaRoute'

function percentTier(percent: number): string {
  if (percent === 0) return 'bg-slate-100 text-slate-500'
  if (percent < 25) return 'bg-red-100 text-red-800'
  if (percent < 60) return 'bg-amber-100 text-amber-900'
  if (percent < 100) return 'bg-sky-100 text-sky-900'
  return 'bg-emerald-100 text-emerald-900'
}

function quarterPipClass(percent: number): string {
  if (percent === 0) return 'border-slate-200 bg-slate-50 text-slate-500'
  if (percent < 25) return 'border-red-200 bg-red-50 text-red-800'
  if (percent < 60) return 'border-amber-200 bg-amber-50 text-amber-900'
  if (percent < 100) return 'border-sky-200 bg-sky-50 text-sky-900'
  return 'border-emerald-200 bg-emerald-50 text-emerald-900'
}

function ClassCard({
  classItem,
  quarterColumns,
  currentQuarter,
}: {
  classItem: GradeStandardsClassCard
  quarterColumns: string[]
  currentQuarter: string
}) {
  const overall = classItem.stats.overall
  return (
    <Link
      to={spaRoute(`${classItem.editor_path}?quarter=${currentQuarter}`)}
      className="block rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-violet-300 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-bold text-hub-text">{classItem.name}</p>
          <p className="mt-1 text-sm text-hub-muted">
            {classItem.subject} · {classItem.student_count} student{classItem.student_count === 1 ? '' : 's'}
          </p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${percentTier(overall.percent)}`}>
          {overall.percent}%
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {quarterColumns.map((quarter) => {
          const qStats = classItem.stats.quarters[quarter]
          return (
            <span
              key={quarter}
              className={`rounded-lg border px-2 py-1 text-[11px] font-semibold ${quarterPipClass(qStats?.percent ?? 0)}`}
              title={`${quarter} · ${qStats?.filled ?? 0}/${qStats?.total ?? 0}`}
            >
              {quarter} · {qStats?.percent ?? 0}%
            </span>
          )
        })}
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-hub-muted">
        <span>
          {overall.filled} / {overall.total} cells filled
        </span>
        <span className="font-semibold text-violet-700">
          Open <i className="bi bi-arrow-right-short" aria-hidden />
        </span>
      </div>
    </Link>
  )
}

function ClassGroup({
  title,
  icon,
  classes,
  quarterColumns,
  currentQuarter,
}: {
  title: string
  icon: string
  classes: GradeStandardsClassCard[]
  quarterColumns: string[]
  currentQuarter: string
}) {
  if (!classes.length) return null
  return (
    <section>
      <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-hub-muted">
        <i className={`bi ${icon} text-violet-700`} aria-hidden />
        {title}
      </h2>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {classes.map((classItem) => (
          <ClassCard
            key={classItem.id}
            classItem={classItem}
            quarterColumns={quarterColumns}
            currentQuarter={currentQuarter}
          />
        ))}
      </div>
    </section>
  )
}

export default function GradeStandardsHubPage() {
  const { grade = 'grade1' } = useParams<{ grade: GradeLevelRoute }>()
  const gradeRoute = grade === 'grade3' ? 'grade3' : 'grade1'

  const [data, setData] = useState<GradeStandardsHubResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchGradeStandardsHub(gradeRoute))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load standards checklist.')
    } finally {
      setLoading(false)
    }
  }, [gradeRoute])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
        Loading standards checklist…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
        {error || 'Could not load standards checklist.'}
      </div>
    )
  }

  const { summary, groups, quarter_columns: quarterColumns, current_quarter: currentQuarter } = data

  return (
    <div className="space-y-6">
      <header className="rounded-2xl border border-slate-200 bg-gradient-to-br from-violet-50 to-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-violet-700">Standards-based grading</p>
            <h1 className="mt-1 text-2xl font-bold text-hub-text">{data.title}</h1>
            <p className="mt-2 text-sm text-hub-muted">
              <i className="bi bi-check2-square mr-1 text-violet-700" aria-hidden />
              {data.school_year?.name ?? 'No active school year'} · Mark each student M / W / NA / UA per standard,
              per quarter
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to={spaRoute(data.urls.report_cards)}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
            >
              <i className="bi bi-arrow-left" aria-hidden />
              Report cards
            </Link>
          </div>
        </div>
      </header>

      {data.error ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{data.error}</div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-2xl font-bold text-hub-text">{summary.total_classes}</div>
          <div className="text-sm text-hub-muted">Classes</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-2xl font-bold text-hub-text">{summary.total_students}</div>
          <div className="text-sm text-hub-muted">Students</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-2xl font-bold text-hub-text">{summary.overall_percent}%</div>
          <div className="text-sm text-hub-muted">Year-to-date complete</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold text-hub-text">
            {summary.overall_filled} / {summary.overall_total}
          </div>
          <div className="text-sm text-hub-muted">Cells filled</div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wide text-hub-muted">Mark legend</h2>
        <dl className="mt-3 grid gap-2 sm:grid-cols-2">
          {data.legend.map((item) => (
            <div key={item.code} className="text-sm text-hub-muted">
              <dt className="inline font-bold text-hub-text">{item.code}</dt>
              <dd className="inline"> — {item.label}</dd>
            </div>
          ))}
        </dl>
      </div>

      {!groups.language_arts.length && !groups.math.length ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
          No eligible {gradeRoute === 'grade1' ? '1st' : '3rd'} grade Language Arts or Math classes found for the
          active school year.
        </div>
      ) : (
        <div className="space-y-8">
          <ClassGroup
            title="Language Arts"
            icon="bi-book"
            classes={groups.language_arts}
            quarterColumns={quarterColumns}
            currentQuarter={currentQuarter}
          />
          <ClassGroup
            title="Math"
            icon="bi-calculator"
            classes={groups.math}
            quarterColumns={quarterColumns}
            currentQuarter={currentQuarter}
          />
        </div>
      )}
    </div>
  )
}
