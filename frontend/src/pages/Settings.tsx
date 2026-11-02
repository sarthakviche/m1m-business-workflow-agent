import { useState } from 'react'
import { api } from '../api/client'
import type { TelegramLinkCode } from '../api/client'
import { IconCheck, IconCopy, IconTelegram } from '../components/icons'
import { Button, Card, CardHeader, Page, PageHeader } from '../components/ui'
import { useApp } from '../context/AppContext'

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="px-5 py-3.5 sm:grid sm:grid-cols-3 sm:gap-4">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-slate-900 sm:col-span-2 sm:mt-0">{value || '—'}</dd>
    </div>
  )
}

function TelegramConnect() {
  const [link, setLink] = useState<TelegramLinkCode | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  async function generate() {
    setBusy(true)
    setError(null)
    setCopied(false)
    try {
      setLink(await api.createTelegramLinkCode())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create a code.')
    } finally {
      setBusy(false)
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  const command = link ? `/link ${link.code}` : ''
  const expires = link ? new Date(link.expires_at).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) : ''

  return (
    <Card>
      <CardHeader title="Telegram" />
      <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-sky-50 text-sky-600"><IconTelegram size={22} /></span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-900">Use Munim from Telegram</p>
          <p className="mt-1 text-sm text-slate-500">
            Create quotations and invoices from your phone and get the PDF right in the chat.
            Generate a one-time code, then send it to the Munim bot.
          </p>

          {link ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Send this to the bot</p>
              <div className="mt-2 flex items-center gap-2">
                <code className="flex-1 rounded-lg bg-white px-3 py-2 font-mono text-base font-semibold tracking-wider text-slate-900 ring-1 ring-slate-200">{command}</code>
                <Button variant="secondary" className="px-3" onClick={() => copy(command)} aria-label="Copy command">
                  {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                </Button>
              </div>
              <p className="mt-2 text-xs text-slate-500">Works once · expires at {expires}</p>
            </div>
          ) : null}

          {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}

          <Button className="mt-4" onClick={generate} disabled={busy}>
            {busy ? 'Creating…' : link ? 'Generate a new code' : 'Generate link code'}
          </Button>
        </div>
      </div>
    </Card>
  )
}

export default function Settings() {
  const { business } = useApp()

  return (
    <Page>
      <PageHeader title="Settings" description="Your business details and connected apps." />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Business profile" />
          <dl className="divide-y divide-slate-100">
            <Field label="Business name" value={business?.business_name} />
            <Field label="GSTIN" value={business?.gstin} />
            <Field label="State" value={business?.state} />
            <Field label="Address" value={business?.address} />
          </dl>
          <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
            These details are printed on every quotation and invoice. The state decides CGST + SGST versus IGST.
          </p>
        </Card>
        <TelegramConnect />
      </div>
    </Page>
  )
}
