// Links a Telegram chat to this business: one tap opens the bot with the code
// filled in, and the panel notices by itself when the link goes through.

import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { TelegramLinkCode, TelegramStatus } from '../api/client'
import { IconCheck, IconCopy, IconTelegram } from './icons'
import { Button } from './ui'

const POLL_MS = 3000

export default function TelegramLinkPanel({ onLinked }: { onLinked?: () => void }) {
  const [status, setStatus] = useState<TelegramStatus | null>(null)
  const [link, setLink] = useState<TelegramLinkCode | null>(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const linkedRef = useRef(false)

  const refresh = useCallback(async () => {
    try {
      const next = await api.telegramStatus()
      setStatus(next)
      if (next.linked && !linkedRef.current) {
        linkedRef.current = true
        setLink(null)
        onLinked?.()
      }
    } catch {
      // Status is a convenience; the code still works without it.
    }
  }, [onLinked])

  useEffect(() => { void refresh() }, [refresh])

  // While a code is out, watch for the chat to link.
  useEffect(() => {
    if (!link) return
    const timer = setInterval(() => void refresh(), POLL_MS)
    return () => clearInterval(timer)
  }, [link, refresh])

  async function connect() {
    // Open the tab during the click so popup blockers allow it; point it at the bot once the code exists.
    const tab = window.open('', '_blank')
    setBusy(true)
    setError(null)
    setCopied(false)
    try {
      const issued = await api.createTelegramLinkCode()
      setLink(issued)
      if (tab && issued.deep_link) tab.location.href = issued.deep_link
      else tab?.close()
    } catch (err) {
      tab?.close()
      setError(err instanceof Error ? err.message : 'Could not create a link code.')
    } finally {
      setBusy(false)
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  if (status && !status.configured) {
    return <p className="text-sm text-slate-500">Telegram isn't set up on this server yet.</p>
  }

  if (status?.linked) {
    const names = status.chats.map((c) => c.display_name).filter(Boolean).join(', ')
    return (
      <div className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white"><IconCheck size={18} /></span>
        <div className="min-w-0">
          <p className="font-semibold text-emerald-900">Telegram connected</p>
          <p className="mt-0.5 text-sm text-emerald-800">
            {names ? `Linked to ${names}. ` : ''}Message {status.bot_username ? `@${status.bot_username}` : 'the bot'} to create quotations and invoices.
          </p>
          <Button variant="secondary" className="mt-3" onClick={connect} disabled={busy}>
            {busy ? 'Creating…' : 'Link another phone'}
          </Button>
        </div>
      </div>
    )
  }

  const command = link ? `/link ${link.code}` : ''
  const expires = link ? new Date(link.expires_at).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) : ''

  return (
    <div>
      {link ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50/60 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-sky-900">
            <span className="h-2 w-2 animate-pulse rounded-full bg-sky-500" aria-hidden /> Waiting for Telegram…
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Tap <strong>Start</strong> in the Munim bot. If it didn't open, send this to {link.bot_username ? <strong>@{link.bot_username}</strong> : 'the bot'}:
          </p>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 rounded-lg bg-white px-3 py-2 font-mono text-base font-semibold tracking-wider text-slate-900 ring-1 ring-slate-200">{command}</code>
            <Button variant="secondary" className="px-3" onClick={() => copy(command)} aria-label="Copy command">
              {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
            </Button>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {link.deep_link && (
              <a href={link.deep_link} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-600">
                <IconTelegram size={16} /> Open Telegram
              </a>
            )}
            <span className="text-xs text-slate-500">Works once · expires at {expires}</span>
          </div>
        </div>
      ) : (
        <Button onClick={connect} disabled={busy}>
          <IconTelegram size={16} /> {busy ? 'Opening…' : 'Connect Telegram'}
        </Button>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  )
}
