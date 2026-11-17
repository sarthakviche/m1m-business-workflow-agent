// Display formatting shared by every screen (Indian locale).

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 })
const inrCompact = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const qty = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })

export function formatINR(amount: number | null | undefined, { compact = false } = {}): string {
  const value = Number.isFinite(amount) ? (amount as number) : 0
  return (compact ? inrCompact : inr).format(value)
}

export function formatQty(value: number): string {
  return qty.format(value)
}

/** Backend timestamps are UTC; values without an offset are treated as UTC. */
function parseDate(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`)
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  return parseDate(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true })
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?'
}
