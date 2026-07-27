export type CleaningDeductions = {
  bathroom_not_restocked: boolean
  trash_can_left_full: boolean
  floor_not_swept: boolean
  materials_left_out: boolean
  tables_missed: boolean
  classroom_trash_full: boolean
  bathroom_floor_poor: boolean
  not_finished_on_time: boolean
  small_debris_left: boolean
  trash_spilled: boolean
  dispensers_half_filled: boolean
}

export type CleaningBonuses = {
  exceptional_finish: boolean
  speed_efficiency: boolean
  going_above_beyond: boolean
  teamwork_award: boolean
}

export function calculateCleaningInspectionScore(
  deductions: CleaningDeductions,
  bonuses: CleaningBonuses,
): {
  final_score: number
  major_deductions: number
  moderate_deductions: number
  minor_deductions: number
  bonus_points: number
} {
  let score = 100
  let major = 0
  let moderate = 0
  let minor = 0

  if (deductions.bathroom_not_restocked) {
    score -= 10
    major += 10
  }
  if (deductions.trash_can_left_full) {
    score -= 10
    major += 10
  }
  if (deductions.floor_not_swept) {
    score -= 10
    major += 10
  }
  if (deductions.materials_left_out) {
    score -= 10
    major += 10
  }
  if (deductions.tables_missed) {
    score -= 5
    moderate += 5
  }
  if (deductions.classroom_trash_full) {
    score -= 5
    moderate += 5
  }
  if (deductions.bathroom_floor_poor) {
    score -= 5
    moderate += 5
  }
  if (deductions.not_finished_on_time) {
    score -= 5
    moderate += 5
  }
  if (deductions.small_debris_left) {
    score -= 2
    minor += 2
  }
  if (deductions.trash_spilled) {
    score -= 2
    minor += 2
  }
  if (deductions.dispensers_half_filled) {
    score -= 2
    minor += 2
  }

  let bonus = 0
  if (bonuses.exceptional_finish) bonus += 5
  if (bonuses.speed_efficiency) bonus += 5
  if (bonuses.going_above_beyond) bonus += 3
  if (bonuses.teamwork_award) bonus += 2
  score += bonus

  return {
    final_score: score,
    major_deductions: major,
    moderate_deductions: moderate,
    minor_deductions: minor,
    bonus_points: bonus,
  }
}

export function scoreBadgeClass(score: number): string {
  if (score <= 60) return 'bg-red-100 text-red-800'
  if (score < 80) return 'bg-amber-100 text-amber-900'
  return 'bg-emerald-100 text-emerald-800'
}
