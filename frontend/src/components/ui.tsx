// Shared building blocks so every screen has the same structure and states.

import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconAlert, IconRefresh, IconSearch } from './icons'

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-slate-200/80 bg-white shadow-sm ${className}`}>{children}</section>
}

export function CardHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
      <h2 className="font-display text-base font-semibold text-slate-900">{title}</h2>
      {action}
    </div>
  )
}

const buttonStyles = {
  primary: 'bg-orange-500 text-white shadow-sm hover:bg-orange-600 focus-visible:ring-orange-500',
  secondary: 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 focus-visible:ring-slate-400',
  ghost: 'text-orange-600 hover:bg-orange-50 focus-visible:ring-orange-500',
}

type ButtonVariant = keyof typeof buttonStyles
const buttonBase =
  'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'

export function Button({ variant = 'primary', className = '', ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return <button className={`${buttonBase} ${buttonStyles[variant]} ${className}`} {...props} />
}

export function ButtonLink({ to, variant = 'primary', children, state }:
  { to: string; variant?: ButtonVariant; children: ReactNode; state?: unknown }) {
  return <Link to={to} state={state} className={`${buttonBase} ${buttonStyles[variant]}`}>{children}</Link>
}

const badgeTones = {
  neutral: 'bg-slate-100 text-slate-700',
  orange: 'bg-orange-50 text-orange-700 ring-1 ring-inset ring-orange-200',
  green: 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200',
  red: 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-200',
  amber: 'bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200',
  blue: 'bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200',
}

export type BadgeTone = keyof typeof badgeTones

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeTones[tone]}`}>{children}</span>
}

const STATUS: Record<string, { label: string; tone: BadgeTone }> = {
  draft: { label: 'Draft', tone: 'neutral' },
  sent: { label: 'Sent', tone: 'blue' },
  converted: { label: 'Invoiced', tone: 'green' },
  unpaid: { label: 'Unpaid', tone: 'amber' },
  partially_paid: { label: 'Part paid', tone: 'amber' },
  paid: { label: 'Paid', tone: 'green' },
  overdue: { label: 'Overdue', tone: 'red' },
}

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? { label: status.replace(/_/g, ' '), tone: 'neutral' as BadgeTone }
  return <Badge tone={s.tone}>{s.label}</Badge>
}

export function StatCard({ label, value, hint, tone = 'slate', icon }:
  { label: string; value: string; hint?: string; tone?: 'slate' | 'orange' | 'red' | 'green'; icon?: ReactNode }) {
  const iconTone = { slate: 'bg-slate-100 text-slate-600', orange: 'bg-orange-50 text-orange-600', red: 'bg-red-50 text-red-600', green: 'bg-emerald-50 text-emerald-600' }[tone]
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        {icon && <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${iconTone}`}>{icon}</span>}
      </div>
      <p className="mt-2 font-display text-2xl font-bold tracking-tight text-slate-900 tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  )
}

export function SearchInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="relative block w-full sm:max-w-xs">
      <span className="sr-only">{placeholder}</span>
      <IconSearch size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
      />
    </label>
  )
}

export function Tabs<T extends string>({ value, onChange, options }:
  { value: T; onChange: (v: T) => void; options: { value: T; label: string; count?: number }[] }) {
  return (
    <div role="tablist" className="inline-flex rounded-xl bg-slate-100 p-1">
      {options.map((o) => {
        const active = o.value === value
        return (
          <button key={o.value} role="tab" aria-selected={active} onClick={() => onChange(o.value)}
            className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors ${active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}>
            {o.label}
            {o.count !== undefined && <span className={`ml-1.5 tabular-nums ${active ? 'text-orange-600' : 'text-slate-400'}`}>{o.count}</span>}
          </button>
        )
      })}
    </div>
  )
}

export function EmptyState({ icon, title, description, action }: { icon: ReactNode; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-50 text-orange-500">{icon}</span>
      <p className="mt-4 font-display text-base font-semibold text-slate-900">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-14 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-red-500"><IconAlert /></span>
      <p className="mt-4 font-display text-base font-semibold text-slate-900">Couldn't load this</p>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{message}</p>
      <Button variant="secondary" className="mt-5" onClick={onRetry}><IconRefresh size={16} /> Try again</Button>
    </div>
  )
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-slate-100" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-4">
          <div className="h-9 w-9 animate-pulse rounded-full bg-slate-100" />
          <div className="flex-1 space-y-2">
            <div className="h-3.5 w-1/3 animate-pulse rounded bg-slate-100" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function Page({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</div>
}
