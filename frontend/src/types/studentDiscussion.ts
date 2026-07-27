export type DiscussionAttachment = {
  id: number
  filename: string
  mime_type: string
  is_image: boolean
  size: number | null
  download_url: string
  preview_url: string
}

export type DiscussionThreadSummary = {
  id: number
  title: string
  content_preview: string
  is_pinned: boolean
  is_locked: boolean
  created_display: string | null
  author_name: string
  author_initials: string
  is_mine: boolean
  can_edit: boolean
  reply_count: number
  url: string
}

export type StudentDiscussionBoardResponse = {
  assignment: {
    id: number
    title: string
    class_name: string | null
    due_display: string
    quarter: string | null
    status: string
    prompt: string
    is_active: boolean
  }
  participation: {
    min_initial_posts: number
    min_replies: number
    my_posts: number
    my_replies: number
    posts_done: boolean
    replies_done: boolean
    complete: boolean
    overall_pct: number
  }
  allow_student_threads: boolean
  allow_student_edit_posts: boolean
  threads: DiscussionThreadSummary[]
  links: {
    assignments: string
    board: string
  }
}

export type DiscussionPost = {
  id: number
  content: string
  created_display: string | null
  author_name: string
  author_initials: string
  is_teacher_post: boolean
  is_mine: boolean
  can_edit: boolean
  attachments: DiscussionAttachment[]
}

export type StudentDiscussionThreadResponse = {
  assignment: {
    id: number
    title: string
    status: string
    is_active: boolean
  }
  thread: {
    id: number
    title: string
    content: string
    is_pinned: boolean
    is_locked: boolean
    created_display: string | null
    author_name: string
    author_initials: string
    is_mine: boolean
    can_edit: boolean
    attachments: DiscussionAttachment[]
  }
  posts: DiscussionPost[]
  allow_student_edit_posts: boolean
  can_reply: boolean
  links: {
    board: string
    thread: string
    assignments: string
  }
}

export type DiscussionActionResponse = {
  success: boolean
  message: string
  redirect?: string
  thread_id?: number
  post_id?: number
}
