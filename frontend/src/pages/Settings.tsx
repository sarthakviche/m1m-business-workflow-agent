import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api/client'
import type { TelegramLinkCode } from '../api/client'
import { IconCheck, IconCopy, IconTelegram } from '../components/icons'
import { Button, Card, CardHeader, Page, PageHeader } from '../components/ui'
import { useApp } from '../context/AppContext'
import { GSTIN_PATTERN, INDIAN_STATES } from '../lib/gst'
import { supabase } from '../lib/supabase'

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="px-5 py-3.5 sm:grid sm:grid-cols-3 sm:gap-4">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-slate-900 sm:col-span-2 sm:mt-0">{value || '—'}</dd>
    </div>
  )
}

const inputCls =
  'w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100'

function BusinessProfileCard() {
  const { business, saveBusiness } = useApp()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState('')
  const [state, setState] = useState('')
  const [gstin, setGstin] = useState('')
  const [address, setAddress] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const gstinValue = gstin.trim().toUpperCase()
  const gstinError = gstinValue && !GSTIN_PATTERN.test(gstinValue) ? 'GSTIN should look like 27ABCDE1234F1Z5' : null

  function startEditing() {
    setName(business?.business_name ?? '')
    setState(business?.state ?? '')
    setGstin(business?.gstin ?? '')
    setAddress(business?.address ?? '')
    setError(null)
    setEditing(true)
  }

  async function save(e: FormEvent) {
    e.preventDefault()
    if (gstinError) return
    setSaving(true)
    setError(null)
    try {
      await saveBusiness({ business_name: name.trim(), state, gstin: gstinValue, address: address.trim() })
      setEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save your details.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Business profile" action={!editing && <Button variant="ghost" className="px-3 py-1.5" onClick={startEditing}>Edit</Button>} />
      {editing ? (
        <form onSubmit={save} className="flex flex-col gap-4 p-5">
          <div>
            <label htmlFor="biz-name" className="mb-1.5 block text-sm font-medium text-slate-700">Business name</label>
            <input id="biz-name" className={inputCls} value={name} required onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label htmlFor="biz-state" className="mb-1.5 block text-sm font-medium text-slate-700">State</label>
            <select id="biz-state" className={inputCls} value={state} required onChange={(e) => setState(e.target.value)}>
              {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              {state && !(INDIAN_STATES as readonly string[]).includes(state) && <option value={state}>{state}</option>}
            </select>
          </div>
          <div>
            <label htmlFor="biz-gstin" className="mb-1.5 block text-sm font-medium text-slate-700">GSTIN</label>
            <input id="biz-gstin" className={`${inputCls} uppercase`} value={gstin} maxLength={15} placeholder="27ABCDE1234F1Z5"
              aria-invalid={!!gstinError} onChange={(e) => setGstin(e.target.value)} />
            {gstinError && <p className="mt-1 text-xs font-medium text-red-600">{gstinError}</p>}
          </div>
          <div>
            <label htmlFor="biz-address" className="mb-1.5 block text-sm font-medium text-slate-700">Address</label>
            <textarea id="biz-address" rows={3} maxLength={500} className={inputCls} value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={saving || !name.trim() || !!gstinError}>{saving ? 'Saving…' : 'Save changes'}</Button>
            <Button type="button" variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </form>
      ) : (
        <dl className="divide-y divide-slate-100">
          <Field label="Business name" value={business?.business_name} />
          <Field label="GSTIN" value={business?.gstin} />
          <Field label="State" value={business?.state} />
          <Field label="Address" value={business?.address} />
        </dl>
      )}
      <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
        These details are printed on every quotation and invoice. The state decides CGST + SGST versus IGST.
      </p>
    </Card>
  )
}

function AccountCard() {
  const { email, signOut } = useApp()
  return (
    <Card>
      <CardHeader title="Account" />
      <div className="flex items-center justify-between gap-4 p-5">
        <div className="min-w-0">
          <p className="text-sm text-slate-500">Signed in as</p>
          <p className="truncate text-sm font-medium text-slate-900">{email ?? '—'}</p>
        </div>
        <Button variant="secondary" onClick={() => void signOut()}>Sign out</Button>
      </div>
    </Card>
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
  return (
    <Page>
      <PageHeader title="Settings" description="Your business details and connected apps." />
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
        <BusinessProfileCard />
        <div className="flex flex-col gap-6">
          <TelegramConnect />
          {supabase && <AccountCard />}
        </div>
      </div>
    </Page>
  )
}
