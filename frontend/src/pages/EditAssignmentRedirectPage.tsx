import { useEffect } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useAssignmentWorkspaceScope, assignmentWorkspaceHubPath } from '../utils/assignmentWorkspaceScope'

/** Legacy /edit URLs — open the assignment view (edit is a modal there). */
export function EditAssignmentRedirectPage() {
  const { classId, assignmentId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const isGroup = location.pathname.includes('/group/')

  const workspaceScope = useAssignmentWorkspaceScope()
  const base = assignmentWorkspaceHubPath(workspaceScope, Number(classId))

  useEffect(() => {
    if (!assignmentId || !classId) return
    const viewPath = isGroup
      ? `${base}/group/${assignmentId}/view`
      : `${base}/individual/${assignmentId}/view`
    navigate(viewPath, { replace: true, state: { openEdit: true } })
  }, [assignmentId, classId, isGroup, navigate, base])

  const backPath = assignmentWorkspaceHubPath(workspaceScope, classId ? Number(classId) : undefined)

  return (
    <div className="rounded-2xl bg-white p-8 text-center shadow-sm">
      <p className="text-hub-muted">Opening assignment editor…</p>
      <Link to={backPath} className="mt-4 inline-block font-semibold text-teal-700">
        Back
      </Link>
    </div>
  )
}

export default EditAssignmentRedirectPage
