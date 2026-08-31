import { useEffect, useState } from 'react'
import type { AppVersionInfo } from '../../types/session'

const SESSION_KEY = 'spaUpdateModalShownAug31_2026_v2'

const LATEST_UPDATES: Array<{ title: string; body: string }> = [
  {
    title: 'Assign duties to a cleaning team',
    body: 'Each team now has an editable list of duties — a name, the area it covers, and what has to be done. Open a team and use Duties to add, edit, or remove them, then pick a duty for each student from the Members panel. The duties that used to be hardcoded per team were carried over automatically, and students see their own duty highlighted on the Jobs page.',
  },
  {
    title: 'Stairway and Lunch Hall added to the cleaning detail',
    body: 'Both areas now appear on every cleaning team. Stairway is part of the normal inspection, with a new "Stairway not swept or cleaned" deduction worth 10 points.',
  },
  {
    title: 'Lunch Hall is scored on its own',
    body: 'Lunch Hall has a separate checklist worth 20 points per item: tables wiped and cleared, no trash on the floor, no dishes left out, food and condiments put up, and trash taken out. Use the Lunch Hall button on a team to run it, and inspection history labels which checklist was used.',
  },
  {
    title: 'Student Jobs has been rebuilt',
    body: 'New layout with team performance at a glance: score, trend, average, pass rate, and a mini chart of recent inspections. Teams and inspections are now separate tabs with search and filters, the inspection form shows plain-English items with their point values and a live score, and every browser alert/confirm popup has been replaced with proper in-app dialogs. The student view was rebuilt to match and puts your own team first.',
  },
  {
    title: 'School Administrators can post announcements again',
    body: 'An "Unauthorized" message appeared above the title box when a School Administrator opened the announcement composer. Announcement permission checks now recognise every way the role is stored, including when it is a secondary role.',
  },
  {
    title: 'Teachers can see their class mailing list',
    body: 'The class page now shows the Google Group address for the class with a copy button, so you can email the whole class from your own mail app.',
  },
  {
    title: 'Mark what a period is used for',
    body: 'In the schedule editor you can now label a class period, for example Period 7 as "Electives". Labelled periods show that label on student, teacher, and printed schedules instead of a blank slot, and no longer accept classes.',
  },
  {
    title: 'Students move to the right Google Group when their grade changes',
    body: 'Promoting a student updated the portal and their Workspace org unit but left them in their old school-level group. Grade changes now move students between the elementary, middle school, and high school groups automatically.',
  },
  {
    title: 'Clearer Google Classroom roster problems',
    body: 'Students enrolled without a school email were silently left off the Classroom roster. Those students are now named in the logs and in the roster repair tool, and failures to add a student are reported instead of ignored.',
  },
  {
    title: 'Art and Music are now one Art/Music class',
    body: 'Every grade had a separate Art class and Music class. They are now a single "Art/Music" class per grade, matching the report card. Existing rosters, assignments, grades, and attendance were merged into the combined class, and core class setup creates just the one going forward.',
  },
  {
    title: 'Graded redos no longer stay "Pending"',
    body: 'Grading a redo through the speed grader never closed out the redo record, so the dashboard kept showing Pending with no final grade. Grading now records the redo score and final grade, keeping the higher of the original and the redo. Redos you already graded show their grade again automatically.',
  },
  {
    title: 'Archive or delete inspections',
    body: 'Student Jobs inspections can now be archived (removed from history and no longer counted toward the team score) or permanently deleted.',
  },
  {
    title: 'Inspection details open in a real popup',
    body: 'Viewing an inspection used a plain browser alert box. It now opens an in-app panel listing the score, every deduction and bonus, and the inspector notes.',
  },
  {
    title: 'Grade colors now match the grade',
    body: 'Score cards, letter badges, and the assignment view popup were always green regardless of the grade. They now follow the score: A green, B blue, C amber, D orange, F red.',
  },
  {
    title: 'Link a Google Drive folder to Class Notes',
    body: 'Teachers can paste a shared Drive folder link on a class Notes page. Its subfolders and files appear in Class Notes automatically, and anything you drop in Drive shows up after the next sync.',
  },
  {
    title: 'Students download Drive files without Drive access',
    body: 'Mirrored files stream through the portal using the same class permission checks, so students never need to be shared on the folder. Google Docs and Slides download as PDF; Sheets as Excel.',
  },
  {
    title: 'Sync now, Unlink, and reconnect prompts',
    body: 'The Drive panel shows the last sync time with Sync now and Unlink buttons. If Google access expires, a banner links straight to reconnecting your account.',
  },
  {
    title: 'Simpler weekly bell periods',
    body: 'Bell schedules now use one set of periods for the whole week. When you assign a class, pick Mon–Fri on the assignment card instead of duplicating periods per day pattern.',
  },
  {
    title: 'Drag classes into bell periods',
    body: 'Management Schedule → Assign classes: drag grade classes into periods; meeting times update automatically. Students see them on their schedule grid.',
  },
  {
    title: 'Schedule by grade + editor layout',
    body: 'Management Schedule lets you pick which grade a bell schedule is for. Period color pickers no longer stretch off-screen.',
  },
  {
    title: 'Bell schedule grids & PDF downloads',
    body: 'Student and teacher Schedule tabs show a color Mon–Fri period grid. Download a PDF of your personal schedule. Classes fill periods by matching meeting times.',
  },
  {
    title: 'Management Schedule tab',
    body: 'School admins can edit school-wide or per-grade bell schedules (periods, days, times, colors) and download master schedule PDFs by grade level.',
  },
  {
    title: 'Student assistant console restored',
    body: 'Student assistants can open the class assistant workspace again (attendance, grading, and assignment proposals). Templates removed during the SPA cutover are back.',
  },
]

export function PortalUpdatesHost({ version }: { version?: AppVersionInfo | null }) {
  const [open, setOpen] = useState(false)
  const [versionOpen, setVersionOpen] = useState(false)

  const display = version?.display || 'v 2.519.0'
  const releaseLabel = version?.release_label || 'August 28, 2026'
  const origin = version?.origin || '0.0.0'
  const updatesEstimate = version?.updates_estimate ?? 2719
  const productName = version?.product_name || 'Clara Science Academy Portal'

  useEffect(() => {
    if (sessionStorage.getItem(SESSION_KEY)) return
    const timer = window.setTimeout(() => {
      setOpen(true)
      sessionStorage.setItem(SESSION_KEY, 'true')
    }, 600)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <>
      <button
        type="button"
        className="spa-version-badge fixed bottom-4 right-4 z-[1080] inline-flex items-center gap-2 rounded-full border border-teal-700/20 bg-teal-800 px-3.5 py-2 text-sm font-semibold text-white shadow-lg shadow-teal-900/25 transition hover:bg-teal-700"
        aria-label={`Portal version ${display}`}
        onClick={() => setVersionOpen(true)}
      >
        <i className="bi bi-layers-fill" aria-hidden />
        <span>{display}</span>
      </button>

      {versionOpen ? (
        <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-slate-900/45 p-4" role="presentation">
          <div
            className="w-full max-w-sm overflow-hidden rounded-2xl bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="spa-version-title"
          >
            <div className="bg-gradient-to-br from-teal-800 to-teal-600 px-5 py-4 text-white">
              <p className="mb-1 text-[0.7rem] font-bold uppercase tracking-[0.16em] text-teal-100">Release info</p>
              <h2 id="spa-version-title" className="text-lg font-extrabold">
                {productName}
              </h2>
            </div>
            <div className="space-y-3 px-5 py-4 text-sm text-slate-700">
              <div className="inline-flex rounded-full bg-teal-50 px-3 py-1 text-sm font-bold text-teal-900">
                {display}
              </div>
              <p className="mb-0">
                <span className="text-hub-muted">Started at</span> <strong>v {origin}</strong>
              </p>
              <p className="mb-0">
                <span className="text-hub-muted">Improvements</span>{' '}
                <strong>{updatesEstimate.toLocaleString()}+</strong> updates shipped
              </p>
              <p className="mb-0">
                <span className="text-hub-muted">Release window</span> <strong>{releaseLabel}</strong>
              </p>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">
              <button
                type="button"
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => setVersionOpen(false)}
              >
                Close
              </button>
              <button
                type="button"
                className="rounded-xl bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                onClick={() => {
                  setVersionOpen(false)
                  setOpen(true)
                }}
              >
                <i className="bi bi-megaphone me-1" aria-hidden />
                Latest changes
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {open ? (
        <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-slate-900/45 p-4" role="presentation">
          <div
            className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="spa-updates-title"
          >
            <div className="flex items-start justify-between gap-3 bg-gradient-to-br from-teal-800 to-teal-600 px-5 py-4 text-white">
              <div>
                <h2 id="spa-updates-title" className="text-lg font-extrabold">
                  System Updates
                </h2>
                <p className="mb-0 text-sm text-teal-100">
                  Latest improvements · {releaseLabel} · {display}
                </p>
              </div>
              <button
                type="button"
                className="rounded-lg p-1.5 text-white/80 hover:bg-white/10 hover:text-white"
                aria-label="Close"
                onClick={() => setOpen(false)}
              >
                <i className="bi bi-x-lg" aria-hidden />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
              <div className="rounded-2xl border border-teal-100 bg-teal-50/70 p-4">
                <h3 className="mb-2 text-sm font-bold text-teal-950">
                  Redos, Inspections &amp; Grade Colors – {releaseLabel}
                </h3>
                <p className="mb-0 text-sm text-teal-900/90">
                  Graded redos close out properly instead of sitting at Pending, inspections can be
                  archived or deleted, and grade colors follow the actual score.
                </p>
              </div>
              <ul className="m-0 list-none space-y-3 p-0">
                {LATEST_UPDATES.map((item) => (
                  <li key={item.title} className="rounded-xl border border-slate-200 bg-slate-50/80 px-3.5 py-3">
                    <p className="mb-1 flex items-start gap-2 text-sm font-semibold text-hub-text">
                      <i className="bi bi-check-circle-fill mt-0.5 text-teal-600" aria-hidden />
                      {item.title}
                    </p>
                    <p className="mb-0 pl-6 text-sm text-hub-muted">{item.body}</p>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex justify-end border-t border-slate-100 px-5 py-3">
              <button
                type="button"
                className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                onClick={() => setOpen(false)}
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
