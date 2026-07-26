import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  fetchStudentQuiz,
  loadQuizProgress,
  quizKeepalive,
  saveQuizProgress,
  submitStudentQuiz,
} from '../api/studentQuiz'
import { ManagementPageShell } from '../components/layout/ManagementPageShell'
import type { QuizQuestion, StudentQuizResponse } from '../types/studentQuiz'

function optionLetter(index: number) {
  return String.fromCharCode(65 + index)
}

const quizBtnBase =
  'inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 disabled:cursor-not-allowed disabled:opacity-45'

const quizBtnMuted = `${quizBtnBase} border border-slate-300 bg-white text-slate-700 shadow-sm hover:border-slate-400 hover:bg-slate-50`

const quizBtnTealOutline = `${quizBtnBase} border-2 border-teal-600 bg-white text-teal-800 shadow-sm hover:bg-teal-50`

const quizBtnPrimary = `${quizBtnBase} border border-teal-700 bg-gradient-to-br from-teal-700 to-teal-600 text-white shadow-md hover:from-teal-800 hover:to-teal-700`

function formatTimer(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function StudentTakeQuizPage() {
  const { assignmentId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const retake = searchParams.get('retake') === 'true'
  const navigate = useNavigate()
  const id = Number(assignmentId)

  const [data, setData] = useState<StudentQuizResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [current, setCurrent] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)
  const [timerSeconds, setTimerSeconds] = useState<number | null>(null)
  const openedAtRef = useRef<string | null>(null)
  const timerRef = useRef<number | null>(null)
  const autoSubmittedRef = useRef(false)

  const load = useCallback(async () => {
    if (!Number.isFinite(id) || id <= 0) {
      setError('Invalid quiz')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchStudentQuiz(id, retake)
      if (payload.mode === 'google_form' && payload.assignment.google_form_url) {
        window.location.assign(payload.assignment.google_form_url)
        return
      }
      setData(payload)
      openedAtRef.current = payload.quiz_opened_at || new Date().toISOString()
      if (typeof payload.timer_remaining_seconds === 'number') {
        setTimerSeconds(payload.timer_remaining_seconds)
      } else {
        setTimerSeconds(null)
      }

      if (payload.mode === 'results' && payload.questions) {
        const seeded: Record<string, string> = {}
        for (const q of payload.questions) {
          if (q.student_answer?.selected_option_id != null) {
            seeded[String(q.id)] = String(q.student_answer.selected_option_id)
          } else if (q.student_answer?.answer_text) {
            seeded[String(q.id)] = q.student_answer.answer_text
          }
        }
        setAnswers(seeded)
      } else if (payload.assignment.allow_save_and_continue) {
        try {
          const saved = await loadQuizProgress(id)
          if (saved.success && saved.progress?.answers) {
            setAnswers(saved.progress.answers)
            if (typeof saved.progress.timer_remaining_seconds === 'number') {
              setTimerSeconds(saved.progress.timer_remaining_seconds)
            }
          }
        } catch {
          // No saved progress is fine
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load quiz')
    } finally {
      setLoading(false)
    }
  }, [id, retake])

  useEffect(() => {
    void load()
  }, [load])

  const questions = data?.questions || []
  const answeredCount = useMemo(() => {
    return questions.filter((q) => {
      const v = answers[String(q.id)]
      return v != null && String(v).trim() !== ''
    }).length
  }, [answers, questions])

  const progressPct = questions.length
    ? Math.round((answeredCount / questions.length) * 100)
    : 0

  const collectAnswers = useCallback(() => {
    const out: Record<string, string> = {}
    for (const [k, v] of Object.entries(answers)) {
      if (v != null && String(v).trim() !== '') out[k] = String(v)
    }
    return out
  }, [answers])

  const doSave = useCallback(
    async (opts?: { pauseTimer?: boolean; silent?: boolean }) => {
      if (!data || data.mode !== 'take' || !data.assignment.allow_save_and_continue) return
      try {
        const res = await saveQuizProgress(id, {
          answers: collectAnswers(),
          progress_percentage: progressPct,
          questions_answered: answeredCount,
          pause_timer: opts?.pauseTimer,
        })
        if (typeof res.timer_remaining_seconds === 'number') {
          setTimerSeconds(res.timer_remaining_seconds)
        }
        if (!opts?.silent) setSaveMsg(res.message || 'Progress saved')
      } catch (err) {
        if (!opts?.silent) {
          setSaveMsg(err instanceof Error ? err.message : 'Could not save progress')
        }
      }
    },
    [answeredCount, collectAnswers, data, id, progressPct],
  )

  const doSubmit = useCallback(async () => {
    if (!data || data.mode !== 'take' || submitting || autoSubmittedRef.current) return
    setSubmitting(true)
    setError(null)
    try {
      await submitStudentQuiz(id, collectAnswers(), openedAtRef.current)
      autoSubmittedRef.current = false
      const payload = await fetchStudentQuiz(id, false)
      setData(payload)
      setAnswers({})
      setCurrent(0)
      setTimerSeconds(null)
      if (payload.mode === 'results' && payload.questions) {
        const seeded: Record<string, string> = {}
        for (const q of payload.questions) {
          if (q.student_answer?.selected_option_id != null) {
            seeded[String(q.id)] = String(q.student_answer.selected_option_id)
          } else if (q.student_answer?.answer_text) {
            seeded[String(q.id)] = q.student_answer.answer_text
          }
        }
        setAnswers(seeded)
      }
      if (retake) {
        navigate(`/student/take-quiz/${id}`, { replace: true })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit quiz')
      autoSubmittedRef.current = false
    } finally {
      setSubmitting(false)
    }
  }, [collectAnswers, data, id, navigate, retake, submitting])

  useEffect(() => {
    if (data?.mode !== 'take' || timerSeconds == null) return
    if (timerRef.current) window.clearInterval(timerRef.current)
    timerRef.current = window.setInterval(() => {
      setTimerSeconds((prev) => {
        if (prev == null) return prev
        if (prev <= 1) {
          if (!autoSubmittedRef.current) {
            autoSubmittedRef.current = true
            void doSubmit()
          }
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current)
    }
  }, [data?.mode, timerSeconds == null, doSubmit])

  useEffect(() => {
    if (data?.mode !== 'take' || !data.assignment.allow_save_and_continue) return
    const saveInterval = window.setInterval(() => {
      void doSave({ silent: true })
    }, 30000)
    const keepAlive = window.setInterval(() => {
      void quizKeepalive(id).catch(() => undefined)
    }, 60000)
    return () => {
      window.clearInterval(saveInterval)
      window.clearInterval(keepAlive)
    }
  }, [data, doSave, id])

  const setAnswer = (questionId: number, value: string) => {
    setAnswers((prev) => ({ ...prev, [String(questionId)]: value }))
  }

  const currentQuestion = questions[current] || null

  return (
    <ManagementPageShell>
      <div className="mgmt-home mgmt-home--teacher container-fluid px-0 px-md-1">
        <div className="mgmt-home-shell">
          {loading && !data ? (
            <div className="p-5 text-center text-muted">Loading quiz…</div>
          ) : error && !data ? (
            <div className="m-3 space-y-3">
              <div className="alert alert-danger mb-0">{error}</div>
              <Link to="/student/assignments" className="btn btn-outline-secondary btn-sm">
                Back to assignments
              </Link>
            </div>
          ) : data ? (
            <div className="space-y-4 px-1 pb-8 md:px-2">
              <QuizHero data={data} timerSeconds={timerSeconds} />
              {error ? <div className="alert alert-danger">{error}</div> : null}
              {saveMsg ? (
                <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
                  {saveMsg}
                  <button
                    type="button"
                    className="ms-2 text-teal-700 underline"
                    onClick={() => setSaveMsg(null)}
                  >
                    Dismiss
                  </button>
                </div>
              ) : null}

              {data.mode === 'results' ? (
                <QuizResults
                  data={data}
                  questions={questions}
                  onRetake={() => navigate(`/student/take-quiz/${id}?retake=true`)}
                />
              ) : (
                <>
                  <QuizActionsBar
                    answeredCount={answeredCount}
                    total={questions.length}
                    progressPct={progressPct}
                    allowSave={Boolean(data.assignment.allow_save_and_continue)}
                    submitting={submitting}
                    onSave={() => void doSave()}
                    onExit={() => {
                      void doSave({ pauseTimer: true }).finally(() =>
                        navigate('/student/assignments'),
                      )
                    }}
                    onSubmit={() => {
                      if (
                        window.confirm(
                          answeredCount < questions.length
                            ? `You have answered ${answeredCount} of ${questions.length} questions. Submit anyway?`
                            : 'Submit this quiz?',
                        )
                      ) {
                        void doSubmit()
                      }
                    }}
                  />
                  {currentQuestion ? (
                    <QuizQuestionCard
                      question={currentQuestion}
                      index={current}
                      total={questions.length}
                      value={answers[String(currentQuestion.id)] || ''}
                      onChange={(v) => setAnswer(currentQuestion.id, v)}
                      onPrev={() => setCurrent((c) => Math.max(0, c - 1))}
                      onNext={() => setCurrent((c) => Math.min(questions.length - 1, c + 1))}
                      resultsMode={false}
                    />
                  ) : (
                    <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-hub-muted">
                      No questions available for this quiz.
                    </div>
                  )}
                  {questions.length > 1 ? (
                    <div className="flex flex-wrap gap-2">
                      {questions.map((q, i) => {
                        const filled = Boolean(answers[String(q.id)]?.trim())
                        return (
                          <button
                            key={q.id}
                            type="button"
                            onClick={() => setCurrent(i)}
                            aria-label={`Go to question ${i + 1}`}
                            aria-current={i === current ? 'true' : undefined}
                            className={`inline-flex h-10 w-10 items-center justify-center rounded-xl text-sm font-bold shadow-sm transition ${
                              i === current
                                ? 'bg-teal-700 text-white ring-2 ring-teal-700/30'
                                : filled
                                  ? 'border-2 border-teal-300 bg-teal-50 text-teal-900 hover:bg-teal-100'
                                  : 'border border-slate-300 bg-white text-slate-600 hover:border-teal-400 hover:text-teal-800'
                            }`}
                          >
                            {i + 1}
                          </button>
                        )
                      })}
                    </div>
                  ) : null}
                </>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </ManagementPageShell>
  )
}

function QuizHero({
  data,
  timerSeconds,
}: {
  data: StudentQuizResponse
  timerSeconds: number | null
}) {
  const a = data.assignment
  return (
    <section className="overflow-hidden rounded-2xl border border-teal-800/10 shadow-sm">
      <div className="bg-gradient-to-br from-teal-800 via-teal-700 to-cyan-600 px-4 py-5 text-white md:px-6">
        <div className="mb-3 flex flex-wrap gap-2 text-xs">
          {a.class_name ? <MetaChip label="Class" value={a.class_name} /> : null}
          <MetaChip label="Due" value={a.due_display || 'No due date'} />
          {a.quarter ? <MetaChip label="Quarter" value={a.quarter} /> : null}
          {a.status ? <MetaChip label="Status" value={a.status} /> : null}
          {timerSeconds != null ? (
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-semibold ${
                timerSeconds <= 60
                  ? 'bg-rose-500/40'
                  : timerSeconds <= 300
                    ? 'bg-amber-400/40'
                    : 'bg-white/15'
              }`}
            >
              Time left {formatTimer(timerSeconds)}
            </span>
          ) : null}
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{a.title}</h1>
            <p className="mt-1 text-sm text-teal-50/90">Quiz assignment</p>
          </div>
          <span className="rounded-full bg-white/20 px-3 py-1 text-sm font-semibold backdrop-blur">
            {data.mode === 'results' ? 'Submitted' : 'In progress'}
          </span>
        </div>
      </div>
      {a.description ? (
        <div className="border-t border-teal-100 bg-white px-4 py-4 md:px-6">
          <h2 className="mb-1 text-sm font-bold text-teal-900">Instructions</h2>
          <p className="mb-0 whitespace-pre-wrap text-sm text-slate-700">{a.description}</p>
        </div>
      ) : null}
    </section>
  )
}

function MetaChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-1">
      <span className="opacity-80">{label}</span>
      <strong>{value}</strong>
    </span>
  )
}

function QuizActionsBar({
  answeredCount,
  total,
  progressPct,
  allowSave,
  submitting,
  onSave,
  onExit,
  onSubmit,
}: {
  answeredCount: number
  total: number
  progressPct: number
  allowSave: boolean
  submitting: boolean
  onSave: () => void
  onExit: () => void
  onSubmit: () => void
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="mb-0 text-base font-bold text-slate-900">Quiz actions</h2>
          <p className="mb-0 text-sm text-hub-muted">
            {answeredCount} of {total} answered
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={quizBtnMuted} onClick={onExit}>
            Exit
          </button>
          {allowSave ? (
            <button type="button" className={quizBtnTealOutline} onClick={onSave}>
              Save & continue
            </button>
          ) : null}
          <button
            type="button"
            className={quizBtnPrimary}
            disabled={submitting}
            onClick={onSubmit}
          >
            {submitting ? 'Submitting…' : 'Submit quiz'}
          </button>
        </div>
      </div>
      {allowSave ? (
        <div className="mt-3">
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-teal-600 transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <p className="mb-0 mt-1 text-xs text-hub-muted">Progress: {progressPct}%</p>
        </div>
      ) : null}
    </section>
  )
}

function QuizResults({
  data,
  questions,
  onRetake,
}: {
  data: StudentQuizResponse
  questions: QuizQuestion[]
  onRetake: () => void
}) {
  const pending = (data.grade?.grading_status || '').toLowerCase() === 'pending'
  const showCorrect = Boolean(data.assignment.show_correct_answers)
  const correctCount = questions.filter((q) => q.student_answer?.is_correct === true).length

  return (
    <div className="space-y-4">
      <section
        className={`overflow-hidden rounded-2xl border shadow-sm ${
          pending ? 'border-amber-200' : 'border-emerald-200'
        }`}
      >
        <div
          className={`px-4 py-5 text-white md:px-6 ${
            pending
              ? 'bg-gradient-to-br from-amber-500 to-orange-500'
              : 'bg-gradient-to-br from-emerald-600 to-teal-500'
          }`}
        >
          <h2 className="mb-1 text-xl font-bold">
            {pending ? 'Quiz submitted (grade pending)' : 'Quiz completed and graded'}
          </h2>
          <p className="mb-0 text-sm text-white/90">
            {pending
              ? 'Open-ended answers need teacher review before your final score.'
              : `Your grade: ${data.grade?.percentage ?? '—'}%`}
          </p>
        </div>
        <div className="bg-white px-4 py-4 md:px-6">
          <div className="mb-4 flex flex-wrap gap-2">
            {!pending ? (
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-800">
                {correctCount} / {questions.length} correct
              </span>
            ) : (
              <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-900">
                Auto-graded so far: {data.grade?.points_earned ?? 0} /{' '}
                {data.grade?.total_points ?? data.assignment.total_points ?? 0}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/student/assignments" className="btn btn-sm text-white" style={{ background: '#0f766e' }}>
              Back to assignments
            </Link>
            {data.attempt?.can_retake ? (
              <button type="button" className="btn btn-success btn-sm" onClick={onRetake}>
                Retake quiz ({data.attempt.attempts_remaining} left)
              </button>
            ) : null}
          </div>
        </div>
      </section>

      {showCorrect
        ? questions.map((q, i) => (
            <QuizQuestionCard
              key={q.id}
              question={q}
              index={i}
              total={questions.length}
              value={
                q.student_answer?.selected_option_id != null
                  ? String(q.student_answer.selected_option_id)
                  : q.student_answer?.answer_text || ''
              }
              onChange={() => undefined}
              onPrev={() => undefined}
              onNext={() => undefined}
              resultsMode
            />
          ))
        : null}
    </div>
  )
}

function QuizQuestionCard({
  question,
  index,
  total,
  value,
  onChange,
  onPrev,
  onNext,
  resultsMode,
}: {
  question: QuizQuestion
  index: number
  total: number
  value: string
  onChange: (v: string) => void
  onPrev: () => void
  onNext: () => void
  resultsMode: boolean
}) {
  const showSection =
    question.section &&
    (index === 0 || question.section.title /* always show when present in single view */)

  return (
    <section className="space-y-3">
      {showSection && question.section ? (
        <div className="rounded-xl border border-teal-200 bg-gradient-to-r from-teal-50 to-emerald-50 px-4 py-3">
          <h3 className="mb-0 text-sm font-bold text-teal-900">{question.section.title}</h3>
        </div>
      ) : null}
      <article className="rounded-2xl border border-l-4 border-slate-200 border-l-teal-700 bg-white p-4 shadow-sm md:p-5">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <span className="rounded-lg bg-teal-700 px-3 py-1 text-sm font-semibold text-white">
            Question {index + 1}
            {!resultsMode ? ` of ${total}` : ''}
          </span>
          <span className="rounded-lg bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-800">
            {question.points} pt{question.points === 1 ? '' : 's'}
          </span>
        </div>
        <p className="mb-4 whitespace-pre-wrap text-lg font-semibold text-slate-800">
          {question.question_text}
        </p>

        {question.question_type === 'multiple_choice' || question.question_type === 'true_false' ? (
          <div className="space-y-2">
            {question.options.map((opt, oi) => {
              const selected = value === String(opt.id)
              const isCorrect = opt.is_correct === true
              const tone = resultsMode
                ? isCorrect
                  ? 'border-emerald-400 bg-emerald-50'
                  : selected
                    ? 'border-rose-300 bg-rose-50'
                    : 'border-slate-200 bg-white'
                : selected
                  ? 'border-teal-500 bg-teal-50'
                  : 'border-slate-200 bg-white hover:border-teal-400'
              return (
                <label
                  key={opt.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border-2 px-3 py-3 ${tone} ${
                    resultsMode ? 'cursor-default' : ''
                  }`}
                >
                  <input
                    type="radio"
                    className="mt-1"
                    name={`q_${question.id}`}
                    value={opt.id}
                    checked={selected}
                    disabled={resultsMode}
                    onChange={() => onChange(String(opt.id))}
                  />
                  <span className="flex-1">
                    {question.question_type === 'multiple_choice' ? (
                      <span className="me-2 inline-flex h-6 w-6 items-center justify-center rounded bg-teal-700 text-xs font-bold text-white">
                        {optionLetter(oi)}
                      </span>
                    ) : null}
                    {opt.option_text}
                  </span>
                </label>
              )
            })}
          </div>
        ) : question.question_type === 'short_answer' ? (
          <input
            type="text"
            className="form-control"
            value={value}
            disabled={resultsMode}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Your answer"
          />
        ) : (
          <textarea
            className="form-control"
            rows={5}
            value={value}
            disabled={resultsMode}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Your essay response"
          />
        )}

        {!resultsMode ? (
          <div className="mt-5 flex justify-between gap-2 border-t border-slate-100 pt-4">
            <button
              type="button"
              className={quizBtnMuted}
              disabled={index === 0}
              onClick={onPrev}
            >
              ← Previous
            </button>
            <button
              type="button"
              className={quizBtnTealOutline}
              disabled={index >= total - 1}
              onClick={onNext}
            >
              Next →
            </button>
          </div>
        ) : null}
      </article>
    </section>
  )
}
