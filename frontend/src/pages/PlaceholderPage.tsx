interface PlaceholderPageProps {
  title: string
  description: string
  legacyPath: string
}

export function PlaceholderPage({ title, description, legacyPath }: PlaceholderPageProps) {
  return (
    <div className="rounded-3xl border border-white/90 bg-white/90 p-6 shadow-xl md:p-8">
      <p className="text-xs font-semibold uppercase tracking-wider text-hub-muted">
        Not migrated yet
      </p>
      <h1 className="mt-1 text-3xl font-extrabold text-hub-text">{title}</h1>
      <p className="mt-3 max-w-2xl text-hub-muted">{description}</p>
      <p className="mt-2 text-sm text-hub-muted">
        Use the sidebar to open the live legacy page, or the button below.
      </p>
      <a
        href={legacyPath}
        className="mt-6 inline-flex items-center gap-2 rounded-xl bg-hub-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-hub-accent-deep"
      >
        <i className="bi bi-box-arrow-up-right" aria-hidden />
        Open legacy {title.toLowerCase()}
      </a>
    </div>
  )
}
