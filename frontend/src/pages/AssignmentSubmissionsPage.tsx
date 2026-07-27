import { useCallback, useEffect, useState } from 'react'

import { Link, useLocation, useParams } from 'react-router-dom'

import {

  fetchAssignmentSubmissions,

  type AssignmentSubmissionsResponse,

  type DiscussionSubmissionRow,

  type PdfSubmissionRow,

  type QuizSubmissionRow,

} from '../api/assignmentWorkspace'

import { DiscussionSubmissionsPanel } from '../components/assignments/submissions/DiscussionSubmissionsPanel'

import { PdfSubmissionsPanel } from '../components/assignments/submissions/PdfSubmissionsPanel'

import { QuizSubmissionsPanel } from '../components/assignments/submissions/QuizSubmissionsPanel'

import { formatWhen, StatGrid } from '../components/assignments/submissions/submissionsShared'
import { useAssignmentWorkspaceScope, assignmentWorkspaceHubPath } from '../utils/assignmentWorkspaceScope'



const MODE_LABEL: Record<string, string> = {

  pdf: 'File submissions',

  quiz: 'Quiz review',

  discussion: 'Discussion & grading',

  default: 'Submissions',

}



export function AssignmentSubmissionsPage() {

  const { classId, assignmentId } = useParams()

  const location = useLocation()

  const isGroup = location.pathname.includes('/group/')

  const id = Number(assignmentId)
  const workspaceScope = useAssignmentWorkspaceScope()
  const base = assignmentWorkspaceHubPath(workspaceScope, Number(classId))



  const [data, setData] = useState<AssignmentSubmissionsResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState<string | null>(null)



  const load = useCallback(async () => {

    if (!id) return

    setLoading(true)

    setError(null)

    try {

      setData(await fetchAssignmentSubmissions(id, isGroup, workspaceScope))

    } catch (e) {

      setError(e instanceof Error ? e.message : 'Failed to load submissions')

    } finally {

      setLoading(false)

    }

  }, [id, isGroup, workspaceScope])



  useEffect(() => {

    void load()

  }, [load])



  const viewPath =
    data?.links.view_spa ||
    `${base}/${isGroup ? 'group' : 'individual'}/${assignmentId}/view`
  const gradePath =
    data?.links.grade_spa ||
    `${base}/${isGroup ? 'group' : 'individual'}/${assignmentId}/grade`



  if (loading) {

    return (

      <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">

        Loading submissions…

      </div>

    )

  }



  if (error || !data) {

    return (

      <div className="rounded-2xl bg-white p-8 shadow-sm">

        <p className="text-red-700">{error || 'Could not load submissions'}</p>

        <Link to={viewPath} className="mt-4 inline-block text-sm font-semibold text-teal-700">

          Back to assignment

        </Link>

      </div>

    )

  }



  const uiMode = data.ui_mode || 'default'

  const totalPoints = data.assignment.total_points ?? 100

  const isGradingPage = Boolean(data.grading_on_submissions)



  return (

    <div className="mx-auto max-w-[1200px] space-y-5">

      <div className="flex flex-wrap items-start justify-between gap-4">

        <div>

          <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">

            {isGradingPage ? 'Submissions & grading' : 'Submissions'}

          </p>

          <h1 className="text-2xl font-extrabold text-hub-text">{data.assignment.title}</h1>

          <p className="mt-1 text-sm text-hub-muted">

            {data.class.name}

            {data.assignment.due_date ? ` · Due ${formatWhen(data.assignment.due_date)}` : ''}

            {` · ${MODE_LABEL[uiMode] || 'Submissions'}`}

          </p>

        </div>

        <div className="flex flex-wrap gap-2">

          <Link

            to={viewPath}

            className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"

          >

            View assignment

          </Link>

          {data.show_grade_link !== false && !isGradingPage ? (

            <Link

              to={gradePath}

              className="rounded-full bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800"

            >

              Grade

            </Link>

          ) : null}

        </div>

      </div>



      <StatGrid stats={data.stats} />



      {!isGroup && uiMode === 'pdf' ? (

        <PdfSubmissionsPanel

          assignmentId={data.assignment.id}

          totalPoints={totalPoints}

          rows={data.rows as unknown as PdfSubmissionRow[]}

          gradePath={gradePath}

          workspaceScope={workspaceScope}

          onSaved={() => void load()}

        />

      ) : null}



      {!isGroup && uiMode === 'quiz' ? (

        <QuizSubmissionsPanel

          assignmentId={data.assignment.id}

          totalPoints={totalPoints}

          hasOpenEnded={Boolean(data.has_open_ended)}

          rows={data.rows as unknown as QuizSubmissionRow[]}

          workspaceScope={workspaceScope}

          onSaved={() => void load()}

        />

      ) : null}



      {!isGroup && uiMode === 'discussion' ? (

        <DiscussionSubmissionsPanel

          assignmentId={data.assignment.id}

          totalPoints={totalPoints}

          rows={data.rows as unknown as DiscussionSubmissionRow[]}

          workspaceScope={workspaceScope}

          onSaved={() => void load()}

        />

      ) : null}



      {!isGroup && uiMode === 'default' ? (

        <PdfSubmissionsPanel

          assignmentId={data.assignment.id}

          totalPoints={totalPoints}

          rows={data.rows as unknown as PdfSubmissionRow[]}

          gradePath={gradePath}

          workspaceScope={workspaceScope}

          onSaved={() => void load()}

        />

      ) : null}



      {isGroup ? (

        <div className="space-y-3">

          {(data.rows as {

            group: { id: number; name: string }

            member_count: number

            submitted: boolean

            members: { display_name: string }[]

          }[]).map((row) => (

            <div key={row.group.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">

              <div className="flex flex-wrap items-center justify-between gap-2">

                <h2 className="font-bold text-hub-text">{row.group.name}</h2>

                <span

                  className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${row.submitted ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}

                >

                  {row.submitted ? 'Submitted' : 'Not submitted'}

                </span>

              </div>

              <p className="mt-1 text-sm text-hub-muted">{row.member_count} members</p>

              <ul className="mt-2 flex flex-wrap gap-2 text-xs text-hub-muted">

                {row.members.map((m, i) => (

                  <li key={i} className="rounded-full bg-slate-50 px-2 py-0.5">

                    {m.display_name}

                  </li>

                ))}

              </ul>

            </div>

          ))}

        </div>

      ) : null}

    </div>

  )

}



export default AssignmentSubmissionsPage


