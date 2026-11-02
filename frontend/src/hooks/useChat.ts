// Conversation state for the assistant screen.
//
// Every turn goes to POST /api/v1/chat with the prior turns and a stable
// conversation id, so the backend can resume a half-finished request
// ("quotation for Ramesh" → "10 TMT rods"). Starting a new chat issues a new id.

import { useCallback, useRef, useState } from 'react'
import { api } from '../api/client'
import type { ChatTurn } from '../api/client'
import type { ChatMessage } from '../types/chat'

function newId(): string {
  return crypto.randomUUID()
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const conversationId = useRef(newId())
  // Mirror of `messages` so sendMessage always builds history from the latest turns.
  const messagesRef = useRef<ChatMessage[]>([])

  const append = useCallback((message: ChatMessage) => {
    messagesRef.current = [...messagesRef.current, message]
    setMessages(messagesRef.current)
  }, [])

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return

    const history: ChatTurn[] = messagesRef.current
      .filter((m) => !m.failed)
      .map((m) => ({ role: m.role, content: m.text }))
    append({ id: newId(), role: 'user', text: trimmed, timestamp: new Date() })
    setIsLoading(true)

    try {
      const response = await api.chat(trimmed, history, conversationId.current)
      append({
        id: newId(),
        role: 'assistant',
        text: response.response_text || 'Done.',
        timestamp: new Date(),
        document_type: response.document_type ?? undefined,
        document_data: response.data ?? undefined,
        pdf_url: response.pdf_url,
      })
    } catch (err) {
      append({
        id: newId(),
        role: 'assistant',
        text: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
        timestamp: new Date(),
        failed: true,
      })
    } finally {
      setIsLoading(false)
    }
  }, [append])

  const reset = useCallback(() => {
    conversationId.current = newId()
    messagesRef.current = []
    setMessages([])
  }, [])

  return { messages, isLoading, sendMessage, reset }
}
