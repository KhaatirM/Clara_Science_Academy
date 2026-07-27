import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import {
  fetchReportCardComments,
  fetchReportCardGenerateForm,
  fetchReportCardStudentClasses,
  fetchReportCardStudentDetails,
  reportCardPdfUrl,
  submitReportCardGenerate,
} from '../api/reportCards'
import { StandardsChecklistCallout } from '../components/reportCards/StandardsChecklistCallout'
import type {
  ReportCardClassOption,
  ReportCardGenerateFormResponse,
  ReportCardStandardsChecklist,
  ReportCardStandardsMarksSummary,
  ReportCardStudentDetails,
} from '../types/reportCards'

const STEPS = ['Student', 'Confirm', 'Period', 'Classes', 'Options'] as const

export default function ReportCardGeneratePage() {
  const { studentId: studentIdParam } = useParams()
  const [searchParams] = useSearchParams()
  const category = searchParams.get('category') || ''
  const preselectedSchoolYearId = Number(searchParams.get('school_year_id') || '') || undefined
  const navigate = useNavigate()

  const preselectedId = Number(studentIdParam || '') || undefined

  const [formMeta, setFormMeta] = useState<ReportCardGenerateFormResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState(0)
  const [showWithdrawn, setShowWithdrawn] = useState(false)

  const [studentId, setStudentId] = useState<number | null>(null)
  const [studentDetails, setStudentDetails] = useState<ReportCardStudentDetails | null>(null)
  const [schoolYearId, setSchoolYearId] = useState<number | null>(null)
  const [quarters, setQuarters] = useState<string[]>(['Q1', 'Q2', 'Q3', 'Q4'])
  const [classes, setClasses] = useState<ReportCardClassOption[]>([])
  const [classesLoading, setClassesLoading] = useState(false)
  const [selectedClassIds, setSelectedClassIds] = useState<number[]>([])
  const [reportType, setReportType] = useState<'official' | 'unofficial'>('official')
  const [includeAttendance, setIncludeAttendance] = useState(false)
  const [includeComments, setIncludeComments] = useState(true)
  const [persistComments, setPersistComments] = useState(false)
  const [additionalComments, setAdditionalComments] = useState('')
  const [commentOverrides, setCommentOverrides] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [gradeAtYearDisplay, setGradeAtYearDisplay] = useState<string | null>(null)
  const [standardsChecklist, setStandardsChecklist] = useState<ReportCardStandardsChecklist | null>(null)
  const [standardsMarksSummary, setStandardsMarksSummary] = useState<ReportCardStandardsMarksSummary | null>(null)

  const loadForm = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchReportCardGenerateForm({
        studentId: preselectedId,
        category,
        schoolYearId: preselectedSchoolYearId,
      })
      setFormMeta(data)
      const initialStudent = data.preselected_student?.id ?? null
      setStudentId(initialStudent)
      setSchoolYearId(preselectedSchoolYearId ?? data.default_school_year_id)
      setStandardsChecklist(data.preselected_standards_checklist)
      if (initialStudent) setStep(1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load form.')
    } finally {
      setLoading(false)
    }
  }, [preselectedId, category, preselectedSchoolYearId])

  useEffect(() => {
    void loadForm()
  }, [loadForm])

  useEffect(() => {
    if (!studentId) {
      setStudentDetails(null)
      return
    }
    void fetchReportCardStudentDetails(studentId)
      .then((details) => {
        setStudentDetails(details)
        setStandardsChecklist(details.standards_checklist ?? null)
      })
      .catch(() => {
        setStudentDetails(null)
        setStandardsChecklist(null)
      })
  }, [studentId])

  useEffect(() => {
    if (!studentId || !schoolYearId || !quarters.length) {
      setClasses([])
      return
    }
    setClassesLoading(true)
    void fetchReportCardStudentClasses(studentId, schoolYearId, quarters)
      .then((payload) => {
        const list = payload.classes
        setClasses(list)
        setGradeAtYearDisplay(payload.grade_at_year_display ?? null)
        setStandardsChecklist(payload.standards_checklist ?? null)
        setStandardsMarksSummary(payload.standards_marks_summary ?? null)
        setSelectedClassIds((prev) => {
          const filtered = prev.filter((id) => list.some((c) => c.id === id))
          if (filtered.length) return filtered
          return list.map((c) => c.id)
        })
      })
      .catch(() => setClasses([]))
      .finally(() => setClassesLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId, schoolYearId, quarters.join(',')])

  useEffect(() => {
    if (!includeComments || !studentId || !schoolYearId || !selectedClassIds.length) return
    void fetchReportCardComments(studentId, schoolYearId, selectedClassIds).then((byClass) => {
      setCommentOverrides((prev) => ({ ...byClass, ...prev }))
    })
  }, [includeComments, studentId, schoolYearId, selectedClassIds.join(',')])

  const studentOptions = useMemo(() => {
    if (!formMeta) return []
    return formMeta.students.filter((s) => showWithdrawn || s.is_active)
  }, [formMeta, showWithdrawn])

  const selectedSchoolYear = useMemo(
    () => formMeta?.school_years.find((sy) => sy.id === schoolYearId) ?? null,
    [formMeta, schoolYearId],
  )

  const unfinalizedBanner = useMemo(() => {
    if (!formMeta || studentDetails == null) return null
    const gradeKey =
      gradeAtYearDisplay != null
        ? gradeAtYearDisplay === 'K'
          ? '0'
          : gradeAtYearDisplay
        : String(studentDetails.grade_level)
    return formMeta.warnings.banner_messages[gradeKey] || null
  }, [formMeta, studentDetails, gradeAtYearDisplay])

  const canAdvance = useMemo(() => {
    switch (step) {
      case 0:
        return studentId != null
      case 1:
        return studentDetails != null
      case 2:
        return schoolYearId != null && quarters.length > 0
      case 3:
        return selectedClassIds.length > 0
      default:
        return true
    }
  }, [step, studentId, studentDetails, selectedClassIds, schoolYearId, quarters])

  async function handleSubmit() {
    if (!studentId || !schoolYearId || !selectedClassIds.length || !quarters.length) return
    setSubmitting(true)
    setSubmitError(null)
    setWarnings([])
    try {
      const result = await submitReportCardGenerate({
        student_id: studentId,
        school_year_id: schoolYearId,
        class_ids: selectedClassIds,
        quarters,
        report_type: reportType,
        include_attendance: includeAttendance,
        include_comments: includeComments,
        persist_comment_overrides: persistComments,
        additional_comments: additionalComments,
        comment_overrides: commentOverrides,
        return_category: category || undefined,
      })
      if (!result.success || !result.report_card_id) {
        throw new Error(result.message || 'Generation failed.')
      }
      if (result.warnings?.length) setWarnings(result.warnings)
      window.open(reportCardPdfUrl(result.report_card_id), '_blank', 'noopener,noreferrer')
      if (result.urls?.return_category) {
        navigate(result.urls.return_category)
      } else if (result.urls?.view) {
        navigate(result.urls.view)
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Could not generate report card.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-hub-muted">
        Loading generate form…
      </div>
    )
  }

  if (error || !formMeta) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
        <p>{error || 'Form unavailable.'}</p>
        <Link to="/management/report-cards" className="mt-4 inline-block underline">
          Back to report cards
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-12">
      <header className="rounded-2xl border border-slate-200 bg-gradient-to-br from-violet-50 to-white p-6 shadow-sm">
        <Link
          to="/management/report-cards"
          className="text-sm font-semibold text-violet-700 hover:underline"
        >
          <i className="bi bi-arrow-left mr-1" aria-hidden />
          Back to report cards
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-hub-text">Generate report card</h1>
        <p className="mt-1 text-sm text-hub-muted">
          Build a printable PDF by selecting student, classes, and term details.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2" aria-label="Form progress">
        {STEPS.map((label, index) => (
          <button
            key={label}
            type="button"
            onClick={() => index <= step && setStep(index)}
            className={[
              'rounded-full px-4 py-1.5 text-sm font-semibold transition',
              index === step
                ? 'bg-violet-700 text-white'
                : index < step
                  ? 'bg-violet-100 text-violet-800'
                  : 'bg-slate-100 text-hub-muted',
            ].join(' ')}
          >
            {index + 1}. {label}
          </button>
        ))}
      </nav>

      {unfinalizedBanner ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <i className="bi bi-exclamation-triangle-fill mr-2" aria-hidden />
          {unfinalizedBanner}
        </div>
      ) : null}

      {warnings.length ? (
        <div className="space-y-2">
          {warnings.map((w) => (
            <div
              key={w}
              className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            >
              {w}
            </div>
          ))}
        </div>
      ) : null}

      {step === 0 ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-hub-text">Select student</h2>
          {formMeta.preselected_student ? (
            <div className="mt-4 flex items-center gap-4 rounded-xl bg-violet-50 p-4">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-200 text-violet-800">
                <i className="bi bi-person-fill" aria-hidden />
              </span>
              <div>
                <p className="font-bold">
                  {formMeta.preselected_student.first_name} {formMeta.preselected_student.last_name}
                </p>
                <p className="text-sm text-hub-muted">
                  Grade {formMeta.preselected_student.grade_display}
                </p>
              </div>
            </div>
          ) : (
            <>
              <label className="mt-4 flex items-center gap-2 text-sm text-hub-muted">
                <input
                  type="checkbox"
                  checked={showWithdrawn}
                  onChange={(e) => setShowWithdrawn(e.target.checked)}
                />
                Show withdrawn students
              </label>
              <select
                className="mt-3 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
                value={studentId ?? ''}
                onChange={(e) => setStudentId(Number(e.target.value) || null)}
              >
                <option value="">Choose a student…</option>
                {studentOptions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                    {!s.is_active ? ' (Withdrawn)' : ''}
                  </option>
                ))}
              </select>
            </>
          )}
        </section>
      ) : null}

      {step === 1 && studentDetails ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-hub-text">Confirm synced details</h2>
          <p className="mt-1 text-sm text-hub-muted">
            Pulled from the student profile. Update missing fields there before generating.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {[
              ['First name', studentDetails.first_name],
              ['Last name', studentDetails.last_name],
              ['Student ID', studentDetails.student_id],
              ['Gender', studentDetails.gender || '—'],
              ['Grade (current)', studentDetails.grade_display],
              ...(gradeAtYearDisplay
                ? [['Grade for selected year', gradeAtYearDisplay] as const]
                : []),
              ['Date of birth', studentDetails.dob || '—'],
              ['State ID', studentDetails.state_id || '—'],
              ['Entrance school year', studentDetails.entrance_date || '—'],
              ['Expected graduation', studentDetails.expected_grad_date || '—'],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-xs font-bold uppercase text-hub-muted">{label}</p>
                <p className="mt-1 text-sm font-medium text-hub-text">{value}</p>
              </div>
            ))}
            <div className="sm:col-span-2">
              <p className="text-xs font-bold uppercase text-hub-muted">Address</p>
              <p className="mt-1 text-sm font-medium text-hub-text">
                {studentDetails.address || '—'}
              </p>
            </div>
          </div>
          <Link
            to={studentDetails.profile_url}
            className="mt-4 inline-flex text-sm font-semibold text-violet-700 hover:underline"
          >
            Open student profile
          </Link>
        </section>
      ) : null}

      {step === 2 ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-hub-text">Reporting period</h2>
          <p className="mt-1 text-sm text-hub-muted">
            Choose the school year and quarters. Closed years include archived enrollments.
          </p>
          {selectedSchoolYear && !selectedSchoolYear.is_active ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-hub-muted">
              <i className="bi bi-archive mr-2" aria-hidden />
              {selectedSchoolYear.name} is a closed year. Classes from that year will be loaded from
              historical enrollments.
            </div>
          ) : null}
          <label className="mt-4 block text-sm font-semibold text-hub-text">School year</label>
          <select
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
            value={schoolYearId ?? ''}
            onChange={(e) => setSchoolYearId(Number(e.target.value) || null)}
          >
            {formMeta.school_years.map((sy) => (
              <option key={sy.id} value={sy.id}>
                {sy.name}
                {sy.is_active ? ' (active)' : ' (closed)'}
              </option>
            ))}
          </select>
          {gradeAtYearDisplay ? (
            <p className="mt-3 text-sm text-hub-muted">
              Student was in grade <span className="font-semibold text-hub-text">{gradeAtYearDisplay}</span>{' '}
              during this year.
            </p>
          ) : null}
          <p className="mt-4 text-sm font-semibold text-hub-text">Quarters to include</p>
          <div className="mt-2 flex flex-wrap gap-3">
            {formMeta.quarters.map((q) => (
              <label key={q} className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={quarters.includes(q)}
                  onChange={() =>
                    setQuarters((prev) =>
                      prev.includes(q) ? prev.filter((x) => x !== q) : [...prev, q].sort(),
                    )
                  }
                />
                {q}
              </label>
            ))}
          </div>
        </section>
      ) : null}

      {step === 3 ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-hub-text">Classes</h2>
          {classesLoading ? (
            <p className="mt-4 text-sm text-hub-muted">Loading classes…</p>
          ) : classes.length ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {classes.map((c) => {
                const checked = selectedClassIds.includes(c.id)
                return (
                  <label
                    key={c.id}
                    className={[
                      'flex cursor-pointer gap-3 rounded-xl border p-4 transition',
                      checked ? 'border-violet-400 bg-violet-50' : 'border-slate-200',
                    ].join(' ')}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        setSelectedClassIds((prev) =>
                          checked ? prev.filter((id) => id !== c.id) : [...prev, c.id],
                        )
                      }
                      className="mt-1"
                    />
                    <div>
                      <p className="font-semibold text-hub-text">{c.name}</p>
                      <p className="text-xs text-hub-muted">
                        {c.subject} · {c.teacher_name}
                      </p>
                    </div>
                  </label>
                )
              })}
            </div>
          ) : (
            <p className="mt-4 text-sm text-hub-muted">
              No classes found for this student in the selected school year and quarters. Try a
              different year or confirm the student was enrolled that year.
            </p>
          )}
        </section>
      ) : null}

      {step === 4 ? (
        <section className="space-y-6">
          <StandardsChecklistCallout checklist={standardsChecklist} marksSummary={standardsMarksSummary} />

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-bold text-hub-text">Report type</h2>
            <div className="mt-4 space-y-3">
              {(['official', 'unofficial'] as const).map((type) => (
                <label key={type} className="flex cursor-pointer items-start gap-3 rounded-xl border p-4">
                  <input
                    type="radio"
                    name="report_type"
                    checked={reportType === type}
                    onChange={() => setReportType(type)}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-semibold capitalize">{type}</p>
                    <p className="text-xs text-hub-muted">
                      {type === 'official'
                        ? 'For official records and Family Portal release.'
                        : 'Watermarked preview; not eligible for parent release.'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={includeAttendance}
                onChange={(e) => setIncludeAttendance(e.target.checked)}
              />
              <span className="text-sm font-medium">Include attendance summary</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={includeComments}
                onChange={(e) => setIncludeComments(e.target.checked)}
              />
              <span className="text-sm font-medium">Include teacher comments</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={persistComments}
                onChange={(e) => setPersistComments(e.target.checked)}
              />
              <span className="text-sm font-medium">Save comment overrides for future cards</span>
            </label>
          </div>

          {includeComments ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <h3 className="font-bold text-hub-text">Comment overrides</h3>
              {selectedClassIds.map((cid) => {
                const cls = classes.find((c) => c.id === cid)
                return (
                  <div key={cid}>
                    <label className="text-sm font-semibold">{cls?.name || `Class ${cid}`}</label>
                    <textarea
                      className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                      rows={2}
                      value={commentOverrides[String(cid)] || ''}
                      onChange={(e) =>
                        setCommentOverrides((prev) => ({ ...prev, [String(cid)]: e.target.value }))
                      }
                    />
                  </div>
                )
              })}
              <div>
                <label className="text-sm font-semibold">Additional comments</label>
                <textarea
                  className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  rows={3}
                  value={additionalComments}
                  onChange={(e) => setAdditionalComments(e.target.value)}
                />
              </div>
            </div>
          ) : null}

          {submitError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {submitError}
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="flex flex-wrap justify-between gap-3">
        <button
          type="button"
          disabled={step === 0}
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-semibold disabled:opacity-40"
        >
          Back
        </button>
        {step < STEPS.length - 1 ? (
          <button
            type="button"
            disabled={!canAdvance}
            onClick={() => setStep((s) => s + 1)}
            className="rounded-xl bg-violet-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
          >
            Continue
          </button>
        ) : (
          <button
            type="button"
            disabled={submitting || !canAdvance}
            onClick={() => void handleSubmit()}
            className="rounded-xl bg-violet-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
          >
            {submitting ? 'Generating…' : 'Generate PDF'}
          </button>
        )}
      </div>
    </div>
  )
}
