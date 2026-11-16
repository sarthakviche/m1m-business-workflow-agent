// Price-list import: photo/PDF/CSV → Gemini reads it → owner reviews every row → save.
// Nothing reaches the catalog until the owner presses Save on the review step.

import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ImportPreview, ImportPreviewRow, ImportResult, ImportRow } from '../api/client'
import { IconAlert, IconArrowRight, IconBox, IconCamera, IconCheck, IconFile, IconUpload } from '../components/icons'
import { Badge, Button, ButtonLink, Card, Page, PageHeader } from '../components/ui'
import { formatINR } from '../lib/format'
import { GST_RATES, HSN_PATTERN } from '../lib/gst'

const MAX_BYTES = 10 * 1024 * 1024
const ACCEPT = 'image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf,text/csv,.csv'
const UNITS = ['pcs', 'kg', 'g', 'mtr', 'ft', 'sqft', 'ltr', 'ml', 'box', 'set', 'pair', 'roll', 'bag', 'pkt', 'dozen', 'bundle', 'coil', 'ton']

interface DraftRow {
  key: number
  include: boolean
  name: string
  price: string
  unit: string
  gst: string
  hsn: string
  qty: string
  match: ImportPreviewRow['match']
  existingPrice: number | null
  /** Notes from reading the sheet (e.g. "Unit not written; assumed pcs"). */
  hints: string[]
}

type Stage =
  | { kind: 'pick'; error?: string }
  | { kind: 'reading' }
  | { kind: 'review'; preview: ImportPreview }
  | { kind: 'done'; result: ImportResult }

function toDraft(row: ImportPreviewRow, key: number): DraftRow {
  return {
    key,
    include: row.match !== 'unchanged',
    name: row.name,
    price: row.unit_price?.toString() ?? '',
    unit: row.unit,
    gst: row.gst_rate_percent?.toString() ?? '',
    hsn: row.hsn_code ?? '',
    qty: row.quantity_available?.toString() ?? '',
    match: row.match,
    existingPrice: row.existing_unit_price,
    // Missing price/GST show as field errors; keep only the other notes as hints.
    hints: row.issues.filter((i) => !/^Price missing|^GST rate missing/.test(i)),
  }
}

/** Field-level problems that block saving. */
function problems(row: DraftRow): Partial<Record<'name' | 'price' | 'gst' | 'hsn' | 'qty', string>> {
  const p: ReturnType<typeof problems> = {}
  if (!row.name.trim()) p.name = 'Name needed'
  const price = Number(row.price)
  if (!row.price.trim() || !Number.isFinite(price) || price <= 0) p.price = 'Price needed'
  if (row.gst === '') p.gst = 'Pick GST'
  if (row.hsn.trim() && !HSN_PATTERN.test(row.hsn.trim())) p.hsn = '4, 6 or 8 digits'
  if (row.qty.trim() && !(Number(row.qty) >= 0)) p.qty = 'Invalid'
  return p
}

function toImportRow(row: DraftRow): ImportRow {
  return {
    name: row.name.trim(),
    unit_price: Number(Number(row.price).toFixed(2)),
    unit: row.unit,
    hsn_code: row.hsn.trim() || null,
    gst_rate_percent: Number(row.gst),
    quantity_available: row.qty.trim() ? Number(Number(row.qty).toFixed(2)) : null,
  }
}

// ── Step 1: pick a file ──────────────────────────────────────────────────────

function FilePicker({ onFile, error }: { onFile: (f: File) => void; error?: string }) {
  const cameraRef = useRef<HTMLInputElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }

  const pick = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) onFile(file)
  }

  return (
    <Card>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`m-4 flex flex-col items-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors sm:m-6
          ${dragging ? 'border-orange-400 bg-orange-50/60' : 'border-slate-200 bg-slate-50/50'}`}
      >
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-500 text-white shadow-sm"><IconUpload size={26} /></span>
        <p className="mt-4 font-display text-lg font-semibold text-slate-900">Add your price list</p>
        <p className="mt-1 max-w-md text-sm text-slate-500">
          A photo of the rate list on paper, a PDF, or a CSV export. We read every item, price and GST rate, then show
          them to you before anything is saved.
        </p>
        <div className="mt-6 flex w-full max-w-sm flex-col gap-2 sm:flex-row sm:justify-center">
          <Button onClick={() => cameraRef.current?.click()} className="sm:hidden"><IconCamera size={18} /> Take a photo</Button>
          <Button variant="secondary" onClick={() => fileRef.current?.click()} className="sm:hidden">Choose a file</Button>
          <Button onClick={() => fileRef.current?.click()} className="hidden sm:inline-flex"><IconUpload size={18} /> Choose a file</Button>
        </div>
        <p className="mt-3 hidden text-xs text-slate-400 sm:block">or drop it here · JPG, PNG, HEIC, PDF or CSV · up to 10 MB</p>
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={pick} />
        <input ref={fileRef} type="file" accept={ACCEPT} className="hidden" onChange={pick} />
      </div>

      {error && (
        <div role="alert" className="mx-4 mb-4 flex items-start gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 sm:mx-6">
          <IconAlert size={18} className="mt-0.5 shrink-0" /> {error}
        </div>
      )}

      <ul className="grid gap-3 border-t border-slate-100 p-5 text-sm text-slate-600 sm:grid-cols-3 sm:px-6">
        {[
          ['Flat and bright', 'Lay the sheet flat in daylight so every number is sharp.'],
          ['One page per photo', 'For several pages, a PDF works best.'],
          ['You check first', 'Nothing is added to your catalog until you press Save.'],
        ].map(([title, text]) => (
          <li key={title} className="flex gap-2.5">
            <IconCheck size={18} className="mt-0.5 shrink-0 text-emerald-600" />
            <span><span className="font-semibold text-slate-800">{title}.</span> {text}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

// ── Original file preview (side by side with the review) ─────────────────────

function OriginalPreview({ file, url }: { file: File; url: string }) {
  const isImage = file.type.startsWith('image/')
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <p className="truncate text-sm font-semibold text-slate-900">{file.name}</p>
        <a href={url} target="_blank" rel="noreferrer" className="shrink-0 text-sm font-semibold text-orange-600 hover:text-orange-700">Open</a>
      </div>
      {isImage ? (
        <img src={url} alt="Your price list" className="max-h-[70vh] w-full bg-slate-100 object-contain" />
      ) : (
        <div className="flex items-center gap-3 px-4 py-6 text-sm text-slate-500"><IconFile /> Open the original to compare.</div>
      )}
    </Card>
  )
}

// ── Step 3: review ───────────────────────────────────────────────────────────

const inputBase = 'w-full rounded-lg border bg-white px-2.5 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2'
const inputOk = 'border-slate-200 focus:border-orange-400 focus:ring-orange-100'
const inputBad = 'border-red-300 bg-red-50/40 focus:border-red-400 focus:ring-red-100'

function Field({ label, error, className = '', children }: { label: string; error?: string; className?: string; children: ReactNode }) {
  return (
    <label className={`block min-w-0 ${className}`}>
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</span>
      {children}
      {error && <span className="mt-0.5 block text-xs font-medium text-red-600">{error}</span>}
    </label>
  )
}

function MatchBadge({ row }: { row: DraftRow }) {
  if (row.match === 'new') return <Badge tone="green">New</Badge>
  if (row.match === 'unchanged') return <Badge>Already in catalog</Badge>
  return <Badge tone="blue">Updates existing{row.existingPrice !== null ? ` · was ${formatINR(row.existingPrice)}` : ''}</Badge>
}

function ReviewRow({ row, onChange }: { row: DraftRow; onChange: (patch: Partial<DraftRow>) => void }) {
  const p = row.include ? problems(row) : {}
  const cls = (bad?: string) => `${inputBase} ${bad ? inputBad : inputOk}`
  return (
    <li className={`px-4 py-4 sm:px-5 ${row.include ? '' : 'bg-slate-50/70'}`}>
      <div className="flex items-start gap-3">
        <input type="checkbox" checked={row.include} onChange={(e) => onChange({ include: e.target.checked })}
          aria-label={`Include ${row.name || 'this item'}`}
          className="mt-8 h-4 w-4 shrink-0 rounded border-slate-300 accent-orange-500" />
        <div className={`grid min-w-0 flex-1 grid-cols-2 gap-x-3 gap-y-3 sm:grid-cols-5 ${row.include ? '' : 'opacity-50'}`}>
          <Field label="Item" error={p.name} className="col-span-2 sm:col-span-5">
            <input className={cls(p.name)} value={row.name} onChange={(e) => onChange({ name: e.target.value })} />
          </Field>
          <Field label="Price ₹" error={p.price}>
            <input className={`${cls(p.price)} tabular-nums`} inputMode="decimal" value={row.price}
              onChange={(e) => onChange({ price: e.target.value })} placeholder="0.00" />
          </Field>
          <Field label="Per">
            <select className={cls()} value={row.unit} onChange={(e) => onChange({ unit: e.target.value })}>
              {(UNITS.includes(row.unit) ? UNITS : [row.unit, ...UNITS]).map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </Field>
          <Field label="GST" error={p.gst}>
            <select className={cls(p.gst)} value={row.gst} onChange={(e) => onChange({ gst: e.target.value })}>
              <option value="">—</option>
              {GST_RATES.map((r) => <option key={r} value={String(r)}>{r}%</option>)}
            </select>
          </Field>
          <Field label="HSN" error={p.hsn}>
            <input className={`${cls(p.hsn)} tabular-nums`} inputMode="numeric" value={row.hsn}
              onChange={(e) => onChange({ hsn: e.target.value })} placeholder="Optional" />
          </Field>
          <Field label="In stock" error={p.qty} className="col-span-2 sm:col-span-1">
            <input className={`${cls(p.qty)} tabular-nums`} inputMode="decimal" value={row.qty}
              onChange={(e) => onChange({ qty: e.target.value })} placeholder="—" />
          </Field>
          <div className="col-span-2 flex flex-wrap items-center gap-2 sm:col-span-5">
            <MatchBadge row={row} />
            {row.hints.map((h) => <Badge key={h} tone="amber">{h}</Badge>)}
          </div>
        </div>
      </div>
    </li>
  )
}

function Review({ file, url, preview, onSaved, onRestart }:
  { file: File; url: string; preview: ImportPreview; onSaved: (r: ImportResult) => void; onRestart: () => void }) {
  const [rows, setRows] = useState<DraftRow[]>(() => preview.rows.map(toDraft))
  const [bulkGst, setBulkGst] = useState('18')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const included = rows.filter((r) => r.include)
  const invalid = included.filter((r) => Object.keys(problems(r)).length > 0)
  const missingGst = included.filter((r) => r.gst === '').length
  const counts = {
    add: included.filter((r) => r.match === 'new').length,
    update: included.filter((r) => r.match !== 'new').length,
  }

  const update = (key: number, patch: Partial<DraftRow>) =>
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)))

  async function save() {
    setSaving(true)
    setError(null)
    try {
      onSaved(await api.importCatalog(included.map(toImportRow)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the items.')
      setSaving(false)
    }
  }

  if (rows.length === 0) {
    return (
      <Card className="px-6 py-12 text-center">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-amber-600"><IconAlert /></span>
        <p className="mt-4 font-display text-base font-semibold text-slate-900">No items found in that file</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
          {preview.notes ?? 'Try a sharper photo with the whole list in frame.'}
        </p>
        <Button className="mt-5" onClick={onRestart}>Try another file</Button>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0 space-y-4">
        <Card>
          <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600"><IconCheck size={18} /></span>
              <div>
                <p className="font-semibold text-slate-900">Found {rows.length} item{rows.length === 1 ? '' : 's'}. Check them against your list.</p>
                <p className="mt-0.5 text-sm text-slate-500">
                  Edit anything that's off, untick what you don't sell.
                  {preview.skipped > 0 && ` ${preview.skipped} duplicate or blank row${preview.skipped === 1 ? ' was' : 's were'} left out.`}
                </p>
                {preview.notes && <p className="mt-1.5 text-sm text-slate-600"><span className="font-medium">Note:</span> {preview.notes}</p>}
              </div>
            </div>
          </div>
          {missingGst > 0 && (
            <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 bg-amber-50/60 px-4 py-3 text-sm sm:px-5">
              <span className="text-amber-900">{missingGst} item{missingGst === 1 ? ' has' : 's have'} no GST rate on the list.</span>
              <select value={bulkGst} onChange={(e) => setBulkGst(e.target.value)} aria-label="GST rate for items without one"
                className="rounded-lg border border-amber-200 bg-white px-2 py-1 text-sm">
                {GST_RATES.map((r) => <option key={r} value={String(r)}>{r}%</option>)}
              </select>
              <Button variant="secondary" className="!px-3 !py-1.5"
                onClick={() => setRows((rs) => rs.map((r) => (r.include && r.gst === '' ? { ...r, gst: bulkGst } : r)))}>
                Apply to them
              </Button>
            </div>
          )}
        </Card>

        <Card>
          <ul className="divide-y divide-slate-100">
            {rows.map((r) => <ReviewRow key={r.key} row={r} onChange={(patch) => update(r.key, patch)} />)}
          </ul>
        </Card>

        {/* Save bar stays in reach on long lists */}
        <div className="sticky bottom-0 z-10 -mx-4 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-2xl sm:border sm:shadow-sm">
          {error && <p role="alert" className="mb-2 text-sm font-medium text-red-600">{error}</p>}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-600">
              {invalid.length > 0
                ? <span className="font-medium text-red-600">Fix {invalid.length} highlighted item{invalid.length === 1 ? '' : 's'} or untick {invalid.length === 1 ? 'it' : 'them'}.</span>
                : included.length === 0 ? 'Tick at least one item to save.'
                : <>{counts.add} new{counts.update > 0 && `, ${counts.update} existing to update`}</>}
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={onRestart} disabled={saving}>Start over</Button>
              <Button onClick={save} disabled={saving || invalid.length > 0 || included.length === 0}>
                {saving ? 'Saving…' : `Save ${included.length} item${included.length === 1 ? '' : 's'}`}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="hidden lg:block">
        <div className="sticky top-6"><OriginalPreview file={file} url={url} /></div>
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ImportCatalog() {
  const [params] = useSearchParams()
  const welcome = params.has('welcome')
  const [stage, setStage] = useState<Stage>({ kind: 'pick' })
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => () => { if (url) URL.revokeObjectURL(url) }, [url])

  async function read(f: File) {
    if (f.size > MAX_BYTES) {
      setStage({ kind: 'pick', error: 'That file is larger than 10 MB. Try a smaller photo or split the PDF.' })
      return
    }
    setFile(f)
    setUrl(URL.createObjectURL(f))
    setStage({ kind: 'reading' })
    try {
      setStage({ kind: 'review', preview: await api.previewCatalogImport(f) })
    } catch (err) {
      setStage({ kind: 'pick', error: err instanceof Error ? err.message : 'Could not read that file.' })
    }
  }

  const restart = () => { setFile(null); setUrl(null); setStage({ kind: 'pick' }) }

  return (
    <Page>
      <PageHeader
        title={welcome ? 'Set up your catalog' : 'Import price list'}
        description={welcome
          ? 'Snap your rate list and Munim fills in your products, prices and GST so you can quote straight away.'
          : 'Add or update many items at once from a photo, PDF or CSV of your price list.'}
        actions={stage.kind !== 'done' ? <ButtonLink to="/inventory" variant="secondary">Back to stock</ButtonLink> : undefined}
      />

      {stage.kind === 'pick' && <FilePicker onFile={read} error={stage.error} />}

      {stage.kind === 'reading' && file && url && (
        <Card className="flex flex-col items-center px-6 py-14 text-center">
          {file.type.startsWith('image/')
            ? <img src={url} alt="" className="h-40 w-auto max-w-full rounded-xl object-contain shadow-sm" />
            : <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500"><IconFile size={26} /></span>}
          <div className="mt-6 flex items-center gap-2" role="status">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-orange-200 border-t-orange-500" />
            <p className="font-semibold text-slate-900">Reading your price list…</p>
          </div>
          <p className="mt-1 text-sm text-slate-500">This usually takes 10 to 20 seconds.</p>
        </Card>
      )}

      {stage.kind === 'review' && file && url && (
        <Review file={file} url={url} preview={stage.preview} onRestart={restart}
          onSaved={(result) => setStage({ kind: 'done', result })} />
      )}

      {stage.kind === 'done' && (
        <Card className="flex flex-col items-center px-6 py-14 text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600"><IconCheck size={28} /></span>
          <p className="mt-4 font-display text-xl font-bold text-slate-900">Your catalog is ready</p>
          <p className="mt-1 text-sm text-slate-500">
            {[
              stage.result.created && `${stage.result.created} item${stage.result.created === 1 ? '' : 's'} added`,
              stage.result.updated && `${stage.result.updated} updated`,
              stage.result.unchanged && `${stage.result.unchanged} already up to date`,
            ].filter(Boolean).join(' · ')}
          </p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <ButtonLink to="/chat" state={{ draft: 'Create a quotation for ' }}>Create a quotation <IconArrowRight size={16} /></ButtonLink>
            <ButtonLink to="/inventory" variant="secondary"><IconBox size={18} /> View stock</ButtonLink>
          </div>
          <button onClick={restart} className="mt-4 text-sm font-semibold text-orange-600 hover:text-orange-700">Import another list</button>
        </Card>
      )}
    </Page>
  )
}
