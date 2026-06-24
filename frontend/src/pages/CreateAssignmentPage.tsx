import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  AssignmentTypeCarousel,
  type AssignmentTypeKey,
  type AssignmentTypeOption,
} from '../components/assignments/AssignmentTypeCarousel'
import { fetchCreateAssignmentMeta, type CreateAssignmentMeta } from '../api/createAssignment'
import { spaRoute } from '../utils/spaRoute'

const ASSIGNMENT_TYPES: AssignmentTypeOption[] = [
  {
    key: 'pdf',
    title: 'PDF / Paper',
    description: 'Upload documents; students submit files for grading.',
    icon: 'bi-file-earmark-pdf',
    cta: 'Create PDF assignment',
    features: ['PDF, Word, and more', 'Due dates & feedback', 'Homework or in-class'],
    guidelineTitle: 'PDF / Paper',
    guidelineBody:
      'Upload a handout or prompt; students submit files individually. Set homework vs in-class on the form.',
    guidelineLead:
      'PDF / Paper works well for essays, lab reports, and uploaded documents with teacher feedback.',
  },
  {
    key: 'quiz',
    title: 'Quiz',
    description: 'Auto-graded questionnaires with multiple question types.',
    icon: 'bi-question-circle',
    cta: 'Create quiz assignment',
    features: ['Multiple choice & short answer', 'Optional time limits', 'Instant feedback'],
    guidelineTitle: 'Quiz',
    guidelineBody:
      'Build multiple-choice and short-answer questions with optional time limits and automatic scoring.',
    guidelineLead:
      'Quizzes are ideal for quick checks, unit tests, and auto-graded review with optional timers.',
  },
  {
    key: 'discussion',
    title: 'Discussion',
    description: 'Rubric-based dialogue and critical thinking prompts.',
    icon: 'bi-chat-dots',
    cta: 'Create discussion assignment',
    features: ['Threaded responses', 'Rubric grading', 'Quality indicators'],
    guidelineTitle: 'Discussion',
    guidelineBody: 'Post a prompt for threaded replies; grade with a rubric and participation indicators.',
    guidelineLead:
      'Discussions encourage critical thinking—use rubrics to grade quality of replies, not just participation.',
  },
  {
    key: 'group',
    title: 'Group assignment',
    description: 'Collaborative work per class group—one submission per team.',
    icon: 'bi-people-fill',
    cta: 'Create group assignment',
    features: ['Assign to class groups', 'Shared group submission', 'Per-member grades'],
    guidelineTitle: 'Group',
    guidelineBody:
      'Assign to existing class groups—one submission per team, with grades per member when needed.',
    guidelineLead:
      'Group assignments tie to your class groups; teams share one submission and can receive individual grades.',
  },
]

export function CreateAssignmentPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const classIdParam = searchParams.get('class_id')
  const classId = classIdParam && /^\d+$/.test(classIdParam) ? Number(classIdParam) : null

  const [data, setData] = useState<CreateAssignmentMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchCreateAssignmentMeta(classId))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load assignment types')
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    void load()
  }, [load])

  const goToSpa = (path: string) => {
    navigate(spaRoute(path))
  }

  const handleTypeSelect = (type: AssignmentTypeKey) => {
    if (!data) return
    switch (type) {
      case 'pdf':
        goToSpa(data.links.pdf_homework)
        break
      case 'quiz':
        goToSpa(data.links.quiz)
        break
      case 'discussion':
        goToSpa(data.links.discussion)
        break
      case 'group':
        navigate(
          classId
            ? `/management/assignments/create/group/${classId}`
            : '/management/assignments/create/group',
        )
        break
      default:
        break
    }
  }

  const backTo = useMemo(() => {
    if (data?.back_url) return spaRoute(data.back_url)
    return classId ? `/management/assignments/${classId}` : '/management/assignments'
  }, [classId, data?.back_url])

  if (loading) {
    return <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">Loading assignment types…</div>
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-red-700">{error || 'Could not load page'}</p>
        <Link to={backTo} className="mt-4 inline-block text-sm font-semibold text-teal-700">
          Back
        </Link>
      </div>
    )
  }

  return (
    <div className="assignment-type-page mx-auto max-w-[1280px] px-1">
      <header className="assignment-selector-header mb-6 rounded-[20px] bg-gradient-to-br from-[#667eea] to-[#764ba2] px-6 py-5 text-white shadow-[0_10px_40px_rgba(102,126,234,0.28)]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="mb-1 flex items-center gap-2 text-2xl font-bold">
              <i className="bi bi-plus-circle" aria-hidden />
              Create New Assignment
            </h1>
            <p className="text-[0.95rem] text-white/90">Browse types with the arrows — tap a card to select it</p>
            {data.preselected_class ? (
              <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold">
                <i className="bi bi-book" aria-hidden />
                {data.preselected_class.name}
                {data.preselected_class.subject ? ` · ${data.preselected_class.subject}` : ''}
              </p>
            ) : null}
          </div>
          <Link
            to={backTo}
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-[#667eea] hover:bg-white/95"
          >
            <i className="bi bi-arrow-left" aria-hidden />
            Back to Assignments
          </Link>
        </div>
      </header>

      <AssignmentTypeCarousel types={ASSIGNMENT_TYPES} onSelect={handleTypeSelect} />
    </div>
  )
}
