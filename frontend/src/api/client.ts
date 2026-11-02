// Typed client for the FastAPI backend. Every screen goes through here.
// Requests are relative: the Vite dev server proxies /api and /documents to
// the backend; set VITE_API_BASE_URL when the API is served from elsewhere.

import type { ChatResponse, DocumentHistoryItem } from '../types/chat'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    })
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.")
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.message ?? body?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

/** Absolute URL for a generated PDF (pdf_url values are root-relative). */
export function documentUrl(pdfUrl: string): string {
  return `${API_BASE}${pdfUrl}`
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface BusinessProfile {
  id: string
  business_name: string
  gstin: string | null
  state: string
  address: string | null
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

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  business: () => request<BusinessProfile>('/api/v1/business'),
  dashboard: () => request<DashboardSummary>('/api/v1/dashboard/summary'),
  customers: () => request<Customer[]>('/api/v1/customers'),
  items: () => request<CatalogItem[]>('/api/v1/items'),
  documents: () =>
    request<{ documents: DocumentHistoryItem[] }>('/api/v1/documents').then((r) => r.documents),
  createTelegramLinkCode: () =>
    request<TelegramLinkCode>('/api/v1/telegram/link-codes', { method: 'POST' }),
  chat: (message: string, history: ChatTurn[], conversationId: string) =>
    request<ChatResponse>('/api/v1/chat', {
      method: 'POST',
      headers: { 'X-Conversation-Id': conversationId, 'X-Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ message, conversation_history: history }),
    }),
}
