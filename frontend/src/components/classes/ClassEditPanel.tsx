import type { ReactNode } from 'react'

export function ClassEditPanel({
  icon,
  title,
  children,
  className = '',
}: {
  icon: string
  title: string
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50/80 px-4 py-2.5">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-100 text-sm text-teal-800">
          <i className={`bi ${icon}`} aria-hidden />
        </span>
        <h2 className="text-sm font-bold text-hub-text">{title}</h2>
      </div>
      <div className="p-4">{children}</div>
    </section>
  )
}
