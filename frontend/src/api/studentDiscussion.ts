import { apiFetch, getCsrfToken } from './client'
import type {
  DiscussionActionResponse,
  StudentDiscussionBoardResponse,
  StudentDiscussionThreadResponse,
} from '../types/studentDiscussion'

export async function fetchDiscussionBoard(assignmentId: number) {
  return apiFetch<StudentDiscussionBoardResponse>(`/api/spa/student/discussion/${assignmentId}`)
}

export async function fetchDiscussionThread(threadId: number) {
  return apiFetch<StudentDiscussionThreadResponse>(
    `/api/spa/student/discussion/thread/${threadId}`,
  )
}

async function postMultipart(url: string, formData: FormData) {
  const token = getCsrfToken()
  if (token) formData.set('csrf_token', token)
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(token ? { 'X-CSRFToken': token } : {}),
    },
    body: formData,
  })
  const data = (await response.json().catch(() => ({}))) as DiscussionActionResponse & {
    error?: string
  }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || data.error || `Request failed (${response.status})`)
  }
  return data
}

export async function createDiscussionThread(
  assignmentId: number,
  payload: { title: string; content: string; files?: File[] },
) {
  const form = new FormData()
  form.set('thread_title', payload.title)
  form.set('thread_content', payload.content)
  for (const file of payload.files || []) {
    form.append('attachments', file)
  }
  return postMultipart(`/api/spa/student/discussion/${assignmentId}/threads`, form)
}

export async function replyToDiscussionThread(
  threadId: number,
  payload: { content: string; files?: File[] },
) {
  const form = new FormData()
  form.set('reply_content', payload.content)
  for (const file of payload.files || []) {
    form.append('attachments', file)
  }
  return postMultipart(`/api/spa/student/discussion/thread/${threadId}/reply`, form)
}

export async function editDiscussionThread(
  threadId: number,
  payload: { title: string; content: string },
) {
  return apiFetch<DiscussionActionResponse>(`/api/spa/student/discussion/thread/${threadId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      thread_title: payload.title,
      thread_content: payload.content,
    }),
  })
}

export async function editDiscussionPost(postId: number, content: string) {
  return apiFetch<DiscussionActionResponse>(`/api/spa/student/discussion/post/${postId}`, {
    method: 'PATCH',
    body: JSON.stringify({ post_content: content }),
  })
}
