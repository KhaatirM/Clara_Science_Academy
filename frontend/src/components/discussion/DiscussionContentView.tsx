import { parseDiscussionContent } from '../../utils/discussionContent'

type Props = {
  content: string | null | undefined
  className?: string
}

/** Safe renderer for discussion posts (plain text or DISCUSSION_CODE blocks). */
export function DiscussionContentView({ content, className = '' }: Props) {
  const parsed = parseDiscussionContent(content)

  if (parsed.kind === 'code') {
    const lines = parsed.code.length ? parsed.code.split('\n') : ['']
    return (
      <div
        className={`overflow-hidden rounded-xl border border-slate-700 bg-slate-950 text-slate-100 ${className}`}
      >
        <div className="flex items-center justify-between border-b border-slate-700 bg-slate-900 px-3 py-1.5">
          <span className="rounded bg-teal-700/80 px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-white">
            {parsed.lang}
          </span>
          <span className="text-[0.65rem] text-slate-400">{lines.length} lines</span>
        </div>
        <div className="flex max-h-[min(32rem,60vh)] overflow-auto font-mono text-[0.8rem] leading-5">
          <pre className="select-none border-r border-slate-800 bg-slate-900/80 px-2 py-3 text-right text-slate-500">
            {lines.map((_, i) => i + 1).join('\n')}
          </pre>
          <pre className="flex-1 whitespace-pre px-3 py-3 text-slate-100">
            <code>{parsed.code}</code>
          </pre>
        </div>
      </div>
    )
  }

  return (
    <p className={`mb-0 whitespace-pre-wrap text-slate-800 ${className}`}>
      {parsed.text || <span className="text-hub-muted">(empty)</span>}
    </p>
  )
}
