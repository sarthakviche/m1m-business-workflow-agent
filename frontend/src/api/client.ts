// Typed client for the FastAPI backend. Every screen goes through here.
// Requests are relative: the Vite dev server proxies /api and /documents to
// the backend; set VITE_API_BASE_URL when the API is served from elsewhere.

import type { ChatResponse, DocumentHistoryItem } from '../types/chat'
import { supabase } from '../lib/supabase'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

async function authHeaders(): Promise<Record<string, string>> {
  if (!supabase) return {}
  // getSession refreshes the token first if it has expired.
  const { data } = await supabase.auth.getSession()
  return data.session ? { Authorization: `Bearer ${data.session.access_token}` } : {}
}

/** The server no longer accepts this session, so drop it. The app then shows the login screen. */
function handleUnauthorized(status: number) {
  if (status === 401 && supabase) void supabase.auth.signOut({ scope: 'local' })
}

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await send(path, {
    ...init,
    // FormData bodies set their own multipart boundary, so only JSON gets a Content-Type here.
    headers: { Accept: 'application/json', ...(typeof init.body === 'string' ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
  })
  return response.json() as Promise<T>
}

/** Sends an authenticated request and turns every failure into an ApiError. */
async function send(path: string, init: RequestInit = {}): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...(await authHeaders()), ...init.headers },
    })
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.")
  }
  if (!response.ok) {
    handleUnauthorized(response.status)
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, errorMessage(body) ?? `Request failed (${response.status})`)
  }
  return response
}

/** Munim errors carry `message`; FastAPI validation errors carry a `detail` list. */
function errorMessage(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const { message, detail } = body as { message?: unknown; detail?: unknown }
  if (typeof message === 'string') return message
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string }
    return first.msg?.replace(/^Value error, /, '') ?? null
  }
  return null
}

/**
 * Opens a generated PDF. PDFs need the login token, which a plain link can't send,
 * so this fetches the file and opens it in a new tab. The tab has to be opened
 * during the click, or popup blockers stop it.
 */
export async function openDocument(pdfUrl: string): Promise<void> {
  const tab = window.open('', '_blank')
  try {
    const blob = await (await send(pdfUrl)).blob()
    const objectUrl = URL.createObjectURL(blob)
    if (tab) {
      tab.location.href = objectUrl
    } else {
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = pdfUrl.split('/').pop() ?? 'document.pdf'
      link.click()
    }
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
  } catch (err) {
    tab?.close()
    throw err
  }
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface BusinessProfile {
  id: string
  business_name: string
  gstin: string | null
  state: string
  address: string | null
  onboarded: boolean
}

export interface Me {
  email: string | null
  name: string | null
  role: string | null
  business: BusinessProfile | null
}

export interface RecentDocument {
  document_type: 'quotation' | 'invoice'
  document_number: string
  customer_name: string
  total: number
  status: string
  created_at: string | null
  pdf_url: string | null
}

export interface DashboardSummary {
  total_sales: number
  amount_received: number
  outstanding_amount: number
  unpaid_invoices: number
  open_quotations: number
  open_quotations_value: number
  total_customers: number
  total_items: number
  low_stock_threshold: number
  low_stock_items: { id: string; name: string; unit: string; quantity_available: number }[]
  recent_documents: RecentDocument[]
}

export interface Customer {
  id: string
  name: string
  phone: string | null
  gstin: string | null
  state: string | null
  address: string | null
  quotation_count: number
  invoice_count: number
  total_billed: number
}

export interface CatalogItem {
  id: string
  name: string
  hsn_code: string | null
  unit: string
  unit_price: number
  gst_rate_percent: number
  quantity_available: number
  low_stock: boolean
}

export interface TelegramLinkCode {
  code: string
  expires_at: string
  instructions: string
}

export type BusinessProfileUpdate = Partial<Pick<BusinessProfile, 'business_name' | 'gstin' | 'state' | 'address'>>

export interface ImportPreviewRow {
  name: string
  unit_price: number | null
  unit: string
  hsn_code: string | null
  gst_rate_percent: number | null
  quantity_available: number | null
  issues: string[]
  match: 'new' | 'update' | 'unchanged'
  existing_item_id: string | null
  existing_unit_price: number | null
}

export interface ImportPreview {
  rows: ImportPreviewRow[]
  notes: string | null
  skipped: number
}

export interface ImportRow {
  name: string
  unit_price: number
  unit: string
  hsn_code: string | null
  gst_rate_percent: number
  quantity_available: number | null
}

export interface ImportResult {
  created: number
  updated: number
  unchanged: number
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  me: () => request<Me>('/api/v1/me'),
  createBusiness: (details: BusinessProfileUpdate) =>
    request<BusinessProfile>('/api/v1/business', { method: 'POST', body: JSON.stringify(details) }),
  updateBusiness: (changes: BusinessProfileUpdate) =>
    request<BusinessProfile>('/api/v1/business', { method: 'PATCH', body: JSON.stringify(changes) }),
  completeOnboarding: () => request<BusinessProfile>('/api/v1/business/complete-onboarding', { method: 'POST' }),
  dashboard: () => request<DashboardSummary>('/api/v1/dashboard/summary'),
  customers: () => request<Customer[]>('/api/v1/customers'),
  items: () => request<CatalogItem[]>('/api/v1/items'),
  documents: () =>
    request<{ documents: DocumentHistoryItem[] }>('/api/v1/documents').then((r) => r.documents),
  previewCatalogImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ImportPreview>('/api/v1/catalog/import/preview', { method: 'POST', body: form })
  },
  importCatalog: (items: ImportRow[]) =>
    request<ImportResult>('/api/v1/catalog/import', { method: 'POST', body: JSON.stringify({ items }) }),
  createTelegramLinkCode: () =>
    request<TelegramLinkCode>('/api/v1/telegram/link-codes', { method: 'POST' }),
  chat: (message: string, history: ChatTurn[], conversationId: string) =>
    request<ChatResponse>('/api/v1/chat', {
      method: 'POST',
      headers: { 'X-Conversation-Id': conversationId, 'X-Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ message, conversation_history: history }),
    }),
}
