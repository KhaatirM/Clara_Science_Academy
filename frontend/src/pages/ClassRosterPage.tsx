import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchClassRoster, mutateRoster } from '../api/classes'
import { ClassSubpageShell } from '../components/classes/ClassSubpageShell'
import type { ClassRosterResponse } from '../types/classDetail'

export function ClassRosterPage() {
  const { classId } = useParams()
  const id = Number(classId)
  const [data, setData] = useState<ClassRosterResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [selectedAvailable, setSelectedAvailable] = useState<number[]>([])
  const [selectedEnrolled, setSelectedEnrolled] = useState<number[]>([])

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassRoster(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load roster')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const filterStudents = (name: string) => name.toLowerCase().includes(search.trim().toLowerCase())

  const available = useMemo(
    () => (data?.available_students || []).filter((s) => filterStudents(s.display_name)),
    [data, search],
  )
  const enrolled = useMemo(
    () => (data?.enrolled_students || []).filter((s) => filterStudents(s.display_name)),
    [data, search],
  )

  const toggle = (list: number[], setList: (v: number[]) => void, sid: number) => {
    setList(list.includes(sid) ? list.filter((x) => x !== sid) : [...list, sid])
  }

  const runAction = async (action: 'add' | 'remove', ids: number[]) => {
    if (!id || !ids.length) return
    setBusy(true)
    setMessage(null)
    setError(null)
    try {
      const res = await mutateRoster(id, action, ids)
      setMessage(res.message)
      setSelectedAvailable([])
      setSelectedEnrolled([])
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Roster update failed')
    } finally {
      setBusy(false)
    }
  }

  if (!id) return null

  return (
    <ClassSubpageShell
      eyebrow="Class roster"
      title={data?.class.name || 'Roster'}
      subtitle="Add or remove student enrollments."
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {message ? <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{message}</div> : null}
      <div className="mb-4">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search students…"
          className="w-full max-w-md rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-bold text-hub-text">Available ({available.length})</h2>
            <button
              type="button"
              disabled={busy || !selectedAvailable.length}
              onClick={() => void runAction('add', selectedAvailable)}
              className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              Add selected
            </button>
          </div>
          <ul className="max-h-96 space-y-1 overflow-y-auto">
            {available.map((s) => (
              <li key={s.id}>
                <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={selectedAvailable.includes(s.id)}
                    onChange={() => toggle(selectedAvailable, setSelectedAvailable, s.id)}
                  />
                  <span className="text-sm font-medium text-hub-text">{s.display_name}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-bold text-hub-text">Enrolled ({enrolled.length})</h2>
            <button
              type="button"
              disabled={busy || !selectedEnrolled.length}
              onClick={() => void runAction('remove', selectedEnrolled)}
              className="rounded-full border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-800 disabled:opacity-50"
            >
              Remove selected
            </button>
          </div>
          <ul className="max-h-96 space-y-1 overflow-y-auto">
            {enrolled.map((s) => (
              <li key={s.id}>
                <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={selectedEnrolled.includes(s.id)}
                    onChange={() => toggle(selectedEnrolled, setSelectedEnrolled, s.id)}
                  />
                  <span className="text-sm font-medium text-hub-text">{s.display_name}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </ClassSubpageShell>
  )
}
