import { Link } from 'react-router-dom'

export function AssignmentCreateHeader({
  title,
  subtitle,
  icon,
  backTo,
  backLabel = 'Back',
  badge,
}: {
  title: string
  subtitle: string
  icon: string
  backTo: string
  backLabel?: string
  badge?: string | null
}) {
  return (
    <header className="mb-6 rounded-[20px] bg-gradient-to-br from-[#667eea] to-[#764ba2] px-6 py-5 text-white shadow-[0_10px_40px_rgba(102,126,234,0.28)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="mb-1 flex items-center gap-2 text-2xl font-bold">
            <i className={`bi ${icon}`} aria-hidden />
            {title}
          </h1>
          <p className="text-[0.95rem] text-white/90">{subtitle}</p>
          {badge ? (
            <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold">
              <i className="bi bi-book" aria-hidden />
              {badge}
            </p>
          ) : null}
        </div>
        <Link
          to={backTo}
          className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-[#667eea] hover:bg-white/95"
        >
          <i className="bi bi-arrow-left" aria-hidden />
          {backLabel}
        </Link>
      </div>
    </header>
  )
}

export function FormSection({
  title,
  icon,
  tone = 'primary',
  children,
}: {
  title: string
  icon: string
  tone?: 'primary' | 'info' | 'success' | 'warning' | 'purple' | 'emerald'
  children: React.ReactNode
}) {
  const headerClass: Record<string, string> = {
    primary: 'bg-blue-600',
    info: 'bg-cyan-600',
    success: 'bg-emerald-600',
    warning: 'bg-amber-500 text-amber-950',
    purple: 'bg-gradient-to-r from-indigo-600 to-violet-700',
    emerald: 'bg-gradient-to-r from-emerald-500 to-teal-600',
  }
  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className={`px-4 py-3 text-white ${headerClass[tone]}`}>
        <h2 className="flex items-center gap-2 text-base font-bold">
          <i className={`bi ${icon}`} aria-hidden />
          {title}
        </h2>
      </div>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  )
}

export function FieldLabel({
  htmlFor,
  children,
  required,
}: {
  htmlFor?: string
  children: React.ReactNode
  required?: boolean
}) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-sm font-semibold text-slate-700">
      {children}
      {required ? <span className="text-red-600"> *</span> : null}
    </label>
  )
}

export function inputClass(extra = '') {
  return `w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200 ${extra}`
}

export function FormLoading({ label }: { label: string }) {
  return <div className="rounded-2xl bg-white p-10 text-center text-hub-muted shadow-sm">{label}</div>
}

export function FormError({ message, backTo }: { message: string; backTo: string }) {
  return (
    <div className="rounded-2xl bg-white p-8 shadow-sm">
      <p className="text-red-700">{message}</p>
      <Link to={backTo} className="mt-4 inline-block text-sm font-semibold text-teal-700">
        Back
      </Link>
    </div>
  )
}
