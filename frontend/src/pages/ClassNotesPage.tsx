import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useOutletContext, useParams } from 'react-router-dom'
import {
  classNotesItemDownloadUrl,
  createClassNotesFolder,
  deleteClassNotesFolder,
  deleteClassNotesItem,
  fetchClassNotes,
  fetchClassNotesFolderItems,
  linkClassNotesDriveFolder,
  readVideoDurationSeconds,
  syncClassNotesDriveLink,
  unlinkClassNotesDriveFolder,
  updateClassNotesFolder,
  uploadClassNotesItemsBulk,
} from '../api/classNotes'
import { ClassSubpageShell } from '../components/classes/ClassSubpageShell'
import { ClassWorkflowNav } from '../components/classes/ClassWorkflowNav'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type {
  ClassNotesDriveLink,
  ClassNotesFolder,
  ClassNotesItem,
  ClassNotesResponse,
} from '../types/classNotes'
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

function findFolder(nodes: ClassNotesFolder[], id: number): ClassNotesFolder | null {
  for (const node of nodes) {
    if (node.id === id) return node
    const kids = node.children || []
    const found = findFolder(kids, id)
    if (found) return found
  }
  return null
}

function folderBreadcrumb(
  flat: ClassNotesFolder[],
  folderId: number,
): ClassNotesFolder[] {
  const byId = new Map(flat.map((f) => [f.id, f]))
  const chain: ClassNotesFolder[] = []
  let cur: ClassNotesFolder | undefined = byId.get(folderId)
  const seen = new Set<number>()
  while (cur && !seen.has(cur.id)) {
    seen.add(cur.id)
    chain.unshift(cur)
    cur = cur.parent_id != null ? byId.get(cur.parent_id) : undefined
  }
  return chain
}

function formatSyncedAt(value: string | null) {
  if (!value) return 'not synced yet'
  const when = new Date(value.endsWith('Z') ? value : `${value}Z`)
  if (Number.isNaN(when.getTime())) return 'not synced yet'
  const minutes = Math.round((Date.now() - when.getTime()) / 60000)
  if (minutes < 1) return 'synced just now'
  if (minutes < 60) return `synced ${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `synced ${hours} hr ago`
  return `synced ${when.toLocaleDateString()}`
}

function DrivePanel({
  links,
  busy,
  scope,
  onLink,
  onSync,
  onUnlink,
}: {
  links: ClassNotesDriveLink[]
  busy: boolean
  scope: Scope
  onLink: (url: string) => void
  onSync: (link: ClassNotesDriveLink) => void
  onUnlink: (link: ClassNotesDriveLink) => void
}) {
  const [url, setUrl] = useState('')
  const connectHref =
    scope === 'management' ? '/management/google-account/connect' : '/teacher/google-account/connect'

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-blue-100 bg-gradient-to-r from-blue-100/80 to-blue-50/50 px-4 py-3">
        <h2 className="mb-0 text-sm font-bold uppercase tracking-wide text-hub-text">
          <i className="bi bi-google me-2 text-blue-700" aria-hidden />
          Google Drive
        </h2>
      </div>
      <div className="space-y-3 p-3">
        {links.map((link) => (
          <div key={link.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="truncate text-sm font-semibold text-hub-text">
              {link.drive_folder_name}
            </div>
            <div className="mt-0.5 text-xs text-hub-muted">
              {link.item_count} file{link.item_count === 1 ? '' : 's'} · {formatSyncedAt(link.last_synced_at)}
              {link.is_stale && !link.needs_reauth ? (
                <span className="ms-1 font-semibold text-amber-700">· update available</span>
              ) : null}
            </div>
            {link.needs_reauth ? (
              <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                Google access expired for this folder.{' '}
                <a className="font-semibold underline" href={connectHref}>
                  Reconnect Google account
                </a>
              </div>
            ) : link.last_error ? (
              <div className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
                {link.last_error}
              </div>
            ) : null}
            <div className="mt-2 flex flex-wrap gap-1.5">
              <button
                type="button"
                disabled={busy}
                className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:border-teal-500 disabled:opacity-60"
                onClick={() => onSync(link)}
              >
                Sync now
              </button>
              {link.drive_web_view_link ? (
                <a
                  href={link.drive_web_view_link}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:border-teal-500"
                >
                  Open in Drive
                </a>
              ) : null}
              <button
                type="button"
                disabled={busy}
                className="rounded-full border border-red-200 bg-white px-3 py-1 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                onClick={() => onUnlink(link)}
              >
                Unlink
              </button>
            </div>
          </div>
        ))}

        <div className="rounded-xl border border-dashed border-slate-300 p-3">
          <label className="mb-1 block text-xs font-semibold text-hub-muted">
            Link a shared Drive folder
          </label>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="https://drive.google.com/drive/folders/…"
          />
          <button
            type="button"
            disabled={busy || !url.trim()}
            className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
            onClick={() => {
              onLink(url.trim())
              setUrl('')
            }}
          >
            Link folder
          </button>
          <p className="mb-0 mt-2 text-xs text-hub-muted">
            Uses the Google account connected in Settings (signing in with Google alone is not
            enough). Files stay in Drive; students see and download them here.
          </p>
        </div>
      </div>
    </section>
  )
}

function FolderTreeNode({
  folder,
  depth,
  selectedKey,
  canManage,
  maxDepth,
  expanded,
  onToggle,
  onSelect,
  onRename,
  onDelete,
  onAddChild,
}: {
  folder: ClassNotesFolder
  depth: number
  selectedKey: 'root' | number
  canManage: boolean
  maxDepth: number
  expanded: Set<number>
  onToggle: (id: number) => void
  onSelect: (id: number) => void
  onRename: (folder: ClassNotesFolder) => void
  onDelete: (folder: ClassNotesFolder) => void
  onAddChild: (folder: ClassNotesFolder) => void
}) {
  const kids = folder.children || []
  const isOpen = expanded.has(folder.id)
  const selected = selectedKey === folder.id
  const canNest = (folder.depth ?? depth) < maxDepth

  return (
    <li>
      <div
        className={`rounded-xl border px-2 py-2 ${
          selected ? 'border-teal-400 bg-teal-50' : 'border-slate-200 bg-white'
        }`}
        style={{ marginLeft: Math.max(0, depth - 1) * 12 }}
      >
        <div className="flex items-center gap-1">
          {kids.length > 0 ? (
            <button
              type="button"
              className="rounded p-1 text-slate-500 hover:bg-slate-100"
              onClick={() => onToggle(folder.id)}
              aria-label={isOpen ? 'Collapse' : 'Expand'}
            >
              <i className={`bi ${isOpen ? 'bi-caret-down-fill' : 'bi-caret-right-fill'}`} aria-hidden />
            </button>
          ) : (
            <span className="inline-block w-6" />
          )}
          <button
            type="button"
            className="min-w-0 flex-1 truncate text-left text-sm font-semibold text-hub-text"
            onClick={() => onSelect(folder.id)}
          >
            <i
              className={`bi ${folder.is_drive_folder ? 'bi-google text-blue-700' : 'bi-folder2-open text-teal-700'} me-1`}
              aria-hidden
            />
            {folder.name}
          </button>
          <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-hub-muted">
            {folder.item_count}
          </span>
        </div>
        {canManage && !folder.is_drive_folder ? (
          <div className="mt-1.5 flex flex-wrap gap-1 ps-6">
            {canNest ? (
              <button
                type="button"
                className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[0.7rem] font-semibold text-slate-600 hover:border-teal-400"
                onClick={() => onAddChild(folder)}
              >
                Subfolder
              </button>
            ) : null}
            <button
              type="button"
              className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[0.7rem] font-semibold text-slate-600 hover:border-teal-400"
              onClick={() => onRename(folder)}
            >
              Rename
            </button>
            <button
              type="button"
              className="rounded-full border border-red-100 bg-white px-2 py-0.5 text-[0.7rem] font-semibold text-red-700 hover:bg-red-50"
              onClick={() => onDelete(folder)}
            >
              Delete
            </button>
          </div>
        ) : null}
      </div>
      {kids.length > 0 && isOpen ? (
        <ul className="mb-0 mt-1 space-y-1">
          {kids.map((child) => (
            <FolderTreeNode
              key={child.id}
              folder={child}
              depth={depth + 1}
              selectedKey={selectedKey}
              canManage={canManage}
              maxDepth={maxDepth}
              expanded={expanded}
              onToggle={onToggle}
              onSelect={onSelect}
              onRename={onRename}
              onDelete={onDelete}
              onAddChild={onAddChild}
            />
          ))}
        </ul>
      ) : null}
    </li>
  )
}

function folderCacheKey(key: 'root' | number): string {
  return key === 'root' ? 'root' : String(key)
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
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderParentId, setNewFolderParentId] = useState<number | null>(null)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [dragOver, setDragOver] = useState(false)
  const [itemCache, setItemCache] = useState<Record<string, ClassNotesItem[]>>({})
  const [loadingFolderItems, setLoadingFolderItems] = useState(false)

  const loadFolderItems = useCallback(
    async (folderKey: 'root' | number) => {
      if (!Number.isFinite(id) || id <= 0) return
      const cacheKey = folderCacheKey(folderKey)
      setLoadingFolderItems(true)
      setError(null)
      try {
        const res = await fetchClassNotesFolderItems(id, folderKey)
        setItemCache((prev) => ({ ...prev, [cacheKey]: res.items || [] }))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load folder files')
      } finally {
        setLoadingFolderItems(false)
      }
    },
    [id],
  )

  const applyNotesResponse = useCallback(
    (res: ClassNotesResponse) => {
      setData(res)
      setItemCache({})
      void loadFolderItems(selectedKey)
    },
    [loadFolderItems, selectedKey],
  )

  const load = useCallback(async () => {
    if (!Number.isFinite(id) || id <= 0) return
    setLoading(true)
    setError(null)
    try {
      const next = await fetchClassNotes(id)
      setData(next)
      setItemCache({})
      void loadFolderItems('root')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load class notes')
    } finally {
      setLoading(false)
    }
  }, [id, loadFolderItems])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!data || loading) return
    const cacheKey = folderCacheKey(selectedKey)
    if (itemCache[cacheKey]) return
    if (selectedKey === 'root') return
    const folder = findFolder(data.folders, selectedKey)
    if ((folder?.item_count ?? 0) <= 0) return
    void loadFolderItems(selectedKey)
  }, [data, itemCache, loadFolderItems, loading, selectedKey])

  const canManage = Boolean(data?.can_manage)
  const maxVideoSeconds = data?.max_video_seconds ?? 600
  const maxDepth = data?.max_folder_depth ?? 3
  const flatFolders = data?.folders_flat || []

  const selectedFolder: ClassNotesFolder | null = useMemo(() => {
    if (selectedKey === 'root' || !data) return null
    return findFolder(data.folders, selectedKey)
  }, [data, selectedKey])

  const crumbs = useMemo(() => {
    if (selectedKey === 'root' || !flatFolders.length) return []
    return folderBreadcrumb(flatFolders, selectedKey)
  }, [flatFolders, selectedKey])

  const items: ClassNotesItem[] = useMemo(() => {
    if (!data) return []
    return itemCache[folderCacheKey(selectedKey)] ?? (selectedKey === 'root' ? data.root_items : [])
  }, [data, itemCache, selectedKey])

  function openNewFolder(parentId: number | null) {
    setNewFolderParentId(parentId)
    setNewFolderName('')
    setShowNewFolder(true)
  }

  async function onCreateFolder() {
    if (!canManage || !newFolderName.trim()) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = await createClassNotesFolder(id, {
        name: newFolderName.trim(),
        parent_id: newFolderParentId,
      })
      applyNotesResponse(res)
      setMessage(res.message || 'Folder created.')
      setNewFolderName('')
      setShowNewFolder(false)
      if (newFolderParentId != null) {
        setExpanded((prev) => new Set(prev).add(newFolderParentId))
      }
      const flat = res.folders_flat || []
      const newest = [...flat].reverse().find((f) => f.name === newFolderName.trim())
      if (newest) setSelectedKey(newest.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create folder')
    } finally {
      setBusy(false)
    }
  }

  async function onRenameFolder(folder: ClassNotesFolder) {
    if (!canManage) return
    const name = window.prompt('Rename folder', folder.name)
    if (name == null || !name.trim() || name.trim() === folder.name) return
    setBusy(true)
    setError(null)
    try {
      applyNotesResponse(await updateClassNotesFolder(id, folder.id, { name: name.trim() }))
      setMessage('Folder updated.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update folder')
    } finally {
      setBusy(false)
    }
  }

  async function onDeleteFolder(folder: ClassNotesFolder) {
    if (!canManage) return
    if (
      !window.confirm(
        `Remove “${folder.name}” and all subfolders and files inside it?`,
      )
    ) {
      return
    }
    setBusy(true)
    setError(null)
    try {
      applyNotesResponse(await deleteClassNotesFolder(id, folder.id))
      setSelectedKey('root')
      setMessage('Folder removed.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove folder')
    } finally {
      setBusy(false)
    }
  }

  async function onUploadMany(fileList: FileList | File[] | null) {
    if (!fileList || !canManage) return
    const files = Array.from(fileList)
    if (!files.length) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      for (const file of files) {
        if (isVideoFile(file)) {
          const durationSeconds = await readVideoDurationSeconds(file)
          if (durationSeconds > maxVideoSeconds) {
            throw new Error(`“${file.name}” is longer than 10 minutes.`)
          }
        }
      }
      const res = await uploadClassNotesItemsBulk(id, files, {
        folderId: selectedKey === 'root' ? null : selectedKey,
      })
      applyNotesResponse(res)
      const failed = (res.results || []).filter((r) => !r.ok)
      if (failed.length) {
        setError(
          failed.map((f) => `${f.filename || 'file'}: ${f.error || 'failed'}`).join(' · '),
        )
      }
      setMessage(res.message || 'Upload finished.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
      setDragOver(false)
    }
  }

  async function onLinkDrive(folderUrl: string) {
    if (!canManage || !folderUrl) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = await linkClassNotesDriveFolder(id, {
        folder_url: folderUrl,
        folder_id: selectedKey === 'root' ? null : selectedKey,
      })
      applyNotesResponse(res)
      setMessage(res.message || 'Drive folder linked.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not link that Drive folder')
    } finally {
      setBusy(false)
    }
  }

  async function onSyncDrive(link: ClassNotesDriveLink) {
    if (!canManage) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = await syncClassNotesDriveLink(id, link.id)
      applyNotesResponse(res)
      setMessage(res.message || 'Drive folder synced.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sync that Drive folder')
    } finally {
      setBusy(false)
    }
  }

  async function onUnlinkDrive(link: ClassNotesDriveLink) {
    if (!canManage) return
    if (
      !window.confirm(
        `Unlink “${link.drive_folder_name}”? The files stay in Google Drive but disappear from class notes.`,
      )
    ) {
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await unlinkClassNotesDriveFolder(id, link.id)
      applyNotesResponse(res)
      setSelectedKey('root')
      setMessage(res.message || 'Drive folder unlinked.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not unlink that Drive folder')
    } finally {
      setBusy(false)
    }
  }

  async function onDeleteItem(item: ClassNotesItem) {
    if (!canManage) return
    if (!window.confirm(`Remove “${item.title}”?`)) return
    setBusy(true)
    setError(null)
    try {
      applyNotesResponse(await deleteClassNotesItem(id, item.id))
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

  const driveLinks = data?.drive_links || []
  const needsReauth = canManage && driveLinks.some((link) => link.needs_reauth)
  const staleDriveLinks = canManage && driveLinks.some((link) => link.is_stale && !link.needs_reauth)
  const googleConnectHref =
    scope === 'management' ? '/management/google-account/connect' : '/teacher/google-account/connect'

  const body = (
    <>
      {loading ? <p className="text-hub-muted">Loading class notes…</p> : null}
      {needsReauth ? (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Google access for a linked Drive folder has expired, so its files are not refreshing.{' '}
          <a className="font-semibold underline" href={googleConnectHref}>
            Reconnect your Google account
          </a>
          .
        </div>
      ) : staleDriveLinks ? (
        <div className="mb-4 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
          One or more linked Drive folders are out of date. Use <strong>Sync now</strong> in the Google Drive
          panel to refresh files without slowing down the page.
        </div>
      ) : null}
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
                  Folders
                </h2>
                {canManage ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-full bg-teal-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                    onClick={() => openNewFolder(null)}
                  >
                    <i className="bi bi-folder-plus me-1" aria-hidden />
                    Add folder
                  </button>
                ) : null}
              </div>
              <div className="p-3">
                {showNewFolder ? (
                  <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <label className="mb-1 block text-xs font-semibold text-hub-muted">
                      {newFolderParentId == null ? 'New folder (top level)' : 'New subfolder'}
                    </label>
                    <input
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      placeholder="e.g. Unit 1, Lesson 1, Homework"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busy || !newFolderName.trim()}
                        className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                        onClick={() => void onCreateFolder()}
                      >
                        Create
                      </button>
                      <button
                        type="button"
                        className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
                        onClick={() => {
                          setShowNewFolder(false)
                          setNewFolderName('')
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
                    {itemCache.root?.length ?? data.root_item_count ?? data.root_items.length}
                  </span>
                </button>

                {data.folders.length ? (
                  <ul className="mb-0 space-y-1">
                    {data.folders.map((folder) => (
                      <FolderTreeNode
                        key={folder.id}
                        folder={folder}
                        depth={1}
                        selectedKey={selectedKey}
                        canManage={canManage}
                        maxDepth={maxDepth}
                        expanded={expanded}
                        onToggle={(fid) =>
                          setExpanded((prev) => {
                            const next = new Set(prev)
                            if (next.has(fid)) next.delete(fid)
                            else next.add(fid)
                            return next
                          })
                        }
                        onSelect={setSelectedKey}
                        onRename={(f) => void onRenameFolder(f)}
                        onDelete={(f) => void onDeleteFolder(f)}
                        onAddChild={(f) => openNewFolder(f.id)}
                      />
                    ))}
                  </ul>
                ) : (
                  <p className="mb-0 px-1 text-xs text-hub-muted">
                    {canManage
                      ? 'Create folders like Unit → Lesson → Homework / Slides (up to 3 levels).'
                      : 'No folders yet. Files may still appear under Class notes.'}
                  </p>
                )}
              </div>
            </section>

            {canManage ? (
              <DrivePanel
                links={driveLinks}
                busy={busy}
                scope={scope}
                onLink={(url) => void onLinkDrive(url)}
                onSync={(link) => void onSyncDrive(link)}
                onUnlink={(link) => void onUnlinkDrive(link)}
              />
            ) : null}
          </aside>

          <section className="lg:col-span-8">
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-teal-100 bg-gradient-to-r from-teal-100/80 to-teal-50/50 px-5 py-4">
                <div className="min-w-0">
                  {crumbs.length > 0 ? (
                    <nav className="mb-1 flex flex-wrap items-center gap-1 text-xs text-hub-muted">
                      <button
                        type="button"
                        className="hover:text-teal-800"
                        onClick={() => setSelectedKey('root')}
                      >
                        Class notes
                      </button>
                      {crumbs.map((c) => (
                        <span key={c.id} className="inline-flex items-center gap-1">
                          <i className="bi bi-chevron-right text-[0.65rem]" aria-hidden />
                          <button
                            type="button"
                            className="hover:text-teal-800"
                            onClick={() => setSelectedKey(c.id)}
                          >
                            {c.name}
                          </button>
                        </span>
                      ))}
                    </nav>
                  ) : null}
                  <h2 className="mb-0 text-lg font-bold text-slate-900">
                    {selectedFolder ? selectedFolder.name : 'Class notes'}
                  </h2>
                  <p className="mb-0 mt-1 text-sm text-hub-muted">
                    {selectedFolder?.description ||
                      (selectedFolder
                        ? 'Materials in this folder'
                        : 'General class materials (not inside a folder)')}
                  </p>
                </div>
                {canManage ? (
                  <div>
                    <input
                      ref={fileRef}
                      type="file"
                      multiple
                      className="hidden"
                      accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.gif,.webp,.mp4,.webm,.mov"
                      onChange={(e) => void onUploadMany(e.target.files)}
                    />
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                      onClick={() => fileRef.current?.click()}
                    >
                      <i className="bi bi-cloud-upload me-1" aria-hidden />
                      {busy ? 'Working…' : 'Upload files'}
                    </button>
                  </div>
                ) : null}
              </div>

              <div
                className={`p-5 ${dragOver ? 'bg-teal-50/80' : ''}`}
                onDragEnter={(e) => {
                  if (!canManage) return
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragOver={(e) => {
                  if (!canManage) return
                  e.preventDefault()
                  e.dataTransfer.dropEffect = 'copy'
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  if (!canManage) return
                  e.preventDefault()
                  void onUploadMany(e.dataTransfer.files)
                }}
              >
                {canManage ? (
                  <p className="mb-4 text-xs text-hub-muted">
                    Drop multiple files here or use Upload. Nest folders up to {maxDepth} levels
                    (Unit → Lesson → Homework / Slides). Videos max 10 minutes.
                  </p>
                ) : null}

                {loadingFolderItems ? (
                  <p className="text-sm text-hub-muted">Loading files…</p>
                ) : items.length ? (
                  <ul className="mb-0 space-y-2">
                    {items.map((item) => {
                      const fromDrive = item.source === 'drive'
                      const downloadUrl = item.download_url || classNotesItemDownloadUrl(id, item.id)
                      return (
                        <li
                          key={`${item.source || 'upload'}-${item.id}`}
                          className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
                        >
                          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
                            <i className={`bi ${mediaIcon(item.media_kind)}`} aria-hidden />
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="truncate text-sm font-semibold text-hub-text">
                                {item.title}
                              </span>
                              {fromDrive ? (
                                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-blue-800">
                                  Drive
                                </span>
                              ) : null}
                            </div>
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
                                href={downloadUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
                              >
                                Open
                              </a>
                            ) : null}
                            <a
                              href={downloadUrl}
                              className="rounded-full bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                            >
                              Download
                            </a>
                            {fromDrive && canManage && item.web_view_link ? (
                              <a
                                href={item.web_view_link}
                                target="_blank"
                                rel="noreferrer"
                                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
                              >
                                Open in Drive
                              </a>
                            ) : null}
                            {canManage && !fromDrive ? (
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
                      )
                    })}
                  </ul>
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-300 px-5 py-12 text-center">
                    <i className="bi bi-folder mb-3 block text-3xl text-slate-400" aria-hidden />
                    <p className="mb-1 text-base font-semibold text-slate-800">No files here yet</p>
                    <p className="mb-0 text-sm text-hub-muted">
                      {canManage
                        ? 'Upload one or more documents, slide decks, or short videos.'
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
