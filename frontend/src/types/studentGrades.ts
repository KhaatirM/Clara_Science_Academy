export type GradeBand = 'a' | 'b' | 'c' | 'd' | null

export interface StudentGradeStanding {
  key: 'honor' | 'good' | 'improve' | 'warning'
  label: string
  icon: string
}

export interface StudentGradePeriod {
  name: string
  status: 'in_progress' | 'calculating' | 'released' | string
  average: number | null
  letter: string | null
  gpa: number | null
  assignments: number
  end_date: string | null
  end_display: string | null
  band: GradeBand
}

export interface StudentGradeRecentAssignment {
  title: string
  score: number
  letter: string
  band: GradeBand
  graded_display: string | null
}

export interface StudentGradeAssignmentDetail {
  title: string
  percentage: number
  display: string
  letter: string
  band: GradeBand
  is_group: boolean
  graded_at: string | null
}

export interface StudentGradeClass {
  id: number
  name: string
  subject: string
  teacher_name: string
  final_grade: {
    letter: string
    percentage: number
    band: GradeBand
  }
  class_gpa: number
  graded_count: number
  recent_assignments: StudentGradeRecentAssignment[]
  assignment_details: StudentGradeAssignmentDetail[]
  quarter_grades: StudentGradePeriod[]
  semester_grades: StudentGradePeriod[]
  links: {
    open_class: string
    assignments: string
  }
}

export interface StudentGradesResponse {
  has_active_school_year: boolean
  school_year_name: string | null
  gpa: number
  standing: StudentGradeStanding
  quarters: StudentGradePeriod[]
  semesters: StudentGradePeriod[]
  classes: StudentGradeClass[]
  class_count: number
  graded_class_count: number
}
