import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchStudentClasses } from '../api/studentClasses'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { StudentClassCard, StudentClassesResponse } from '../types/studentClasses'

function averageTone(band: StudentClassCard['average_band']) {
  if (band === 'a') return 'from-emerald-500 to-teal-500'
  if (band === 'b') return 'from-sky-500 to-cyan-500'
  if (band === 'c') return 'from-amber-500 to-orange-500'
  if (band === 'd') return 'from-rose-500 to-red-500'
  return 'from-slate-400 to-slate-500'
}

function accentForIndex(i: number) {
  const accents = [
    'from-teal-700 via-teal-600 to-emerald-500',
    'from-cyan-700 via-teal-600 to-sky-500',
    'from-emerald-700 via-teal-600 to-cyan-500',
    'from-teal-800 via-emerald-700 to-teal-500',
  ]
  return accents[i % accents.length]
}

export function StudentClassesPage() {
  const [data, setData] = useState<StudentClassesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchStudentClasses())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load classes')
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
      const hay = `${c.name} ${c.subject} ${c.teacher_name} ${c.group_name || ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [data, query])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading classes…</div>
          ) : error && !data ? (
            <div className="alert alert-danger m-3">{error}</div>
          ) : data ? (
            <StudentClassesBody
              data={data}
              filtered={filtered}
              query={query}
              onQueryChange={setQuery}
            />
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function StudentClassesBody({
  data,
  filtered,
  query,
  onQueryChange,
}: {
  data: StudentClassesResponse
  filtered: StudentClassCard[]
  query: string
  onQueryChange: (value: string) => void
}) {
  return (
    <>
      <header className="mb-4 overflow-hidden rounded-3xl bg-gradient-to-br from-teal-800 via-teal-700 to-emerald-600 px-5 py-6 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-100">
              Student portal
            </p>
            <h1 className="text-2xl font-bold tracking-tight md:text-3xl">My classes</h1>
            <p className="mb-0 mt-1 text-sm text-teal-50/95">
              {data.school_year_name
                ? `${data.school_year_name} · Jump into materials and assignments`
                : 'Your enrolled courses and quick access to materials'}
            </p>
          </div>
          <div className="rounded-2xl bg-white/15 px-4 py-3 text-center ring-1 ring-white/25">
            <div className="text-3xl font-bold leading-none">{data.classes.length}</div>
            <div className="mt-1 text-[11px] font-bold uppercase tracking-wide text-teal-100">
              {data.classes.length === 1 ? 'Class' : 'Classes'}
            </div>
          </div>
        </div>
      </header>

      {!data.has_active_school_year ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          No active school year is set. Contact your school administrator.
        </div>
      ) : null}

      {data.assistant_classes.length ? (
        <section className="mb-4 overflow-hidden rounded-3xl border border-teal-200 bg-white shadow-sm">
          <div className="bg-gradient-to-r from-teal-50 to-emerald-50 px-5 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-700 text-white">
                  <i className="bi bi-person-badge text-xl" aria-hidden />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-teal-950">Student assistant</h2>
                  <p className="mb-0 text-sm text-hub-muted">
                    You can take attendance and enter grades for{' '}
                    <strong>{data.assistant_classes.length}</strong>{' '}
                    {data.assistant_classes.length === 1 ? 'class' : 'classes'}.
                  </p>
                </div>
              </div>
              <a
                href={data.assistant_console_url}
                className="rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
              >
                <i className="bi bi-grid-1x2 me-1" aria-hidden />
                Assistant console
              </a>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.assistant_classes.map((c) => (
                <a
                  key={c.id}
                  href={c.hub_url}
                  className="rounded-full border border-teal-300 bg-white px-3 py-1.5 text-xs font-semibold text-teal-800 hover:bg-teal-50"
                >
                  {c.name}
                </a>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="block text-sm">
          <span className="mb-1 block font-semibold text-hub-muted">Search classes</span>
          <div className="relative">
            <i className="bi bi-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden />
            <input
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Search by class, subject, teacher, or group…"
              className="w-full rounded-xl border border-slate-300 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
            />
          </div>
        </label>
      </div>

      {filtered.length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((card, index) => (
            <StudentClassCardView key={card.id} card={card} accent={accentForIndex(index)} />
          ))}
        </div>
      ) : (
        <div className="rounded-3xl border border-dashed border-teal-200 bg-teal-50/40 px-6 py-14 text-center">
          <i className="bi bi-journal-bookmark mb-3 block text-4xl text-teal-300" aria-hidden />
          <h3 className="text-lg font-bold text-hub-text">
            {data.classes.length ? 'No matching classes' : 'No classes enrolled'}
          </h3>
          <p className="mb-0 mt-1 text-sm text-hub-muted">
            {data.classes.length
              ? 'Try a different search.'
              : 'You are not currently enrolled in any classes. Contact your school administrator for help.'}
          </p>
        </div>
      )}

      {data.archived_classes.length ? (
        <section className="mt-6">
          <h2 className="mb-3 text-lg font-bold text-hub-text">
            Archived for this year
            {data.closure_phase_label ? (
              <span className="ms-2 text-sm font-semibold text-hub-muted">
                ({data.closure_phase_label})
              </span>
            ) : null}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.archived_classes.map((card, index) => (
              <StudentClassCardView
                key={`arch-${card.id}`}
                card={card}
                accent={accentForIndex(index)}
                muted
              />
            ))}
          </div>
        </section>
      ) : null}
    </>
  )
}

function StudentClassCardView({
  card,
  accent,
  muted = false,
}: {
  card: StudentClassCard
  accent: string
  muted?: boolean
}) {
  return (
    <article
      className={`flex h-full flex-col overflow-hidden rounded-3xl border bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
        muted ? 'border-slate-200 opacity-90' : 'border-teal-100'
      }`}
    >
      <div className={`relative bg-gradient-to-br ${accent} px-4 py-4 text-white`}>
        <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/10" aria-hidden />
        <div className="relative flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25">
            <i className="bi bi-book-fill text-xl" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-bold leading-tight">{card.name}</h3>
            <p className="mb-0 mt-1 text-xs font-semibold uppercase tracking-wide text-white/85">
              Grade {card.grade_levels_display}
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 px-4 py-4">
        <div className="space-y-1.5 text-sm text-hub-muted">
          <p className="mb-0">
            <i className="bi bi-tag me-2 text-teal-700" aria-hidden />
            {card.subject}
          </p>
          <p className="mb-0">
            <i className="bi bi-person me-2 text-teal-700" aria-hidden />
            {card.teacher_name}
          </p>
          {card.group_name ? (
            <p className="mb-0">
              <i className="bi bi-people-fill me-2 text-teal-700" aria-hidden />
              Your group: <strong className="text-hub-text">{card.group_name}</strong>
            </p>
          ) : null}
        </div>

        {card.average != null ? (
          <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2.5">
            <span className="text-xs font-bold uppercase tracking-wide text-hub-muted">
              Current average
            </span>
            <span
              className={`rounded-full bg-gradient-to-r ${averageTone(card.average_band)} px-2.5 py-1 text-sm font-bold text-white`}
            >
              {card.average.toFixed(1)}%
            </span>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 px-3 py-2.5 text-xs text-hub-muted">
            No graded work yet
          </div>
        )}

        <div className="mt-auto flex flex-wrap gap-2 pt-1">
          <Link
            to={`/student/classes/${card.id}`}
            className="inline-flex flex-1 items-center justify-center rounded-full bg-gradient-to-r from-teal-700 to-emerald-600 px-3 py-2 text-sm font-bold text-white hover:from-teal-800 hover:to-emerald-700"
          >
            <i className="bi bi-box-arrow-up-right me-1" aria-hidden />
            Open
          </Link>
          <Link
            to={{ pathname: '/student/assignments', search: `?class_id=${card.id}` }}
            className="inline-flex flex-1 items-center justify-center rounded-full border border-teal-300 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-900 hover:bg-teal-100"
          >
            <i className="bi bi-journal-text me-1" aria-hidden />
            Assignments
          </Link>
          {card.links.assistant ? (
            <a
              href={card.links.assistant}
              className="inline-flex w-full items-center justify-center rounded-full border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <i className="bi bi-person-badge me-1" aria-hidden />
              Assistant
            </a>
          ) : null}
        </div>
      </div>
    </article>
  )
}
