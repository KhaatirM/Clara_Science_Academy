import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

function ActionLink({
  href,
  icon,
  label,
  external,
}: {
  href?: string
  icon: string
  label: string
  external?: boolean
}) {
  if (!href) return null
  const className =
    'inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-teal-300 bg-white px-3 py-2 text-sm font-semibold text-teal-800 hover:border-teal-500 hover:bg-teal-50'
  if (href.startsWith('/app/')) {
    return (
      <Link to={href.replace('/app', '')} className={className}>
        <i className={`bi ${icon}`} aria-hidden />
        {label}
      </Link>
    )
  }
  if (external || href.startsWith('/management/') || href.startsWith('/teacher/')) {
    return (
      <a href={href} className={className}>
        <i className={`bi ${icon}`} aria-hidden />
        {label}
      </a>
    )
  }
  return (
    <Link to={href} className={className}>
      <i className={`bi ${icon}`} aria-hidden />
      {label}
    </Link>
  )
}

function Section({ title, icon, children }: { title: string; icon: string; children: ReactNode }) {
  return (
    <div className="mb-5 last:mb-0">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-hub-text">
        <i className={`bi ${icon} text-teal-700`} aria-hidden />
        {title}
      </h3>
      <div className="grid gap-2">{children}</div>
    </div>
  )
}

export interface ClassManagementLinks {
  add_assignment: string
  attendance: string
  manage_roster: string
  grade1_standards?: string
  grade3_standards?: string
  assistant_approvals: string
  view_grades: string
  edit_class: string
  analytics: string
  feedback_360: string
  reflection_journals: string
  conflicts: string
  assignments_and_grades: string
  manage_groups: string
  deadline_reminders: string
}

export function ClassManagementPanel({
  links,
  features = { grade1_standards: false, grade3_standards: false },
  canAdminUi,
}: {
  links: Partial<ClassManagementLinks>
  features?: { grade1_standards: boolean; grade3_standards: boolean }
  canAdminUi: boolean
}) {
  return (
    <section className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-teal-100 bg-gradient-to-r from-teal-100/80 to-teal-50/50 px-5 py-4">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-100 text-lg text-teal-800">
            <i className="bi bi-tools" aria-hidden />
          </span>
          <div>
            <h2 className="text-base font-bold text-hub-text">Class Management</h2>
            <p className="text-sm text-hub-muted">Quick Actions</p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-5">
        <Section title="Core Management" icon="bi-gear">
          <ActionLink href={links.add_assignment} icon="bi-plus-circle" label="Add Assignment" />
          <ActionLink href={links.attendance} icon="bi-clipboard-check" label="Attendance" />
          <ActionLink href={links.manage_roster} icon="bi-people" label="Manage Roster" />
          {features.grade1_standards && links.grade1_standards ? (
            <ActionLink href={links.grade1_standards} icon="bi-check2-square" label="1st Grade Standards" />
          ) : null}
          {features.grade3_standards && links.grade3_standards ? (
            <ActionLink href={links.grade3_standards} icon="bi-check2-square" label="3rd Grade Standards" />
          ) : null}
        </Section>
        {canAdminUi ? (
          <Section title="Administrative" icon="bi-shield-check">
            <ActionLink href={links.view_grades} icon="bi-journal-plus" label="View Grades" />
            <ActionLink href={links.edit_class} icon="bi-pencil" label="Edit Class" />
            <ActionLink href={links.analytics} icon="bi-graph-up" label="Reports & Analytics" />
          </Section>
        ) : null}
        <Section title="Assessment & Feedback" icon="bi-star">
          <ActionLink href={links.feedback_360} icon="bi-arrow-repeat" label="360° Feedback" />
          <ActionLink href={links.reflection_journals} icon="bi-journal-text" label="Reflection Journals" />
          <ActionLink href={links.conflicts} icon="bi-exclamation-triangle" label="Conflict Resolution" />
        </Section>
        <Section title="Group Management" icon="bi-people-fill">
          <ActionLink href={links.assignments_and_grades} icon="bi-journal-plus" label="Assignments & Grades" />
          <ActionLink href={links.manage_groups} icon="bi-people" label="Manage Groups" />
          <ActionLink href={links.deadline_reminders} icon="bi-bell" label="Deadline Reminders" />
        </Section>
      </div>
    </section>
  )
}
