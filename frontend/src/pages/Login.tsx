// Sign in, sign up, forgotten password and setting a new one.

import { useState } from 'react'
import type { FormEvent, InputHTMLAttributes, ReactNode } from 'react'
import { IconArrowRight, IconCamera, IconCheck, IconEye, IconEyeOff, IconReceipt, IconTelegram } from '../components/icons'
import Logo from '../components/Logo'
import { Button } from '../components/ui'
import { useApp } from '../context/AppContext'
import { googleSignInEnabled, supabase } from '../lib/supabase'

type Mode = 'sign_in' | 'sign_up' | 'forgot'

const COPY: Record<Mode, { title: string; subtitle: string; submit: string }> = {
  sign_in: { title: 'Welcome back', subtitle: 'Sign in to pick up where you left off.', submit: 'Sign in' },
  sign_up: { title: 'Create your free account', subtitle: 'Your first GST invoice is only a few minutes away.', submit: 'Create account' },
  forgot: { title: 'Reset your password', subtitle: "Enter your email and we'll send you a link to choose a new one.", submit: 'Send reset link' },
}

const inputCls =
  'w-full rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm text-slate-900 transition-colors placeholder:text-slate-400 hover:border-slate-300 focus:border-orange-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-orange-100'

const primaryCls = 'w-full bg-gradient-to-r from-orange-600 to-orange-500 py-3 shadow-md shadow-orange-200 hover:from-orange-700 hover:to-orange-600'

const HIGHLIGHTS = [
  { Icon: IconCamera, text: 'Photograph your rate list to build your catalog' },
  { Icon: IconCheck, text: 'GST is calculated exactly, never guessed by AI' },
  { Icon: IconTelegram, text: 'Create documents from Telegram too' },
]

/** A worked example of the product. The figures add up: 200 × ₹68.50, plus 18% GST. */
function ProductPreview() {
  return (
    <div aria-hidden="true" className="mx-auto w-full max-w-md select-none motion-safe:animate-float">
      <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-white/20 px-4 py-2.5 text-sm font-medium text-white ring-1 ring-inset ring-white/25 backdrop-blur-sm">
        Ramesh Traders ke liye 200 kg TMT Rod ka invoice banao
      </div>
      <div className="mt-3 overflow-hidden rounded-2xl bg-white text-slate-900 shadow-2xl shadow-orange-950/25">
        <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600"><IconReceipt size={18} /></span>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Tax invoice</p>
            <p className="truncate text-sm font-semibold">INV-202611-001 · Ramesh Traders</p>
          </div>
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">Ready</span>
        </div>
        <div className="flex justify-between gap-4 px-4 py-3 text-sm">
          <div>
            <p className="font-medium">TMT Rod 12mm</p>
            <p className="text-xs text-slate-500">200 kg × ₹68.50 · HSN 7214</p>
          </div>
          <span className="font-medium tabular-nums">₹13,700.00</span>
        </div>
        <div className="space-y-1 bg-slate-50/80 px-4 py-3 text-xs text-slate-600">
          <div className="flex justify-between"><span>CGST 9%</span><span className="tabular-nums">₹1,233.00</span></div>
          <div className="flex justify-between"><span>SGST 9%</span><span className="tabular-nums">₹1,233.00</span></div>
          <div className="flex justify-between pt-1.5 text-sm font-bold text-slate-900"><span>Total</span><span className="tabular-nums">₹16,166.00</span></div>
        </div>
      </div>
    </div>
  )
}

function BrandPanel() {
  return (
    <aside className="relative m-3 hidden flex-col justify-center gap-9 overflow-hidden rounded-[2rem] bg-gradient-to-br from-orange-400 via-orange-500 to-orange-700 p-10 text-white lg:flex xl:p-14">
      {/* Large soft pills echo the shapes in the logo. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <span className="absolute -right-16 -top-24 h-96 w-40 rotate-[28deg] rounded-full bg-white/10" />
        <span className="absolute right-36 -top-32 h-96 w-40 -rotate-[28deg] rounded-full bg-white/[0.07]" />
        <span className="absolute -bottom-32 -left-14 h-96 w-40 rotate-[28deg] rounded-full bg-orange-800/20" />
      </div>
      <div className="relative motion-safe:animate-fade-up">
        <h2 className="max-w-md font-display text-3xl font-extrabold leading-tight tracking-tight xl:text-4xl">
          Say it in a message.<br />Get the GST invoice.
        </h2>
        <p className="mt-3 max-w-md text-base text-orange-50">
          Quotations, invoices and stock for your business, in plain English or Hinglish.
        </p>
      </div>
      <div className="relative"><ProductPreview /></div>
      <ul className="relative mx-auto grid w-full max-w-md gap-2.5 text-sm font-medium text-white [@media(max-height:700px)]:hidden">
        {HIGHLIGHTS.map(({ Icon, text }) => (
          <li key={text} className="flex items-center gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/20"><Icon size={15} /></span>
            {text}
          </li>
        ))}
      </ul>
    </aside>
  )
}

function AuthLayout({ title, subtitle, above, children }:
  { title: string; subtitle: string; above?: ReactNode; children: ReactNode }) {
  return (
    <div className="grid min-h-dvh bg-white lg:grid-cols-2">
      <main className="relative flex flex-col overflow-hidden px-6 py-7 sm:px-10">
        {/* A soft wash of brand colour, so small screens without the panel still feel warm. */}
        <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-orange-100/70 blur-3xl lg:hidden" />
        <div className="relative"><Logo size="lg" /></div>
        <div className="relative flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-[400px] motion-safe:animate-fade-up">
            {above}
            <h1 className="font-display text-[1.75rem] font-extrabold leading-tight tracking-tight text-slate-900">{title}</h1>
            <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p>
            {children}
            {/* Phones don't get the side panel, so the highlights live here instead. */}
            <ul className="mt-8 grid gap-3 border-t border-slate-100 pt-6 text-sm text-slate-600 lg:hidden">
              {HIGHLIGHTS.map(({ Icon, text }) => (
                <li key={text} className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-50 text-orange-600"><Icon size={16} /></span>
                  {text}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>
      <BrandPanel />
    </div>
  )
}

function Field({ id, label, hint, ...props }:
  { id: string; label: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
      <input id={id} className={inputCls} required {...props} />
      {hint && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

function PasswordField({ id, label, hint, ...props }:
  { id: string; label: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false)
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
      <div className="relative">
        <input id={id} className={`${inputCls} pr-12`} type={visible ? 'text' : 'password'} minLength={8} required {...props} />
        <button type="button" onClick={() => setVisible(!visible)}
          aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex w-12 items-center justify-center rounded-r-xl text-slate-400 transition-colors hover:text-slate-700 focus-visible:text-orange-600 focus-visible:outline-none">
          {visible ? <IconEyeOff size={18} /> : <IconEye size={18} />}
        </button>
      </div>
      {hint && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

function Message({ tone, children }: { tone: 'error' | 'success'; children: ReactNode }) {
  const style = tone === 'error' ? 'bg-red-50 text-red-700 ring-red-100' : 'bg-emerald-50 text-emerald-800 ring-emerald-100'
  return <p role={tone === 'error' ? 'alert' : 'status'} className={`rounded-xl px-4 py-3 text-sm ring-1 ring-inset ${style}`}>{children}</p>
}

function ModeSwitch({ mode, onChange }: { mode: Mode; onChange: (mode: Mode) => void }) {
  return (
    <div className="mb-7 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
      {([['sign_up', 'Create account'], ['sign_in', 'Sign in']] as const).map(([value, label]) => (
        <button key={value} type="button" aria-pressed={mode === value} onClick={() => onChange(value)}
          className={`rounded-lg py-2 text-sm font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 ${mode === value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}>
          {label}
        </button>
      ))}
    </div>
  )
}

export default function Login() {
  const [mode, setMode] = useState<Mode>('sign_up')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  function switchMode(next: Mode) {
    setMode(next)
    setError(null)
    setNotice(null)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!supabase) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const address = email.trim()
      if (mode === 'sign_in') {
        const { error: failure } = await supabase.auth.signInWithPassword({ email: address, password })
        if (failure) throw failure
      } else if (mode === 'sign_up') {
        const { data, error: failure } = await supabase.auth.signUp({
          email: address,
          password,
          options: { emailRedirectTo: window.location.origin },
        })
        if (failure) throw failure
        if (!data.session) setNotice(`Almost there. We sent a confirmation link to ${address}.`)
      } else {
        const { error: failure } = await supabase.auth.resetPasswordForEmail(address, { redirectTo: window.location.origin })
        if (failure) throw failure
        setNotice(`If ${address} has an account, a reset link is on its way.`)
      }
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setBusy(false)
    }
  }

  async function signInWithGoogle() {
    setError(null)
    const { error: failure } = await supabase!.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
    if (failure) setError(friendlyError(failure))
  }

  const copy = COPY[mode]
  const showGoogle = googleSignInEnabled && mode !== 'forgot'

  return (
    <AuthLayout title={copy.title} subtitle={copy.subtitle}
      above={mode !== 'forgot' && <ModeSwitch mode={mode} onChange={switchMode} />}>
      {showGoogle && (
        <>
          <Button variant="secondary" className="mt-6 w-full py-3" onClick={signInWithGoogle}>Continue with Google</Button>
          <div className="my-5 flex items-center gap-3 text-xs text-slate-400" aria-hidden="true">
            <span className="h-px flex-1 bg-slate-200" /> or <span className="h-px flex-1 bg-slate-200" />
          </div>
        </>
      )}
      <form onSubmit={submit} className={`flex flex-col gap-4 ${showGoogle ? '' : 'mt-6'}`}>
        <Field id="email" label="Email" type="email" autoComplete="email" placeholder="you@business.com"
          value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        {mode !== 'forgot' && (
          <PasswordField id="password" label="Password"
            autoComplete={mode === 'sign_up' ? 'new-password' : 'current-password'}
            hint={mode === 'sign_up' ? 'Use at least 8 characters.' : undefined}
            value={password} onChange={(e) => setPassword(e.target.value)} />
        )}
        {error && <Message tone="error">{error}</Message>}
        {notice && <Message tone="success">{notice}</Message>}
        <Button type="submit" disabled={busy} className={primaryCls}>
          {busy ? 'Please wait…' : <>{copy.submit} <IconArrowRight size={16} /></>}
        </Button>
      </form>

      <div className="mt-5 text-center text-sm">
        {mode === 'sign_in' && (
          <button type="button" className="font-medium text-slate-500 hover:text-orange-600" onClick={() => switchMode('forgot')}>Forgot password?</button>
        )}
        {mode === 'forgot' && (
          <button type="button" className="font-semibold text-orange-600 hover:underline" onClick={() => switchMode('sign_in')}>Back to sign in</button>
        )}
      </div>
    </AuthLayout>
  )
}

/** Shown after following a password-reset link. */
export function SetNewPassword() {
  const { finishPasswordRecovery } = useApp()
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const { error: failure } = await supabase!.auth.updateUser({ password })
    setBusy(false)
    if (failure) setError(friendlyError(failure))
    else finishPasswordRecovery()
  }

  return (
    <AuthLayout title="Choose a new password" subtitle="You'll be signed in straight after.">
      <form onSubmit={submit} className="mt-6 flex flex-col gap-4">
        <PasswordField id="new-password" label="New password" autoComplete="new-password"
          hint="Use at least 8 characters." value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
        {error && <Message tone="error">{error}</Message>}
        <Button type="submit" disabled={busy} className={primaryCls}>{busy ? 'Saving…' : 'Save password'}</Button>
      </form>
    </AuthLayout>
  )
}

function friendlyError(err: unknown): string {
  const message = err instanceof Error ? err.message : ''
  if (/invalid login credentials/i.test(message)) return "That email and password don't match. Try again or reset your password."
  if (/email not confirmed/i.test(message)) return 'Please confirm your email first. Check your inbox for the link.'
  if (/rate limit|too many/i.test(message)) return 'Too many attempts. Please wait a few minutes and try again.'
  if (/fetch|network/i.test(message)) return "Can't reach the server. Check your connection and try again."
  return message || 'Something went wrong. Please try again.'
}
