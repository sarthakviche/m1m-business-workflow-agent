import React, { useEffect, useState } from 'react'

interface Item {
  id: string
  name: string
  hsn_code: string | null
  gst_rate_percent: number
  unit_price: number
  unit: string
}

const API_BASE = 'http://127.0.0.1:8000'

export default function Inventory() {
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API_BASE}/items/?phone=9876543210`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(data => {
        setItems(data)
        setLoading(false)
      })
      .catch(() => {
        fetch('http://localhost:8000/items/?phone=9876543210')
          .then(res => res.json())
          .then(data => {
            setItems(data)
            setLoading(false)
          })
          .catch(() => {
            setError('Failed to fetch inventory catalog.')
            setLoading(false)
          })
      })
  }, [])

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>Product & Inventory Catalog</h1>
        <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>Real database item pricing & GST rates</p>
      </header>

      <nav style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <a href="/dashboard" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Dashboard</a>
        <a href="/customers" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Customers</a>
        <a href="/inventory" style={{ color: '#38bdf8', padding: '8px 16px', borderRadius: '6px', background: '#1e293b', textDecoration: 'none', fontWeight: 600 }}>Inventory</a>
        <a href="/documents" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Invoices & Quotations</a>
        <a href="/chat" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Copilot Chat</a>
      </nav>

      {loading && <div style={{ color: '#94a3b8' }}>Loading catalog items...</div>}
      {error && <div style={{ color: '#f87171', padding: '12px', background: '#450a0a', borderRadius: '6px' }}>{error}</div>}

      {!loading && !error && (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#1e293b', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ background: '#334155', color: '#38bdf8', textAlign: 'left' }}>
              <th style={{ padding: '12px' }}>Item Name</th>
              <th style={{ padding: '12px' }}>HSN Code</th>
              <th style={{ padding: '12px' }}>Unit Price</th>
              <th style={{ padding: '12px' }}>GST Rate</th>
              <th style={{ padding: '12px' }}>Unit</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, idx) => (
              <tr key={it.id} style={{ borderBottom: '1px solid #334155', background: idx % 2 === 0 ? '#1e293b' : '#0f172a' }}>
                <td style={{ padding: '12px', fontWeight: 600 }}>{it.name}</td>
                <td style={{ padding: '12px' }}>{it.hsn_code || 'N/A'}</td>
                <td style={{ padding: '12px', color: '#4ade80' }}>₹{it.unit_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                <td style={{ padding: '12px' }}>{it.gst_rate_percent}%</td>
                <td style={{ padding: '12px' }}>{it.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
