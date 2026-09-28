import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { API_BASE, TEST_PHONE } from '../api/config'

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

function StatCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent: string }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 flex flex-col gap-1">
      <div className="flex items-center gap-2 mb-1">
        <div className={`w-1 h-8 rounded-full ${accent}`} />
        <span className="text-sm text-slate-500 font-medium">{label}</span>
      </div>
      <p className="text-2xl font-bold text-slate-900 font-display">{value}</p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const { businessName } = useApp()
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/dashboard/summary?phone=${TEST_PHONE}`)
      .then(r => r.json())
      .then(d => { setMetrics(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="p-5 md:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-display font-bold text-slate-900">
          {greeting}, <span className="text-orange-500">{businessName}</span> 👋
        </h1>
        <p className="text-slate-500 mt-1 text-sm">Here's what's happening with your business today.</p>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-3 mb-8 flex-wrap">
        <a
          href="/chat"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-orange-500 to-orange-600 text-white text-sm font-semibold shadow-md shadow-orange-200 hover:shadow-orange-300 transition-all"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
          </svg>
          New Invoice via Chat
        </a>
        <a
          href="/documents"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-orange-200 text-orange-600 text-sm font-semibold hover:bg-orange-50 transition-all"
        >
          View Documents
        </a>
      </div>

      {/* Metrics */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="bg-white rounded-2xl p-5 h-28 animate-pulse border border-slate-100" />
          ))}
        </div>
      ) : metrics ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard
            label="Total Sales"
            value={`₹${(metrics.total_sales || 0).toLocaleString('en-IN')}`}
            sub="This financial year"
            accent="bg-orange-500"
          />
          <StatCard
            label="Outstanding Dues"
            value={`₹${(metrics.outstanding_amount || 0).toLocaleString('en-IN')}`}
            sub="Pending payments"
            accent="bg-red-400"
          />
          <StatCard
            label="Received"
            value={`₹${(metrics.total_paid_amount || 0).toLocaleString('en-IN')}`}
            sub="Payments collected"
            accent="bg-green-400"
          />
          <StatCard
            label="Customers"
            value={String(metrics.total_customers || 0)}
            accent="bg-violet-400"
          />
          <StatCard
            label="Catalog Items"
            value={String(metrics.total_items || 0)}
            accent="bg-blue-400"
          />
          <StatCard
            label="Invoices"
            value={String(metrics.total_invoices || 0)}
            sub={`${metrics.overdue_invoices_count || 0} overdue`}
            accent="bg-amber-400"
          />
        </div>
      ) : (
        <div className="bg-orange-50 border border-orange-100 rounded-2xl p-6 text-center">
          <p className="text-orange-600 font-medium">Backend not connected</p>
          <p className="text-slate-500 text-sm mt-1">Start the FastAPI server at port 8000</p>
        </div>
      )}
    </div>
  )
}
