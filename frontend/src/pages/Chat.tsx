import { Fragment, useEffect, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import DocumentResultCard from '../components/chat/DocumentResultCard'
import { IconAlert, IconBox, IconFile, IconPlus, IconReceipt, IconSend } from '../components/icons'
import { LogoMark } from '../components/Logo'
import { Button } from '../components/ui'
import { useApp } from '../context/AppContext'
import { useChat } from '../hooks/useChat'
import { formatTime } from '../lib/format'
import type { ChatMessage } from '../types/chat'

// Only things the backend can actually do today.
const SUGGESTIONS = [
  { Icon: IconFile, title: 'Create a quotation', prompt: 'Create a quotation for Ramesh Traders for 10 TMT Steel Rod 12mm' },
  { Icon: IconReceipt, title: 'Make a GST invoice', prompt: 'Create an invoice for Patel Constructions for 20 MS Hex Bolt' },
  { Icon: IconReceipt, title: 'Convert a quotation', prompt: 'Convert quotation Q-202611-001 to an invoice' },
  { Icon: IconBox, title: 'Check price & stock', prompt: 'What is the price and stock of MS Hex Bolt?' },
]

/** Renders the assistant's Markdown subset: **bold**, _italic_ and line breaks. */
function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split('\n').map((line, li) => (
        <Fragment key={li}>
          {li > 0 && <br />}
          {line.split(/(\*\*[^*]+\*\*|(?<![\w])_[^_\n]+_(?![\w]))/g).map((part, pi) => {
            if (part.startsWith('**') && part.endsWith('**')) return <strong key={pi} className="font-semibold">{part.slice(2, -2)}</strong>
            if (/^_[^_]+_$/.test(part)) return <em key={pi}>{part.slice(1, -1)}</em>
            return <Fragment key={pi}>{part}</Fragment>
          })}
        </Fragment>
      ))}
    </>
  )
}

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed sm:max-w-[75%]
        ${isUser ? 'rounded-br-md bg-orange-500 text-white'
          : message.failed ? 'rounded-bl-md border border-red-200 bg-red-50 text-red-800'
          : 'rounded-bl-md border border-slate-200 bg-white text-slate-800 shadow-sm'}`}>
        {message.failed && <IconAlert size={16} className="mb-1 inline-block" />}{' '}
        <RichText text={message.text} />
      </div>
      {message.document_type && message.document_data && (
        <DocumentResultCard documentType={message.document_type} data={message.document_data} pdfUrl={message.pdf_url} />
      )}
      <span className="px-1 text-[11px] text-slate-400">{formatTime(message.timestamp)}</span>
    </div>
  )
}

function Welcome({ businessName, onPick }: { businessName: string; onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center py-8">
      <LogoMark className="h-12 self-start" />
      <h1 className="mt-4 font-display text-2xl font-bold tracking-tight text-slate-900">How can I help {businessName} today?</h1>
      <p className="mt-1 text-sm text-slate-500">
        Type in English or Hinglish. Prices, GST and stock always come from your catalog. Nothing is guessed.
      </p>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map(({ Icon, title, prompt }) => (
          <button key={title} onClick={() => onPick(prompt)}
            className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition-colors hover:border-orange-200 hover:bg-orange-50/40">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-600"><Icon size={18} /></span>
            <span>
              <span className="block text-sm font-semibold text-slate-900">{title}</span>
              <span className="mt-0.5 block text-xs text-slate-500">“{prompt}”</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

function Typing(): ReactNode {
  return (
    <div className="flex items-center gap-1.5 self-start rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm" aria-label="Assistant is typing">
      {[0, 150, 300].map((d) => <span key={d} className="h-2 w-2 animate-bounce rounded-full bg-slate-300" style={{ animationDelay: `${d}ms` }} />)}
    </div>
  )
}

export default function Chat() {
  const { business } = useApp()
  const { messages, isLoading, sendMessage, reset } = useChat()
  const location = useLocation()
  const navigate = useNavigate()
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  // Quick actions elsewhere open this screen with a prompt to finish.
  useEffect(() => {
    const incoming = (location.state as { draft?: string } | null)?.draft
    if (incoming) {
      setDraft(incoming)
      navigate(location.pathname, { replace: true, state: null })
      requestAnimationFrame(() => {
        const el = inputRef.current
        if (el) { el.focus(); el.setSelectionRange(incoming.length, incoming.length) }
      })
    }
  }, [location.state, location.pathname, navigate])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isLoading])

  // Grow the composer with its content, up to a limit.
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [draft])

  function submit(text = draft) {
    if (!text.trim() || isLoading) return
    setDraft('')
    void sendMessage(text)
    inputRef.current?.focus()
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200/80 bg-white px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <h1 className="font-display text-base font-semibold text-slate-900">Assistant</h1>
          <p className="truncate text-xs text-slate-500">Quotations, GST invoices and stock checks</p>
        </div>
        {messages.length > 0 && (
          <Button variant="secondary" className="px-3 py-2" onClick={() => { reset(); setDraft(''); inputRef.current?.focus() }}>
            <IconPlus size={16} /> New chat
          </Button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6" aria-live="polite">
        {messages.length === 0 ? (
          // Suggestions fill the composer rather than sending: they name sample
          // customers, and sending would create a real document for them.
          <Welcome businessName={business?.business_name ?? 'your business'}
            onPick={(p) => { setDraft(p); requestAnimationFrame(() => inputRef.current?.focus()) }} />
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 py-6">
            {messages.map((m) => <Bubble key={m.id} message={m} />)}
            {isLoading && <Typing />}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <form className="border-t border-slate-200/80 bg-white px-4 py-3 sm:px-6"
        onSubmit={(e) => { e.preventDefault(); submit() }}>
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-1.5 focus-within:border-orange-300 focus-within:ring-2 focus-within:ring-orange-100">
          <label htmlFor="chat-input" className="sr-only">Message the assistant</label>
          <textarea id="chat-input" ref={inputRef} rows={1} value={draft} maxLength={2000}
            onChange={(e) => setDraft(e.target.value)} onKeyDown={onKeyDown}
            placeholder="e.g. Quotation for Ramesh Traders, 10 TMT Steel Rod 12mm"
            className="max-h-40 min-h-[40px] flex-1 resize-none bg-transparent px-3 py-2 text-[15px] text-slate-900 placeholder:text-slate-400 focus:outline-none" />
          <button type="submit" disabled={!draft.trim() || isLoading} aria-label="Send"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-orange-500 text-white transition-colors hover:bg-orange-600 disabled:bg-slate-200 disabled:text-slate-400">
            <IconSend size={18} />
          </button>
        </div>
        <p className="mx-auto mt-1.5 hidden max-w-3xl px-1 text-[11px] text-slate-400 sm:block">Enter to send · Shift + Enter for a new line</p>
      </form>
    </div>
  )
}
