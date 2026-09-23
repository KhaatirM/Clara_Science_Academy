/** Discussion post content: plain text or `[DISCUSSION_CODE:lang]\\n…` (legacy format). */

export const DISCUSSION_CODE_LANGS = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'c', label: 'C' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'sql', label: 'SQL' },
  { value: 'text', label: 'Plain text' },
] as const

export type DiscussionEditorMode = 'text' | 'code'

export type ParsedDiscussionContent =
  | { kind: 'text'; text: string }
  | { kind: 'code'; lang: string; code: string }

const CODE_PREFIX = '[DISCUSSION_CODE:'

export function parseDiscussionContent(raw: string | null | undefined): ParsedDiscussionContent {
  const s = String(raw ?? '')
  if (!s.startsWith(CODE_PREFIX)) {
    return { kind: 'text', text: s }
  }
  try {
    const end = s.indexOf(']')
    if (end < 0) return { kind: 'text', text: s }
    const lang = s.slice(CODE_PREFIX.length, end).trim() || 'text'
    const code = s.slice(end + 1).replace(/^\r?\n/, '')
    return { kind: 'code', lang, code }
  } catch {
    return { kind: 'text', text: s }
  }
}

export function formatDiscussionContent(
  mode: DiscussionEditorMode,
  textOrCode: string,
  lang = 'python',
): string {
  const body = textOrCode.replace(/\r\n/g, '\n')
  if (mode === 'code') {
    const safeLang = (lang || 'text').trim() || 'text'
    return `${CODE_PREFIX}${safeLang}]\n${body}`
  }
  return body
}

export function discussionContentPreview(raw: string | null | undefined, maxlen = 180): string {
  const parsed = parseDiscussionContent(raw)
  if (parsed.kind === 'code') {
    const prefix = `[${parsed.lang} code] `
    const full = prefix + parsed.code
    return full.length > maxlen ? `${full.slice(0, maxlen)}…` : full
  }
  const s = parsed.text.trim()
  return s.length > maxlen ? `${s.slice(0, maxlen)}…` : s
}
