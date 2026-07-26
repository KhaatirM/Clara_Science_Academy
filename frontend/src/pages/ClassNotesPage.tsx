import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useOutletContext, useParams } from 'react-router-dom'
import {
  classNotesItemDownloadUrl,
  createClassNotesFolder,
  deleteClassNotesFolder,
  deleteClassNotesItem,
  fetchClassNotes,
  readVideoDurationSeconds,
  updateClassNotesFolder,
  uploadClassNotesItem,
} from '../api/classNotes'
import { ClassSubpageShell } from '../components/classes/ClassSubpageShell'
import { ClassWorkflowNav } from '../components/classes/ClassWorkflowNav'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { ClassNotesFolder, ClassNotesItem, ClassNotesResponse } from '../types/classNotes'
import type { ManagementOutletContext } from '../types/layout'

type Scope = 'management' | 'teacher' | 'student'

function detectScope(pathname: string): Scope {
  if (pathname.startsWith('/teacher/')) return 'teacher'
  if (pathname.startsWith('/student/')) return 'student'
  return 'management'
}

function backPath(scope: Scope, classId: number) {
  if (scope === 'teacher') return `/teacher/classes/${classId}`
  if (scope === 'student') return `/student/classes/${classId}`
  return `/management/classes/${classId}`
}

function formatBytes(size: number | null | undefined) {
  if (size == null || !Number.isFinite(size)) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds: number | null | undefined) {
  if (seconds == null || !Number.isFinite(seconds)) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function mediaIcon(kind: string) {
  if (kind === 'video') return 'bi-camera-video'
  if (kind === 'image') return 'bi-image'
  return 'bi-file-earmark-text'
}

function isVideoFile(file: File) {
  const name = file.name.toLowerCase()
  return name.endsWith('.mp4') || name.endsWith('.webm') || name.endsWith('.mov') || file.type.startsWith('video/')
}

export function ClassNotesPage() {
  const { classId = '' } = useParams()
  const id = Number(classId)
  const location = useLocation()
  const scope = detectScope(location.pathname)
  const outlet = useOutletContext<ManagementOutletContext | null>()
  const user = outlet?.user
  const isDirector = user?.role_canonical === 'Director'
  const fileRef = useRef<HTMLInputElement>(null)

  const [data, setData] = useState<ClassNotesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [selectedKey, setSelectedKey] = useState<'root' | number>('root')
  const [newUnitName, setNewUnitName] = useState('')
  const [showNewUnit, setShowNewUnit] = useState(false)

  const load = useCallback(async () => {
    if (!Number.isFinite(id) || id <= 0) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassNotes(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load class notes')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const canManage = Boolean(data?.can_manage)
  const maxVideoSeconds = data?.max_video_seconds ?? 600

  const selectedFolder: ClassNotesFolder | null = useMemo(() => {
    if (selectedKey === 'root' || !data) return null
    return data.folders.find((f) => f.id === selectedKey) || null
  }, [data, selectedKey])

  const items: ClassNotesItem[] = useMemo(() => {
    if (!data) return []
    if (selectedKey === 'root') return data.root_items
    return selectedFolder?.items || []
  }, [data, selectedKey, selectedFolder])

  async function onCreateUnit() {
    if (!canManage || !newUnitName.trim()) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = await createClassNotesFolder(id, { name: newUnitName.trim() })
      setData(res)
      setMessage(res.message || 'Unit created.')
      setNewUnitName('')
      setShowNewUnit(false)
      if (res.folders?.length) {
        const newest = res.folders[res.folders.length - 1]
        if (newest) setSelectedKey(newest.id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create unit')
    } finally {
      setBusy(false)
    }
  }

  async function onRenameUnit(folder: ClassNotesFolder) {
    if (!canManage) return
    const name = window.prompt('Rename unit', folder.name)
    if (name == null || !name.trim() || name.trim() === folder.name) return
    setBusy(true)
    setError(null)
    try {
      setData(await updateClassNotesFolder(id, folder.id, { name: name.trim() }))
      setMessage('Unit updated.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update unit')
    } finally {
      setBusy(false)
    }
  }

  async function onDeleteUnit(folder: ClassNotesFolder) {
    if (!canManage) return
    if (!window.confirm(`Remove unit “${folder.name}” and all files inside it?`)) return
    setBusy(true)
    setError(null)
    try {
      setData(await deleteClassNotesFolder(id, folder.id))
      setSelectedKey('root')
      setMessage('Unit removed.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove unit')
    } finally {
      setBusy(false)
    }
  }

  async function onUpload(file: File | null) {
    if (!file || !canManage) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      let durationSeconds: number | undefined
      if (isVideoFile(file)) {
        durationSeconds = await readVideoDurationSeconds(file)
        if (durationSeconds > maxVideoSeconds) {
          throw new Error('Videos must be 10 minutes or shorter.')
        }
      }
      const res = await uploadClassNotesItem(id, file, {
        folderId: selectedKey === 'root' ? null : selectedKey,
        durationSeconds,
      })
      setData(res)
      setMessage(res.message || 'File uploaded.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function onDeleteItem(item: ClassNotesItem) {
    if (!canManage) return
    if (!window.confirm(`Remove “${item.title}”?`)) return
    setBusy(true)
    setError(null)
    try {
      setData(await deleteClassNotesItem(id, item.id))
      setMessage('File removed.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove file')
    } finally {
      setBusy(false)
    }
  }

  const title = data?.class.name || 'Class notes'
  const subtitle = data?.class.subject

  const actions =
    scope === 'management' && Number.isFinite(id) && id > 0 ? (
      <ClassWorkflowNav
        classId={id}
        active="view"
        isDirector={isDirector}
        canAdminUi={Boolean(user?.management_entry)}
      />
    ) : (
      <div className="flex flex-wrap gap-2">
        <Link
          to={backPath(scope, id)}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          Class view
        </Link>
      </div>
    )

  const body = (
    <>
      {loading ? <p className="text-hub-muted">Loading class notes…</p> : null}
      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}
      {message ? (
        <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          {message}
        </div>
      ) : null}

      {data ? (
        <div className="grid gap-4 lg:grid-cols-12">
          <aside className="space-y-3 lg:col-span-4">
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between gap-2 border-b border-teal-100 bg-gradient-to-r from-teal-100/80 to-teal-50/50 px-4 py-3">
                <h2 className="mb-0 text-sm font-bold uppercase tracking-wide text-hub-text">
                  Units &amp; folders
                </h2>
                {canManage ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-full bg-teal-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                    onClick={() => setShowNewUnit((v) => !v)}
                  >
                    <i className="bi bi-folder-plus me-1" aria-hidden />
                    Add unit
                  </button>
                ) : null}
              </div>
              <div className="p-3">
                {showNewUnit ? (
                  <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <label className="mb-1 block text-xs font-semibold text-hub-muted">Unit name</label>
                    <input
                      value={newUnitName}
                      onChange={(e) => setNewUnitName(e.target.value)}
                      className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      placeholder="e.g. Unit 1 — Fractions"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busy || !newUnitName.trim()}
                        className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                        onClick={() => void onCreateUnit()}
                      >
                        Create
                      </button>
                      <button
                        type="button"
                        className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
                        onClick={() => {
                          setShowNewUnit(false)
                          setNewUnitName('')
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : null}

                <button
                  type="button"
                  onClick={() => setSelectedKey('root')}
                  className={`mb-2 flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm font-semibold ${
                    selectedKey === 'root'
                      ? 'border-teal-400 bg-teal-50 text-teal-900'
                      : 'border-slate-200 bg-white text-hub-text hover:border-teal-300'
                  }`}
                >
                  <span>
                    <i className="bi bi-journal-text me-2" aria-hidden />
                    Class notes
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-hub-muted">
                    {data.root_items.length}
                  </span>
                </button>

                {data.folders.length ? (
                  <ul className="mb-0 space-y-2">
                    {data.folders.map((folder) => (
                      <li key={folder.id}>
                        <div
                          className={`rounded-xl border px-3 py-2.5 ${
                            selectedKey === folder.id
                              ? 'border-teal-400 bg-teal-50'
                              : 'border-slate-200 bg-white'
                          }`}
                        >
                          <button
                            type="button"
                            className="flex w-full items-center justify-between text-left text-sm font-semibold text-hub-text"
                            onClick={() => setSelectedKey(folder.id)}
                          >
                            <span className="min-w-0 truncate">
                              <i className="bi bi-folder2-open me-2 text-teal-700" aria-hidden />
                              {folder.name}
                            </span>
                            <span className="ms-2 shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-hub-muted">
                              {folder.item_count}
                            </span>
                          </button>
                          {canManage ? (
                            <div className="mt-2 flex flex-wrap gap-1">
                              <button
                                type="button"
                                className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[0.7rem] font-semibold text-slate-600 hover:border-teal-400"
                                onClick={() => void onRenameUnit(folder)}
                              >
                                Rename
                              </button>
                              <button
                                type="button"
                                className="rounded-full border border-red-100 bg-white px-2 py-0.5 text-[0.7rem] font-semibold text-red-700 hover:bg-red-50"
                                onClick={() => void onDeleteUnit(folder)}
                              >
                                Delete
                              </button>
                            </div>
                          ) : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mb-0 px-1 text-xs text-hub-muted">
                    {canManage
                      ? 'Optional: create units/folders to organize materials.'
                      : 'No units yet. Files may still appear under Class notes.'}
                  </p>
                )}
              </div>
            </section>
          </aside>

          <section className="lg:col-span-8">
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-teal-100 bg-gradient-to-r from-teal-100/80 to-teal-50/50 px-5 py-4">
                <div>
                  <h2 className="mb-0 text-lg font-bold text-slate-900">
                    {selectedFolder ? selectedFolder.name : 'Class notes'}
                  </h2>
                  <p className="mb-0 mt-1 text-sm text-hub-muted">
                    {selectedFolder?.description ||
                      (selectedFolder
                        ? 'Materials for this unit'
                        : 'General class materials (not inside a unit)')}
                  </p>
                </div>
                {canManage ? (
                  <div>
                    <input
                      ref={fileRef}
                      type="file"
                      className="hidden"
                      accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.gif,.webp,.mp4,.webm,.mov"
                      onChange={(e) => void onUpload(e.target.files?.[0] || null)}
                    />
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                      onClick={() => fileRef.current?.click()}
                    >
                      <i className="bi bi-cloud-upload me-1" aria-hidden />
                      {busy ? 'Working…' : 'Upload'}
                    </button>
                  </div>
                ) : null}
              </div>

              <div className="p-5">
                {canManage ? (
                  <p className="mb-4 text-xs text-hub-muted">
                    Documents, slides, images, and videos up to 10 minutes. Uploads go into the
                    selected unit (or Class notes if none is selected).
                  </p>
                ) : null}

                {items.length ? (
                  <ul className="mb-0 space-y-2">
                    {items.map((item) => (
                      <li
                        key={item.id}
                        className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
                      >
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
                          <i className={`bi ${mediaIcon(item.media_kind)}`} aria-hidden />
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-semibold text-hub-text">{item.title}</div>
                          <div className="text-xs text-hub-muted">
                            {item.original_filename}
                            {item.file_size != null ? ` · ${formatBytes(item.file_size)}` : ''}
                            {item.media_kind === 'video' && item.duration_seconds != null
                              ? ` · ${formatDuration(item.duration_seconds)}`
                              : ''}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {item.media_kind === 'video' ? (
                            <a
                              href={classNotesItemDownloadUrl(id, item.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
                            >
                              Open
                            </a>
                          ) : null}
                          <a
                            href={classNotesItemDownloadUrl(id, item.id)}
                            className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                            download={item.media_kind !== 'video' ? undefined : undefined}
                          >
                            Download
                          </a>
                          {canManage ? (
                            <button
                              type="button"
                              disabled={busy}
                              className="rounded-full border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                              onClick={() => void onDeleteItem(item)}
                            >
                              Remove
                            </button>
                          ) : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-300 px-5 py-12 text-center">
                    <i className="bi bi-folder mb-3 block text-3xl text-slate-400" aria-hidden />
                    <p className="mb-1 text-base font-semibold text-slate-800">No files here yet</p>
                    <p className="mb-0 text-sm text-hub-muted">
                      {canManage
                        ? 'Upload a document, slide deck, or short video to get started.'
                        : 'Your teacher has not added materials to this section yet.'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </>
  )

  if (scope === 'management') {
    return (
      <ClassSubpageShell eyebrow="Class notes" title={title} subtitle={subtitle} actions={actions}>
        {body}
      </ClassSubpageShell>
    )
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell space-y-4 px-1 pb-8 md:px-2">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-hub-muted">Class notes</p>
              <h1 className="mb-0 text-2xl font-bold text-slate-900">{title}</h1>
              {subtitle ? <p className="mb-0 mt-1 text-sm text-hub-muted">{subtitle}</p> : null}
            </div>
            {actions}
          </div>
          {body}
        </div>
      </div>
    </ManagementPageShell>
  )
}
