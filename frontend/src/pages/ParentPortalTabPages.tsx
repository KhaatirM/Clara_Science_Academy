import { useCallback, useEffect, useState } from 'react'
import {
  fetchParentAttendance,
  fetchParentClasses,
  fetchParentGrades,
  fetchParentReportCards,
  selectParentChild,
} from '../api/parentPortal'
import { ParentEmptyChildren, ParentPageShell } from '../components/parent/ParentPageShell'
import type { ParentTabResponse } from '../types/parentPortal'

type TabKey = 'grades' | 'attendance' | 'classes' | 'report-cards'

async function loadTab(tab: TabKey) {
  if (tab === 'grades') return fetchParentGrades()
  if (tab === 'attendance') return fetchParentAttendance()
  if (tab === 'classes') return fetchParentClasses()
  return fetchParentReportCards()
}

function useParentTab(tab: TabKey) {
  const [data, setData] = useState<ParentTabResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await loadTab(tab))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load page')
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => {
    void load()
  }, [load])

  async function onSelectChild(studentId: number) {
    setBusy(true)
    setError(null)
    try {
      await selectParentChild(studentId)
      setData(await loadTab(tab))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not switch child')
    } finally {
      setBusy(false)
    }
  }

  return { data, loading, busy, error, onSelectChild }
}

export function ParentGradesPage() {
  const { data, loading, busy, error, onSelectChild } = useParentTab('grades')
  const summary = data?.summary
  const child = data?.active_child

  return (
    <ParentPageShell
      title="Grades"
      subtitle={child ? `Class averages for ${child.display_name}` : undefined}
      childrenList={data?.children || []}
      activeChildId={data?.active_child_id ?? null}
      onSelectChild={onSelectChild}
      childBusy={busy}
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}
      {data && !data.children.length ? <ParentEmptyChildren /> : null}
      {summary ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-teal-200 bg-teal-50 px-5 py-4">
            <p className="mb-0 text-xs font-semibold uppercase tracking-wide text-teal-800">Overall GPA</p>
            <p className="mb-0 text-3xl font-extrabold text-teal-950">{summary.gpa.toFixed(2)}</p>
          </div>
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-5 py-3">
              <h2 className="mb-0 text-base font-bold text-hub-text">By class</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs font-bold uppercase tracking-wide text-hub-muted">
                    <th className="px-5 py-3">Class</th>
                    <th className="px-5 py-3">Teacher</th>
                    <th className="px-5 py-3">Average</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.classes.map((c) => (
                    <tr key={c.id} className="border-b border-slate-50">
                      <td className="px-5 py-3 font-semibold text-hub-text">{c.name}</td>
                      <td className="px-5 py-3 text-hub-muted">{c.teacher_name}</td>
                      <td className="px-5 py-3 font-bold text-teal-800">
                        {c.average != null ? `${c.average}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!summary.classes.length ? (
                <p className="px-5 py-8 text-sm text-hub-muted">No graded classes yet.</p>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}
    </ParentPageShell>
  )
}

export function ParentAttendancePage() {
  const { data, loading, busy, error, onSelectChild } = useParentTab('attendance')
  const summary = data?.summary
  const child = data?.active_child
  const att = summary?.attendance_summary

  return (
    <ParentPageShell
      title="Attendance"
      subtitle={child ? `Attendance for ${child.display_name}` : undefined}
      childrenList={data?.children || []}
      activeChildId={data?.active_child_id ?? null}
      onSelectChild={onSelectChild}
      childBusy={busy}
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}
      {data && !data.children.length ? <ParentEmptyChildren /> : null}
      {summary && att ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-teal-200 bg-teal-50 px-5 py-4">
            <p className="mb-0 text-xs font-semibold uppercase tracking-wide text-teal-800">
              Attendance rate
            </p>
            <p className="mb-0 text-3xl font-extrabold text-teal-950">
              {summary.attendance_rate != null ? `${summary.attendance_rate}%` : '—'}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {(
              [
                ['Present', att.Present, 'bi-check-circle text-emerald-700'],
                ['Tardy', att.Tardy, 'bi-clock-history text-amber-700'],
                ['Absent', att.Absent, 'bi-x-circle text-rose-700'],
              ] as const
            ).map(([label, value, icon]) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <i className={`bi ${icon} mb-2 block text-xl`} aria-hidden />
                <div className="text-2xl font-extrabold text-hub-text">{value}</div>
                <div className="text-xs font-semibold uppercase tracking-wide text-hub-muted">{label}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </ParentPageShell>
  )
}

export function ParentClassesPage() {
  const { data, loading, busy, error, onSelectChild } = useParentTab('classes')
  const summary = data?.summary
  const child = data?.active_child

  return (
    <ParentPageShell
      title="Classes"
      subtitle={child ? `Enrolled classes for ${child.display_name}` : undefined}
      childrenList={data?.children || []}
      activeChildId={data?.active_child_id ?? null}
      onSelectChild={onSelectChild}
      childBusy={busy}
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}
      {data && !data.children.length ? <ParentEmptyChildren /> : null}
      {summary ? (
        <div className="grid gap-3 md:grid-cols-2">
          {summary.classes.map((c) => (
            <article
              key={c.id}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              <div className="border-b border-teal-100 bg-gradient-to-r from-teal-50 to-white px-4 py-3">
                <h2 className="mb-0 text-base font-bold text-hub-text">{c.name}</h2>
                <p className="mb-0 text-sm text-hub-muted">{c.subject || 'Class'}</p>
              </div>
              <div className="space-y-2 p-4 text-sm">
                <p className="mb-0">
                  <span className="text-hub-muted">Teacher:</span>{' '}
                  <strong className="text-hub-text">{c.teacher_name}</strong>
                </p>
                <p className="mb-0">
                  <span className="text-hub-muted">Room:</span> {c.room || 'N/A'}
                </p>
                <p className="mb-0">
                  <span className="text-hub-muted">Schedule:</span> {c.schedule || 'TBD'}
                </p>
                <p className="mb-0">
                  <span className="text-hub-muted">Average:</span>{' '}
                  <strong className="text-teal-800">
                    {c.average != null ? `${c.average}%` : '—'}
                  </strong>
                </p>
              </div>
            </article>
          ))}
          {!summary.classes.length ? (
            <p className="text-sm text-hub-muted">No active class enrollments.</p>
          ) : null}
        </div>
      ) : null}
    </ParentPageShell>
  )
}

export function ParentReportCardsPage() {
  const { data, loading, busy, error, onSelectChild } = useParentTab('report-cards')
  const child = data?.active_child
  const cards = data?.report_cards || []

  return (
    <ParentPageShell
      title="Report cards"
      subtitle={
        child
          ? `Director-approved report cards for ${child.display_name}`
          : 'Official report cards released by the school'
      }
      childrenList={data?.children || []}
      activeChildId={data?.active_child_id ?? null}
      onSelectChild={onSelectChild}
      childBusy={busy}
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}
      {data && !data.children.length ? <ParentEmptyChildren /> : null}
      {data && data.children.length ? (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          {cards.length ? (
            <ul className="mb-0 divide-y divide-slate-100">
              {cards.map((card) => (
                <li key={card.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                  <div>
                    <p className="mb-0 text-sm font-bold text-hub-text">
                      Quarter {card.quarter ?? '—'}
                    </p>
                    <p className="mb-0 text-xs text-hub-muted">
                      Generated {card.generated_at_display || '—'}
                    </p>
                  </div>
                  <a
                    href={card.download_url}
                    className="inline-flex items-center gap-1.5 rounded-full bg-teal-700 px-3.5 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                  >
                    <i className="bi bi-download" aria-hidden />
                    Download PDF
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-5 py-12 text-center">
              <i className="bi bi-file-earmark-pdf mb-3 block text-3xl text-slate-300" aria-hidden />
              <p className="mb-1 font-semibold text-hub-text">No report cards available yet</p>
              <p className="mb-0 text-sm text-hub-muted">
                Official cards appear here after the Director releases them.
              </p>
            </div>
          )}
        </section>
      ) : null}
    </ParentPageShell>
  )
}
