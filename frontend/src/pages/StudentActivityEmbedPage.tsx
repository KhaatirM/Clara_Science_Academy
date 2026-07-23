import { useCallback, useEffect, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

/**
 * Full-bleed embed of legacy quiz/discussion so the page is the activity itself
 * (no extra "Student portal" chrome wrapping the content).
 */
export function StudentActivityEmbedPage({ kind }: { kind: 'quiz' | 'discussion' }) {
  const { assignmentId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const iframeRef = useRef<HTMLIFrameElement | null>(null)

  const legacyParams = new URLSearchParams(searchParams)
  legacyParams.set('embed', '1')
  const qs = legacyParams.toString()
  const legacySrc =
    kind === 'quiz'
      ? `/student/take-quiz/${assignmentId}${qs ? `?${qs}` : ''}`
      : `/student/discussion/${assignmentId}${qs ? `?${qs}` : ''}`

  const title = kind === 'quiz' ? 'Take quiz' : 'Discussion'

  const maybeBreakOut = useCallback(() => {
    const frame = iframeRef.current
    if (!frame?.contentWindow) return
    try {
      const path = frame.contentWindow.location.pathname + frame.contentWindow.location.search
      if (
        path.includes('/app/student') &&
        !path.includes('/student/take-quiz/') &&
        !path.includes('/student/discussion/')
      ) {
        window.location.assign(path.startsWith('/app') ? path : `/app${path}`)
      }
    } catch {
      // Ignore cross-document access errors
    }
  }, [])

  useEffect(() => {
    const frame = iframeRef.current
    if (!frame) return
    const onLoad = () => maybeBreakOut()
    frame.addEventListener('load', onLoad)
    return () => frame.removeEventListener('load', onLoad)
  }, [legacySrc, maybeBreakOut])

  return (
    <div className="-m-4 h-[calc(100dvh)] bg-transparent md:-m-8">
      <iframe ref={iframeRef} title={title} src={legacySrc} className="h-full w-full border-0 bg-transparent" />
    </div>
  )
}

export function StudentTakeQuizPage() {
  return <StudentActivityEmbedPage kind="quiz" />
}

export function StudentDiscussionPage() {
  return <StudentActivityEmbedPage kind="discussion" />
}
