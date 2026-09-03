import React, { useState } from 'react'

interface Message {
  sender: 'user' | 'copilot'
  text: string
  mode?: string
  intent?: string
}

const API_BASE = 'http://127.0.0.1:8000'

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'copilot',
      text: 'Hello! I am your Munim.ai Business Copilot. How can I help your business today?',
      mode: 'ready',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async (textToSend?: string) => {
    const query = textToSend || input
    if (!query.trim()) return

    const newMsgs: Message[] = [...messages, { sender: 'user', text: query }]
    setMessages(newMsgs)
    if (!textToSend) setInput('')
    setLoading(true)

    try {
      let res = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, phone: '9876543210' }),
      })
      if (!res.ok) {
        res = await fetch('http://localhost:8000/chat/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query, phone: '9876543210' }),
        })
      }
      const data = await res.json()
      setMessages([
        ...newMsgs,
        {
          sender: 'copilot',
          text: data.reply || 'No response from copilot.',
          mode: data.mode,
          intent: data.intent,
        },
      ])
    } catch (err) {
      setMessages([
        ...newMsgs,
        {
          sender: 'copilot',
          text: 'Error connecting to backend chat service.',
          mode: 'error',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>Munim.ai Copilot Chat</h1>
        <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>LLM Agent with Deterministic Database Fallback</p>
      </header>

      <nav style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <a href="/dashboard" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Dashboard</a>
        <a href="/customers" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Customers</a>
        <a href="/inventory" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Inventory</a>
        <a href="/documents" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Invoices & Quotations</a>
        <a href="/chat" style={{ color: '#38bdf8', padding: '8px 16px', borderRadius: '6px', background: '#1e293b', textDecoration: 'none', fontWeight: 600 }}>Copilot Chat</a>
      </nav>

      {/* Preset demo buttons */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
        <span style={{ color: '#64748b', fontSize: '13px', alignSelf: 'center' }}>Demo Shortcuts:</span>
        {['show my customers', 'show my items', 'show unpaid invoices', 'how much money is outstanding?', 'show invoice INV-002', 'show my quotations'].map(prompt => (
          <button
            key={prompt}
            onClick={() => sendMessage(prompt)}
            style={{
              background: '#334155',
              color: '#e2e8f0',
              border: 'none',
              padding: '6px 12px',
              borderRadius: '20px',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Chat Messages */}
      <div style={{ flex: 1, background: '#1e293b', borderRadius: '12px', padding: '16px', overflowY: 'auto', marginBottom: '16px', border: '1px solid #334155', minHeight: '320px' }}>
        {messages.map((m, idx) => (
          <div key={idx} style={{ marginBottom: '12px', textAlign: m.sender === 'user' ? 'right' : 'left' }}>
            <div
              style={{
                display: 'inline-block',
                maxWidth: '75%',
                padding: '12px 16px',
                borderRadius: '12px',
                background: m.sender === 'user' ? '#0284c7' : '#0f172a',
                color: '#fff',
                whiteSpace: 'pre-wrap',
                border: m.sender === 'user' ? 'none' : '1px solid #334155',
              }}
            >
              {m.text}
              {m.mode && (
                <div style={{ fontSize: '10px', marginTop: '6px', color: m.mode === 'llm' ? '#4ade80' : '#fbbf24', textAlign: 'right' }}>
                  Mode: {m.mode.toUpperCase()} {m.intent ? `(${m.intent})` : ''}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <div style={{ color: '#94a3b8', fontStyle: 'italic' }}>Copilot is thinking...</div>}
      </div>

      {/* Input box */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="Ask Copilot about customers, invoices, items, or dues..."
          style={{ flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid #334155', background: '#0f172a', color: '#fff', fontSize: '14px' }}
        />
        <button
          onClick={() => sendMessage()}
          style={{ padding: '12px 24px', borderRadius: '8px', border: 'none', background: 'linear-gradient(135deg, #0284c7, #2563eb)', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
