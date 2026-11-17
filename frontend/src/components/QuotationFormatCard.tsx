// "Use my own quotation format": upload a quotation you already send, Munim reads
// its layout, you check it and preview a sample, then every new quotation follows it.

import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { FormatAnalysis, QuotationFormat } from '../api/client'
import { IconCheck, IconEye, IconFile, IconUpload } from './icons'
import { Badge, Button, Card, CardHeader } from './ui'

const ACCEPT = '.pdf,.png,.jpg,.jpeg,.webp,.docx,.xlsx'

const inputCls =
  'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100'

const FIELD_NAMES: Record<string, string> = {
  business_name: 'Your business name', business_address: 'Your address', business_gstin: 'Your GSTIN',
  business_phone: 'Your phone', business_email: 'Your email',
  customer_name: 'Customer name', customer_address: 'Customer address', customer_gstin: 'Customer GSTIN',
  customer_phone: 'Customer phone', quotation_number: 'Quotation number', date: 'Date', valid_until: 'Validity',
  item_table: 'Item table', subtotal: 'Subtotal', tax: 'GST', grand_total: 'Grand total',
  amount_in_words: 'Amount in words', other: 'Not filled automatically',
}

const lines = (text: string) => text.split('\n').map((l) => l.trim()).filter(Boolean)

export default function QuotationFormatCard() {
  const [saved, setSaved] = useState<FormatAnalysis | null>(null)
  const [draft, setDraft] = useState<FormatAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<null | 'reading' | 'saving' | 'preview' | 'reset'>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.quotationFormat()
      .then(setSaved)
      .catch(() => setSaved(null))
      .finally(() => setLoading(false))
  }, [])

  const shown = draft ?? saved
  const fmt = shown?.format

  function edit(changes: Partial<QuotationFormat>) {
    if (!shown) return
    setDraft({ ...shown, format: { ...shown.format, ...changes } })
    setNotice(null)
  }

  async function run<T>(kind: NonNullable<typeof busy>, task: () => Promise<T>): Promise<T | undefined> {
    setBusy(kind)
    setError(null)
    setNotice(null)
    try {
      return await task()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
      return undefined
    } finally {
      setBusy(null)
    }
  }

  async function upload(file: File | undefined) {
    if (!file) return
    const result = await run('reading', () => api.analyzeQuotationFormat(file))
    if (result) setDraft(result)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function save() {
    if (!draft) return
    const result = await run('saving', () => api.saveQuotationFormat(draft.format))
    if (result) {
      setSaved(result)
      setDraft(null)
      setNotice('Saved. New quotations from the web and Telegram now use your format.')
    }
  }

  async function reset() {
    const done = await run('reset', async () => { await api.resetQuotationFormat(); return true })
    if (done) {
      setSaved(null)
      setDraft(null)
      setNotice('Back to the standard Munim quotation.')
    }
  }

  return (
    <Card>
      <CardHeader title="Quotation format" action={saved && !draft ? <Badge tone="green">Your format is on</Badge> : undefined} />
      <div className="flex flex-col gap-4 p-5">
        <input ref={fileRef} type="file" accept={ACCEPT} className="hidden" onChange={(e) => void upload(e.target.files?.[0])} />

        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : !fmt ? (
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-orange-50 text-orange-600"><IconFile size={22} /></span>
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-slate-900">Use your own quotation format</p>
              <p className="mt-1 text-sm text-slate-500">
                Upload a quotation you already send (PDF, photo, Word or Excel). Munim reads its title, columns, terms and bank details,
                and new quotations follow it. Prices and GST still come from your catalog.
              </p>
              <Button className="mt-4" onClick={() => fileRef.current?.click()} disabled={busy === 'reading'}>
                <IconUpload size={16} /> {busy === 'reading' ? 'Reading your format…' : 'Upload a sample quotation'}
              </Button>
              {busy === 'reading' && <p className="mt-2 text-xs text-slate-500">This takes about 10–20 seconds.</p>}
            </div>
          </div>
        ) : (
          <>
            {draft && (
              <p className="rounded-xl bg-orange-50 px-4 py-3 text-sm text-orange-800">
                Here's what we read{fmt.source_filename ? ` from ${fmt.source_filename}` : ''}. Check it, preview a sample, then save.
              </p>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="text-sm">
                <span className="mb-1 block font-medium text-slate-700">Title</span>
                <input className={inputCls} value={fmt.title} maxLength={40} onChange={(e) => edit({ title: e.target.value })} />
              </label>
              <label className="text-sm">
                <span className="mb-1 block font-medium text-slate-700">Customer label</span>
                <input className={inputCls} value={fmt.party_label} maxLength={40} onChange={(e) => edit({ party_label: e.target.value })} />
              </label>
              <label className="text-sm">
                <span className="mb-1 block font-medium text-slate-700">Signature line</span>
                <input className={inputCls} value={fmt.signatory_label} maxLength={40} onChange={(e) => edit({ signatory_label: e.target.value })} />
              </label>
              <label className="text-sm">
                <span className="mb-1 block font-medium text-slate-700">Valid for (days)</span>
                <input className={inputCls} type="number" min={1} max={365} value={fmt.validity_days ?? ''} placeholder="30"
                  onChange={(e) => edit({ validity_days: e.target.value ? Math.max(1, Math.min(365, Number(e.target.value))) : null })} />
              </label>
            </div>

            <div>
              <p className="mb-1.5 text-sm font-medium text-slate-700">Item table columns</p>
              <div className="flex flex-wrap gap-1.5">
                {fmt.columns.map((c) => (
                  <span key={c.key} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">{c.label}</span>
                ))}
              </div>
            </div>

            {fmt.accent_color && (
              <p className="flex items-center gap-2 text-sm text-slate-600">
                <span className="h-4 w-4 rounded" style={{ background: fmt.accent_color }} aria-hidden /> Accent colour {fmt.accent_color.toUpperCase()}
              </p>
            )}

            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-700">Terms &amp; conditions <span className="font-normal text-slate-400">one per line</span></span>
              <textarea className={`${inputCls} min-h-24`} value={fmt.terms.join('\n')}
                onChange={(e) => edit({ terms: lines(e.target.value).slice(0, 12) })} />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-700">Bank details <span className="font-normal text-slate-400">one per line</span></span>
              <textarea className={`${inputCls} min-h-20`} value={fmt.bank_details.join('\n')}
                onChange={(e) => edit({ bank_details: lines(e.target.value).slice(0, 8) })} />
            </label>

            {shown && (shown.supported_placeholders.length > 0 || shown.unsupported_placeholders.length > 0) && (
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="text-sm font-medium text-slate-700">Placeholders found in your quotation</p>
                <ul className="mt-2 space-y-1 text-sm">
                  {shown.supported_placeholders.map((p, i) => (
                    <li key={`s${i}`} className="flex items-center gap-2 text-slate-600">
                      <IconCheck size={14} className="shrink-0 text-emerald-600" />
                      <span className="font-medium text-slate-800">{p.label}</span> → {FIELD_NAMES[p.field] ?? p.field}
                    </li>
                  ))}
                  {shown.unsupported_placeholders.map((p, i) => (
                    <li key={`u${i}`} className="flex items-center gap-2 text-slate-500">
                      <span className="h-3.5 w-3.5 shrink-0 rounded-full border border-slate-300" aria-hidden />
                      <span className="font-medium">{p.label}</span> → left out for now
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => void run('preview', () => api.previewQuotationFormat(fmt))} disabled={!!busy}>
                <IconEye size={16} /> {busy === 'preview' ? 'Preparing…' : 'Preview sample PDF'}
              </Button>
              {draft && (
                <Button onClick={() => void save()} disabled={!!busy}>
                  <IconCheck size={16} /> {busy === 'saving' ? 'Saving…' : saved ? 'Save changes' : 'Use this format'}
                </Button>
              )}
              <Button variant="secondary" onClick={() => fileRef.current?.click()} disabled={!!busy}>
                <IconUpload size={16} /> {busy === 'reading' ? 'Reading…' : 'Upload a different sample'}
              </Button>
              {draft && <Button variant="ghost" onClick={() => { setDraft(null); setError(null) }} disabled={!!busy}>Cancel</Button>}
              {saved && !draft && (
                <Button variant="ghost" onClick={() => void reset()} disabled={!!busy}>
                  {busy === 'reset' ? 'Resetting…' : 'Use standard format'}
                </Button>
              )}
            </div>
          </>
        )}

        {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {notice && <p role="status" className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p>}
      </div>
    </Card>
  )
}
