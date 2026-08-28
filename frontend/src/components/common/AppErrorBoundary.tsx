import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null; stack: string | null }

/** Keeps a render failure from blanking the whole portal. */
export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null, stack: null }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState({ stack: info.componentStack ?? null })
    console.error('Portal render error:', error, info.componentStack)
  }

  render() {
    const { error, stack } = this.state
    if (!error) return this.props.children

    return (
      <div className="mx-auto my-10 max-w-2xl rounded-2xl border border-red-200 bg-white p-6 shadow-sm">
        <h1 className="mb-2 text-xl font-bold text-red-900">Something went wrong on this page</h1>
        <p className="mb-4 text-sm text-hub-muted">
          The rest of the portal is still available. Reload to try again, and share the details
          below if the problem repeats.
        </p>
        <pre className="mb-4 max-h-64 overflow-auto rounded-xl bg-slate-50 p-3 text-xs text-slate-800">
          {error.message}
          {stack ? `\n${stack}` : ''}
        </pre>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800"
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
          <button
            type="button"
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            onClick={() => this.setState({ error: null, stack: null })}
          >
            Try again
          </button>
        </div>
      </div>
    )
  }
}
