import React, { useEffect, useState } from 'react'

interface Metrics {
  total_customers: number
  total_items: number
  total_invoices: number
  total_quotations: number
  total_sales: number
  total_paid_amount: number
  outstanding_amount: number
  paid_invoices_count: number
  unpaid_invoices_count: number
  partially_paid_count: number
  overdue_invoices_count: number
}

const API_BASE = 'http://127.0.0.1:8000'

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API_BASE}/dashboard/summary?phone=9876543210`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`)
        return res.json()
      })
      .then(data => {
        setMetrics(data)
        setLoading(false)
      })
      .catch(() => {
        // Fallback to localhost if 127.0.0.1 fails
        fetch('http://localhost:8000/dashboard/summary?phone=9876543210')
          .then(res => res.json())
          .then(data => {
            setMetrics(data)
            setLoading(false)
          })
          .catch(() => {
            setError('Failed to connect to backend at http://127.0.0.1:8000 or http://localhost:8000')
            setLoading(false)
          })
      })
  }, [])

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh' }}>
      <header style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>Munim.ai Dashboard</h1>
          <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>WhatsApp + Web SME Business Copilot (Tenant Phone: 9876543210)</p>
        </div>
        <a href="/chat" style={{ background: 'linear-gradient(135deg, #0284c7, #2563eb)', color: '#fff', padding: '10px 20px', borderRadius: '8px', textDecoration: 'none', fontWeight: 600 }}>Open Copilot Chat</a>
      </header>

      <nav style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <a href="/dashboard" style={{ color: '#38bdf8', padding: '8px 16px', borderRadius: '6px', background: '#1e293b', textDecoration: 'none', fontWeight: 600 }}>Dashboard</a>
        <a href="/customers" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Customers</a>
        <a href="/inventory" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Inventory</a>
        <a href="/documents" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Invoices & Quotations</a>
        <a href="/chat" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Copilot Chat</a>
      </nav>

      {loading && <div style={{ color: '#94a3b8', padding: '16px', background: '#1e293b', borderRadius: '8px' }}>Loading live backend database metrics...</div>}
      {error && <div style={{ color: '#f87171', padding: '12px', background: '#450a0a', borderRadius: '6px' }}>{error}</div>}

      {metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <span style={{ color: '#94a3b8', fontSize: '14px' }}>Total Sales</span>
            <h2 style={{ fontSize: '32px', margin: '8px 0', color: '#4ade80' }}>₹{metrics.total_sales.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</h2>
            <span style={{ color: '#64748b', fontSize: '12px' }}>Real PostgreSQL Sum</span>
          </div>

          <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <span style={{ color: '#94a3b8', fontSize: '14px' }}>Outstanding Dues</span>
            <h2 style={{ fontSize: '32px', margin: '8px 0', color: '#f87171' }}>₹{metrics.outstanding_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</h2>
            <span style={{ color: '#64748b', fontSize: '12px' }}>Invoiced - Payments</span>
          </div>

          <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <span style={{ color: '#94a3b8', fontSize: '14px' }}>Total Received</span>
            <h2 style={{ fontSize: '32px', margin: '8px 0', color: '#38bdf8' }}>₹{metrics.total_paid_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</h2>
            <span style={{ color: '#64748b', fontSize: '12px' }}>Payments Received</span>
          </div>

          <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <span style={{ color: '#94a3b8', fontSize: '14px' }}>Invoices Breakdown</span>
            <h3 style={{ fontSize: '20px', margin: '8px 0' }}>
              <span style={{ color: '#4ade80' }}>{metrics.paid_invoices_count} Paid</span> | <span style={{ color: '#fbbf24' }}>{metrics.unpaid_invoices_count} Unpaid</span>
            </h3>
            <span style={{ color: '#f87171', fontSize: '12px' }}>{metrics.overdue_invoices_count} Overdue Invoices</span>
          </div>

          <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <span style={{ color: '#94a3b8', fontSize: '14px' }}>Customers</span>
            <h2 style={{ fontSize: '32px', margin: '8px 0', color: '#f472b6' }}>{metrics.total_customers}</h2>
            <span style={{ color: '#64748b', fontSize: '12px' }}>Tenant Isolation Active</span>
          </div>

          <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <span style={{ color: '#94a3b8', fontSize: '14px' }}>Catalog Items</span>
            <h2 style={{ fontSize: '32px', margin: '8px 0', color: '#a78bfa' }}>{metrics.total_items}</h2>
            <span style={{ color: '#64748b', fontSize: '12px' }}>Items & Stock</span>
          </div>
        </div>
      )}
    </div>
  )
}
