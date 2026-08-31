import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchTeacherClassView } from '../api/teacherClasses'
import type { AssessmentToolSlug } from '../api/classTools'
import { AnnouncementComposeModal } from '../components/announcements/AnnouncementComposeModal'
import { ClassAnalyticsModal } from '../components/classes/ClassAnalyticsModal'
import { ClassAssessmentToolModal } from '../components/classes/ClassAssessmentToolModal'
import { ClassDeadlineRemindersModal } from '../components/classes/ClassDeadlineRemindersModal'
import { ClassSyllabusModal } from '../components/classes/ClassSyllabusModal'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import { TeacherClassRosterModal } from '../components/teacher/TeacherClassRosterModal'
import type { TeacherClassViewAssistantLog, TeacherClassViewResponse } from '../types/teacherClassView'
import { spaRoute } from '../utils/spaRoute'

const ACTION_BADGE_CLASS: Record<string, string> = {
  primary: 'bg-primary',
  warn: 'bg-warning text-dark',
  info: 'bg-info',
  danger: 'bg-danger',
  muted: 'bg-secondary',
}

const actionClass = 'btn-teacher-class-action teacher-class-view-action'

function spaToolKey(href: string | undefined): string | null {
  if (!href) return null
  if (href.startsWith('spa:')) return href.slice(4)
  if (href.startsWith('modal:')) return href.slice(6)
  return null
}

function ActionLink({ href, icon, children }: { href: string; icon: string; children: ReactNode }) {
  const tool = spaToolKey(href)
  if (tool) return null
  const to = spaRoute(href)
  if (to.startsWith('http') || href.startsWith('mailto:') || href.startsWith('#')) {
    return (
      <a href={href} className={actionClass}>
        <i className={`bi ${icon} me-1`} aria-hidden />
        {children}
      </a>
    )
  }
  return (
    <Link to={to} className={actionClass}>
      <i className={`bi ${icon} me-1`} aria-hidden />
      {children}
    </Link>
  )
}

function ActionButton({ icon, onClick, children }: { icon: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className={`${actionClass} border-0`} onClick={onClick}>
      <i className={`bi ${icon} me-1`} aria-hidden />
      {children}
    </button>
  )
}

function AssistantLogBadge({ log }: { log: TeacherClassViewAssistantLog }) {
  const cls = ACTION_BADGE_CLASS[log.action_tone] || ACTION_BADGE_CLASS.muted
  return <span className={`badge ${cls}`}>{log.action_label}</span>
}

function ClassMailingList({ email }: { email: string | null }) {
  const [copied, setCopied] = useState(false)

  const copy = useCallback(() => {
    if (!email) return
    navigator.clipboard.writeText(email).then(
      () => {
        setCopied(true)
        window.setTimeout(() => setCopied(false), 2000)
      },
      () => setCopied(false),
    )
  }, [email])

  return (
    <div className="teacher-class-view-mailing-list">
      <div className="teacher-class-view-mailing-list__icon">
        <i className="bi bi-envelope-at" aria-hidden />
      </div>
      <div className="teacher-class-view-mailing-list__content">
        <div className="teacher-class-view-mailing-list__label">
          Class mailing list
          <span className="teacher-class-view-mailing-list__hint">
            Email this address to reach every student in the class.
          </span>
        </div>
        {email ? (
          <div className="teacher-class-view-mailing-list__row">
            <a href={`mailto:${email}`} className="teacher-class-view-mailing-list__email">
              {email}
            </a>
            <button
              type="button"
              className="teacher-class-view-mailing-list__copy"
              onClick={copy}
              title="Copy address"
            >
              <i className={`bi ${copied ? 'bi-check-lg' : 'bi-clipboard'}`} aria-hidden />
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        ) : (
          <span className="teacher-class-view-mailing-list__pending">
            Not set up yet — the group is created once the class is provisioned in Google.
          </span>
        )}
      </div>
    </div>
  )
}

export function TeacherClassViewPage() {
  const { classId } = useParams<{ classId: string }>()
  const id = Number(classId)
  const [data, setData] = useState<TeacherClassViewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rosterOpen, setRosterOpen] = useState(false)
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [deadlineRemindersOpen, setDeadlineRemindersOpen] = useState(false)
  const [assessmentTool, setAssessmentTool] = useState<AssessmentToolSlug | null>(null)
  const [announceOpen, setAnnounceOpen] = useState(false)
  const [syllabusOpen, setSyllabusOpen] = useState(false)

  const load = useCallback(async () => {
    if (!classId) {
      setError('Missing class id')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      setData(await fetchTeacherClassView(classId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load class')
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <ManagementPageShell>
      <div className="container-fluid px-2 px-md-4 teacher-class-view">
        {loading ? (
          <div className="p-5 text-center text-muted">Loading class…</div>
        ) : error || !data ? (
          <div className="alert alert-danger m-3">{error || 'Could not load class'}</div>
        ) : (
          <>
            <TeacherClassViewBody
              data={data}
              onOpenRoster={() => setRosterOpen(true)}
              onOpenAnalytics={() => setAnalyticsOpen(true)}
              onOpenDeadlineReminders={() => setDeadlineRemindersOpen(true)}
              onOpenAssessmentTool={setAssessmentTool}
              onOpenAnnouncements={() => setAnnounceOpen(true)}
              onOpenSyllabus={() => setSyllabusOpen(true)}
            />
            <TeacherClassRosterModal
              open={rosterOpen}
              className={data.class.name}
              students={data.enrolled_students}
              onClose={() => setRosterOpen(false)}
            />
            {Number.isFinite(id) && id > 0 ? (
              <>
                <ClassAnalyticsModal
                  open={analyticsOpen}
                  classId={id}
                  scope="teacher"
                  onClose={() => setAnalyticsOpen(false)}
                />
                <ClassSyllabusModal open={syllabusOpen} classId={id} onClose={() => setSyllabusOpen(false)} />
                <ClassDeadlineRemindersModal
                  open={deadlineRemindersOpen}
                  classId={id}
                  scope="teacher"
                  onClose={() => setDeadlineRemindersOpen(false)}
                />
                {assessmentTool ? (
                  <ClassAssessmentToolModal
                    open
                    classId={id}
                    tool={assessmentTool}
                    scope="teacher"
                    onClose={() => setAssessmentTool(null)}
                  />
                ) : null}
                <AnnouncementComposeModal
                  open={announceOpen}
                  classId={id}
                  className={data.class.name}
                  onClose={() => setAnnounceOpen(false)}
                  onSent={() => void load()}
                />
              </>
            ) : null}
          </>
        )}
      </div>
    </ManagementPageShell>
  )
}

function TeacherClassViewBody({
  data,
  onOpenRoster,
  onOpenAnalytics,
  onOpenDeadlineReminders,
  onOpenAssessmentTool,
  onOpenAnnouncements,
  onOpenSyllabus,
}: {
  data: TeacherClassViewResponse
  onOpenRoster: () => void
  onOpenAnalytics: () => void
  onOpenDeadlineReminders: () => void
  onOpenAssessmentTool: (tool: AssessmentToolSlug) => void
  onOpenAnnouncements: () => void
  onOpenSyllabus: () => void
}) {
  const cls = data.class
  const links = data.links
  const subtitle = `${cls.subject} • ${cls.grade_levels_display || 'All Grades'}`
  const hasAssistants = data.has_student_assistants
  const assistantTo = spaRoute(links.assistant_approvals)

  const openTool = (href: string | undefined, fallback?: () => void) => {
    const key = spaToolKey(href)
    if (key === 'analytics') {
      onOpenAnalytics()
      return
    }
    if (key === 'deadline_reminders' || key === 'deadline-reminders') {
      onOpenDeadlineReminders()
      return
    }
    if (key === '360-feedback' || key === 'reflection-journals' || key === 'conflicts') {
      onOpenAssessmentTool(key as AssessmentToolSlug)
      return
    }
    fallback?.()
  }

  return (
    <>
      <div className="teacher-class-header mb-4">
        <div className="teacher-class-header-content">
          <div className="teacher-class-title-section">
            <h1 className="teacher-class-title">
              <i className="bi bi-mortarboard me-3" aria-hidden />
              {cls.name}
            </h1>
            <p className="teacher-class-subtitle">{subtitle}</p>
          </div>
          <Link to="/teacher/classes" className="btn-teacher-class-back">
            <i className="bi bi-arrow-left me-2" aria-hidden />
            Back to My Classes
          </Link>
        </div>
      </div>

      {hasAssistants && data.pending_assistant_count > 0 ? (
        <div
          className="alert assistant-proposals-alert-banner d-flex flex-wrap align-items-center justify-content-between gap-3 mb-3 py-3 px-4"
          role="alert"
        >
          <div className="mb-0">
            <i className="bi bi-stars text-warning me-2" aria-hidden />
            <strong>{data.pending_assistant_count}</strong> proposal(s) from a student assistant need your approval
            before students can see them.
          </div>
          <Link to={assistantTo} className="btn btn-assistant-review-now btn-sm">
            Review proposals
          </Link>
        </div>
      ) : null}

      {hasAssistants ? (
        <div className="mb-4 d-flex flex-wrap align-items-center gap-2">
          <Link to={assistantTo} className="btn btn-assistant-proposals-subtle">
            <i className="bi bi-patch-check-fill" aria-hidden />
            Assistant approvals
          </Link>
          <span className="text-muted small">Approve or reject assignments proposed by student assistants.</span>
        </div>
      ) : null}

      <div className="teacher-class-card-modern teacher-class-view-details mb-4">
        <div className="teacher-class-card-header">
          <div className="teacher-class-card-icon">
            <i className="bi bi-info-circle" aria-hidden />
          </div>
          <div className="teacher-class-card-title-section">
            <h5 className="teacher-class-card-title">Class details</h5>
            <p className="teacher-class-card-subject">Course information</p>
          </div>
        </div>
        <div className="teacher-class-card-body">
          <div className="teacher-class-view-details-grid">
            <div className="teacher-class-info-item">
              <i className="bi bi-book" aria-hidden />
              <div>
                <strong>Subject</strong>
                <div>{cls.subject}</div>
              </div>
            </div>
            <div className="teacher-class-info-item">
              <i className="bi bi-mortarboard" aria-hidden />
              <div>
                <strong>Grade level</strong>
                <div>{cls.grade_levels_display || 'N/A'}</div>
              </div>
            </div>
            <div className="teacher-class-info-item">
              <i className="bi bi-door-open" aria-hidden />
              <div>
                <strong>Room</strong>
                <div>{cls.room_display}</div>
              </div>
            </div>
            <div className="teacher-class-info-item">
              <i className="bi bi-clock" aria-hidden />
              <div>
                <strong>Schedule</strong>
                <div>{cls.schedule_display}</div>
              </div>
            </div>
            <div className="teacher-class-info-item">
              <i className="bi bi-calendar3" aria-hidden />
              <div>
                <strong>School year</strong>
                <div>{cls.school_year_name || 'N/A'}</div>
              </div>
            </div>
          </div>

          <div className="teacher-class-view-details-stats">
            <div className="teacher-class-stat-card">
              <div className="teacher-class-stat-icon">
                <i className="bi bi-people-fill" aria-hidden />
              </div>
              <div className="teacher-class-stat-content">
                <div className="teacher-class-stat-number">{data.stats.students}</div>
                <div className="teacher-class-stat-label">Students</div>
              </div>
            </div>
            <div className="teacher-class-stat-card">
              <div className="teacher-class-stat-icon">
                <i className="bi bi-journal-text" aria-hidden />
              </div>
              <div className="teacher-class-stat-content">
                <div className="teacher-class-stat-number">{data.stats.assignments}</div>
                <div className="teacher-class-stat-label">Assignments</div>
              </div>
            </div>
            <div className="teacher-class-stat-card">
              <div className="teacher-class-stat-icon">
                <i className="bi bi-megaphone" aria-hidden />
              </div>
              <div className="teacher-class-stat-content">
                <div className="teacher-class-stat-number">{data.stats.announcements}</div>
                <div className="teacher-class-stat-label">Announcements</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="teacher-class-view-split">
        <div className="teacher-class-card-modern teacher-class-view-panel">
          <div className="teacher-class-card-header">
            <div className="teacher-class-card-icon">
              <i className="bi bi-tools" aria-hidden />
            </div>
            <div className="teacher-class-card-title-section">
              <h5 className="teacher-class-card-title">Class management</h5>
              <p className="teacher-class-card-subject">Quick actions</p>
            </div>
          </div>
          <div className="teacher-class-card-body teacher-class-card-body--mgmt">
            <div className="mb-2">
              <h6 className="teacher-class-section-title">
                <i className="bi bi-gear me-2" aria-hidden />
                Core management
              </h6>
              <div className="teacher-class-view-actions">
                <ActionButton icon="bi-people-fill" onClick={onOpenRoster}>
                  Class roster
                </ActionButton>
                <ActionLink href={links.add_assignment} icon="bi-plus-circle">
                  Add assignment
                </ActionLink>
                <ActionLink href={links.take_attendance} icon="bi-clipboard-check">
                  Take attendance
                </ActionLink>
                <ActionLink href={links.manage_groups} icon="bi-people">
                  Manage groups
                </ActionLink>
                {links.class_notes ? (
                  <ActionLink href={links.class_notes} icon="bi-journal-bookmark">
                    Class notes
                  </ActionLink>
                ) : null}
                {links.syllabus || data.features.syllabus ? (
                  <ActionButton icon="bi-journal-richtext" onClick={onOpenSyllabus}>
                    Syllabus
                  </ActionButton>
                ) : null}
                {hasAssistants ? (
                  <ActionLink href={links.assistant_approvals} icon="bi-patch-check-fill">
                    Assistant approvals
                  </ActionLink>
                ) : null}
                {data.features.gradek_standards && links.gradek_standards ? (
                  <ActionLink href={links.gradek_standards} icon="bi-check2-square">
                    Kindergarten standards
                  </ActionLink>
                ) : null}
                {data.features.grade1_standards && links.grade1_standards ? (
                  <ActionLink href={links.grade1_standards} icon="bi-check2-square">
                    1st grade standards
                  </ActionLink>
                ) : null}
                {data.features.grade2_standards && links.grade2_standards ? (
                  <ActionLink href={links.grade2_standards} icon="bi-check2-square">
                    2nd grade standards
                  </ActionLink>
                ) : null}
                {data.features.grade3_standards && links.grade3_standards ? (
                  <ActionLink href={links.grade3_standards} icon="bi-check2-square">
                    3rd grade standards
                  </ActionLink>
                ) : null}
                <ActionButton icon="bi-megaphone" onClick={onOpenAnnouncements}>
                  Announcements
                </ActionButton>
              </div>
            </div>
            <div className="mb-2">
              <h6 className="teacher-class-section-title">
                <i className="bi bi-people-fill me-2" aria-hidden />
                Group work & assignments
              </h6>
              <div className="teacher-class-view-actions">
                <ActionLink href={links.assignments_and_grades} icon="bi-journal-plus">
                  Assignments & grades
                </ActionLink>
                <ActionLink href={links.group_assignments} icon="bi-people-fill">
                  Group assignments
                </ActionLink>
                {spaToolKey(links.deadline_reminders) ? (
                  <ActionButton icon="bi-bell" onClick={() => openTool(links.deadline_reminders)}>
                    Deadline reminders
                  </ActionButton>
                ) : (
                  <ActionLink href={links.deadline_reminders} icon="bi-bell">
                    Deadline reminders
                  </ActionLink>
                )}
                {spaToolKey(links.analytics) ? (
                  <ActionButton icon="bi-graph-up" onClick={() => openTool(links.analytics)}>
                    Reports & analytics
                  </ActionButton>
                ) : (
                  <ActionLink href={links.analytics} icon="bi-graph-up">
                    Reports & analytics
                  </ActionLink>
                )}
              </div>
            </div>
            <div>
              <h6 className="teacher-class-section-title">
                <i className="bi bi-star me-2" aria-hidden />
                Assessment & feedback
              </h6>
              <div className="teacher-class-view-actions">
                {spaToolKey(links.feedback_360) ? (
                  <ActionButton icon="bi-arrow-repeat" onClick={() => openTool(links.feedback_360)}>
                    360° feedback
                  </ActionButton>
                ) : (
                  <ActionLink href={links.feedback_360} icon="bi-arrow-repeat">
                    360° feedback
                  </ActionLink>
                )}
                {spaToolKey(links.reflection_journals) ? (
                  <ActionButton icon="bi-journal-text" onClick={() => openTool(links.reflection_journals)}>
                    Reflection journals
                  </ActionButton>
                ) : (
                  <ActionLink href={links.reflection_journals} icon="bi-journal-text">
                    Reflection journals
                  </ActionLink>
                )}
                {spaToolKey(links.conflicts) ? (
                  <ActionButton icon="bi-exclamation-triangle" onClick={() => openTool(links.conflicts)}>
                    Conflict resolution
                  </ActionButton>
                ) : (
                  <ActionLink href={links.conflicts} icon="bi-exclamation-triangle">
                    Conflict resolution
                  </ActionLink>
                )}
              </div>
            </div>
          </div>
        </div>

        <div
          id="announcements"
          className="teacher-class-card-modern teacher-class-view-panel teacher-class-card-announcements-tall"
        >
          <div className="teacher-class-card-header">
            <div className="teacher-class-card-icon">
              <i className="bi bi-megaphone" aria-hidden />
            </div>
            <div className="teacher-class-card-title-section flex-grow-1">
              <h5 className="teacher-class-card-title">Announcements</h5>
              <p className="teacher-class-card-subject">Recent updates</p>
            </div>
            <button type="button" className={actionClass} onClick={onOpenAnnouncements}>
              <i className="bi bi-plus-lg me-1" aria-hidden />
              New
            </button>
          </div>
          <div className="teacher-class-card-body teacher-class-announcements-body-tall">
            {cls.show_google_integration || cls.google_group_email ? (
              <ClassMailingList email={cls.google_group_email} />
            ) : null}
            {data.announcements.length > 0 ? (
              <div className="teacher-class-announcements">
                {data.announcements.map((ann) => (
                  <div key={ann.id} className="teacher-class-announcement-item">
                    <div className="teacher-class-announcement-header">
                      <h6 className="teacher-class-announcement-title">{ann.title}</h6>
                      <small className="teacher-class-announcement-date">{ann.timestamp_display}</small>
                    </div>
                    <p className="teacher-class-announcement-message">{ann.message_preview}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="teacher-class-empty-state">
                <i className="bi bi-megaphone" aria-hidden />
                <p>No recent announcements.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {hasAssistants ? (
        <div className="teacher-class-card-modern mt-4 mb-0">
          <div className="teacher-class-card-header">
            <div className="teacher-class-card-icon">
              <i className="bi bi-person-badge" aria-hidden />
            </div>
            <div className="teacher-class-card-title-section">
              <h5 className="teacher-class-card-title">Student assistant activity</h5>
              <p className="teacher-class-card-subject">
                {data.student_assistants.map((sa, i) => (
                  <span key={sa.id}>
                    {i > 0 ? ', ' : null}
                    <span className="fw-semibold">{sa.display_name}</span>
                  </span>
                ))}{' '}
                can take attendance and enter grades. All actions are logged.
              </p>
            </div>
          </div>
          <div className="teacher-class-card-body">
            {data.assistant_action_logs.length > 0 ? (
              <div className="table-responsive">
                <table className="table table-sm table-hover mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>Time</th>
                      <th>Action</th>
                      <th>Details</th>
                      <th>Alert</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.assistant_action_logs.map((log) => (
                      <tr key={log.id}>
                        <td className="text-nowrap">{log.created_at_display}</td>
                        <td>
                          <AssistantLogBadge log={log} />
                        </td>
                        <td className="small">{log.summary}</td>
                        <td>
                          {log.alert_sent ? (
                            <span className="badge bg-warning text-dark">Alert sent</span>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-muted mb-0">No assistant actions logged yet.</p>
            )}
          </div>
        </div>
      ) : null}
    </>
  )
}
