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
    throw new ApiError(response.status, errorMessage(body) ?? friendlyStatus(response.status))
  }
  return response
}

/** Gateway errors come from the host, not Munim: the server is restarting, waking up or overloaded. */
function friendlyStatus(status: number): string {
  if (status === 502 || status === 503 || status === 504) {
    return "Munim's server didn't answer in time (it may be waking up). Nothing was saved — please send that again."
  }
  return `Request failed (${status})`
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
export async function openDocument(pdfUrl: string, init?: RequestInit): Promise<void> {
  const tab = window.open('', '_blank')
  try {
    const blob = await (await send(pdfUrl, init)).blob()
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
  bot_username: string | null
  /** Opens the bot with the code filled in, so linking is one tap. */
  deep_link: string | null
}

export interface TelegramStatus {
  configured: boolean
  bot_username: string | null
  linked: boolean
  chats: { display_name: string | null; linked_at: string }[]
}

export type FormatColumnKey = 'index' | 'item' | 'hsn' | 'qty' | 'unit' | 'rate' | 'gst' | 'amount'

export interface QuotationFormat {
  source_filename: string | null
  title: string
  party_label: string
  date_label: string
  valid_until_label: string
  columns: { key: FormatColumnKey; label: string }[]
  accent_color: string | null
  intro_text: string | null
  terms: string[]
  bank_details: string[]
  footer_text: string | null
  signatory_label: string
  validity_days: number | null
  show_amount_in_words: boolean
  show_tax_breakdown: boolean
  placeholders: FormatPlaceholder[]
}

export interface FormatPlaceholder {
  label: string
  field: string
}

export interface FormatAnalysis {
  format: QuotationFormat
  supported_placeholders: FormatPlaceholder[]
  unsupported_placeholders: FormatPlaceholder[]
}

export interface BusinessBranding {
  brand_color: string | null
  logo_url: string | null
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

/** What the agent is doing during a chat turn, as streamed by /chat/stream. */
export type ChatStage =
  | 'sending'
  | 'understanding'
  | 'drafting_quotation'
  | 'drafting_invoice'
  | 'converting_quotation'
  | 'searching_catalog'

// A turn normally takes 1–3s; the backend stops itself at 25s.
const CHAT_TIMEOUT_MS = 35_000

/**
 * Sends one chat turn and reports progress through onStage. The response is
 * newline-delimited JSON: zero or more status lines, then one result line.
 */
async function chatStream(
  message: string,
  history: ChatTurn[],
  conversationId: string,
  onStage: (stage: ChatStage) => void,
): Promise<ChatResponse> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS)
  try {
    const response = await send('/api/v1/chat/stream', {
      method: 'POST',
      signal: controller.signal,
      headers: {
        Accept: 'application/x-ndjson',
        'Content-Type': 'application/json',
        'X-Conversation-Id': conversationId,
        'X-Idempotency-Key': crypto.randomUUID(),
      },
      body: JSON.stringify({ message, conversation_history: history }),
    })
    if (!response.body) throw new ApiError(0, 'Empty response from the server. Please try again.')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let newline: number
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, newline).trim()
        buffer = buffer.slice(newline + 1)
        if (!line) continue
        const event = JSON.parse(line) as { type: string; stage?: ChatStage; response?: ChatResponse }
        if (event.type === 'status' && event.stage) onStage(event.stage)
        if (event.type === 'result' && event.response) return event.response
      }
      if (done) break
    }
    throw new ApiError(0, 'The connection closed before Munim answered. Please send that again.')
  } catch (err) {
    if (controller.signal.aborted) {
      throw new ApiError(0, 'Munim is taking too long to answer. Nothing was saved — please send that again.')
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  me: () => request<Me>('/api/v1/me'),
  createBusiness: (details: BusinessProfileUpdate) =>
    request<BusinessProfile>('/api/v1/business', { method: 'POST', body: JSON.stringify(details) }),
  updateBusiness: (changes: BusinessProfileUpdate) =>
    request<BusinessProfile>('/api/v1/business', { method: 'PATCH', body: JSON.stringify(changes) }),
  businessBranding: () => request<BusinessBranding>('/api/v1/business/branding'),
  updateBusinessBranding: (brandColor: string | null) =>
    request<BusinessBranding>('/api/v1/business/branding', { method: 'PATCH', body: JSON.stringify({ brand_color: brandColor }) }),
  uploadBusinessLogo: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<BusinessBranding>('/api/v1/business/logo', { method: 'POST', body: form })
  },
  businessLogo: async () => (await send('/api/v1/business/logo')).blob(),
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
  telegramStatus: () => request<TelegramStatus>('/api/v1/telegram/status'),
  quotationFormat: () =>
    request<{ analysis: FormatAnalysis | null }>('/api/v1/business/quotation-format').then((r) => r.analysis),
  analyzeQuotationFormat: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<FormatAnalysis>('/api/v1/business/quotation-format/analyze', { method: 'POST', body: form })
  },
  saveQuotationFormat: (format: QuotationFormat) =>
    request<FormatAnalysis>('/api/v1/business/quotation-format', { method: 'PUT', body: JSON.stringify(format) }),
  resetQuotationFormat: () => send('/api/v1/business/quotation-format', { method: 'DELETE' }).then(() => undefined),
  /** Opens a sample quotation PDF in the given format (or the saved one) in a new tab. */
  previewQuotationFormat: (format: QuotationFormat | null) =>
    openDocument('/api/v1/business/quotation-format/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(format),
    }),
  chatStream,
  chat: (message: string, history: ChatTurn[], conversationId: string) =>
    request<ChatResponse>('/api/v1/chat', {
      method: 'POST',
      headers: { 'X-Conversation-Id': conversationId, 'X-Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ message, conversation_history: history }),
    }),
}
