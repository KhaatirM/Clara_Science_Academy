import { useCallback, useId, useState } from 'react'
import { FieldLabel, inputClass } from './AssignmentCreateLayout'
import {
  createEmptyQuestion,
  type QuizQuestionDraft,
} from './QuizQuestionsEditor'

export type QuizBlock =
  | { kind: 'section'; id: string; title: string }
  | { kind: 'question'; question: QuizQuestionDraft }

type BankQuestion = {
  id: number
  question_text: string
  question_type: string
  points: number
  options?: { option_text: string; is_correct: boolean }[]
}

type QuestionBank = {
  id: number
  name: string
  description?: string
  questions: BankQuestion[]
}

function nextBlockId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
}

function questionTypeLabel(type: string) {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function bankQuestionToDraft(q: BankQuestion): QuizQuestionDraft {
  const id = nextBlockId('q')
  const draft = createEmptyQuestion(id)
  draft.questionText = q.question_text
  const allowed: QuizQuestionDraft['questionType'][] = [
    'multiple_choice',
    'true_false',
    'short_answer',
    'essay',
  ]
  draft.questionType = allowed.includes(q.question_type as QuizQuestionDraft['questionType'])
    ? (q.question_type as QuizQuestionDraft['questionType'])
    : 'multiple_choice'
  draft.points = String(q.points || 1)
  if (q.question_type === 'multiple_choice' && q.options?.length) {
    const opts = q.options.map((o) => o.option_text)
    while (opts.length < 4) opts.push('')
    draft.options = opts.slice(0, 8)
    const correctIdx = q.options.findIndex((o) => o.is_correct)
    draft.correctIndex = String(correctIdx >= 0 ? correctIdx : 0)
  } else if (q.question_type === 'true_false' && q.options?.length) {
    const trueOpt = q.options.find((o) => o.option_text.toLowerCase() === 'true')
    draft.correctTrueFalse = trueOpt?.is_correct ? 'true' : 'false'
  }
  return draft
}

type BulkTab = 'count' | 'paste' | 'csv'

const QUIZ_CSV_TEMPLATE =
  'question_number,section,question_text,question_type,points,option_a,option_b,option_c,option_d,correct\n' +
  '1,"Part A","What is 2+2?",multiple_choice,1,3,4,5,6,B\n' +
  '2,"Part A","The sky is blue.",true_false,1,,,,,true\n' +
  '3,"Part B","Explain your reasoning.",short_answer,2,,,,,\n'

function parseCsvLine(line: string): string[] {
  const out: string[] = []
  let cur = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"'
        i += 1
      } else {
        inQuotes = !inQuotes
      }
    } else if (ch === ',' && !inQuotes) {
      out.push(cur)
      cur = ''
    } else {
      cur += ch
    }
  }
  out.push(cur)
  return out.map((v) => (v || '').trim())
}

function normalizeCsvHeader(h: string) {
  return (h || '')
    .toLowerCase()
    .trim()
    .replace(/^"|"$/g, '')
    .replace(/\s+/g, '_')
}

type ParsedCsvQuestion = {
  questionNumber: number
  sectionTitle: string
  questionText: string
  questionType: QuizQuestionDraft['questionType']
  points: number
  options: string[]
  correctIndex: string
  correctTrueFalse: 'true' | 'false'
}

function parseQuizCsv(text: string): QuizBlock[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
  if (lines.length < 2) {
    throw new Error('CSV must include a header row and at least one data row.')
  }

  const headers = parseCsvLine(lines[0]).map(normalizeCsvHeader)
  const idxAny = (...names: string[]) => {
    for (const n of names) {
      const i = headers.indexOf(n)
      if (i >= 0) return i
    }
    return -1
  }

  const numberIdx = idxAny(
    'question_number',
    'question_num',
    'question_no',
    'q_number',
    'number',
    'order',
    'num',
  )
  if (numberIdx < 0) {
    throw new Error(
      'CSV must include a question_number column so questions can be ordered correctly.',
    )
  }

  const qTextIdx = idxAny('question_text', 'question', 'text')
  const typeIdx = idxAny('question_type', 'type')
  const pointsIdx = idxAny('points', 'pts', 'point')
  const sectionIdx = idxAny('section', 'section_title', 'part', 'part_title')
  const correctIdx = idxAny('correct', 'correct_answer', 'answer')

  const optionCols: { idx: number; label: string }[] = []
  headers.forEach((h, i) => {
    if (/^option_[a-h]$/.test(h)) {
      optionCols.push({ idx: i, label: h.replace('option_', '').toUpperCase() })
    }
    if (/^option[1-8]$/.test(h)) {
      optionCols.push({
        idx: i,
        label: String.fromCharCode(64 + Number.parseInt(h.replace('option', ''), 10)),
      })
    }
  })
  optionCols.sort((a, b) => a.idx - b.idx)

  const parsed: ParsedCsvQuestion[] = []
  const seenNumbers = new Set<number>()

  for (let i = 1; i < lines.length; i += 1) {
    const row = parseCsvLine(lines[i]).map((v) => v.replace(/^"|"$/g, '').trim())
    const questionText = (qTextIdx >= 0 ? row[qTextIdx] : row[0] || '').trim()
    if (!questionText) continue

    const numberRaw = (row[numberIdx] || '').trim()
    const questionNumber = Number.parseInt(numberRaw, 10)
    if (!Number.isFinite(questionNumber) || questionNumber < 1) {
      throw new Error(
        `Row ${i + 1}: question_number must be a positive integer (got "${numberRaw || 'blank'}").`,
      )
    }
    if (seenNumbers.has(questionNumber)) {
      throw new Error(`Row ${i + 1}: duplicate question_number ${questionNumber}.`)
    }
    seenNumbers.add(questionNumber)

    const rawType = ((typeIdx >= 0 ? row[typeIdx] : '') || 'multiple_choice')
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '_')
    const allowed: QuizQuestionDraft['questionType'][] = [
      'multiple_choice',
      'true_false',
      'short_answer',
      'essay',
    ]
    const questionType = allowed.includes(rawType as QuizQuestionDraft['questionType'])
      ? (rawType as QuizQuestionDraft['questionType'])
      : 'multiple_choice'
    const points = Number.parseFloat(pointsIdx >= 0 ? row[pointsIdx] || '' : '') || 1
    const sectionTitle = (sectionIdx >= 0 ? row[sectionIdx] || '' : '').trim()

    let options: string[] = ['', '', '', '']
    let correctIndex = '0'
    let correctTrueFalse: 'true' | 'false' = 'true'

    if (questionType === 'multiple_choice') {
      const correctRaw = (correctIdx >= 0 ? row[correctIdx] || '' : '').trim()
      const correctLetter = (correctRaw || 'A').toUpperCase().charAt(0)
      const colsToUse =
        optionCols.length > 0
          ? optionCols
          : [
              { idx: 4, label: 'A' },
              { idx: 5, label: 'B' },
              { idx: 6, label: 'C' },
              { idx: 7, label: 'D' },
            ]
      options = []
      colsToUse.forEach((c, optIdx) => {
        const opt = (row[c.idx] || '').trim()
        if (opt) {
          if (c.label === correctLetter) correctIndex = String(options.length)
          options.push(opt)
        } else if (optIdx < 4) {
          options.push('')
        }
      })
      while (options.length < 4) options.push('')
    } else if (questionType === 'true_false') {
      const correctRaw = (correctIdx >= 0 ? row[correctIdx] || '' : 'true').trim().toLowerCase()
      correctTrueFalse =
        correctRaw === 'false' || correctRaw === 'f' || correctRaw === '0' ? 'false' : 'true'
    }

    parsed.push({
      questionNumber,
      sectionTitle,
      questionText,
      questionType,
      points,
      options,
      correctIndex,
      correctTrueFalse,
    })
  }

  if (!parsed.length) {
    throw new Error('No questions found in the CSV file.')
  }

  parsed.sort((a, b) => a.questionNumber - b.questionNumber)

  const newBlocks: QuizBlock[] = []
  let lastSectionTitle: string | null = null

  for (const item of parsed) {
    if (item.sectionTitle && item.sectionTitle !== lastSectionTitle) {
      newBlocks.push({ kind: 'section', id: nextBlockId('s'), title: item.sectionTitle })
      lastSectionTitle = item.sectionTitle
    }

    const draft = createEmptyQuestion(nextBlockId('q'))
    draft.questionText = item.questionText
    draft.questionType = item.questionType
    draft.points = String(item.points)
    draft.options = item.options
    draft.correctIndex = item.correctIndex
    draft.correctTrueFalse = item.correctTrueFalse
    newBlocks.push({ kind: 'question', question: draft })
  }

  return newBlocks
}

function downloadQuizCsvTemplate() {
  const blob = new Blob([QUIZ_CSV_TEMPLATE], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'quiz_bulk_import_template.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function appendQuizBlocksToForm(form: FormData, blocks: QuizBlock[]) {
  const blockOrder = blocks
    .map((b) => (b.kind === 'section' ? `section_${b.id}` : `question_${b.question.id}`))
    .join(',')
  form.append('block_order', blockOrder)
  form.append('assignment_type', 'quiz')

  for (const block of blocks) {
    if (block.kind === 'section') {
      form.append(`section_title_${block.id}`, block.title.trim() || 'Section')
      continue
    }
    const q = block.question
    form.append(`question_text_${q.id}`, q.questionText.trim())
    form.append(`question_type_${q.id}`, q.questionType)
    form.append(`question_points_${q.id}`, q.points || '1')
    if (q.questionType === 'multiple_choice') {
      form.append(`correct_answer_${q.id}`, q.correctIndex)
      q.options.forEach((opt) => {
        if (opt.trim()) form.append(`option_text_${q.id}[]`, opt.trim())
      })
    } else if (q.questionType === 'true_false') {
      form.append(`correct_answer_${q.id}`, q.correctTrueFalse)
    }
  }
}

export function QuizAuthoringBlocksEditor({
  blocks,
  onChange,
  questionBanksUrl,
  saveToBankUrl,
}: {
  blocks: QuizBlock[]
  onChange: (blocks: QuizBlock[]) => void
  questionBanksUrl?: string | null
  saveToBankUrl?: string | null
}) {
  const baseId = useId()
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkTab, setBulkTab] = useState<BulkTab>('count')
  const [bankOpen, setBankOpen] = useState(false)
  const [bulkCount, setBulkCount] = useState('5')
  const [bulkType, setBulkType] = useState<QuizQuestionDraft['questionType']>('multiple_choice')
  const [pasteLines, setPasteLines] = useState('')
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [csvError, setCsvError] = useState<string | null>(null)
  const [csvHelpOpen, setCsvHelpOpen] = useState(false)
  const [csvImporting, setCsvImporting] = useState(false)
  const [banks, setBanks] = useState<QuestionBank[]>([])
  const [banksLoading, setBanksLoading] = useState(false)
  const [bankError, setBankError] = useState<string | null>(null)
  const [saveBankName, setSaveBankName] = useState('')
  const [saveBankQuestionId, setSaveBankQuestionId] = useState<string | null>(null)

  const updateQuestion = (questionId: string, patch: Partial<QuizQuestionDraft>) => {
    onChange(
      blocks.map((b) =>
        b.kind === 'question' && b.question.id === questionId
          ? { ...b, question: { ...b.question, ...patch } }
          : b,
      ),
    )
  }

  const updateOption = (questionId: string, optionIndex: number, value: string) => {
    onChange(
      blocks.map((b) => {
        if (b.kind !== 'question' || b.question.id !== questionId) return b
        const options = [...b.question.options]
        options[optionIndex] = value
        return { ...b, question: { ...b.question, options } }
      }),
    )
  }

  const removeBlock = (index: number) => {
    if (blocks.length <= 1) return
    onChange(blocks.filter((_, i) => i !== index))
  }

  /** Move a single block (section header or question) so sections can sit between questions. */
  const moveBlock = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= blocks.length) return
    const next = [...blocks]
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }

  const BlockMoveControls = ({ index }: { index: number }) => (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => moveBlock(index, -1)}
        disabled={index === 0}
        title="Move up"
        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <i className="bi bi-arrow-up" aria-hidden />
        <span className="sr-only">Move up</span>
      </button>
      <button
        type="button"
        onClick={() => moveBlock(index, 1)}
        disabled={index >= blocks.length - 1}
        title="Move down"
        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <i className="bi bi-arrow-down" aria-hidden />
        <span className="sr-only">Move down</span>
      </button>
    </div>
  )

  const addQuestion = () => {
    onChange([...blocks, { kind: 'question', question: createEmptyQuestion(nextBlockId('q')) }])
  }

  const addSection = () => {
    const sectionCount = blocks.filter((b) => b.kind === 'section').length
    onChange([
      ...blocks,
      { kind: 'section', id: nextBlockId('s'), title: `Part ${sectionCount + 1}` },
    ])
  }

  const bulkAddQuestions = (count: number, type: QuizQuestionDraft['questionType']) => {
    const newBlocks: QuizBlock[] = []
    for (let i = 0; i < count; i += 1) {
      const q = createEmptyQuestion(nextBlockId('q'))
      q.questionType = type
      newBlocks.push({ kind: 'question', question: q })
    }
    onChange([...blocks, ...newBlocks])
    setBulkOpen(false)
  }

  const bulkAddFromPaste = () => {
    const lines = pasteLines.split(/\n/).map((l) => l.trim()).filter(Boolean)
    if (!lines.length) return
    const newBlocks: QuizBlock[] = lines.map((line) => {
      const q = createEmptyQuestion(nextBlockId('q'))
      q.questionText = line
      q.questionType = 'short_answer'
      return { kind: 'question', question: q }
    })
    onChange([...blocks, ...newBlocks])
    setPasteLines('')
    setBulkOpen(false)
  }

  const bulkAddFromCsv = async () => {
    if (!csvFile) {
      setCsvError('Choose a CSV file first.')
      return
    }
    setCsvImporting(true)
    setCsvError(null)
    try {
      const text = await csvFile.text()
      const imported = parseQuizCsv(text)
      // CSV import replaces the current quiz authoring blocks so order/sections match the file.
      onChange(imported)
      setCsvFile(null)
      setCsvHelpOpen(false)
      setBulkOpen(false)
    } catch (e) {
      setCsvError(e instanceof Error ? e.message : 'Could not import CSV')
    } finally {
      setCsvImporting(false)
    }
  }

  const loadBanks = useCallback(async () => {
    if (!questionBanksUrl) return
    setBanksLoading(true)
    setBankError(null)
    try {
      const res = await fetch(questionBanksUrl, { credentials: 'include' })
      if (!res.ok) throw new Error('Could not load question banks')
      const data = (await res.json()) as QuestionBank[]
      setBanks(Array.isArray(data) ? data : [])
    } catch (e) {
      setBankError(e instanceof Error ? e.message : 'Could not load question banks')
    } finally {
      setBanksLoading(false)
    }
  }, [questionBanksUrl])

  const saveQuestionToBank = async (question: QuizQuestionDraft) => {
    if (!saveToBankUrl || !saveBankName.trim() || !question.questionText.trim()) return
    const payload: Record<string, unknown> = {
      name: saveBankName.trim(),
      questions: [
        {
          question_text: question.questionText.trim(),
          question_type: question.questionType,
          points: Number(question.points) || 1,
          options:
            question.questionType === 'multiple_choice'
              ? question.options
                  .filter((o) => o.trim())
                  .map((option_text, idx) => ({
                    option_text,
                    is_correct: String(idx) === question.correctIndex,
                  }))
              : question.questionType === 'true_false'
                ? [
                    { option_text: 'True', is_correct: question.correctTrueFalse === 'true' },
                    { option_text: 'False', is_correct: question.correctTrueFalse === 'false' },
                  ]
                : [],
        },
      ],
    }
    const res = await fetch(saveToBankUrl, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { message?: string } | null
      throw new Error(body?.message || 'Could not save to bank')
    }
    setSaveBankQuestionId(null)
    setSaveBankName('')
  }

  const importBankQuestion = (bq: BankQuestion) => {
    onChange([...blocks, { kind: 'question', question: bankQuestionToDraft(bq) }])
    setBankOpen(false)
  }

  let questionNum = 0

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={addQuestion}
          className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-800 hover:bg-indigo-100"
        >
          <i className="bi bi-plus-lg" />
          Add question
        </button>
        <button
          type="button"
          onClick={addSection}
          className="inline-flex items-center gap-1.5 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-semibold text-violet-800 hover:bg-violet-100"
        >
          <i className="bi bi-collection" />
          Add section
        </button>
        <button
          type="button"
          onClick={() => {
            setBulkTab('count')
            setCsvError(null)
            setCsvFile(null)
            setCsvHelpOpen(false)
            setBulkOpen(true)
          }}
          className="inline-flex items-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-800 hover:bg-teal-100"
        >
          <i className="bi bi-stack" />
          Bulk add
        </button>
        {questionBanksUrl ? (
          <button
            type="button"
            onClick={() => {
              setBankOpen(true)
              void loadBanks()
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900 hover:bg-amber-100"
          >
            <i className="bi bi-journal-bookmark" />
            Question bank
          </button>
        ) : null}
      </div>

      {blocks.map((block, index) => {
        if (block.kind === 'section') {
          return (
            <div
              key={block.id}
              className="rounded-xl border-2 border-dashed border-violet-300 bg-violet-50/60 p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex flex-1 items-center gap-2">
                  <i className="bi bi-bookmark-fill text-violet-700" />
                  <input
                    className={inputClass('font-bold')}
                    value={block.title}
                    onChange={(e) =>
                      onChange(
                        blocks.map((b, i) =>
                          i === index && b.kind === 'section' ? { ...b, title: e.target.value } : b,
                        ),
                      )
                    }
                    placeholder="Section title (e.g. Part A)"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <BlockMoveControls index={index} />
                  <button
                    type="button"
                    onClick={() => removeBlock(index)}
                    className="quiz-action-btn quiz-action-btn--remove group inline-flex items-center gap-1 rounded-full border border-red-200 bg-white px-2.5 py-1 text-xs font-bold text-red-600 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-red-400 hover:bg-red-50 hover:text-red-700 hover:shadow-md active:translate-y-0 active:scale-95"
                  >
                    <i className="bi bi-trash3 transition-transform duration-200 group-hover:animate-[quiz-btn-wiggle_360ms_ease-in-out]" aria-hidden />
                    Remove
                  </button>
                </div>
              </div>
            </div>
          )
        }

        questionNum += 1
        const q = block.question
        return (
          <div key={q.id} className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-slate-800">Question {questionNum}</h3>
              <div className="flex flex-wrap items-center gap-2">
                <BlockMoveControls index={index} />
                {saveToBankUrl ? (
                  <button
                    type="button"
                    onClick={() => setSaveBankQuestionId(q.id)}
                    className="quiz-action-btn quiz-action-btn--bank group inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-amber-500 hover:bg-amber-100 hover:text-amber-950 hover:shadow-md active:translate-y-0 active:scale-95"
                  >
                    <i className="bi bi-journal-bookmark transition-transform duration-200 group-hover:animate-[quiz-btn-bob_420ms_ease-in-out]" aria-hidden />
                    Save to bank
                  </button>
                ) : null}
                {blocks.filter((b) => b.kind === 'question').length > 1 ? (
                  <button
                    type="button"
                    onClick={() => removeBlock(index)}
                    className="quiz-action-btn quiz-action-btn--remove group inline-flex items-center gap-1 rounded-full border border-red-200 bg-white px-2.5 py-1 text-xs font-bold text-red-600 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-red-400 hover:bg-red-50 hover:text-red-700 hover:shadow-md active:translate-y-0 active:scale-95"
                  >
                    <i className="bi bi-trash3 transition-transform duration-200 group-hover:animate-[quiz-btn-wiggle_360ms_ease-in-out]" aria-hidden />
                    Remove
                  </button>
                ) : null}
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <FieldLabel htmlFor={`${baseId}-${q.id}-text`} required>
                  Question text
                </FieldLabel>
                <textarea
                  id={`${baseId}-${q.id}-text`}
                  className={inputClass()}
                  rows={q.questionType === 'essay' ? 4 : 3}
                  value={q.questionText}
                  onChange={(e) => updateQuestion(q.id, { questionText: e.target.value })}
                  required
                />
              </div>
              <div>
                <FieldLabel htmlFor={`${baseId}-${q.id}-type`}>Type</FieldLabel>
                <select
                  id={`${baseId}-${q.id}-type`}
                  className={inputClass()}
                  value={q.questionType}
                  onChange={(e) =>
                    updateQuestion(q.id, {
                      questionType: e.target.value as QuizQuestionDraft['questionType'],
                    })
                  }
                >
                  <option value="multiple_choice">Multiple choice</option>
                  <option value="true_false">True / false</option>
                  <option value="short_answer">Short answer</option>
                  <option value="essay">Long essay</option>
                </select>
              </div>
              <div>
                <FieldLabel htmlFor={`${baseId}-${q.id}-points`}>Points</FieldLabel>
                <input
                  id={`${baseId}-${q.id}-points`}
                  type="number"
                  min="0.1"
                  step="0.1"
                  className={inputClass()}
                  value={q.points}
                  onChange={(e) => updateQuestion(q.id, { points: e.target.value })}
                />
              </div>
            </div>

            {q.questionType === 'multiple_choice' ? (
              <div className="mt-3 space-y-2">
                <p className="text-xs font-semibold text-slate-600">Answer options (mark correct)</p>
                {q.options.map((opt, optIdx) => (
                  <label key={`${q.id}-opt-${optIdx}`} className="flex items-center gap-2">
                    <input
                      type="radio"
                      name={`correct-${q.id}`}
                      checked={q.correctIndex === String(optIdx)}
                      onChange={() => updateQuestion(q.id, { correctIndex: String(optIdx) })}
                    />
                    <input
                      className={`${inputClass()} flex-1`}
                      value={opt}
                      onChange={(e) => updateOption(q.id, optIdx, e.target.value)}
                      placeholder={`Option ${String.fromCharCode(65 + optIdx)}`}
                    />
                  </label>
                ))}
              </div>
            ) : null}

            {q.questionType === 'true_false' ? (
              <div className="mt-3 flex gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`tf-${q.id}`}
                    checked={q.correctTrueFalse === 'true'}
                    onChange={() => updateQuestion(q.id, { correctTrueFalse: 'true' })}
                  />
                  True is correct
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`tf-${q.id}`}
                    checked={q.correctTrueFalse === 'false'}
                    onChange={() => updateQuestion(q.id, { correctTrueFalse: 'false' })}
                  />
                  False is correct
                </label>
              </div>
            ) : null}

            {q.questionType === 'short_answer' || q.questionType === 'essay' ? (
              <p className="mt-2 text-xs text-slate-500">
                {q.questionType === 'essay'
                  ? 'Essay responses are graded manually after students submit.'
                  : 'Short-answer questions are graded manually after submission.'}
              </p>
            ) : null}

            {saveBankQuestionId === q.id ? (
              <div className="mt-3 flex flex-wrap items-end gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
                <div className="min-w-[12rem] flex-1">
                  <FieldLabel htmlFor={`${baseId}-bank-name`}>Bank name</FieldLabel>
                  <input
                    id={`${baseId}-bank-name`}
                    className={inputClass()}
                    value={saveBankName}
                    onChange={(e) => setSaveBankName(e.target.value)}
                    placeholder="e.g. Biology unit 3"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => void saveQuestionToBank(q)}
                  className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-semibold text-white"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setSaveBankQuestionId(null)}
                  className="text-sm text-slate-600"
                >
                  Cancel
                </button>
              </div>
            ) : null}
          </div>
        )
      })}

      {bulkOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-xl">
            <div className="rounded-t-2xl bg-gradient-to-r from-blue-600 to-blue-800 px-6 py-4 text-white">
              <h3 className="text-lg font-bold">
                <i className="bi bi-collection me-2" aria-hidden />
                Bulk add questions
              </h3>
            </div>
            <div className="px-6 py-4">
              <div className="mb-4 flex border-b border-slate-200 text-sm font-semibold">
                {(
                  [
                    { id: 'count' as const, label: 'Add N questions' },
                    { id: 'paste' as const, label: 'Paste list' },
                    { id: 'csv' as const, label: 'Import CSV' },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => {
                      setBulkTab(tab.id)
                      setCsvError(null)
                    }}
                    className={`-mb-px border-b-2 px-3 py-2 transition ${
                      bulkTab === tab.id
                        ? 'border-blue-600 text-hub-text'
                        : 'border-transparent text-blue-700 hover:text-blue-900'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {bulkTab === 'count' ? (
                <div className="space-y-3">
                  <p className="text-sm text-hub-muted">
                    Add several empty questions at once, then fill them in.
                  </p>
                  <FieldLabel htmlFor={`${baseId}-bulk-count`}>Number of questions</FieldLabel>
                  <div className="mb-2 flex flex-wrap gap-2">
                    {[5, 10, 20, 50].map((n) => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setBulkCount(String(n))}
                        className={`rounded-lg border px-3 py-1.5 text-sm font-semibold ${
                          bulkCount === String(n)
                            ? 'border-blue-600 bg-blue-600 text-white'
                            : 'border-blue-300 bg-white text-blue-800 hover:bg-blue-50'
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      id={`${baseId}-bulk-count`}
                      type="number"
                      min="1"
                      max="100"
                      className={`${inputClass()} w-32`}
                      value={bulkCount}
                      onChange={(e) => setBulkCount(e.target.value)}
                      placeholder="e.g. 15"
                    />
                  </div>
                  <div>
                    <FieldLabel htmlFor={`${baseId}-bulk-type`}>Default type</FieldLabel>
                    <select
                      id={`${baseId}-bulk-type`}
                      className={inputClass()}
                      value={bulkType}
                      onChange={(e) =>
                        setBulkType(e.target.value as QuizQuestionDraft['questionType'])
                      }
                    >
                      <option value="multiple_choice">Multiple Choice</option>
                      <option value="true_false">True/False</option>
                      <option value="short_answer">Short Answer</option>
                      <option value="essay">Essay</option>
                    </select>
                  </div>
                </div>
              ) : null}

              {bulkTab === 'paste' ? (
                <div className="space-y-3">
                  <p className="text-sm text-hub-muted">
                    Paste one question per line. Each line becomes one question (short answer by
                    default).
                  </p>
                  <textarea
                    id={`${baseId}-paste`}
                    className={`${inputClass()} font-mono`}
                    rows={10}
                    value={pasteLines}
                    onChange={(e) => setPasteLines(e.target.value)}
                    placeholder={'Question 1 text\nQuestion 2 text\nQuestion 3 text'}
                  />
                </div>
              ) : null}

              {bulkTab === 'csv' ? (
                <div className="space-y-3">
                  <p className="text-sm text-hub-muted">
                    Upload a CSV file. First row must be headers. Import{' '}
                    <strong>replaces</strong> all current questions and sections.
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      className={`${inputClass()} min-w-0 flex-1`}
                      onChange={(e) => {
                        setCsvFile(e.target.files?.[0] || null)
                        setCsvError(null)
                      }}
                    />
                    <button
                      type="button"
                      onClick={downloadQuizCsvTemplate}
                      className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                      title="Download CSV template"
                    >
                      <i className="bi bi-download" aria-hidden />
                      Template
                    </button>
                    <button
                      type="button"
                      onClick={() => setCsvHelpOpen((v) => !v)}
                      className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-sky-300 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800 hover:bg-sky-100"
                      title="CSV format help"
                      aria-expanded={csvHelpOpen}
                    >
                      <i className="bi bi-info-circle" aria-hidden />
                      Format help
                    </button>
                  </div>
                  {csvHelpOpen ? (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
                      <p className="font-bold text-hub-text">Required columns:</p>
                      <ul className="mb-2 list-disc space-y-0.5 ps-4">
                        <li>
                          <code>question_number</code> – positive integer used to order questions
                          (1, 2, 3…)
                        </li>
                        <li>
                          <code>question_text</code> – the question
                        </li>
                        <li>
                          <code>question_type</code> – one of:{' '}
                          <code>multiple_choice</code>, <code>true_false</code>,{' '}
                          <code>short_answer</code>, <code>essay</code>
                        </li>
                        <li>
                          <code>points</code> – number (e.g. 1 or 2.5)
                        </li>
                      </ul>
                      <p className="font-bold text-hub-text">Optional columns:</p>
                      <ul className="mb-2 list-disc space-y-0.5 ps-4">
                        <li>
                          <code>section</code> – section/part title. After sorting by{' '}
                          <code>question_number</code>, a section header is inserted whenever this
                          value changes.
                        </li>
                      </ul>
                      <p className="font-bold text-hub-text">For multiple choice only:</p>
                      <ul className="mb-2 list-disc space-y-0.5 ps-4">
                        <li>
                          <code>option_a</code>, <code>option_b</code>, <code>option_c</code>,{' '}
                          <code>option_d</code> – answer choices
                        </li>
                        <li>
                          <code>correct</code> – letter of correct answer: <code>A</code>,{' '}
                          <code>B</code>, <code>C</code>, or <code>D</code>
                        </li>
                      </ul>
                      <p className="font-bold text-hub-text">Example (first row = headers):</p>
                      <pre className="mt-1 overflow-x-auto rounded-lg border border-slate-200 bg-white p-2 text-[0.7rem]">
                        {QUIZ_CSV_TEMPLATE.trim()}
                      </pre>
                    </div>
                  ) : null}
                  {csvError ? <p className="text-sm font-semibold text-red-700">{csvError}</p> : null}
                </div>
              ) : null}
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 px-6 py-4">
              <button
                type="button"
                onClick={() => setBulkOpen(false)}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={csvImporting}
                onClick={() => {
                  if (bulkTab === 'count') {
                    bulkAddQuestions(
                      Math.min(100, Math.max(1, Number(bulkCount) || 1)),
                      bulkType,
                    )
                  } else if (bulkTab === 'paste') {
                    bulkAddFromPaste()
                  } else {
                    void bulkAddFromCsv()
                  }
                }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
              >
                <i className="bi bi-plus-circle" aria-hidden />
                {csvImporting ? 'Importing…' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {bankOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-hub-text">Import from question bank</h3>
            {banksLoading ? <p className="mt-4 text-sm text-hub-muted">Loading banks…</p> : null}
            {bankError ? <p className="mt-4 text-sm text-red-700">{bankError}</p> : null}
            <div className="mt-4 space-y-4">
              {banks.map((bank) => (
                <div key={bank.id} className="rounded-xl border border-slate-200 p-4">
                  <h4 className="font-bold text-hub-text">{bank.name}</h4>
                  {bank.description ? (
                    <p className="text-xs text-hub-muted">{bank.description}</p>
                  ) : null}
                  <ul className="mt-2 space-y-2">
                    {bank.questions.map((bq) => (
                      <li
                        key={bq.id}
                        className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm"
                      >
                        <div>
                          <span className="font-medium">{bq.question_text}</span>
                          <span className="ms-2 text-xs text-hub-muted">
                            {questionTypeLabel(bq.question_type)} · {bq.points} pts
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => importBankQuestion(bq)}
                          className="shrink-0 text-xs font-semibold text-teal-800"
                        >
                          Import
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {!banksLoading && !banks.length && !bankError ? (
                <p className="text-sm text-hub-muted">No question banks yet. Save questions to a bank first.</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => setBankOpen(false)}
              className="mt-6 text-sm font-semibold text-slate-600"
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
