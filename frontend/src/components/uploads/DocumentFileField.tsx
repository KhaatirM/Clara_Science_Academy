import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  browseDrive,
  downloadDriveFileAsBrowserFile,
  fetchDriveStatus,
  type DriveEntry,
  type DriveStatus,
} from '../../api/drive'

export type DocumentFileFieldProps = {
  /** Controlled selected files (caller owns submit/FormData). */
  files?: File[]
  onChange?: (files: File[]) => void
  /** When set (uncontrolled), syncs a named file input for native form posts. */
  name?: string
  accept?: string
  multiple?: boolean
  disabled?: boolean
  label?: string
  helpText?: string
  className?: string
  /** Prefer teacher Google connect URL when status is fetched. */
  driveScope?: 'teacher' | 'management'
  /** Hide local file button (Drive only) — rare. */
  allowLocal?: boolean
  allowDrive?: boolean
}

function formatBytes(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function extensionOf(name: string) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

function acceptMatches(fileName: string, mime: string, accept?: string) {
  if (!accept || accept.trim() === '*' || accept.includes('*/*')) return true
  const tokens = accept.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean)
  if (!tokens.length) return true
  const ext = extensionOf(fileName)
  const mimeLower = (mime || '').toLowerCase()
  return tokens.some((token) => {
    if (token.startsWith('.')) return ext === token
    if (token.endsWith('/*')) return mimeLower.startsWith(token.slice(0, -1))
    if (token.includes('/')) return mimeLower === token
    return ext === `.${token.replace(/^\./, '')}`
  })
}

export function DocumentFileField({
  files: controlledFiles,
  onChange,
  name,
  accept,
  multiple = false,
  disabled = false,
  label,
  helpText,
  className = '',
  driveScope,
  allowLocal = true,
  allowDrive = true,
}: DocumentFileFieldProps) {
  const inputId = useId()
  const localInputRef = useRef<HTMLInputElement>(null)
  const hiddenFormInputRef = useRef<HTMLInputElement>(null)
  const [internalFiles, setInternalFiles] = useState<File[]>([])
  const [driveOpen, setDriveOpen] = useState(false)

  const isControlled = controlledFiles !== undefined
  const files = isControlled ? controlledFiles! : internalFiles

  const setFiles = (next: File[]) => {
    if (!isControlled) setInternalFiles(next)
    onChange?.(next)
  }

  useEffect(() => {
    if (!name || !hiddenFormInputRef.current) return
    const dt = new DataTransfer()
    for (const f of files) dt.items.add(f)
    hiddenFormInputRef.current.files = dt.files
  }, [files, name])

  const addFiles = (incoming: FileList | File[] | null) => {
    if (!incoming) return
    const list = Array.from(incoming)
    const filtered = list.filter((f) => acceptMatches(f.name, f.type, accept))
    if (!filtered.length) return
    setFiles(multiple ? [...files, ...filtered] : filtered.slice(0, 1))
  }

  const removeAt = (idx: number) => {
    setFiles(files.filter((_, i) => i !== idx))
  }

  return (
    <div className={className}>
      {label ? (
        <label htmlFor={inputId} className="mb-1 block text-sm font-semibold text-hub-text">
          {label}
        </label>
      ) : null}
      {helpText ? <p className="mb-2 text-xs text-hub-muted">{helpText}</p> : null}

      {name ? (
        <input
          ref={hiddenFormInputRef}
          type="file"
          name={name}
          multiple={multiple}
          className="hidden"
          accept={accept}
          tabIndex={-1}
          aria-hidden
        />
      ) : null}

      <input
        id={inputId}
        ref={localInputRef}
        type="file"
        className="hidden"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={(e) => {
          addFiles(e.target.files)
          e.target.value = ''
        }}
      />

      <div className="flex flex-wrap gap-2">
        {allowLocal ? (
          <button
            type="button"
            disabled={disabled}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
            onClick={() => localInputRef.current?.click()}
          >
            <i className="bi bi-upload" aria-hidden />
            From computer
          </button>
        ) : null}
        {allowDrive ? (
          <button
            type="button"
            disabled={disabled}
            className="inline-flex items-center gap-1.5 rounded-xl border border-teal-600 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-900 shadow-sm hover:bg-teal-100 disabled:opacity-50"
            onClick={() => setDriveOpen(true)}
          >
            <i className="bi bi-google" aria-hidden />
            From Google Drive
          </button>
        ) : null}
      </div>

      {files.length > 0 ? (
        <ul className="mt-2 space-y-1">
          {files.map((f, idx) => (
            <li
              key={`${f.name}-${f.size}-${idx}`}
              className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-sm"
            >
              <span className="min-w-0 truncate font-medium text-hub-text">
                <i className="bi bi-file-earmark me-1.5 text-hub-muted" aria-hidden />
                {f.name}
                <span className="ms-2 text-xs text-hub-muted">{formatBytes(f.size)}</span>
              </span>
              {!disabled ? (
                <button
                  type="button"
                  className="shrink-0 text-xs font-semibold text-red-700 hover:underline"
                  onClick={() => removeAt(idx)}
                >
                  Remove
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {driveOpen ? (
        <DrivePickerModal
          accept={accept}
          multiple={multiple}
          driveScope={driveScope}
          onClose={() => setDriveOpen(false)}
          onPick={(picked) => {
            addFiles(picked)
            setDriveOpen(false)
          }}
        />
      ) : null}
    </div>
  )
}

function DrivePickerModal({
  accept,
  multiple,
  driveScope,
  onClose,
  onPick,
}: {
  accept?: string
  multiple: boolean
  driveScope?: 'teacher' | 'management'
  onClose: () => void
  onPick: (files: File[]) => void
}) {
  const [status, setStatus] = useState<DriveStatus | null>(null)
  const [folderId, setFolderId] = useState('root')
  const [folderName, setFolderName] = useState('My Drive')
  const [parentId, setParentId] = useState<string | null>(null)
  const [folders, setFolders] = useState<DriveEntry[]>([])
  const [driveFiles, setDriveFiles] = useState<DriveEntry[]>([])
  const [selected, setSelected] = useState<Record<string, DriveEntry>>({})
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const s = await fetchDriveStatus(driveScope)
        if (cancelled) return
        setStatus(s)
        if (!s.connected) {
          setLoading(false)
          return
        }
        setLoading(true)
        const browse = await browseDrive(folderId)
        if (cancelled) return
        setFolderName(browse.folder_name)
        setParentId(browse.parent_id)
        setFolders(browse.folders)
        setDriveFiles(browse.files)
        setError(null)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Could not open Drive')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [driveScope, folderId])

  const toggleFile = (entry: DriveEntry) => {
    if (!acceptMatches(entry.name, entry.mime_type, accept)) {
      setError(`“${entry.name}” is not an allowed file type for this field.`)
      return
    }
    setError(null)
    setSelected((prev) => {
      if (!multiple) return { [entry.id]: entry }
      const next = { ...prev }
      if (next[entry.id]) delete next[entry.id]
      else next[entry.id] = entry
      return next
    })
  }

  const confirm = async () => {
    const entries = Object.values(selected)
    if (!entries.length) return
    setImporting(true)
    setError(null)
    try {
      const files: File[] = []
      for (const entry of entries) {
        files.push(await downloadDriveFileAsBrowserFile(entry.id, entry.name))
      }
      onPick(multiple ? files : files.slice(0, 1))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not import from Drive')
    } finally {
      setImporting(false)
    }
  }

  const selectedCount = Object.keys(selected).length

  return (
    <div
      className="fixed inset-0 z-[1200] flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Pick from Google Drive"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <h3 className="mb-0 text-base font-bold text-hub-text">Google Drive</h3>
            <p className="mb-0 text-xs text-hub-muted">{folderName}</p>
          </div>
          <button type="button" className="text-hub-muted hover:text-hub-text" onClick={onClose} aria-label="Close">
            <i className="bi bi-x-lg" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          {status && !status.connected ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-950">
              <p className="mb-2">{status.message}</p>
              <div className="flex flex-wrap gap-2">
                <a
                  href={status.connect_url}
                  className="inline-flex rounded-lg bg-teal-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal-800"
                >
                  Connect Google account
                </a>
                <Link to={status.settings_path} className="inline-flex rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700">
                  Open Settings
                </Link>
              </div>
            </div>
          ) : (
            <>
              <div className="mb-2 flex items-center gap-2">
                {folderId !== 'root' ? (
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    onClick={() => setFolderId(parentId || 'root')}
                    disabled={loading}
                  >
                    <i className="bi bi-arrow-left me-1" />
                    Up
                  </button>
                ) : null}
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  onClick={() => setFolderId('root')}
                  disabled={loading || folderId === 'root'}
                >
                  My Drive
                </button>
              </div>

              {loading ? (
                <p className="text-sm text-hub-muted">Loading…</p>
              ) : (
                <ul className="space-y-1">
                  {folders.map((f) => (
                    <li key={f.id}>
                      <button
                        type="button"
                        className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm hover:bg-slate-100"
                        onClick={() => setFolderId(f.id)}
                      >
                        <i className="bi bi-folder-fill text-amber-500" aria-hidden />
                        <span className="font-medium text-hub-text">{f.name}</span>
                      </button>
                    </li>
                  ))}
                  {driveFiles.map((f) => {
                    const isSelected = Boolean(selected[f.id])
                    const allowed = acceptMatches(f.name, f.mime_type, accept)
                    return (
                      <li key={f.id}>
                        <button
                          type="button"
                          disabled={!allowed}
                          className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm ${
                            isSelected ? 'bg-teal-50 ring-1 ring-teal-300' : 'hover:bg-slate-100'
                          } disabled:cursor-not-allowed disabled:opacity-40`}
                          onClick={() => toggleFile(f)}
                        >
                          <i
                            className={`bi ${isSelected ? 'bi-check-square-fill text-teal-700' : 'bi-square text-slate-400'}`}
                            aria-hidden
                          />
                          <i className="bi bi-file-earmark text-slate-500" aria-hidden />
                          <span className="min-w-0 flex-1 truncate font-medium text-hub-text">{f.name}</span>
                          <span className="shrink-0 text-xs text-hub-muted">{formatBytes(f.size)}</span>
                        </button>
                      </li>
                    )
                  })}
                  {!folders.length && !driveFiles.length ? (
                    <li className="text-sm text-hub-muted">This folder is empty.</li>
                  ) : null}
                </ul>
              )}
            </>
          )}
          {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-slate-200 px-4 py-3">
          <span className="text-xs text-hub-muted">
            {selectedCount ? `${selectedCount} selected` : 'Select a file'}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded-xl border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700"
              onClick={onClose}
              disabled={importing}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-xl bg-teal-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              disabled={!selectedCount || importing || (status != null && !status.connected)}
              onClick={() => void confirm()}
            >
              {importing ? 'Importing…' : 'Add selected'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
