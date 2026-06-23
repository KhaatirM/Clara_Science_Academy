import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createCoreSetup, fetchCoreSetupForm, previewCoreSetup } from '../api/classes'
import { ClassSubpageShell } from '../components/classes/ClassSubpageShell'
import type { CoreSetupFormResponse, CoreSetupPreviewResult } from '../types/classDetail'

export function CoreClassSetupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<CoreSetupFormResponse | null>(null)
  const [schoolYearId, setSchoolYearId] = useState<number | ''>('')
  const [selectedGrades, setSelectedGrades] = useState<number[]>([])
  const [gradeDefaults, setGradeDefaults] = useState<Record<number, number | ''>>({})
  const [teacherAssignments, setTeacherAssignments] = useState<Record<string, number | ''>>({})
  const [preview, setPreview] = useState<CoreSetupPreviewResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    void fetchCoreSetupForm()
      .then((res) => {
        setForm(res)
        setSchoolYearId(res.default_school_year_id ?? '')
        setSelectedGrades(res.setup_grade_levels)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load core setup'))
      .finally(() => setLoading(false))
  }, [])

  const visibleGrades = useMemo(
    () => (form?.grades || []).filter((g) => selectedGrades.includes(g.grade_level)),
    [form, selectedGrades],
  )

  const buildBody = useCallback(() => {
    const assignments: Record<string, number> = {}
    Object.entries(teacherAssignments).forEach(([k, v]) => {
      if (v) assignments[k] = Number(v)
    })
    const defaults: Record<string, number> = {}
    Object.entries(gradeDefaults).forEach(([k, v]) => {
      if (v) defaults[k] = Number(v)
    })
    return {
      school_year_id: schoolYearId,
      grade_levels: selectedGrades,
      teacher_assignments: assignments,
      grade_default_teachers: defaults,
    }
  }, [gradeDefaults, schoolYearId, selectedGrades, teacherAssignments])

  const onPreview = async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await previewCoreSetup(buildBody())
      if (!res.success) throw new Error(res.message || 'Preview failed')
      setPreview(res.preview)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setBusy(false)
    }
  }

  const onCreate = async () => {
    if (!window.confirm('Create core classes for the selected grades?')) return
    setBusy(true)
    setError(null)
    try {
      const res = await createCoreSetup(buildBody())
      if (!res.success) throw new Error(res.message)
      setMessage(res.message)
      if (res.redirect) setTimeout(() => navigate('/management/classes'), 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed')
    } finally {
      setBusy(false)
    }
  }

  const toggleGrade = (g: number) => {
    setSelectedGrades((prev) => (prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g].sort((a, b) => a - b)))
  }

  const applyGradeDefault = (grade: number) => {
    const tid = gradeDefaults[grade]
    if (!tid || !form) return
    const gradeData = form.grades.find((g) => g.grade_level === grade)
    if (!gradeData) return
    setTeacherAssignments((prev) => {
      const next = { ...prev }
      gradeData.entries.forEach((e) => {
        next[e.assignment_key] = tid
      })
      return next
    })
  }

  return (
    <ClassSubpageShell
      eyebrow="School year planning"
      title="Core class setup"
      subtitle="Auto-create required K–8 core classes for a school year."
    >
      {loading ? <p className="text-hub-muted">Loading…</p> : null}
      {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}
      {message ? <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{message}</div> : null}
      {form ? (
        <div className="space-y-5">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <label className="mb-1 block text-sm font-medium text-hub-muted">School year</label>
            <select
              value={schoolYearId}
              onChange={(e) => setSchoolYearId(e.target.value ? Number(e.target.value) : '')}
              className="w-full max-w-md rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
            >
              {form.school_years.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                  {y.is_active ? ' (Active)' : ''}
                </option>
              ))}
            </select>
            <p className="mt-4 mb-2 text-sm font-medium text-hub-muted">Grade levels</p>
            <div className="flex flex-wrap gap-2">
              {form.setup_grade_levels.map((g) => {
                const label = form.grades.find((x) => x.grade_level === g)?.label || `Grade ${g}`
                return (
                  <button
                    key={g}
                    type="button"
                    onClick={() => toggleGrade(g)}
                    className={[
                      'rounded-full px-3 py-1 text-xs font-semibold',
                      selectedGrades.includes(g) ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-700',
                    ].join(' ')}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </section>

          {visibleGrades.map((grade) => (
            <section key={grade.grade_level} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
                <h2 className="text-lg font-bold text-hub-text">{grade.label}</h2>
                <div className="flex items-end gap-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-hub-muted">Grade primary teacher</label>
                    <select
                      value={gradeDefaults[grade.grade_level] ?? ''}
                      onChange={(e) =>
                        setGradeDefaults((prev) => ({
                          ...prev,
                          [grade.grade_level]: e.target.value ? Number(e.target.value) : '',
                        }))
                      }
                      className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                    >
                      <option value="">Optional shortcut</option>
                      {form.teachers.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.display_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => applyGradeDefault(grade.grade_level)}
                    className="rounded-full border border-teal-300 bg-teal-50 px-3 py-2 text-xs font-semibold text-teal-800"
                  >
                    Apply to all subjects
                  </button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs font-bold uppercase text-hub-muted">
                      <th className="px-3 py-2">Subject</th>
                      <th className="px-3 py-2">Class name</th>
                      <th className="px-3 py-2">Primary teacher</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grade.entries.map((entry) => (
                      <tr key={entry.assignment_key} className="border-b border-slate-100">
                        <td className="px-3 py-2">{entry.subject}</td>
                        <td className="px-3 py-2 font-medium">{entry.class_name}</td>
                        <td className="px-3 py-2">
                          <select
                            value={teacherAssignments[entry.assignment_key] ?? ''}
                            onChange={(e) =>
                              setTeacherAssignments((prev) => ({
                                ...prev,
                                [entry.assignment_key]: e.target.value ? Number(e.target.value) : '',
                              }))
                            }
                            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5"
                          >
                            <option value="">Select teacher</option>
                            {form.teachers.map((t) => (
                              <option key={t.id} value={t.id}>
                                {t.display_name}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void onPreview()}
              className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
            >
              Preview
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onCreate()}
              className="rounded-full bg-gradient-to-br from-teal-600 to-teal-800 px-4 py-2 text-sm font-semibold text-white"
            >
              Create core classes
            </button>
          </div>

          {preview ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 font-bold text-hub-text">Preview</h2>
              {preview.errors?.length ? (
                <ul className="mb-3 list-disc pl-5 text-sm text-amber-800">
                  {preview.errors.map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              ) : null}
              <p className="text-sm text-hub-muted">
                To create: <strong>{preview.to_create?.length ?? 0}</strong> · Skipped:{' '}
                <strong>{preview.skipped?.length ?? 0}</strong>
              </p>
            </section>
          ) : null}
        </div>
      ) : null}
    </ClassSubpageShell>
  )
}
