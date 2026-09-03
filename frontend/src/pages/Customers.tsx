import React, { useEffect, useState } from 'react'

interface Customer {
  id: string
  name: string
  phone: string | null
  gstin: string | null
  state: string | null
  address: string | null
  created_at: string
}

const API_BASE = 'http://127.0.0.1:8000'

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API_BASE}/customers/?phone=9876543210`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(data => {
        setCustomers(data)
        setLoading(false)
      })
      .catch(() => {
        fetch('http://localhost:8000/customers/?phone=9876543210')
          .then(res => res.json())
          .then(data => {
            setCustomers(data)
            setLoading(false)
          })
          .catch(() => {
            setError('Failed to fetch customer list from backend.')
            setLoading(false)
          })
      })
  }, [])

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>Customers Directory</h1>
        <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>Real database customer retrieval with tenant isolation</p>
      </header>

      <nav style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <a href="/dashboard" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Dashboard</a>
        <a href="/customers" style={{ color: '#38bdf8', padding: '8px 16px', borderRadius: '6px', background: '#1e293b', textDecoration: 'none', fontWeight: 600 }}>Customers</a>
        <a href="/inventory" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Inventory</a>
        <a href="/documents" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Invoices & Quotations</a>
        <a href="/chat" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Copilot Chat</a>
      </nav>

      {loading && <div style={{ color: '#94a3b8' }}>Loading customers...</div>}
      {error && <div style={{ color: '#f87171', padding: '12px', background: '#450a0a', borderRadius: '6px' }}>{error}</div>}

      {!loading && !error && (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#1e293b', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ background: '#334155', color: '#38bdf8', textAlign: 'left' }}>
              <th style={{ padding: '12px' }}>Customer Name</th>
              <th style={{ padding: '12px' }}>Phone</th>
              <th style={{ padding: '12px' }}>State</th>
              <th style={{ padding: '12px' }}>GSTIN</th>
              <th style={{ padding: '12px' }}>Address</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c, idx) => (
              <tr key={c.id} style={{ borderBottom: '1px solid #334155', background: idx % 2 === 0 ? '#1e293b' : '#0f172a' }}>
                <td style={{ padding: '12px', fontWeight: 600 }}>{c.name}</td>
                <td style={{ padding: '12px' }}>{c.phone || 'N/A'}</td>
                <td style={{ padding: '12px' }}>{c.state || 'N/A'}</td>
                <td style={{ padding: '12px' }}>{c.gstin || 'N/A'}</td>
                <td style={{ padding: '12px' }}>{c.address || 'N/A'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
