import { formatGradeLabel, gradeBadgeClass, type GradeDisplayValue } from '../../utils/gradeDisplay'

export function GradeBadge({ grade, bold }: { grade: GradeDisplayValue; bold?: boolean }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-[0.68rem] font-semibold ${gradeBadgeClass(grade)} ${
        bold ? 'font-bold' : ''
      }`}
    >
      {formatGradeLabel(grade)}
    </span>
  )
}
