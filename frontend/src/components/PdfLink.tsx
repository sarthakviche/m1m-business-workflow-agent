import { useState } from 'react'
import type { ReactNode } from 'react'
import { openDocument } from '../api/client'

/** Opens a generated PDF using the login token, with a busy state and visible failure. */
export default function PdfLink({ pdfUrl, label, className, children }:
  { pdfUrl: string; label?: string; className: string; children: ReactNode }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function open() {
    setBusy(true)
    setError(null)
    try {
      await openDocument(pdfUrl)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't open this PDF.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button type="button" onClick={open} disabled={busy} aria-label={label} title={error ?? undefined}
        className={`${className} ${busy ? 'cursor-wait opacity-60' : ''} ${error ? 'text-red-600' : ''}`}>
        {children}
      </button>
      {error && <span role="alert" className="sr-only">{error}</span>}
    </>
  )
}
