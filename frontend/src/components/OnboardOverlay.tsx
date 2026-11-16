// First-run setup: confirm the business details that go on every document,
// then add the catalog from a photo of the price list.

import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { GSTIN_PATTERN, INDIAN_STATES } from '../lib/gst'
import { IconArrowRight, IconCamera, IconCheck } from './icons'
import { LogoMark } from './Logo'
import { Button } from './ui'

interface Props {
  onComplete: () => Promise<void>
}

const inputCls =
  'w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100'

function Label({ htmlFor, children, hint }: { htmlFor: string; children: string; hint?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 flex items-baseline justify-between text-sm font-medium text-slate-700">
      {children}
      {hint && <span className="text-xs font-normal text-slate-400">{hint}</span>}
    </label>
  )
}

export default function OnboardOverlay({ onComplete }: Props) {
  const { business, saveBusiness } = useApp()
  const navigate = useNavigate()
  const [step, setStep] = useState<1 | 2>(1)
  const [name, setName] = useState('')
  const [gstin, setGstin] = useState('')
  const [state, setState] = useState('')
  const [touched, setTouched] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Prefill from the server once it loads, unless the owner already started typing.
  useEffect(() => {
    if (business && !touched) {
      setName(business.business_name)
      setGstin(business.gstin ?? '')
      setState(business.state)
    }
  }, [business, touched])

  const gstinValue = gstin.trim().toUpperCase()
  const gstinError = gstinValue && !GSTIN_PATTERN.test(gstinValue) ? 'GSTIN should look like 27ABCDE1234F1Z5' : null

  async function saveDetails(e: FormEvent) {
    e.preventDefault()
    if (!name.trim() || !state || gstinError) return
    setSaving(true)
    setError(null)
    try {
      await saveBusiness({ business_name: name.trim(), gstin: gstinValue, state })
      setStep(2)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save your details.')
    } finally {
      setSaving(false)
    }
  }

  async function finish(path?: string) {
    setError(null)
    try {
      await onComplete()
      if (path) navigate(path)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not finish setup. Please try again.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex bg-white sm:items-center sm:justify-center sm:bg-slate-900/40 sm:p-4 sm:backdrop-blur-sm"
      role="dialog" aria-modal="true" aria-labelledby="onboard-title">
      <div className="flex w-full flex-col overflow-y-auto bg-white sm:max-h-[90vh] sm:max-w-lg sm:rounded-3xl sm:shadow-2xl">
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 px-6 pb-6 pt-10 text-white sm:pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="flex h-10 w-12 items-center justify-center rounded-xl bg-white shadow-sm"><LogoMark className="h-6" /></span>
              <span className="font-display text-lg font-bold">Welcome to Munim</span>
            </div>
            <span className="text-sm text-white/80">Step {step} of 2</span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-1.5" aria-hidden="true">
            <span className="h-1.5 rounded-full bg-white" />
            <span className={`h-1.5 rounded-full ${step === 2 ? 'bg-white' : 'bg-white/30'}`} />
          </div>
        </div>

        {step === 1 ? (
          <form onSubmit={saveDetails} className="flex flex-1 flex-col gap-5 px-6 py-6">
            <div>
              <h2 id="onboard-title" className="font-display text-xl font-bold text-slate-900">Your business details</h2>
              <p className="mt-1 text-sm text-slate-500">These go on every quotation and invoice you send.</p>
            </div>
            <div>
              <Label htmlFor="ob-name">Business name</Label>
              <input id="ob-name" className={inputCls} value={name} required autoFocus placeholder="e.g. Sharma Traders"
                onChange={(e) => { setTouched(true); setName(e.target.value) }} />
            </div>
            <div>
              <Label htmlFor="ob-state" hint="Decides CGST + SGST or IGST">State</Label>
              <select id="ob-state" className={inputCls} value={state} required
                onChange={(e) => { setTouched(true); setState(e.target.value) }}>
                <option value="" disabled>Select your state</option>
                {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                {state && !(INDIAN_STATES as readonly string[]).includes(state) && <option value={state}>{state}</option>}
              </select>
            </div>
            <div>
              <Label htmlFor="ob-gstin" hint="Optional, add it later">GSTIN</Label>
              <input id="ob-gstin" className={`${inputCls} uppercase`} value={gstin} maxLength={15} placeholder="27ABCDE1234F1Z5"
                aria-invalid={!!gstinError} onChange={(e) => { setTouched(true); setGstin(e.target.value) }} />
              {gstinError && <p className="mt-1 text-xs font-medium text-red-600">{gstinError}</p>}
            </div>
            {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <div className="mt-auto flex flex-col gap-2 pt-2">
              <Button type="submit" disabled={saving || !name.trim() || !state || !!gstinError} className="w-full py-3">
                {saving ? 'Saving…' : <>Continue <IconArrowRight size={16} /></>}
              </Button>
              {/* A new login must create its business first; there is nothing to skip to. */}
              {business && (
                <button type="button" onClick={() => finish()} className="py-1 text-sm text-slate-500 hover:text-slate-700">
                  Skip setup
                </button>
              )}
            </div>
          </form>
        ) : (
          <div className="flex flex-1 flex-col gap-5 px-6 py-6">
            <div>
              <h2 id="onboard-title" className="font-display text-xl font-bold text-slate-900">Add your products</h2>
              <p className="mt-1 text-sm text-slate-500">
                Most businesses have a rate list on paper. Take a photo of it and Munim fills in your catalog for you to check.
              </p>
            </div>
            <button type="button" onClick={() => finish('/inventory/import?welcome=1')}
              className="group flex items-center gap-4 rounded-2xl border-2 border-orange-200 bg-orange-50/50 p-4 text-left transition-colors hover:border-orange-400">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-orange-500 text-white"><IconCamera size={22} /></span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold text-slate-900">Upload price list</span>
                <span className="mt-0.5 block text-sm text-slate-500">Photo, PDF or CSV · takes about a minute</span>
              </span>
              <IconArrowRight size={18} className="shrink-0 text-orange-500 transition-transform group-hover:translate-x-0.5" />
            </button>
            <ul className="space-y-2 text-sm text-slate-600">
              {['Prices, units, HSN and GST read from the sheet', 'Nothing is saved until you review it', 'Update prices any time by uploading a new list'].map((t) => (
                <li key={t} className="flex items-center gap-2"><IconCheck size={16} className="shrink-0 text-emerald-600" /> {t}</li>
              ))}
            </ul>
            {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <div className="mt-auto pt-2">
              <Button variant="secondary" onClick={() => finish()} className="w-full py-3">I'll do this later</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
