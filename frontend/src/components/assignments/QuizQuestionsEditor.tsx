import { useId } from 'react'
import { FieldLabel, inputClass } from './AssignmentCreateLayout'

export type QuizQuestionDraft = {
  id: string
  questionText: string
  questionType: 'multiple_choice' | 'true_false' | 'short_answer'
  points: string
  options: string[]
  correctIndex: string
  correctTrueFalse: 'true' | 'false'
}

export function createEmptyQuestion(id: string): QuizQuestionDraft {
  return {
    id,
    questionText: '',
    questionType: 'multiple_choice',
    points: '1',
    options: ['', '', '', ''],
    correctIndex: '0',
    correctTrueFalse: 'true',
  }
}

export function QuizQuestionsEditor({
  questions,
  onChange,
  onAdd,
  onRemove,
}: {
  questions: QuizQuestionDraft[]
  onChange: (questions: QuizQuestionDraft[]) => void
  onAdd: () => void
  onRemove: (id: string) => void
}) {
  const baseId = useId()

  const updateQuestion = (id: string, patch: Partial<QuizQuestionDraft>) => {
    onChange(questions.map((q) => (q.id === id ? { ...q, ...patch } : q)))
  }

  const updateOption = (questionId: string, optionIndex: number, value: string) => {
    onChange(
      questions.map((q) => {
        if (q.id !== questionId) return q
        const options = [...q.options]
        options[optionIndex] = value
        return { ...q, options }
      }),
    )
  }

  return (
    <div className="space-y-4">
      {questions.map((q, index) => (
        <div key={q.id} className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-slate-800">Question {index + 1}</h3>
            {questions.length > 1 ? (
              <button
                type="button"
                onClick={() => onRemove(q.id)}
                className="text-xs font-semibold text-red-600 hover:text-red-800"
              >
                Remove
              </button>
            ) : null}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <FieldLabel htmlFor={`${baseId}-${q.id}-text`} required>
                Question text
              </FieldLabel>
              <textarea
                id={`${baseId}-${q.id}-text`}
                className={inputClass()}
                rows={3}
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
                    className={inputClass('flex-1')}
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

          {q.questionType === 'short_answer' ? (
            <p className="mt-2 text-xs text-slate-500">Short-answer questions are graded manually after submission.</p>
          ) : null}
        </div>
      ))}

      <button
        type="button"
        onClick={onAdd}
        className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-100"
      >
        <i className="bi bi-plus-lg" aria-hidden />
        Add question
      </button>
    </div>
  )
}

export function appendQuizQuestionsToForm(form: FormData, questions: QuizQuestionDraft[]) {
  const blockOrder = questions.map((q) => `question_${q.id}`).join(',')
  form.append('block_order', blockOrder)
  form.append('assignment_type', 'quiz')

  questions.forEach((q) => {
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
  })
}

export function appendGroupQuizQuestionsToForm(form: FormData, questions: QuizQuestionDraft[]) {
  questions.forEach((q) => {
    form.append(`question_text_${q.id}`, q.questionText.trim())
    form.append(`question_type_${q.id}`, q.questionType)
    form.append(`question_points_${q.id}`, q.points || '1')
    if (q.questionType === 'multiple_choice') {
      form.append(`correct_answer_${q.id}`, q.correctIndex)
      q.options.forEach((opt) => {
        if (opt.trim()) form.append(`option_text_${q.id}[]`, opt.trim())
      })
    } else if (q.questionType === 'true_false') {
      form.append(`correct_answer_${q.id}`, q.correctTrueFalse === 'true' ? '0' : '1')
      form.append(`option_text_${q.id}[]`, 'True')
      form.append(`option_text_${q.id}[]`, 'False')
    }
  })
}
