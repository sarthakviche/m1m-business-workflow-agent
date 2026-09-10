import React, { useState, useRef, useEffect } from 'react'

// ─── Types ───────────────────────────────────────────────────────────────────

interface Message {
  id: number
  sender: 'user' | 'copilot'
  text: string
  mode?: string
  intent?: string
  pdfUrl?: string
  pdfLabel?: string
  timestamp: Date
}

// ─── Constants ───────────────────────────────────────────────────────────────

const API_BASE = 'http://127.0.0.1:8000'
const PHONE = '9876543210'

const QUICK_ACTIONS = [
  { label: 'Show customers', query: 'show my customers' },
  { label: 'Show items', query: 'show my items' },
  { label: 'Unpaid invoices', query: 'show unpaid invoices' },
  { label: 'Outstanding amount', query: 'how much money is outstanding?' },
  { label: 'Invoice INV-002', query: 'show invoice INV-002' },
  { label: 'Quotations', query: 'show my quotations' },
]

const WELCOME_TEXT = `Hi! 👋

I'm M1M, your business copilot.

You can ask me:
• Show my customers
• Show my items
• Show unpaid invoices
• How much money is outstanding?
• Show invoice INV-002
• Show my quotations
• Generate an invoice PDF
• Generate a quotation PDF

Just send me a message.`

// ─── WhatsApp authentic chat background ──────────────────────────────────────

const WA_BG_STYLE: React.CSSProperties = {
  backgroundColor: '#efeae2',
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cdefs%3E%3Cpattern id='wa' x='0' y='0' width='57.6' height='57.6' patternUnits='userSpaceOnUse'%3E%3Cpath fill='none' stroke='%23d9d0c7' stroke-width='1' stroke-opacity='0.35' d='M28.8 5.8c12.7 0 23 10.3 23 23s-10.3 23-23 23-23-10.3-23-23 10.3-23 23-23zm0 3c-11 0-20 9-20 20s9 20 20 20 20-9 20-20-9-20-20-20z'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='400' height='400' fill='url(%23wa)'/%3E%3C/svg%3E")`,
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

let msgIdCounter = 0
function newId() { return ++msgIdCounter }

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
}

function formatSidebarTime(date: Date) {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 86400000) return formatTime(date)
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: '2-digit' })
}

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
}

function formatDateLabel(date: Date): string {
  const now = new Date()
  if (isSameDay(date, now)) return 'Today'
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (isSameDay(date, yesterday)) return 'Yesterday'
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })
}

/** Detect if backend reply contains a PDF URL */
function extractPdfUrl(text: string): { pdfUrl: string; pdfLabel: string } | null {
  const match = text.match(/(https?:\/\/[^\s]+\/pdf[^\s]*)/i)
  if (match) return { pdfUrl: match[1], pdfLabel: 'Generated PDF' }

  const pathMatch = text.match(/\/(invoices|quotations)\/([a-f0-9-]+)\/pdf/i)
  if (pathMatch) {
    const label = pathMatch[1] === 'invoices' ? 'Invoice PDF' : 'Quotation PDF'
    return { pdfUrl: `${API_BASE}${pathMatch[0]}?phone=${PHONE}`, pdfLabel: label }
  }
  return null
}

// ─── SVG Icons ────────────────────────────────────────────────────────────────

function IconSearch() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
      <path d="M15.009 13.805h-.636l-.22-.219a5.184 5.184 0 0 0 1.256-3.386 5.207 5.207 0 1 0-5.207 5.208 5.184 5.184 0 0 0 3.385-1.255l.221.22v.635l4.004 3.999 1.194-1.195-3.997-4.007zm-4.808 0a3.605 3.605 0 1 1 0-7.21 3.605 3.605 0 0 1 0 7.21z" />
    </svg>
  )
}

function IconDots() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
      <path d="M12 7a2 2 0 1 0-.001-4.001A2 2 0 0 0 12 7zm0 2a2 2 0 1 0-.001 3.999A2 2 0 0 0 12 9zm0 6a2 2 0 1 0-.001 3.999A2 2 0 0 0 12 15z" />
    </svg>
  )
}

function IconNewChat() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
      <path d="M19.005 3.175H4.674C3.642 3.175 3 3.789 3 4.821V21.02l3.544-3.514h12.461c1.033 0 2.064-1.06 2.064-2.093V4.821c-.001-1.032-1.032-1.646-2.064-1.646zm-4.989 9.869H7.041V11.1h6.975v1.944zm3-4H7.041V7.1h9.975v1.944z" />
    </svg>
  )
}

function IconVideoCall() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
      <path d="M15.854 7.64C16.082 7.41 16.082 7.036 15.854 6.808C15.626 6.579 15.251 6.579 15.023 6.808L11.891 9.94L10.977 9.026C10.749 8.797 10.374 8.797 10.146 9.026C9.918 9.254 9.918 9.628 10.146 9.857L11.414 11.125C11.642 11.353 12.017 11.353 12.245 11.125L15.854 7.64ZM16 2H8C5.791 2 4 3.791 4 6V18C4 20.209 5.791 22 8 22H16C18.209 22 20 20.209 20 18V6C20 3.791 18.209 2 16 2ZM18 18C18 19.105 17.105 20 16 20H8C6.895 20 6 19.105 6 18V6C6 4.895 6.895 4 8 4H16C17.105 4 18 4.895 18 6V18Z" />
    </svg>
  )
}

function IconEmoji() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor">
      <path d="M9.153 11.603c.795 0 1.44-.88 1.44-1.962s-.645-1.96-1.44-1.96c-.795 0-1.44.88-1.44 1.96s.645 1.965 1.44 1.965zM5.95 12.965c-.027-.307-.132 5.218 6.062 5.218 6.2 0 6.03-5.543 6.01-5.218H5.95zm11.09 1.296c-.482 2.146-2.317 3.263-5.042 3.263-2.726 0-4.559-1.117-5.042-3.263h10.084zm-7.152-2.658c.795 0 1.44-.88 1.44-1.962s-.645-1.96-1.44-1.96c-.795 0-1.44.88-1.44 1.96s.645 1.965 1.44 1.965z" />
      <path d="M12 2C6.486 2 2 6.486 2 12s4.486 10 10 10 10-4.486 10-10S17.514 2 12 2zm0 18c-4.411 0-8-3.589-8-8s3.589-8 8-8 8 3.589 8 8-3.589 8-8 8z" />
    </svg>
  )
}

function IconAttach() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor">
      <path d="M1.816 15.556v.002c0 1.502.584 2.912 1.646 3.972s2.472 1.647 3.974 1.647a5.58 5.58 0 0 0 3.972-1.645l9.547-9.548c.769-.768 1.147-1.767 1.058-2.817-.079-.968-.548-1.927-1.319-2.698-1.594-1.592-4.068-1.653-5.517-.098l-7.816 8.011c-.04.045-.064.092-.091.139-.135.228-.149.491-.032.723.119.234.349.403.604.418.275.016.54-.097.712-.318l7.783-7.979c.768.852.687 2.265.019 3.535-.573 1.082-1.512 1.88-2.648 2.249a4.078 4.078 0 0 1-3.272-.465l-.001-.001a4.082 4.082 0 0 1-1.745-2.538 4.084 4.084 0 0 1 .578-3.09l7.816-8.011a5.748 5.748 0 0 1 8.143.117c2.238 2.237 2.321 5.844.186 8.18l-9.547 9.548a4.243 4.243 0 0 1-2.988 1.241 4.245 4.245 0 0 1-2.987-1.241 4.243 4.243 0 0 1-1.241-2.99 4.24 4.24 0 0 1 1.241-2.988l5.026-5.026.002.002.001-.001 1.175 1.175-.001.001-5.026 5.025a2.194 2.194 0 0 0-.64 1.68 2.2 2.2 0 0 0 .703 1.52c.983.984 2.653.976 3.624.002l9.548-9.549a2.195 2.195 0 0 0 .64-1.679 2.2 2.2 0 0 0-.703-1.521c-.983-.984-2.652-.976-3.624-.002l-8.085 8.28-.001-.001-.002-.002-.001.001-1.176-1.174.001-.001 8.085-8.281c1.572-1.571 4.233-1.525 5.755-.002z" />
    </svg>
  )
}

function IconSend() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
      <path d="M1.101 21.757L23.8 12.028 1.101 2.3l.011 7.912 13.623 1.816-13.623 1.817-.011 7.912z" />
    </svg>
  )
}

function IconMic() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
      <path d="M12 1a4 4 0 0 0-4 4v7a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4zm0 2a2 2 0 0 1 2 2v7a2 2 0 0 1-4 0V5a2 2 0 0 1 2-2zm-6 8a6 6 0 0 0 12 0h2a8 8 0 0 1-7 7.938V21h2v2H9v-2h2v-2.062A8 8 0 0 1 4 11H6z" />
    </svg>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Avatar({ letter, size = 40, color = '#00a884' }: { letter: string; size?: number; color?: string }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', background: color,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#fff', fontWeight: 700, fontSize: size * 0.4, flexShrink: 0,
      userSelect: 'none',
    }}>
      {letter}
    </div>
  )
}

function DateSeparator({ label }: { label: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '8px 0 12px',
    }}>
      <span style={{
        background: '#fff', color: '#54656f', fontSize: 12, fontWeight: 500,
        padding: '5px 12px', borderRadius: 8,
        boxShadow: '0 1px 0.5px rgba(11,20,26,0.13)',
        userSelect: 'none',
      }}>
        {label}
      </span>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, marginBottom: 2, paddingLeft: 12 }}>
      <Avatar letter="M" size={32} />
      <div style={{
        background: '#fff', borderRadius: '0 8px 8px 8px', padding: '12px 16px',
        boxShadow: '0 1px 0.5px rgba(11,20,26,0.13)', display: 'flex', alignItems: 'center', gap: 5,
        position: 'relative',
      }}>
        {/* Bubble tail */}
        <div style={{
          position: 'absolute', left: -8, top: 0,
          width: 0, height: 0,
          borderTop: '8px solid #fff',
          borderLeft: '8px solid transparent',
        }} />
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 7, height: 7, borderRadius: '50%', background: '#8696a0',
            animation: `wa-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  )
}

function PdfCard({ pdfUrl, pdfLabel, timestamp, mode }: {
  pdfUrl: string; pdfLabel: string; timestamp: Date; mode?: string
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, marginBottom: 2, paddingLeft: 12 }}>
      <Avatar letter="M" size={32} />
      <div style={{
        background: '#fff', borderRadius: '0 8px 8px 8px', overflow: 'hidden',
        boxShadow: '0 1px 0.5px rgba(11,20,26,0.13)', maxWidth: 320, minWidth: 220,
        position: 'relative',
      }}>
        {/* Bubble tail */}
        <div style={{
          position: 'absolute', left: -8, top: 0,
          width: 0, height: 0,
          borderTop: '8px solid #fff',
          borderLeft: '8px solid transparent',
          zIndex: 1,
        }} />
        <div style={{ background: '#f0f2f5', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 8, background: '#00a884',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, flexShrink: 0,
          }}>📄</div>
          <div>
            <div style={{ fontWeight: 600, color: '#111b21', fontSize: 14 }}>{pdfLabel}</div>
            <div style={{ color: '#667781', fontSize: 12, marginTop: 2 }}>Generated successfully</div>
          </div>
        </div>
        <div style={{ padding: '10px 16px', borderTop: '1px solid #f0f2f5' }}>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'block', textAlign: 'center', color: '#00a884',
              fontWeight: 600, fontSize: 14, textDecoration: 'none', padding: '4px 0',
            }}
          >
            Open PDF ↗
          </a>
        </div>
        <div style={{ padding: '2px 12px 8px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, color: '#667781' }}>{formatTime(timestamp)}</span>
          {mode && mode !== 'ready' && (
            <span style={{
              fontSize: 10, color: mode === 'llm' ? '#00a884' : '#f59e0b',
              background: mode === 'llm' ? '#e8fdf5' : '#fef3c7',
              borderRadius: 4, padding: '1px 5px',
            }}>{mode.toUpperCase()}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function CopilotBubble({ msg, isFirst }: { msg: Message; isFirst: boolean }) {
  if (msg.pdfUrl) {
    return <PdfCard pdfUrl={msg.pdfUrl} pdfLabel={msg.pdfLabel || 'PDF'} timestamp={msg.timestamp} mode={msg.mode} />
  }
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', gap: 8,
      marginBottom: 2, paddingLeft: 12,
    }}>
      {/* Avatar only on first bubble in a group */}
      {isFirst
        ? <Avatar letter="M" size={32} />
        : <div style={{ width: 32, flexShrink: 0 }} />
      }
      <div style={{
        background: '#fff',
        borderRadius: isFirst ? '0 8px 8px 8px' : '8px',
        padding: '7px 12px 6px',
        boxShadow: '0 1px 0.5px rgba(11,20,26,0.13)',
        maxWidth: '65%',
        wordBreak: 'break-word',
        position: 'relative',
      }}>
        {/* Bubble tail on first message of group */}
        {isFirst && (
          <div style={{
            position: 'absolute', left: -8, top: 0,
            width: 0, height: 0,
            borderTop: '8px solid #fff',
            borderLeft: '8px solid transparent',
          }} />
        )}
        <div style={{ color: '#111b21', fontSize: 14.5, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{msg.text}</div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 6, marginTop: 3 }}>
          <span style={{ fontSize: 11, color: '#667781' }}>{formatTime(msg.timestamp)}</span>
          {msg.mode && msg.mode !== 'ready' && (
            <span style={{
              fontSize: 10,
              color: msg.mode === 'llm' ? '#00a884' : msg.mode === 'error' ? '#f87171' : '#f59e0b',
              background: msg.mode === 'llm' ? '#e8fdf5' : msg.mode === 'error' ? '#fef2f2' : '#fef3c7',
              borderRadius: 4, padding: '1px 5px', fontWeight: 500,
            }}>{msg.mode.toUpperCase()}{msg.intent ? ` · ${msg.intent}` : ''}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function UserBubble({ msg, isFirst }: { msg: Message; isFirst: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 2, paddingRight: 12 }}>
      <div style={{
        background: '#d9fdd3',
        borderRadius: isFirst ? '8px 0 8px 8px' : '8px',
        padding: '7px 12px 6px',
        boxShadow: '0 1px 0.5px rgba(11,20,26,0.13)',
        maxWidth: '65%',
        wordBreak: 'break-word',
        position: 'relative',
      }}>
        {/* Bubble tail on first message of group */}
        {isFirst && (
          <div style={{
            position: 'absolute', right: -8, top: 0,
            width: 0, height: 0,
            borderTop: '8px solid #d9fdd3',
            borderRight: '8px solid transparent',
          }} />
        )}
        <div style={{ color: '#111b21', fontSize: 14.5, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{msg.text}</div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 4, marginTop: 3 }}>
          <span style={{ fontSize: 11, color: '#667781' }}>{formatTime(msg.timestamp)}</span>
          <span style={{ color: '#53bdeb', fontSize: 14, lineHeight: 1 }}>✓✓</span>
        </div>
      </div>
    </div>
  )
}

// ─── Main Chat Component ──────────────────────────────────────────────────────

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: newId(),
      sender: 'copilot',
      text: WELCOME_TEXT,
      mode: 'ready',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastActivity] = useState(new Date())
  const [sidebarFilter, setSidebarFilter] = useState<'all' | 'unread'>('all')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (textToSend?: string) => {
    const query = (textToSend ?? input).trim()

    if (!query) return

    const userMsg: Message = {
      id: newId(),
      sender: 'user',
      text: query,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMsg])

    if (!textToSend) setInput('')
    setLoading(true)

    try {
      // ------------------------------------------------------------
      // INVOICE PDF REQUESTS
      // Handle invoice PDF generation directly through the backend
      // ------------------------------------------------------------
      const lowerQuery = query.toLowerCase()

      const isInvoicePdfRequest =
        lowerQuery.includes('pdf') && lowerQuery.includes('invoice')

      if (isInvoicePdfRequest) {
        // Try to find an invoice number such as INV-002 or INV002
        const invoiceNumberMatch = query.match(/INV-?\d+/i)
        const requestedInvoiceNumber = invoiceNumberMatch?.[0]?.toUpperCase()

        let invoiceRes: Response | null = null
        try {
          invoiceRes = await fetch(`${API_BASE}/invoices/?phone=${PHONE}`)
          if (!invoiceRes.ok) {
            invoiceRes = await fetch(`http://localhost:8000/invoices/?phone=${PHONE}`)
          }
        } catch {
          try {
            invoiceRes = await fetch(`http://localhost:8000/invoices/?phone=${PHONE}`)
          } catch {
            invoiceRes = null
          }
        }

        if (!invoiceRes || !invoiceRes.ok) {
          throw new Error('Could not fetch invoices')
        }

        const invoiceData = await invoiceRes.json()
        const invoices = Array.isArray(invoiceData)
          ? invoiceData
          : invoiceData.invoices ?? invoiceData.data ?? []

        let invoice = null

        if (requestedInvoiceNumber) {
          const reqClean = requestedInvoiceNumber.replace(/[^A-Z0-9]/g, '')
          invoice = invoices.find((inv: any) => {
            const invNum = String(inv.invoice_number || '').toUpperCase()
            return (
              invNum === requestedInvoiceNumber ||
              invNum.replace(/[^A-Z0-9]/g, '') === reqClean
            )
          })
        } else if (invoices.length === 1) {
          invoice = invoices[0]
        }

        if (!invoice) {
          const messageText = requestedInvoiceNumber
            ? `I couldn't find invoice ${requestedInvoiceNumber}.`
            : 'Please specify which invoice you want the PDF for, for example: "Generate an invoice PDF for INV-002".'

          setMessages(prev => [
            ...prev,
            {
              id: newId(),
              sender: 'copilot',
              text: messageText,
              mode: 'fallback',
              intent: 'invoice_pdf',
              timestamp: new Date()
            }
          ])

          return
        }

        const pdfUrl = `${API_BASE}/invoices/${invoice.id}/pdf?phone=${PHONE}`

        const copilotMsg: Message = {
          id: newId(),
          sender: 'copilot',
          text: '',
          mode: 'fallback',
          intent: 'invoice_pdf',
          pdfUrl,
          pdfLabel: `Invoice PDF — ${invoice.invoice_number}`,
          timestamp: new Date()
        }

        setMessages(prev => [...prev, copilotMsg])

        return
      }

      // ------------------------------------------------------------
      // QUOTATION PDF REQUESTS
      // Handle quotation PDF generation directly through the backend
      // ------------------------------------------------------------
      const isQuotationPdfRequest =
        lowerQuery.includes('pdf') &&
        (lowerQuery.includes('quotation') || lowerQuery.includes('quote'))

      if (isQuotationPdfRequest) {
        // Try to find a quotation number such as QTN-001 or QUO-001
        const quotationNumberMatch = query.match(/(?:QTN|QUO)-?\d+/i)
        const requestedQuotationNumber = quotationNumberMatch?.[0]?.toUpperCase()

        let quotationRes: Response | null = null
        try {
          quotationRes = await fetch(`${API_BASE}/quotations/?phone=${PHONE}`)
          if (!quotationRes.ok) {
            quotationRes = await fetch(`http://localhost:8000/quotations/?phone=${PHONE}`)
          }
        } catch {
          try {
            quotationRes = await fetch(`http://localhost:8000/quotations/?phone=${PHONE}`)
          } catch {
            quotationRes = null
          }
        }

        if (!quotationRes || !quotationRes.ok) {
          throw new Error('Could not fetch quotations')
        }

        const quotationData = await quotationRes.json()
        const quotations = Array.isArray(quotationData)
          ? quotationData
          : quotationData.quotations ?? quotationData.data ?? []

        let quotation = null

        if (requestedQuotationNumber) {
          const reqClean = requestedQuotationNumber.replace(/[^A-Z0-9]/g, '')
          quotation = quotations.find((q: any) => {
            const qNum = String(q.quotation_number || '').toUpperCase()
            return (
              qNum === requestedQuotationNumber ||
              qNum.replace(/[^A-Z0-9]/g, '') === reqClean
            )
          })
        } else if (quotations.length === 1) {
          quotation = quotations[0]
        }

        if (!quotation) {
          const messageText = requestedQuotationNumber
            ? `I couldn't find quotation ${requestedQuotationNumber}.`
            : 'Please specify which quotation you want the PDF for, for example: "Generate a quotation PDF for QTN-001".'

          setMessages(prev => [
            ...prev,
            {
              id: newId(),
              sender: 'copilot',
              text: messageText,
              mode: 'fallback',
              intent: 'quotation_pdf',
              timestamp: new Date()
            }
          ])

          return
        }

        const pdfUrl = `${API_BASE}/quotations/${quotation.id}/pdf?phone=${PHONE}`

        const copilotMsg: Message = {
          id: newId(),
          sender: 'copilot',
          text: '',
          mode: 'fallback',
          intent: 'quotation_pdf',
          pdfUrl,
          pdfLabel: `Quotation PDF — ${quotation.quotation_number}`,
          timestamp: new Date()
        }

        setMessages(prev => [...prev, copilotMsg])

        return
      }

      // ------------------------------------------------------------
      // NORMAL CHAT REQUEST
      // ------------------------------------------------------------
      let res = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, phone: PHONE }),
      })

      if (!res.ok) {
        res = await fetch('http://localhost:8000/chat/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query, phone: PHONE }),
        })
      }

      const data = await res.json()

      const replyText: string =
        data.reply || 'No response from copilot.'

      // Check for embedded PDF references
      const pdfInfo = extractPdfUrl(replyText)

      const copilotMsg: Message = {
        id: newId(),
        sender: 'copilot',
        text: pdfInfo ? '' : replyText,
        mode: data.mode,
        intent: data.intent,
        pdfUrl: pdfInfo?.pdfUrl,
        pdfLabel: pdfInfo?.pdfLabel,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, copilotMsg])

    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          sender: 'copilot',
          text: 'Error connecting to backend.',
          mode: 'error',
          timestamp: new Date()
        },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const hasUserMessages = messages.some(m => m.sender === 'user')

  // ─── Sidebar placeholder conversations ─────────────────────────────────────
  const placeholderConvos = [
    { name: 'Rajesh Traders', preview: 'Invoice INV-001 sent ✓✓', time: 'Yesterday', unread: 0, color: '#7c3aed' },
    { name: 'Sunil & Co.', preview: 'Quotation approved 👍', time: 'Mon', unread: 2, color: '#dc2626' },
    { name: 'Meena Stores', preview: 'Payment received ₹12,000', time: 'Sun', unread: 0, color: '#0891b2' },
  ]

  // ─── Build message list with grouping & date separators ────────────────────
  interface RenderedItem {
    type: 'date' | 'message'
    key: string
    label?: string
    msg?: Message
    isFirst?: boolean
  }

  const rendered: RenderedItem[] = []
  let lastDate: Date | null = null
  let lastSender: string | null = null

  messages.forEach((msg, idx) => {
    // Date separator
    if (!lastDate || !isSameDay(lastDate, msg.timestamp)) {
      rendered.push({ type: 'date', key: `date-${idx}`, label: formatDateLabel(msg.timestamp) })
      lastDate = msg.timestamp
      lastSender = null // reset grouping after date separator
    }
    // Message grouping: isFirst = true if different sender than previous
    const isFirst = lastSender !== msg.sender
    rendered.push({ type: 'message', key: String(msg.id), msg, isFirst })
    lastSender = msg.sender
  })

  return (
    <>
      <style>{`
        @keyframes wa-bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-5px); }
        }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.25); }

        .wa-icon-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 6px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #54656f;
          transition: background 0.15s;
        }
        .wa-icon-btn:hover { background: rgba(11,20,26,0.08); }

        .wa-send-btn {
          border: none;
          border-radius: 50%;
          width: 48px;
          height: 48px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.15s, transform 0.1s;
          flex-shrink: 0;
          background: #00a884;
        }
        .wa-send-btn:hover { background: #009676; transform: scale(1.04); }
        .wa-send-btn:active { transform: scale(0.97); }

        .wa-quick-chip {
          background: #fff;
          color: #00a884;
          border: 1.5px solid #00a884;
          border-radius: 18px;
          padding: 5px 14px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.15s, color 0.15s;
          white-space: nowrap;
          font-family: inherit;
        }
        .wa-quick-chip:hover { background: #00a884; color: #fff; }

        .wa-sidebar-item {
          display: flex;
          align-items: center;
          padding: 10px 16px;
          gap: 12px;
          cursor: pointer;
          border-bottom: 1px solid #f0f2f5;
          transition: background 0.12s;
          min-height: 72px;
        }
        .wa-sidebar-item:hover { background: #f5f6f6; }
        .wa-sidebar-item.active { background: #f0f2f5; }

        .wa-filter-tab {
          flex: 1;
          text-align: center;
          padding: 8px 0;
          font-size: 14px;
          font-weight: 500;
          color: #54656f;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          transition: color 0.15s, border-color 0.15s;
          user-select: none;
        }
        .wa-filter-tab.active {
          color: #00a884;
          border-bottom-color: #00a884;
        }

        .wa-admin-link {
          font-size: 11px;
          color: #667781;
          text-decoration: none;
          padding: 3px 8px;
          border-radius: 12px;
          background: #e9edef;
          transition: background 0.12s, color 0.12s;
        }
        .wa-admin-link:hover { background: #d1d7db; color: #111b21; }

        .wa-composer-input {
          flex: 1;
          background: #fff;
          border: none;
          border-radius: 24px;
          padding: 10px 16px;
          font-size: 15px;
          color: #111b21;
          outline: none;
          font-family: inherit;
          min-height: 42px;
          resize: none;
        }
        .wa-composer-input::placeholder { color: #8696a0; }
      `}</style>

      <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#f0f2f5', overflow: 'hidden' }}>

        {/* ═══════════════════════════ LEFT SIDEBAR ═══════════════════════════ */}
        <div style={{
          width: 360, minWidth: 360, height: '100%', display: 'flex', flexDirection: 'column',
          background: '#fff', borderRight: '1px solid #e9edef', flexShrink: 0,
        }}>

          {/* Sidebar Header */}
          <div style={{
            height: 60, background: '#f0f2f5', display: 'flex', alignItems: 'center',
            padding: '0 16px', gap: 12, flexShrink: 0,
          }}>
            <Avatar letter="U" size={40} color="#54656f" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 16, color: '#111b21' }}>M1M</div>
              <div style={{ fontSize: 12, color: '#667781' }}>Munim.ai</div>
            </div>
            <div style={{ display: 'flex', gap: 2 }}>
              <button className="wa-icon-btn" title="New Chat"><IconNewChat /></button>
              <button className="wa-icon-btn" title="Admin options" onClick={() => window.location.href = '/dashboard'}><IconDots /></button>
            </div>
          </div>

          {/* Search Bar */}
          <div style={{ padding: '8px 12px', background: '#fff', flexShrink: 0 }}>
            <div style={{
              display: 'flex', alignItems: 'center', background: '#f0f2f5',
              borderRadius: 10, padding: '7px 14px', gap: 10,
            }}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="#54656f">
                <path d="M15.009 13.805h-.636l-.22-.219a5.184 5.184 0 0 0 1.256-3.386 5.207 5.207 0 1 0-5.207 5.208 5.184 5.184 0 0 0 3.385-1.255l.221.22v.635l4.004 3.999 1.194-1.195-3.997-4.007zm-4.808 0a3.605 3.605 0 1 1 0-7.21 3.605 3.605 0 0 1 0 7.21z" />
              </svg>
              <input
                type="text"
                placeholder="Search or start new chat"
                style={{
                  border: 'none', background: 'none', outline: 'none',
                  fontSize: 14, color: '#111b21', flex: 1, fontFamily: 'inherit',
                }}
              />
            </div>
          </div>

          {/* Filter Tabs — All / Unread */}
          <div style={{
            display: 'flex', borderBottom: '1px solid #e9edef', flexShrink: 0,
          }}>
            <div
              className={`wa-filter-tab${sidebarFilter === 'all' ? ' active' : ''}`}
              onClick={() => setSidebarFilter('all')}
            >All</div>
            <div
              className={`wa-filter-tab${sidebarFilter === 'unread' ? ' active' : ''}`}
              onClick={() => setSidebarFilter('unread')}
            >Unread</div>
          </div>

          {/* Conversation List */}
          <div style={{ flex: 1, overflowY: 'auto' }}>

            {/* Active: M1M Business Copilot */}
            <div className="wa-sidebar-item active">
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <Avatar letter="M" size={50} color="#00a884" />
                <div style={{
                  position: 'absolute', bottom: 1, right: 1,
                  width: 13, height: 13, background: '#25d366',
                  borderRadius: '50%', border: '2.5px solid #f0f2f5',
                }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 3 }}>
                  <span style={{ fontWeight: 600, fontSize: 16, color: '#111b21' }}>M1M Business Copilot</span>
                  <span style={{ fontSize: 12, color: '#00a884', flexShrink: 0, marginLeft: 4 }}>{formatSidebarTime(lastActivity)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{
                    fontSize: 13.5, color: '#667781',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 210,
                  }}>
                    {messages[messages.length - 1]?.text?.split('\n')[0]?.slice(0, 38) || 'Hi! How can I help your business?'}
                  </span>
                </div>
              </div>
            </div>

            {/* Placeholder conversations — hidden when "Unread" filter active and no unread count */}
            {placeholderConvos
              .filter(c => sidebarFilter === 'all' || c.unread > 0)
              .map(c => (
                <div key={c.name} className="wa-sidebar-item">
                  <Avatar letter={c.name[0]} size={50} color={c.color} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 3 }}>
                      <span style={{ fontWeight: 500, fontSize: 16, color: '#111b21' }}>{c.name}</span>
                      <span style={{ fontSize: 12, color: c.unread > 0 ? '#25d366' : '#667781', flexShrink: 0, marginLeft: 4 }}>{c.time}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{
                        fontSize: 13.5, color: '#667781',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 210,
                      }}>
                        {c.preview}
                      </span>
                      {c.unread > 0 && (
                        <span style={{
                          background: '#25d366', color: '#fff', borderRadius: '50%',
                          minWidth: 20, height: 20, fontSize: 12, fontWeight: 700,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          flexShrink: 0, padding: '0 4px',
                        }}>{c.unread}</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
          </div>

          {/* Sidebar Footer — Admin links */}
          <div style={{
            borderTop: '1px solid #e9edef', padding: '8px 12px',
            display: 'flex', gap: 8, flexWrap: 'wrap', background: '#f0f2f5',
          }}>
            {[
              { label: 'Dashboard', href: '/dashboard' },
              { label: 'Customers', href: '/customers' },
              { label: 'Inventory', href: '/inventory' },
              { label: 'Documents', href: '/documents' },
            ].map(link => (
              <a key={link.href} href={link.href} className="wa-admin-link">{link.label}</a>
            ))}
          </div>
        </div>

        {/* ═══════════════════════════ RIGHT CHAT PANEL ═══════════════════════ */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', minWidth: 0 }}>

          {/* Chat Header */}
          <div style={{
            height: 60, background: '#f0f2f5', display: 'flex', alignItems: 'center',
            padding: '0 16px', gap: 12, flexShrink: 0, borderBottom: '1px solid #e9edef',
          }}>
            <div style={{ position: 'relative', cursor: 'pointer' }}>
              <Avatar letter="M" size={40} color="#00a884" />
              <div style={{
                position: 'absolute', bottom: 1, right: 1,
                width: 10, height: 10, background: '#25d366',
                borderRadius: '50%', border: '2px solid #f0f2f5',
              }} />
            </div>
            <div style={{ flex: 1, cursor: 'pointer' }}>
              <div style={{ fontWeight: 600, fontSize: 16, color: '#111b21', lineHeight: 1.3 }}>
                M1M Business Copilot
              </div>
              <div style={{ fontSize: 13, color: '#25d366', lineHeight: 1.3 }}>online</div>
            </div>
            {/* 3 icons: video, search, more — exactly like WhatsApp Web */}
            <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <button className="wa-icon-btn" title="Video call"><IconVideoCall /></button>
              <button className="wa-icon-btn" title="Search"><IconSearch /></button>
              <button className="wa-icon-btn" title="More options"><IconDots /></button>
            </div>
          </div>

          {/* Message Area */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0', ...WA_BG_STYLE }}>

            {rendered.map(item => {
              if (item.type === 'date') {
                return <DateSeparator key={item.key} label={item.label!} />
              }
              const { msg, isFirst } = item
              return msg!.sender === 'user'
                ? <UserBubble key={item.key} msg={msg!} isFirst={isFirst!} />
                : <CopilotBubble key={item.key} msg={msg!} isFirst={isFirst!} />
            })}

            {/* Quick action chips — shown after welcome message when no user messages yet */}
            {!hasUserMessages && (
              <div style={{ padding: '6px 12px 12px 52px', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {QUICK_ACTIONS.map(action => (
                  <button
                    key={action.query}
                    className="wa-quick-chip"
                    onClick={() => sendMessage(action.query)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}

            {loading && <TypingIndicator />}
            <div ref={bottomRef} style={{ paddingBottom: 4 }} />
          </div>

          {/* Message Composer */}
          <div style={{
            background: '#f0f2f5', padding: '8px 16px',
            display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
          }}>
            {/* Emoji */}
            <button className="wa-icon-btn" title="Emoji"><IconEmoji /></button>

            {/* Attachment */}
            <button className="wa-icon-btn" title="Attach file"><IconAttach /></button>

            {/* Text Input — pill shape */}
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message"
              disabled={loading}
              className="wa-composer-input"
            />

            {/* Send / Mic button */}
            {input.trim() ? (
              <button
                className="wa-send-btn"
                onClick={() => sendMessage()}
                title="Send message"
                id="send-btn"
              >
                <IconSend />
              </button>
            ) : (
              <button
                className="wa-send-btn"
                title="Voice message"
                id="mic-btn"
              >
                <IconMic />
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
