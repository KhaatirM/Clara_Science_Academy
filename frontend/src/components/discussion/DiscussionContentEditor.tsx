import { useId, useState } from 'react'
import {
  DISCUSSION_CODE_LANGS,
  formatDiscussionContent,
  parseDiscussionContent,
  type DiscussionEditorMode,
} from '../../utils/discussionContent'

export const discFieldClass =
  'block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-teal-600 focus:ring-2 focus:ring-teal-600/25 disabled:cursor-not-allowed disabled:bg-slate-50'

type Props = {
  /** Stored content (may include [DISCUSSION_CODE:lang] prefix). */
  value: string
  onChange: (stored: string) => void
  textPlaceholder?: string
  codePlaceholder?: string
  required?: boolean
  disabled?: boolean
  rows?: number
  id?: string
  label?: string
}

/**
 * Text / Code paste editor that serializes to the legacy `[DISCUSSION_CODE:lang]` format.
 */
export function DiscussionContentEditor({
  value,
  onChange,
  textPlaceholder = 'Share your thoughts, ideas, or questions…',
  codePlaceholder = 'Paste or type your code here…',
  required = false,
  disabled = false,
  rows = 8,
  id,
  label = 'Your post',
}: Props) {
  const autoId = useId()
  const fieldId = id || `disc-content-${autoId}`
  const initial = parseDiscussionContent(value)
  const [mode, setMode] = useState<DiscussionEditorMode>(
    initial.kind === 'code' ? 'code' : 'text',
  )
  const [lang, setLang] = useState(initial.kind === 'code' ? initial.lang : 'python')
  const [draft, setDraft] = useState(initial.kind === 'code' ? initial.code : initial.text)

  function emit(nextMode: DiscussionEditorMode, nextDraft: string, nextLang: string) {
    onChange(formatDiscussionContent(nextMode, nextDraft, nextLang))
  }

  function switchMode(next: DiscussionEditorMode) {
    if (next === mode) return
    setMode(next)
    emit(next, draft, lang)
  }

  const lineCount = Math.max(1, draft.split('\n').length)

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={fieldId} className="mb-0 text-sm font-semibold text-slate-800">
          {label}
          {required ? <span className="ms-0.5 text-red-600">*</span> : null}
        </label>
        <div className="inline-flex overflow-hidden rounded-lg border border-slate-300 bg-white text-sm">
          <button
            type="button"
            disabled={disabled}
            className={`px-3 py-1.5 font-semibold transition ${
              mode === 'text'
                ? 'bg-teal-700 text-white'
                : 'bg-white text-slate-700 hover:bg-slate-50'
            }`}
            onClick={() => switchMode('text')}
          >
            <i className="bi bi-chat-text me-1" aria-hidden />
            Text
          </button>
          <button
            type="button"
            disabled={disabled}
            className={`border-l border-slate-300 px-3 py-1.5 font-semibold transition ${
              mode === 'code'
                ? 'bg-teal-700 text-white'
                : 'bg-white text-slate-700 hover:bg-slate-50'
            }`}
            onClick={() => switchMode('code')}
          >
            <i className="bi bi-code-slash me-1" aria-hidden />
            Code
          </button>
        </div>
      </div>

      {mode === 'code' ? (
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={`${fieldId}-lang`} className="text-xs font-semibold text-hub-muted">
            Language
          </label>
          <select
            id={`${fieldId}-lang`}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 shadow-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/25"
            value={lang}
            disabled={disabled}
            onChange={(e) => {
              const nextLang = e.target.value
              setLang(nextLang)
              emit('code', draft, nextLang)
            }}
          >
            {DISCUSSION_CODE_LANGS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {mode === 'text' ? (
        <textarea
          id={fieldId}
          className={`${discFieldClass} min-h-[12rem] resize-y leading-relaxed`}
          rows={rows}
          value={draft}
          disabled={disabled}
          required={required}
          placeholder={textPlaceholder}
          onChange={(e) => {
            const next = e.target.value
            setDraft(next)
            emit('text', next, lang)
          }}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-300 bg-slate-950 shadow-inner">
          <div className="flex max-h-[min(28rem,55vh)] overflow-auto font-mono text-[0.8rem] leading-5">
            <pre
              className="select-none border-r border-slate-700 bg-slate-900 px-2 py-3 text-right text-slate-500"
              aria-hidden
            >
              {Array.from({ length: lineCount }, (_, i) => i + 1).join('\n')}
            </pre>
            <textarea
              id={fieldId}
              className="block min-h-[16rem] w-full flex-1 resize-y border-0 bg-transparent px-3 py-3 font-mono text-slate-100 outline-none placeholder:text-slate-500 focus:ring-0"
              rows={Math.max(rows, 10)}
              value={draft}
              disabled={disabled}
              required={required}
              spellCheck={false}
              placeholder={codePlaceholder}
              onChange={(e) => {
                const next = e.target.value
                setDraft(next)
                emit('code', next, lang)
              }}
              onKeyDown={(e) => {
                if (e.key !== 'Tab') return
                e.preventDefault()
                const el = e.currentTarget
                const start = el.selectionStart
                const end = el.selectionEnd
                const next = `${draft.slice(0, start)}  ${draft.slice(end)}`
                setDraft(next)
                emit('code', next, lang)
                requestAnimationFrame(() => {
                  el.selectionStart = el.selectionEnd = start + 2
                })
              }}
            />
          </div>
        </div>
      )}

      <p className="mb-0 text-xs text-hub-muted">
        {mode === 'code'
          ? 'Code mode wraps your paste with a language badge and line numbers when others read it.'
          : 'Be thoughtful and respectful. Switch to Code to paste snippets with line numbers.'}
      </p>
    </div>
  )
}
