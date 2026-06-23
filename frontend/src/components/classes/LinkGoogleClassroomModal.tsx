import { useEffect, useState } from 'react'
import { fetchGoogleClassroomOptions, googleClassroomAction } from '../../api/classes'
import type { GoogleClassroomOption } from '../../types/classDetail'

interface LinkGoogleClassroomModalProps {
  classId: number
  className: string
  onClose: () => void
  onLinked: () => void
}

export function LinkGoogleClassroomModal({ classId, className, onClose, onLinked }: LinkGoogleClassroomModalProps) {
  const [items, setItems] = useState<GoogleClassroomOption[]>([])
  const [loading, setLoading] = useState(true)
  const [linking, setLinking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchGoogleClassroomOptions(classId)
      .then((res) => {
        if (!res.success) {
          if (res.settings_url) {
            setError(`${res.message} Open settings to connect Google.`)
          } else {
            setError(res.message || 'Could not load Google classrooms')
          }
          return
        }
        setItems(res.items || [])
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load options'))
      .finally(() => setLoading(false))
  }, [classId])

  const onLink = async (googleId: string) => {
    setLinking(true)
    setError(null)
    try {
      const res = await googleClassroomAction(classId, 'link', googleId)
      if (!res.success) throw new Error(res.message)
      onLinked()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Link failed')
    } finally {
      setLinking(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl" role="dialog">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-hub-text">Link Google Classroom</h2>
          <p className="text-sm text-hub-muted">{className}</p>
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-5">
          {loading ? <p className="text-hub-muted">Loading Google classrooms…</p> : null}
          {error ? <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
          {items.length ? (
            <ul className="space-y-2">
              {items.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    disabled={linking}
                    onClick={() => void onLink(c.id)}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left hover:border-teal-400"
                  >
                    <div className="font-semibold text-hub-text">{c.name}</div>
                    {c.section ? <div className="text-xs text-hub-muted">{c.section}</div> : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : !loading && !error ? (
            <p className="text-sm text-hub-muted">No active Google classrooms found.</p>
          ) : null}
        </div>
        <div className="border-t border-slate-100 px-5 py-3 text-right">
          <button type="button" onClick={onClose} className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
