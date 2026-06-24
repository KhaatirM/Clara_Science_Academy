import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchGroupTypeSelector } from '../api/groupCreateForms'
import { spaRoute } from '../utils/spaRoute'

export function CreateGroupTypePage() {
  const navigate = useNavigate()
  const { classId: classIdParam } = useParams()
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [className, setClassName] = useState('')
  const [backUrl, setBackUrl] = useState('/management/assignments')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [quizUrl, setQuizUrl] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!classId) {
      setError('Invalid class')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGroupTypeSelector(classId)
      setClassName(data.class.name)
      setBackUrl(spaRoute(data.back_url))
      setPdfUrl(spaRoute(data.links.pdf))
      setQuizUrl(spaRoute(data.links.quiz))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load group types')
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    void load()
  }, [load])

  if (!classId) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">Invalid class</p>
        <Link to="/management/assignments/create/group" className="mt-4 inline-block text-sm font-semibold text-teal-700">
          Pick a class
        </Link>
      </div>
    )
  }

  if (loading) {
    return <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">Loading group types…</div>
  }

  if (error || !pdfUrl || !quizUrl) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">{error || 'Could not load page'}</p>
        <Link to={backUrl} className="mt-4 inline-block text-sm font-semibold text-teal-700">
          Back
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[900px] px-1 pb-10">
      <header className="mb-6 rounded-[20px] bg-gradient-to-br from-violet-600 to-pink-600 px-6 py-5 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="mb-1 flex items-center gap-2 text-2xl font-bold">
              <i className="bi bi-people-fill" aria-hidden />
              Create Group Assignment
            </h1>
            <p className="text-sm text-white/90">Choose the type of collaborative assignment</p>
            <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold">
              <i className="bi bi-book" aria-hidden />
              {className}
            </p>
          </div>
          <Link
            to={backUrl}
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-violet-700 hover:bg-white/95"
          >
            <i className="bi bi-arrow-left" aria-hidden />
            Back to assignments
          </Link>
        </div>
      </header>

      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        <button
          type="button"
          onClick={() => navigate(pdfUrl)}
          className="flex h-full flex-col rounded-2xl border-2 border-slate-200 bg-white p-6 text-left shadow-sm transition hover:border-violet-400 hover:shadow-md"
        >
          <i className="bi bi-file-earmark-text mb-3 text-4xl text-violet-600" aria-hidden />
          <h2 className="text-lg font-bold text-slate-800">PDF/Paper Assignment</h2>
          <p className="mt-2 flex-1 text-sm text-slate-600">
            File attachments and instructions. One student submits on behalf of the group.
          </p>
          <span className="mt-5 inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-bold text-white">
            <i className="bi bi-file-earmark-plus" aria-hidden />
            Create PDF/Paper
          </span>
        </button>

        <button
          type="button"
          onClick={() => navigate(quizUrl)}
          className="flex h-full flex-col rounded-2xl border-2 border-slate-200 bg-white p-6 text-left shadow-sm transition hover:border-indigo-400 hover:shadow-md"
        >
          <i className="bi bi-ui-checks-grid mb-3 text-4xl text-indigo-600" aria-hidden />
          <h2 className="text-lg font-bold text-slate-800">Group Quiz</h2>
          <p className="mt-2 flex-1 text-sm text-slate-600">
            Shared quiz workspace — the team collaborates on answers; any member can submit for the group.
          </p>
          <span className="mt-5 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white">
            <i className="bi bi-plus-circle" aria-hidden />
            Create group quiz
          </span>
        </button>

        <div className="relative flex h-full flex-col rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 p-6 opacity-80 md:col-span-2 lg:col-span-1">
          <span className="absolute right-4 top-4 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">
            Coming soon
          </span>
          <i className="bi bi-chat-dots-fill mb-3 text-4xl text-slate-400" aria-hidden />
          <h2 className="text-lg font-bold text-slate-600">Discussion Assignment</h2>
          <p className="mt-2 flex-1 text-sm text-slate-500">
            Group discussion assignments are under development and temporarily unavailable.
          </p>
          <span className="mt-5 inline-flex items-center gap-2 rounded-lg bg-slate-200 px-4 py-2 text-sm font-bold text-slate-500">
            <i className="bi bi-lock-fill" aria-hidden />
            Unavailable
          </span>
        </div>
      </div>
    </div>
  )
}
