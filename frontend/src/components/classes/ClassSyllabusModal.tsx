import { useCallback, useEffect, useRef, useState } from 'react'
import {
  classSyllabusDownloadUrl,
  deleteClassSyllabus,
  fetchClassSyllabus,
  uploadClassSyllabus,
} from '../../api/classSyllabus'
import type { ClassSyllabusResponse, SyllabusOutline, SyllabusSection } from '../../types/classSyllabus'

type Props = {
  open: boolean
  classId: number
  onClose: () => void
}

export function ClassSyllabusModal({ open, classId, onClose }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [data, setData] = useState<ClassSyllabusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!Number.isFinite(classId) || classId <= 0) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchClassSyllabus(classId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load syllabus')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    if (!open) return
    setMessage(null)
    void load()
  }, [open, load])

  if (!open) return null

  const canManage = Boolean(data?.can_manage)
  const syllabus = data?.syllabus
  const outline = syllabus?.outline

  async function onUpload(file: File | null) {
    if (!file || !canManage) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = await uploadClassSyllabus(classId, file)
      setData(res)
      setMessage(res.message || 'Syllabus uploaded.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function onRemove() {
    if (!canManage) return
    if (!window.confirm('Remove this class syllabus?')) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = await deleteClassSyllabus(classId)
      setMessage(res.message || 'Syllabus removed.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove syllabus')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="class-syllabus-title"
      >
        <div className="flex items-start justify-between gap-3 bg-teal-800 px-5 py-4 text-white">
          <div className="min-w-0">
            <h2 id="class-syllabus-title" className="text-lg font-bold">
              <i className="bi bi-journal-richtext me-2" aria-hidden />
              Syllabus
            </h2>
            {data ? (
              <p className="mb-0 mt-0.5 truncate text-sm text-white/80">
                {data.class.name}
                {data.class.subject ? ` · ${data.class.subject}` : ''}
              </p>
            ) : null}
          </div>
          <button type="button" onClick={onClose} className="shrink-0 text-white/80 hover:text-white" aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4">
          {loading ? <p className="text-hub-muted">Loading syllabus…</p> : null}
          {error ? (
            <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
          ) : null}
          {message ? (
            <div className="mb-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
              {message}
            </div>
          ) : null}

          {data ? (
            <div className="space-y-4">
              {canManage ? (
                <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <h3 className="mb-1 text-sm font-bold text-slate-900">
                    <i className="bi bi-cloud-upload me-2 text-teal-700" aria-hidden />
                    Upload syllabus
                  </h3>
                  <p className="mb-3 text-sm text-hub-muted">
                    Upload a PDF, DOCX, TXT, or Markdown file. The outline appears here (not a PDF viewer).
                    Students can download the original.
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".pdf,.docx,.txt,.md,application/pdf"
                      className="hidden"
                      onChange={(e) => void onUpload(e.target.files?.[0] || null)}
                    />
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-full bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                      onClick={() => fileRef.current?.click()}
                    >
                      {busy ? 'Working…' : syllabus ? 'Replace syllabus' : 'Upload syllabus'}
                    </button>
                    {syllabus ? (
                      <>
                        <a
                          href={classSyllabusDownloadUrl(classId)}
                          className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-800"
                        >
                          <i className="bi bi-download me-1" aria-hidden />
                          Download
                        </a>
                        <button
                          type="button"
                          disabled={busy}
                          className="rounded-full border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                          onClick={() => void onRemove()}
                        >
                          Remove
                        </button>
                      </>
                    ) : null}
                  </div>
                  {syllabus ? (
                    <p className="mb-0 mt-3 text-xs text-hub-muted">
                      Current file: <strong>{syllabus.original_filename}</strong>
                      {syllabus.uploaded_by ? ` · uploaded by ${syllabus.uploaded_by}` : ''}
                    </p>
                  ) : null}
                </section>
              ) : null}

              {!syllabus ? (
                <section className="rounded-xl border border-dashed border-slate-300 bg-white px-5 py-10 text-center">
                  <i className="bi bi-journal-text mb-3 block text-3xl text-slate-400" aria-hidden />
                  <p className="mb-1 text-base font-semibold text-slate-800">No syllabus yet</p>
                  <p className="mb-0 text-sm text-hub-muted">
                    {canManage
                      ? 'Upload a document to generate an outline for this class.'
                      : 'Your teacher has not uploaded a syllabus for this class yet.'}
                  </p>
                </section>
              ) : (
                <section>
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="mb-0 text-base font-bold text-slate-900">
                        {outline?.title || 'Class syllabus'}
                      </h3>
                      <p className="mb-0 mt-1 text-sm text-hub-muted">
                        Outlined from {syllabus.original_filename}
                      </p>
                    </div>
                    {!canManage ? (
                      <a
                        href={classSyllabusDownloadUrl(classId)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-teal-700 px-3.5 py-2 text-sm font-semibold text-white hover:bg-teal-800"
                      >
                        <i className="bi bi-download" aria-hidden />
                        Download
                      </a>
                    ) : null}
                  </div>
                  <SyllabusOutlineView outline={outline} />
                </section>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function SyllabusOutlineView({ outline }: { outline?: SyllabusOutline | null }) {
  if (!outline?.sections?.length) {
    return <p className="text-sm text-hub-muted">No outline sections were extracted.</p>
  }

  return (
    <div className="space-y-5">
      <nav aria-label="Syllabus outline" className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Outline</p>
        <ol className="mb-0 space-y-1.5 text-sm">
          {outline.sections.map((section, idx) => (
            <li key={`${section.title}-${idx}`} style={{ paddingLeft: `${(section.level - 1) * 0.75}rem` }}>
              <a href={`#syllabus-modal-section-${idx}`} className="font-semibold text-teal-800 hover:underline">
                {section.title}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      {outline.sections.map((section, idx) => (
        <SyllabusSectionBlock key={`${section.title}-${idx}`} section={section} index={idx} />
      ))}
    </div>
  )
}

function SyllabusSectionBlock({ section, index }: { section: SyllabusSection; index: number }) {
  const HeadingTag = section.level >= 3 ? 'h4' : section.level === 2 ? 'h3' : 'h2'
  const headingClass =
    section.level >= 3
      ? 'text-sm font-bold text-slate-800'
      : section.level === 2
        ? 'text-base font-bold text-slate-900'
        : 'border-b border-teal-100 pb-2 text-lg font-extrabold text-slate-900'

  return (
    <section id={`syllabus-modal-section-${index}`} className="scroll-mt-4">
      <HeadingTag className={`mb-2 ${headingClass}`}>{section.title}</HeadingTag>
      <div className="space-y-2">
        {section.blocks?.map((block, bIdx) =>
          block.type === 'bullet' ? (
            <div key={bIdx} className="flex gap-2 text-sm leading-relaxed text-slate-700">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" aria-hidden />
              <p className="mb-0">{block.text}</p>
            </div>
          ) : (
            <p key={bIdx} className="mb-0 text-sm leading-relaxed text-slate-700">
              {block.text}
            </p>
          ),
        )}
      </div>
    </section>
  )
}
