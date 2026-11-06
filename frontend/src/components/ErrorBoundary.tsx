import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

/** Last line of defence: a crash in any screen shows this instead of a blank page. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main role="alert" className="flex min-h-dvh flex-col items-center justify-center bg-slate-50 px-6 text-center">
        <p className="font-display text-xl font-bold text-slate-900">Something went wrong</p>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          This screen hit an unexpected problem. Your saved quotations and invoices aren't affected.
        </p>
        <button onClick={() => window.location.assign('/')}
          className="mt-6 rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-orange-600">
          Reload Munim
        </button>
      </main>
    )
  }
}
