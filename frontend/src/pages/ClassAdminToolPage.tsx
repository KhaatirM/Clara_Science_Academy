import { Navigate, useParams } from 'react-router-dom'

/** Legacy bookmark route — forwards to the current SPA class tools. */
export default function ClassAdminToolPage() {
  const { classId = '', tool = '' } = useParams()
  const id = Number(classId)

  if (!Number.isFinite(id) || id <= 0) {
    return <Navigate to="/management/classes" replace />
  }

  if (tool === 'groups') {
    return <Navigate to={`/management/classes/${id}/groups`} replace />
  }

  return <Navigate to={`/management/classes/${id}`} replace />
}
