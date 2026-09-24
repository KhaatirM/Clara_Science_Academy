import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  createDiscussionThread,
  editDiscussionPost,
  editDiscussionThread,
  fetchDiscussionBoard,
  fetchDiscussionThread,
  replyToDiscussionThread,
} from '../api/studentDiscussion'
import {
  DiscussionContentEditor,
  discFieldClass,
} from '../components/discussion/DiscussionContentEditor'
import { DiscussionContentView } from '../components/discussion/DiscussionContentView'
import { DocumentFileField } from '../components/uploads/DocumentFileField'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type {
  DiscussionAttachment,
  StudentDiscussionBoardResponse,
  StudentDiscussionThreadResponse,
} from '../types/studentDiscussion'
import { discussionContentPreview } from '../utils/discussionContent'

function spaPath(href: string) {
  return href.replace(/^\/app/, '') || '/'
}

const discBtnBase =
  'inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold no-underline transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 disabled:cursor-not-allowed disabled:opacity-45'

const discBtnMuted = `${discBtnBase} border border-slate-300 bg-white text-slate-700 shadow-sm hover:border-slate-400 hover:bg-slate-50`

const discBtnTealOutline = `${discBtnBase} border-2 border-teal-600 bg-white text-teal-800 shadow-sm hover:bg-teal-50`

const discBtnPrimary = `${discBtnBase} border border-teal-700 bg-gradient-to-br from-teal-700 to-teal-600 text-white shadow-md hover:from-teal-800 hover:to-teal-700`

const discErrorClass =
  'rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800'

export function StudentDiscussionPage() {
  const { assignmentId = '' } = useParams()
  const id = Number(assignmentId)
  const navigate = useNavigate()

  const [data, setData] = useState<StudentDiscussionBoardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const load = useCallback(async () => {
    if (!Number.isFinite(id) || id <= 0) {
      setError('Invalid discussion')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      setData(await fetchDiscussionBoard(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load discussion')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-hub-muted">Loading discussion…</div>
          ) : error && !data ? (
            <div className="m-3 space-y-3">
              <div className={discErrorClass}>{error}</div>
              <Link to="/student/assignments" className={discBtnMuted}>
                Back to assignments
              </Link>
            </div>
          ) : data ? (
            <div className="space-y-4 px-1 pb-8 md:px-2">
              <DiscussionHero data={data} />
              {message ? (
                <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
                  {message}
                  <button
                    type="button"
                    className="ms-2 underline"
                    onClick={() => setMessage(null)}
                  >
                    Dismiss
                  </button>
                </div>
              ) : null}
              {error ? <div className={discErrorClass}>{error}</div> : null}

              <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="mb-1 text-base font-bold text-slate-900">Discussion actions</h2>
                    <p className="mb-0 text-sm text-hub-muted">
                      {data.threads.length} thread{data.threads.length === 1 ? '' : 's'} ·{' '}
                      {data.participation.min_initial_posts} post
                      {data.participation.min_initial_posts === 1 ? '' : 's'} +{' '}
                      {data.participation.min_replies}{' '}
                      {data.participation.min_replies === 1 ? 'reply' : 'replies'} required
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link to="/student/assignments" className={discBtnMuted}>
                      Exit
                    </Link>
                    {data.allow_student_threads && data.assignment.is_active ? (
                      <button
                        type="button"
                        className={discBtnPrimary}
                        onClick={() => setShowCreate(true)}
                      >
                        New thread
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="mt-4 grid gap-2 md:grid-cols-3">
                  <ParticipationStat
                    label="Initial posts"
                    value={`${data.participation.my_posts} / ${data.participation.min_initial_posts}`}
                    done={data.participation.posts_done}
                  />
                  <ParticipationStat
                    label="Replies"
                    value={`${data.participation.my_replies} / ${data.participation.min_replies}`}
                    done={data.participation.replies_done}
                  />
                  <ParticipationStat
                    label="Overall"
                    value={data.participation.complete ? 'Complete' : 'Keep going'}
                    done={data.participation.complete}
                  />
                </div>
                <div className="mt-3">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-teal-600"
                      style={{ width: `${data.participation.overall_pct}%` }}
                    />
                  </div>
                  <p className="mb-0 mt-1 text-xs text-hub-muted">
                    Participation progress: {data.participation.overall_pct}%
                  </p>
                </div>
              </section>

              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-4 py-3">
                  <h2 className="mb-0 text-base font-bold text-slate-900">
                    Threads{' '}
                    <span className="rounded-full bg-teal-100 px-2 py-0.5 text-sm text-teal-800">
                      {data.threads.length}
                    </span>
                  </h2>
                </div>
                <div className="divide-y divide-slate-100">
                  {data.threads.length === 0 ? (
                    <p className="mb-0 p-5 text-center text-hub-muted">
                      No threads yet. Start the conversation!
                    </p>
                  ) : (
                    data.threads.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        className={`w-full px-4 py-4 text-start transition hover:bg-teal-50/60 ${
                          t.is_locked ? 'opacity-80' : ''
                        }`}
                        onClick={() => navigate(spaPath(t.url))}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <h3 className="mb-1 text-base font-semibold text-slate-900">
                            {t.is_pinned ? (
                              <span className="me-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-bold text-amber-800">
                                Pinned
                              </span>
                            ) : null}
                            {t.is_locked ? (
                              <span className="me-1 rounded bg-slate-200 px-1.5 py-0.5 text-xs font-bold text-slate-700">
                                Locked
                              </span>
                            ) : null}
                            {t.title}
                          </h3>
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                            {t.reply_count} {t.reply_count === 1 ? 'reply' : 'replies'}
                          </span>
                        </div>
                        <p className="mb-2 line-clamp-2 text-sm text-slate-600">
                          {discussionContentPreview(t.content_preview)}
                        </p>
                        <div className="flex flex-wrap gap-3 text-xs text-hub-muted">
                          <span>
                            {t.author_initials} · {t.author_name}
                          </span>
                          <span>{t.created_display}</span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </section>

              {showCreate ? (
                <CreateThreadModal
                  onClose={() => setShowCreate(false)}
                  onSubmit={async (payload) => {
                    const res = await createDiscussionThread(id, payload)
                    setMessage(res.message)
                    setShowCreate(false)
                    if (res.redirect) navigate(spaPath(res.redirect))
                    else await load()
                  }}
                />
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

export function StudentDiscussionThreadPage() {
  const { assignmentId = '', threadId = '' } = useParams()
  const tid = Number(threadId)

  const [data, setData] = useState<StudentDiscussionThreadResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [reply, setReply] = useState('')
  const [replyEditorKey, setReplyEditorKey] = useState(0)
  const [files, setFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [editingThread, setEditingThread] = useState(false)
  const [threadTitle, setThreadTitle] = useState('')
  const [threadContent, setThreadContent] = useState('')
  const [editingPostId, setEditingPostId] = useState<number | null>(null)
  const [editPostContent, setEditPostContent] = useState('')

  const load = useCallback(async () => {
    if (!Number.isFinite(tid) || tid <= 0) {
      setError('Invalid thread')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchDiscussionThread(tid)
      setData(payload)
      setThreadTitle(payload.thread.title)
      setThreadContent(payload.thread.content)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load thread')
    } finally {
      setLoading(false)
    }
  }, [tid])

  useEffect(() => {
    void load()
  }, [load])

  const onReply = async (e: FormEvent) => {
    e.preventDefault()
    if (!data || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await replyToDiscussionThread(tid, { content: reply, files })
      setMessage(res.message)
      setReply('')
      setReplyEditorKey((k) => k + 1)
      setFiles([])
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not post reply')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-hub-muted">Loading thread…</div>
          ) : error && !data ? (
            <div className="m-3 space-y-3">
              <div className={discErrorClass}>{error}</div>
              <Link
                to={assignmentId ? `/student/discussion/${assignmentId}` : '/student/assignments'}
                className={discBtnMuted}
              >
                Back
              </Link>
            </div>
          ) : data ? (
            <div className="space-y-4 px-1 pb-8 md:px-2">
              <div className="rounded-2xl bg-gradient-to-br from-teal-800 via-teal-700 to-cyan-600 px-4 py-5 text-white shadow-sm md:px-6">
                <Link
                  to={spaPath(data.links.board)}
                  className="mb-3 inline-flex items-center rounded-xl border border-white/30 bg-white/15 px-3 py-1.5 text-sm font-semibold text-white no-underline shadow-sm transition hover:bg-white/25"
                >
                  ← Back to discussion
                </Link>
                <h1 className="text-2xl font-bold tracking-tight">
                  {data.thread.title}
                  {data.thread.is_pinned ? ' · Pinned' : ''}
                  {data.thread.is_locked ? ' · Locked' : ''}
                </h1>
                <p className="mb-0 mt-1 text-sm text-teal-50/90">{data.assignment.title}</p>
              </div>

              {message ? (
                <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
                  {message}
                </div>
              ) : null}
              {error ? <div className={discErrorClass}>{error}</div> : null}

              <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
                <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-teal-700 text-sm font-bold text-white">
                      {data.thread.author_initials}
                    </div>
                    <div>
                      <div className="font-semibold text-teal-950">{data.thread.author_name}</div>
                      <div className="text-xs text-hub-muted">{data.thread.created_display}</div>
                    </div>
                  </div>
                  {data.thread.can_edit ? (
                    <button
                      type="button"
                      className={discBtnTealOutline}
                      onClick={() => setEditingThread((v) => !v)}
                    >
                      {editingThread ? 'Cancel' : 'Edit'}
                    </button>
                  ) : null}
                </div>
                {editingThread ? (
                  <form
                    className="space-y-3"
                    onSubmit={async (e) => {
                      e.preventDefault()
                      try {
                        const res = await editDiscussionThread(tid, {
                          title: threadTitle,
                          content: threadContent,
                        })
                        setMessage(res.message)
                        setEditingThread(false)
                        await load()
                      } catch (err) {
                        setError(err instanceof Error ? err.message : 'Could not update thread')
                      }
                    }}
                  >
                    <input
                      className={discFieldClass}
                      value={threadTitle}
                      onChange={(e) => setThreadTitle(e.target.value)}
                      required
                      placeholder="Thread title"
                    />
                    <DiscussionContentEditor
                      key={`edit-thread-${tid}-${data.thread.content.slice(0, 24)}`}
                      value={threadContent}
                      onChange={setThreadContent}
                      label="Thread post"
                      required
                      rows={6}
                    />
                    <button type="submit" className={discBtnPrimary}>
                      Save thread
                    </button>
                  </form>
                ) : (
                  <>
                    <DiscussionContentView content={data.thread.content} />
                    <AttachmentList items={data.thread.attachments} />
                  </>
                )}
              </article>

              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-4 py-3">
                  <h2 className="mb-0 text-base font-bold">
                    Replies{' '}
                    <span className="rounded-full bg-teal-100 px-2 py-0.5 text-sm text-teal-800">
                      {data.posts.length}
                    </span>
                  </h2>
                </div>
                <div className="divide-y divide-slate-100">
                  {data.posts.length === 0 ? (
                    <p className="mb-0 p-5 text-center text-hub-muted">No replies yet.</p>
                  ) : (
                    data.posts.map((p) => (
                      <div key={p.id} className="px-4 py-4">
                        <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                          <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-700 text-xs font-bold text-white">
                              {p.author_initials}
                            </div>
                            <div>
                              <div className="font-semibold text-slate-900">
                                {p.author_name}
                                {p.is_teacher_post ? (
                                  <span className="ms-2 rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-800">
                                    Teacher
                                  </span>
                                ) : null}
                              </div>
                              <div className="text-xs text-hub-muted">{p.created_display}</div>
                            </div>
                          </div>
                          {p.can_edit ? (
                            <button
                              type="button"
                              className={discBtnMuted}
                              onClick={() => {
                                setEditingPostId(p.id)
                                setEditPostContent(p.content)
                              }}
                            >
                              Edit
                            </button>
                          ) : null}
                        </div>
                        {editingPostId === p.id ? (
                          <form
                            className="space-y-2"
                            onSubmit={async (e) => {
                              e.preventDefault()
                              try {
                                const res = await editDiscussionPost(p.id, editPostContent)
                                setMessage(res.message)
                                setEditingPostId(null)
                                await load()
                              } catch (err) {
                                setError(err instanceof Error ? err.message : 'Could not update post')
                              }
                            }}
                          >
                            <DiscussionContentEditor
                              key={`edit-post-${p.id}`}
                              value={editPostContent}
                              onChange={setEditPostContent}
                              label="Reply"
                              required
                              rows={5}
                            />
                            <div className="flex gap-2">
                              <button type="submit" className={discBtnPrimary}>
                                Save
                              </button>
                              <button
                                type="button"
                                className={discBtnMuted}
                                onClick={() => setEditingPostId(null)}
                              >
                                Cancel
                              </button>
                            </div>
                          </form>
                        ) : (
                          <>
                            <DiscussionContentView content={p.content} />
                            <AttachmentList items={p.attachments} />
                          </>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </section>

              {data.can_reply ? (
                <form
                  onSubmit={onReply}
                  className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <h2 className="mb-3 text-base font-bold">Post a reply</h2>
                  <DiscussionContentEditor
                    key={`reply-${tid}-${replyEditorKey}`}
                    value={reply}
                    onChange={setReply}
                    label="Your reply"
                    required
                    rows={5}
                    textPlaceholder="Share your thoughts…"
                  />
                  <div className="mt-3">
                    <DocumentFileField
                      files={files}
                      onChange={setFiles}
                      multiple
                      helpText="Optional attachments from your computer or Google Drive."
                    />
                  </div>
                  <button
                    type="submit"
                    className={`${discBtnPrimary} mt-3`}
                    disabled={submitting}
                  >
                    {submitting ? 'Posting…' : 'Post reply'}
                  </button>
                </form>
              ) : (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  {data.thread.is_locked
                    ? 'This thread is locked and no longer accepts replies.'
                    : 'This discussion is not currently active.'}
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function DiscussionHero({ data }: { data: StudentDiscussionBoardResponse }) {
  const a = data.assignment
  return (
    <section className="overflow-hidden rounded-2xl border border-teal-800/10 shadow-sm">
      <div className="bg-gradient-to-br from-teal-800 via-teal-700 to-cyan-600 px-4 py-5 text-white md:px-6">
        <div className="mb-3 flex flex-wrap gap-2 text-xs">
          {a.class_name ? (
            <span className="rounded-full bg-white/15 px-2.5 py-1">
              Class <strong>{a.class_name}</strong>
            </span>
          ) : null}
          <span className="rounded-full bg-white/15 px-2.5 py-1">
            Due <strong>{a.due_display}</strong>
          </span>
          {a.quarter ? (
            <span className="rounded-full bg-white/15 px-2.5 py-1">
              Quarter <strong>{a.quarter}</strong>
            </span>
          ) : null}
          <span className="rounded-full bg-white/15 px-2.5 py-1">
            Status <strong>{a.status}</strong>
          </span>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{a.title}</h1>
            <p className="mt-1 text-sm text-teal-50/90">Class discussion</p>
          </div>
          <span className="rounded-full bg-white/20 px-3 py-1 text-sm font-semibold">
            {data.participation.complete ? 'Participation complete' : 'In progress'}
          </span>
        </div>
      </div>
      {a.prompt ? (
        <div className="border-t border-teal-100 bg-white px-4 py-4 md:px-6">
          <h2 className="mb-1 text-sm font-bold text-teal-900">Discussion prompt</h2>
          <p className="mb-0 whitespace-pre-wrap text-sm text-slate-700">{a.prompt}</p>
        </div>
      ) : null}
    </section>
  )
}

function ParticipationStat({
  label,
  value,
  done,
}: {
  label: string
  value: string
  done: boolean
}) {
  return (
    <div
      className={`rounded-xl border px-3 py-3 ${
        done ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'
      }`}
    >
      <div className="text-xs font-medium text-hub-muted">{label}</div>
      <div className={`text-sm font-bold ${done ? 'text-emerald-800' : 'text-slate-800'}`}>
        {value}
      </div>
    </div>
  )
}

function AttachmentList({ items }: { items: DiscussionAttachment[] }) {
  if (!items.length) return null
  return (
    <div className="mt-3 border-t border-slate-100 pt-3">
      <div className="mb-2 text-xs text-hub-muted">Attachments</div>
      <div className="flex flex-wrap gap-2">
        {items.map((att) =>
          att.is_image ? (
            <a key={att.id} href={att.download_url} target="_blank" rel="noopener noreferrer">
              <img
                src={att.preview_url}
                alt={att.filename}
                className="max-h-28 max-w-[200px] rounded-lg object-contain"
              />
            </a>
          ) : (
            <a
              key={att.id}
              href={att.download_url}
              className={discBtnMuted}
              target="_blank"
              rel="noopener noreferrer"
            >
              {att.filename}
            </a>
          ),
        )}
      </div>
    </div>
  )
}

function CreateThreadModal({
  onClose,
  onSubmit,
}: {
  onClose: () => void
  onSubmit: (payload: { title: string; content: string; files?: File[] }) => Promise<void>
}) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  return (
    <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-black/50 p-3 sm:p-6">
      <div className="flex max-h-[94vh] w-full max-w-4xl flex-col overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl md:p-7">
        <h2 className="mb-1 text-xl font-bold text-slate-900">Create thread</h2>
        <p className="mb-4 text-sm text-hub-muted">
          Add a clear title, then write your post in Text or paste code with line numbers.
        </p>
        {err ? <div className={discErrorClass}>{err}</div> : null}
        <form
          className="space-y-4"
          onSubmit={async (e) => {
            e.preventDefault()
            const trimmedTitle = title.trim()
            const trimmedBody = content.replace(/^\[DISCUSSION_CODE:[^\]]+\]\s*/, '').trim()
            if (!trimmedTitle || !trimmedBody) {
              setErr('Please provide both a title and content for your thread.')
              return
            }
            setBusy(true)
            setErr(null)
            try {
              await onSubmit({ title: trimmedTitle, content, files })
            } catch (error) {
              setErr(error instanceof Error ? error.message : 'Could not create thread')
              setBusy(false)
            }
          }}
        >
          <div>
            <label htmlFor="create-thread-title" className="mb-1 block text-sm font-semibold text-slate-800">
              Thread title <span className="text-red-600">*</span>
            </label>
            <input
              id="create-thread-title"
              className={`${discFieldClass} text-base`}
              placeholder="Enter a clear, descriptive title…"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              autoFocus
            />
          </div>

          <DiscussionContentEditor
            value={content}
            onChange={setContent}
            label="Your post"
            required
            rows={8}
            textPlaceholder="Share your thoughts, ideas, or questions about the discussion topic…"
          />

          <DocumentFileField
            files={files}
            onChange={setFiles}
            multiple
            helpText="Optional attachments from your computer or Google Drive."
          />

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
            <button type="button" className={discBtnMuted} onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button type="submit" className={discBtnPrimary} disabled={busy}>
              {busy ? 'Creating…' : 'Create thread'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
