import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { fetchGroupClassPicker } from '../api/groupCreateForms'
import { spaRoute } from '../utils/spaRoute'

export function CreateGroupClassPickerPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const classIdParam = searchParams.get('class_id')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [backUrl, setBackUrl] = useState('/management/assignments/create')
  const [classes, setClasses] = useState<{ id: number; name: string; subject?: string | null }[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGroupClassPicker()
      setBackUrl(spaRoute(data.type_selector_url))
      setClasses(data.classes)
      if (classIdParam && /^\d+$/.test(classIdParam)) {
        navigate(`/management/assignments/create/group/${classIdParam}`, { replace: true })
        return
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load classes')
    } finally {
      setLoading(false)
    }
  }, [classIdParam, navigate])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) {
    return <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">Loading classes…</div>
  }

  if (error) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">{error}</p>
        <Link to={backUrl} className="mt-4 inline-block text-sm font-semibold text-teal-700">
          Back
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1100px] px-1 pb-10">
      <header className="mb-6 rounded-[20px] bg-gradient-to-br from-violet-600 to-pink-600 px-6 py-5 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="mb-1 flex items-center gap-2 text-2xl font-bold">
              <i className="bi bi-people-fill" aria-hidden />
              Select Class for Group Assignment
            </h1>
            <p className="text-sm text-white/90">Choose which class this group assignment belongs to</p>
          </div>
          <Link
            to={backUrl}
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-violet-700 hover:bg-white/95"
          >
            <i className="bi bi-arrow-left" aria-hidden />
            Back to types
          </Link>
        </div>
      </header>

      {classes.length === 0 ? (
        <div className="rounded-xl border border-sky-200 bg-sky-50 p-6 text-sky-900">
          <p className="font-semibold">No classes available</p>
          <p className="mt-1 text-sm">Create a class before adding group assignments.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {classes.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => navigate(`/management/assignments/create/group/${c.id}`)}
              className="rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-violet-300 hover:shadow-md"
            >
              <i className="bi bi-house-door-fill mb-3 block text-3xl text-violet-600" aria-hidden />
              <h2 className="font-bold text-slate-800">{c.name}</h2>
              {c.subject ? <p className="mt-1 text-sm text-slate-500">{c.subject}</p> : null}
              <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-violet-700">
                <i className="bi bi-people-fill" aria-hidden />
                Create group assignment
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
