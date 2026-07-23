import type { TeacherClassViewStudent } from '../../types/teacherClassView'

type Props = {
  open: boolean
  className: string
  students: TeacherClassViewStudent[]
  onClose: () => void
}

export function TeacherClassRosterModal({ open, className, students, onClose }: Props) {
  if (!open) return null

  return (
    <div className="teacher-class-roster-modal" onClick={onClose} role="presentation">
      <div
        className="teacher-class-roster-modal__panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="teacher-class-roster-title"
      >
        <div className="teacher-class-roster-modal__header">
          <div>
            <h2 id="teacher-class-roster-title" className="teacher-class-roster-modal__title">
              <i className="bi bi-people-fill me-2" aria-hidden />
              Class roster
            </h2>
            <p className="teacher-class-roster-modal__subtitle">
              {className} · {students.length} {students.length === 1 ? 'student' : 'students'}
            </p>
          </div>
          <button type="button" className="teacher-class-roster-modal__close" onClick={onClose} aria-label="Close">
            <i className="bi bi-x-lg" aria-hidden />
          </button>
        </div>

        <div className="teacher-class-roster-modal__body">
          {students.length === 0 ? (
            <div className="teacher-class-empty-state">
              <i className="bi bi-people" aria-hidden />
              <p>No students are currently enrolled in this class.</p>
            </div>
          ) : (
            <div className="teacher-class-roster-modal__table-wrap">
              <table className="teacher-class-roster-modal__table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Grade</th>
                    <th>Student ID</th>
                    <th>Email</th>
                    <th>School email</th>
                    <th>Parent / guardian</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr key={student.id}>
                      <td>
                        <div className="teacher-class-roster-modal__student">
                          <img src={student.photo_url} alt="" className="teacher-class-roster-modal__avatar" />
                          <div>
                            <div className="teacher-class-roster-modal__name">{student.display_name}</div>
                            {student.date_of_birth_display ? (
                              <div className="teacher-class-roster-modal__meta">DOB: {student.date_of_birth_display}</div>
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td>{student.grade_label}</td>
                      <td>{student.student_id || '—'}</td>
                      <td>
                        {student.email ? (
                          <a href={`mailto:${student.email}`} className="teacher-class-roster-modal__link">
                            {student.email}
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        {student.school_email ? (
                          <a href={`mailto:${student.school_email}`} className="teacher-class-roster-modal__link">
                            {student.school_email}
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        {student.parent1_name || student.parent1_email || student.parent1_phone ? (
                          <div className="teacher-class-roster-modal__parent">
                            {student.parent1_name ? <div>{student.parent1_name}</div> : null}
                            {student.parent1_email ? (
                              <a href={`mailto:${student.parent1_email}`} className="teacher-class-roster-modal__link">
                                {student.parent1_email}
                              </a>
                            ) : null}
                            {student.parent1_phone ? <div>{student.parent1_phone}</div> : null}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        <div className="teacher-class-roster-modal__actions">
                          <a href={student.links.grades} className="teacher-class-roster-modal__action">
                            Grades
                          </a>
                          <a href={student.links.attendance} className="teacher-class-roster-modal__action">
                            Attendance
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
