import React, { useEffect, useState } from 'react'

interface Invoice {
  id: string
  invoice_number: string
  customer_name: string
  total_amount: number
  status: string
  due_date: string | null
}

interface Quotation {
  id: string
  quotation_number: string
  customer_name: string
  subtotal: number
  status: string
}

const API_BASE = 'http://127.0.0.1:8000'

export default function Documents() {
  const [activeTab, setActiveTab] = useState<'invoices' | 'quotations'>('invoices')
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [quotations, setQuotations] = useState<Quotation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    if (activeTab === 'invoices') {
      fetch(`${API_BASE}/invoices/?phone=9876543210`)
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          return res.json()
        })
        .then(data => {
          setInvoices(data)
          setLoading(false)
        })
        .catch(() => {
          fetch('http://localhost:8000/invoices/?phone=9876543210')
            .then(res => res.json())
            .then(data => {
              setInvoices(data)
              setLoading(false)
            })
            .catch(() => {
              setError('Failed to load invoices.')
              setLoading(false)
            })
        })
    } else {
      fetch(`${API_BASE}/quotations/?phone=9876543210`)
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          return res.json()
        })
        .then(data => {
          setQuotations(data)
          setLoading(false)
        })
        .catch(() => {
          fetch('http://localhost:8000/quotations/?phone=9876543210')
            .then(res => res.json())
            .then(data => {
              setQuotations(data)
              setLoading(false)
            })
            .catch(() => {
              setError('Failed to load quotations.')
              setLoading(false)
            })
        })
    }
  }, [activeTab])

  const downloadInvoicePdf = (invoiceId: string) => {
    window.open(`${API_BASE}/invoices/${invoiceId}/pdf?phone=9876543210`, '_blank')
  }

  const downloadQuotationPdf = (quotationId: string) => {
    window.open(`${API_BASE}/quotations/${quotationId}/pdf?phone=9876543210`, '_blank')
  }

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>Document Management & PDF Generation</h1>
        <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>Real PDF generation from database invoices & quotations</p>
      </header>

      <nav style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <a href="/dashboard" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Dashboard</a>
        <a href="/customers" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Customers</a>
        <a href="/inventory" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Inventory</a>
        <a href="/documents" style={{ color: '#38bdf8', padding: '8px 16px', borderRadius: '6px', background: '#1e293b', textDecoration: 'none', fontWeight: 600 }}>Invoices & Quotations</a>
        <a href="/chat" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Copilot Chat</a>
      </nav>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
        <button
          onClick={() => setActiveTab('invoices')}
          style={{
            padding: '10px 20px',
            borderRadius: '6px',
            border: 'none',
            fontWeight: 600,
            cursor: 'pointer',
            backgroundColor: activeTab === 'invoices' ? '#2563eb' : '#1e293b',
            color: '#fff'
          }}
        >
          📄 Invoices
        </button>
        <button
          onClick={() => setActiveTab('quotations')}
          style={{
            padding: '10px 20px',
            borderRadius: '6px',
            border: 'none',
            fontWeight: 600,
            cursor: 'pointer',
            backgroundColor: activeTab === 'quotations' ? '#2563eb' : '#1e293b',
            color: '#fff'
          }}
        >
          📝 Quotations
        </button>
      </div>

      {loading && <div style={{ color: '#94a3b8' }}>Loading documents...</div>}
      {error && <div style={{ color: '#f87171', padding: '12px', background: '#450a0a', borderRadius: '6px' }}>{error}</div>}

      {!loading && !error && activeTab === 'invoices' && (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#1e293b', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ background: '#334155', color: '#38bdf8', textAlign: 'left' }}>
              <th style={{ padding: '12px' }}>Invoice Number</th>
              <th style={{ padding: '12px' }}>Customer</th>
              <th style={{ padding: '12px' }}>Total Amount</th>
              <th style={{ padding: '12px' }}>Status</th>
              <th style={{ padding: '12px' }}>Due Date</th>
              <th style={{ padding: '12px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv, idx) => (
              <tr key={inv.id} style={{ borderBottom: '1px solid #334155', background: idx % 2 === 0 ? '#1e293b' : '#0f172a' }}>
                <td style={{ padding: '12px', fontWeight: 600 }}>#{inv.invoice_number}</td>
                <td style={{ padding: '12px' }}>{inv.customer_name}</td>
                <td style={{ padding: '12px', color: '#4ade80' }}>₹{inv.total_amount ? inv.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}</td>
                <td style={{ padding: '12px' }}>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 600,
                    backgroundColor: inv.status === 'paid' ? '#14532d' : '#7f1d1d',
                    color: inv.status === 'paid' ? '#4ade80' : '#f87171'
                  }}>
                    {inv.status.toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: '12px' }}>{inv.due_date || 'N/A'}</td>
                <td style={{ padding: '12px' }}>
                  <button
                    onClick={() => downloadInvoicePdf(inv.id)}
                    style={{
                      background: 'linear-gradient(135deg, #059669, #10b981)',
                      color: '#fff',
                      border: 'none',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: 600
                    }}
                  >
                    📥 Generate PDF
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!loading && !error && activeTab === 'quotations' && (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#1e293b', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ background: '#334155', color: '#38bdf8', textAlign: 'left' }}>
              <th style={{ padding: '12px' }}>Quotation Number</th>
              <th style={{ padding: '12px' }}>Customer</th>
              <th style={{ padding: '12px' }}>Subtotal</th>
              <th style={{ padding: '12px' }}>Status</th>
              <th style={{ padding: '12px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {quotations.map((q, idx) => (
              <tr key={q.id} style={{ borderBottom: '1px solid #334155', background: idx % 2 === 0 ? '#1e293b' : '#0f172a' }}>
                <td style={{ padding: '12px', fontWeight: 600 }}>#{q.quotation_number}</td>
                <td style={{ padding: '12px' }}>{q.customer_name}</td>
                <td style={{ padding: '12px', color: '#38bdf8' }}>₹{q.subtotal ? q.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}</td>
                <td style={{ padding: '12px' }}>
                  <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 600, backgroundColor: '#1e3a8a', color: '#93c5fd' }}>
                    {q.status.toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: '12px' }}>
                  <button
                    onClick={() => downloadQuotationPdf(q.id)}
                    style={{
                      background: 'linear-gradient(135deg, #2563eb, #3b82f6)',
                      color: '#fff',
                      border: 'none',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: 600
                    }}
                  >
                    📥 Generate PDF
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
