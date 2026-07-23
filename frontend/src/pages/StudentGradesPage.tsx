import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchStudentGrades } from '../api/studentGrades'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type {
  GradeBand,
  StudentGradeClass,
  StudentGradePeriod,
  StudentGradesResponse,
} from '../types/studentGrades'

function pctTone(band: GradeBand) {
  if (band === 'a') return 'text-emerald-700'
  if (band === 'b') return 'text-sky-700'
  if (band === 'c') return 'text-amber-700'
  if (band === 'd') return 'text-rose-700'
  return 'text-hub-muted'
}

function badgeTone(band: GradeBand) {
  if (band === 'a') return 'bg-emerald-100 text-emerald-800'
  if (band === 'b') return 'bg-sky-100 text-sky-800'
  if (band === 'c') return 'bg-amber-100 text-amber-900'
  if (band === 'd') return 'bg-rose-100 text-rose-800'
  return 'bg-slate-100 text-slate-600'
}

function barTone(band: GradeBand) {
  if (band === 'a') return 'bg-emerald-500'
  if (band === 'b') return 'bg-sky-500'
  if (band === 'c') return 'bg-amber-500'
  if (band === 'd') return 'bg-rose-500'
  return 'bg-slate-400'
}

function headerTone(band: GradeBand) {
  if (band === 'a') return 'from-emerald-700 via-teal-600 to-emerald-500'
  if (band === 'b') return 'from-teal-700 via-cyan-600 to-sky-500'
  if (band === 'c') return 'from-amber-600 via-orange-500 to-amber-400'
  if (band === 'd') return 'from-rose-600 via-red-500 to-rose-400'
  return 'from-slate-600 to-slate-500'
}

function standingTone(key: StudentGradesResponse['standing']['key']) {
  if (key === 'honor') return 'bg-emerald-400/95 text-emerald-950'
  if (key === 'good') return 'bg-white/95 text-teal-900'
  if (key === 'improve') return 'bg-amber-300/95 text-amber-950'
  return 'bg-rose-300/95 text-rose-950'
}

function spaPath(href: string) {
  return href.replace(/^\/app/, '') || '/'
}

export function StudentGradesPage() {
  const [data, setData] = useState<StudentGradesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchStudentGrades())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load grades')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const filtered = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    if (!q) return data.classes
    return data.classes.filter((c) => {
      const hay = `${c.name} ${c.subject} ${c.teacher_name}`.toLowerCase()
      return hay.includes(q)
    })
  }, [data, query])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading grades…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <StudentGradesBody
              data={data}
              filtered={filtered}
              query={query}
              onQueryChange={setQuery}
              expanded={expanded}
              onToggleExpanded={(id) =>
                setExpanded((prev) => ({ ...prev, [id]: !prev[id] }))
              }
            />
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function StudentGradesBody({
  data,
  filtered,
  query,
  onQueryChange,
  expanded,
  onToggleExpanded,
}: {
  data: StudentGradesResponse
  filtered: StudentGradeClass[]
  query: string
  onQueryChange: (value: string) => void
  expanded: Record<number, boolean>
  onToggleExpanded: (id: number) => void
}) {
  return (
    <>
      <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
              Student portal
            </p>
            <h1 className="text-2xl font-bold tracking-tight md:text-3xl">My grades</h1>
            <p className="mb-0 mt-1 text-sm text-teal-50/95">
              {data.school_year_name
                ? `${data.school_year_name} · academic performance`
                : 'Academic performance across your classes'}
            </p>
          </div>
          <div className="min-w-[12rem] rounded-2xl border border-white/20 bg-white/10 px-5 py-4 text-center backdrop-blur-sm">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-teal-100">
              Collective GPA
            </p>
            <p className="mb-2 text-4xl font-bold leading-none tracking-tight">{data.gpa.toFixed(2)}</p>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold ${standingTone(data.standing.key)}`}
            >
              <i className={`bi ${data.standing.icon}`} aria-hidden />
              {data.standing.label}
            </span>
          </div>
        </div>
        <div className="mt-5 flex flex-wrap gap-3 text-sm text-teal-50">
          <span className="rounded-full bg-white/15 px-3 py-1">
            <i className="bi bi-journal-bookmark me-1" aria-hidden />
            {data.graded_class_count} graded class{data.graded_class_count === 1 ? '' : 'es'}
          </span>
          <span className="rounded-full bg-white/15 px-3 py-1">
            <i className="bi bi-collection me-1" aria-hidden />
            {data.class_count} enrolled
          </span>
        </div>
      </header>

      {!data.has_active_school_year ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          No active school year is set up yet. Grades will appear once a school year is active.
        </div>
      ) : null}

      {(data.quarters.length > 0 || data.semesters.length > 0) && data.classes.length > 0 ? (
        <div className="mb-4 grid gap-4 lg:grid-cols-2">
          {data.quarters.length > 0 ? (
            <PeriodSummaryPanel
              title="Quarter performance"
              icon="bi-calendar-week"
              tone="from-cyan-700 to-teal-600"
              periods={data.quarters}
            />
          ) : null}
          {data.semesters.length > 0 ? (
            <PeriodSummaryPanel
              title="Semester performance"
              icon="bi-calendar-month"
              tone="from-emerald-700 to-teal-600"
              periods={data.semesters}
            />
          ) : null}
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="mb-0 text-lg font-bold text-hub-text">By class</h2>
          <p className="mb-0 text-sm text-hub-muted">
            {filtered.length} class{filtered.length === 1 ? '' : 'es'} with grades
          </p>
        </div>
        <label className="relative block w-full max-w-xs">
          <span className="sr-only">Search classes</span>
          <i
            className="bi bi-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-hub-muted"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Search classes…"
            className="w-full rounded-full border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm shadow-sm"
          />
        </label>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-5 py-10 text-center">
          <i className="bi bi-inbox mb-2 text-3xl text-hub-muted" aria-hidden />
          <p className="mb-1 font-semibold text-hub-text">
            {query.trim() ? 'No classes match your search' : 'No graded work yet'}
          </p>
          <p className="mb-0 text-sm text-hub-muted">
            {query.trim()
              ? 'Try a different class name or subject.'
              : 'Once teachers enter grades, your class averages and GPA will show here.'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((card) => (
            <ClassGradeCard
              key={card.id}
              card={card}
              open={Boolean(expanded[card.id])}
              onToggle={() => onToggleExpanded(card.id)}
            />
          ))}
        </div>
      )}
    </>
  )
}

function PeriodSummaryPanel({
  title,
  icon,
  tone,
  periods,
}: {
  title: string
  icon: string
  tone: string
  periods: StudentGradePeriod[]
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className={`bg-gradient-to-r ${tone} px-4 py-3 text-white`}>
        <h2 className="mb-0 text-sm font-bold uppercase tracking-wide">
          <i className={`bi ${icon} me-2`} aria-hidden />
          {title}
        </h2>
      </div>
      <div className="grid grid-cols-2 gap-3 p-4">
        {periods.map((p) => (
          <PeriodTile key={p.name} period={p} />
        ))}
      </div>
    </section>
  )
}

function PeriodTile({ period }: { period: StudentGradePeriod }) {
  if (period.status === 'in_progress') {
    return (
      <div className="rounded-xl border border-sky-100 bg-sky-50/80 px-3 py-3 text-center">
        <p className="mb-1 text-xs font-bold uppercase tracking-wide text-hub-muted">{period.name}</p>
        <p className="mb-0 text-sm font-bold text-sky-800">
          <i className="bi bi-clock me-1" aria-hidden />
          In progress
        </p>
        {period.end_display ? (
          <p className="mb-0 mt-1 text-[11px] text-hub-muted">Ends {period.end_display} · 4:00 PM ET</p>
        ) : null}
      </div>
    )
  }
  if (period.status === 'calculating') {
    return (
      <div className="rounded-xl border border-amber-100 bg-amber-50/80 px-3 py-3 text-center">
        <p className="mb-1 text-xs font-bold uppercase tracking-wide text-hub-muted">{period.name}</p>
        <p className="mb-0 text-sm font-bold text-amber-900">
          <i className="bi bi-hourglass-split me-1" aria-hidden />
          Calculating
        </p>
        <p className="mb-0 mt-1 text-[11px] text-hub-muted">Official GPA within 7 days after period end</p>
      </div>
    )
  }
  if (period.average == null) {
    return (
      <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3 text-center">
        <p className="mb-1 text-xs font-bold uppercase tracking-wide text-hub-muted">{period.name}</p>
        <p className="mb-0 text-lg font-bold text-hub-muted">N/A</p>
        <p className="mb-0 text-[11px] text-hub-muted">No grades</p>
      </div>
    )
  }
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3 text-center">
      <p className="mb-1 text-xs font-bold uppercase tracking-wide text-hub-muted">{period.name}</p>
      <p className={`mb-0 text-xl font-bold ${pctTone(period.band)}`}>{period.average.toFixed(1)}%</p>
      {period.gpa != null ? (
        <p className="mb-0 text-[11px] text-hub-muted">GPA {period.gpa.toFixed(2)}</p>
      ) : null}
      <p className="mb-0 text-[11px] text-hub-muted">
        {period.assignments} class{period.assignments === 1 ? '' : 'es'}
      </p>
    </div>
  )
}

function ClassGradeCard({
  card,
  open,
  onToggle,
}: {
  card: StudentGradeClass
  open: boolean
  onToggle: () => void
}) {
  const band = card.final_grade.band
  return (
    <article className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className={`bg-gradient-to-r ${headerTone(band)} px-4 py-3 text-white`}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="mb-0 truncate text-base font-bold">{card.name}</h3>
            <p className="mb-0 truncate text-xs text-white/85">
              {card.subject} · {card.teacher_name}
            </p>
          </div>
          <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-sm font-bold text-slate-900">
            {card.final_grade.letter}
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="rounded-xl border border-slate-100 bg-slate-50 px-2 py-2.5">
            <p className="mb-0 text-lg font-bold text-teal-800">{card.class_gpa.toFixed(2)}</p>
            <p className="mb-0 text-[10px] font-bold uppercase tracking-wide text-hub-muted">Class GPA</p>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50 px-2 py-2.5">
            <p className={`mb-0 text-lg font-bold ${pctTone(band)}`}>
              {card.final_grade.percentage.toFixed(1)}%
            </p>
            <p className="mb-0 text-[10px] font-bold uppercase tracking-wide text-hub-muted">Overall</p>
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between text-[11px] text-hub-muted">
            <span>Class progress</span>
            <span>{card.final_grade.percentage.toFixed(1)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full ${barTone(band)}`}
              style={{ width: `${Math.min(100, Math.max(0, card.final_grade.percentage))}%` }}
            />
          </div>
        </div>

        {card.quarter_grades.length > 0 ? (
          <MiniPeriodGrid title="Quarters" periods={card.quarter_grades} />
        ) : null}
        {card.semester_grades.length > 0 ? (
          <MiniPeriodGrid title="Semesters" periods={card.semester_grades} />
        ) : null}

        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-hub-muted">
            <i className="bi bi-clock-history me-1" aria-hidden />
            Recent
          </p>
          {card.recent_assignments.length ? (
            <ul className="mb-0 space-y-2">
              {card.recent_assignments.map((a) => (
                <li
                  key={`${a.title}-${a.graded_display}`}
                  className="flex items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50 px-2.5 py-2"
                >
                  <div className="min-w-0">
                    <p className="mb-0 truncate text-sm font-semibold text-hub-text">{a.title}</p>
                    {a.graded_display ? (
                      <p className="mb-0 text-[11px] text-hub-muted">{a.graded_display}</p>
                    ) : null}
                  </div>
                  <div className="shrink-0 text-right">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${badgeTone(a.band)}`}>
                      {a.score}%
                    </span>
                    <p className="mb-0 mt-0.5 text-[10px] text-hub-muted">{a.letter}</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mb-0 text-sm text-hub-muted">No recent graded work</p>
          )}
        </div>

        <div className="mt-auto flex flex-wrap gap-2 pt-1">
          <Link
            to={spaPath(card.links.open_class)}
            className="inline-flex flex-1 items-center justify-center rounded-full bg-gradient-to-r from-teal-700 to-emerald-600 px-3 py-2 text-sm font-bold text-white hover:from-teal-800 hover:to-emerald-700"
          >
            Open class
          </Link>
          <Link
            to={spaPath(card.links.assignments)}
            className="inline-flex flex-1 items-center justify-center rounded-full border border-teal-300 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-900 hover:bg-teal-100"
          >
            Assignments
          </Link>
        </div>
      </div>

      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-center gap-1 border-t border-slate-100 bg-slate-50 px-3 py-2.5 text-sm font-semibold text-teal-900 hover:bg-teal-50"
        aria-expanded={open}
      >
        <i className={`bi bi-chevron-${open ? 'up' : 'down'}`} aria-hidden />
        {open ? 'Hide all grades' : `View all grades (${card.assignment_details.length})`}
      </button>

      {open ? (
        <div className="border-t border-slate-100 px-4 py-3">
          {card.assignment_details.length ? (
            <ul className="mb-0 max-h-64 space-y-2 overflow-y-auto">
              {card.assignment_details.map((row) => (
                <li
                  key={`${row.title}-${row.display}`}
                  className="flex items-center justify-between gap-2 text-sm"
                >
                  <span className="min-w-0 truncate font-medium text-hub-text" title={row.title}>
                    {row.title}
                    {row.is_group ? (
                      <span className="ms-1 text-[10px] font-bold uppercase text-hub-muted">Group</span>
                    ) : null}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span className="font-bold text-hub-text">{row.display}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${badgeTone(row.band)}`}>
                      {row.letter}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mb-0 text-sm text-hub-muted">No assignment grades</p>
          )}
        </div>
      ) : null}
    </article>
  )
}

function MiniPeriodGrid({ title, periods }: { title: string; periods: StudentGradePeriod[] }) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-hub-muted">{title}</p>
      <div className="grid grid-cols-2 gap-1.5">
        {periods.map((p) => (
          <div
            key={`${title}-${p.name}`}
            className="rounded-lg border border-slate-100 bg-white px-2 py-1.5 text-center"
          >
            <p className="mb-0 text-[10px] font-bold uppercase text-hub-muted">{p.name}</p>
            {p.status === 'in_progress' ? (
              <p className="mb-0 text-[11px] font-semibold text-sky-700">In progress</p>
            ) : p.status === 'calculating' ? (
              <p className="mb-0 text-[11px] font-semibold text-amber-800">Calculating</p>
            ) : p.average != null ? (
              <p className={`mb-0 text-xs font-bold ${pctTone(p.band)}`}>{p.average}%</p>
            ) : (
              <p className="mb-0 text-[11px] text-hub-muted">—</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
