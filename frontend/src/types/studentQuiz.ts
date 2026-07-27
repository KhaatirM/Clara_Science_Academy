export type QuizMode = 'take' | 'results' | 'google_form'

export type QuizOption = {
  id: number
  option_text: string
  order: number
  is_correct?: boolean
}

export type QuizQuestion = {
  id: number
  question_text: string
  question_type: string
  points: number
  order: number
  section: { id: number; title: string; order: number } | null
  options: QuizOption[]
  student_answer: {
    selected_option_id: number | null
    answer_text: string | null
    is_correct: boolean | null
    points_earned: number | null
  } | null
}

export type StudentQuizResponse = {
  mode: QuizMode
  assignment: {
    id: number
    title: string
    description?: string | null
    class_name?: string | null
    due_display?: string | null
    quarter?: string | null
    status?: string
    total_points?: number
    time_limit_minutes?: number | null
    allow_save_and_continue?: boolean
    save_timeout_minutes?: number
    max_attempts?: number | null
    show_correct_answers?: boolean
    google_form_url?: string
  }
  attempt?: {
    is_retake: boolean
    submissions_count: number
    attempts_remaining: number | null
    can_retake: boolean
    has_open_ended: boolean
  }
  grade?: {
    percentage: number | null
    grading_status: string | null
    points_earned: number | null
    total_points: number | null
    score: number | null
  } | null
  questions?: QuizQuestion[]
  timer_remaining_seconds?: number | null
  closes_at_iso?: string | null
  server_now_iso?: string
  quiz_opened_at?: string
  links: {
    assignments: string
    retake?: string
    save_progress?: string
    load_progress?: string
    keepalive?: string
  }
}

export type QuizSubmitResponse = {
  success: boolean
  message: string
  redirect: string
}
