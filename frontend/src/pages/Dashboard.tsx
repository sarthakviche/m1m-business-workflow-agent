import { Link } from 'react-router-dom'
import { api } from '../api/client'
import DocumentRow from '../components/DocumentRow'
import { IconAlert, IconBox, IconChat, IconFile, IconReceipt, IconUsers } from '../components/icons'
import { ButtonLink, Card, CardHeader, EmptyState, ErrorState, Page, SkeletonRows, StatCard } from '../components/ui'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { formatINR, formatQty } from '../lib/format'

function greeting(): string {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
}

const QUICK_ACTIONS = [
  { label: 'New quotation', prompt: 'Create a quotation for ', Icon: IconFile },
  { label: 'New GST invoice', prompt: 'Create an invoice for ', Icon: IconReceipt },
  { label: 'Check stock', prompt: 'What is the price and stock of ', Icon: IconBox },
]

export default function Dashboard() {
  const { business } = useApp()
  const { data, error, loading, reload } = useAsync(api.dashboard)

  return (
    <Page>
      <header className="mb-6">
        <p className="text-sm font-medium text-slate-500">{greeting()}</p>
        <h1 className="mt-0.5 font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {business?.business_name ?? 'Your business'}
        </h1>
      </header>

      {/* Quick actions open the assistant with a ready-to-finish prompt */}
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        {QUICK_ACTIONS.map(({ label, prompt, Icon }) => (
          <Link key={label} to="/chat" state={{ draft: prompt }}
            className="group flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm transition-colors hover:border-orange-200 hover:bg-orange-50/40">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-500 text-white"><Icon size={20} /></span>
            <span className="font-semibold text-slate-900">{label}</span>
          </Link>
        ))}
      </div>

      {error ? (
        <Card><ErrorState message={error} onRetry={reload} /></Card>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {loading || !data ? (
              Array.from({ length: 4 }, (_, i) => <div key={i} className="h-[118px] animate-pulse rounded-2xl bg-white shadow-sm" />)
            ) : (
              <>
                <StatCard label="Total sales" value={formatINR(data.total_sales, { compact: true })} hint="All invoices" tone="orange" icon={<IconReceipt size={18} />} />
                <StatCard label="To collect" value={formatINR(data.outstanding_amount, { compact: true })}
                  hint={`${data.unpaid_invoices} unpaid invoice${data.unpaid_invoices === 1 ? '' : 's'}`}
                  tone={data.outstanding_amount > 0 ? 'red' : 'green'} icon={<IconAlert size={18} />} />
                <StatCard label="Open quotations" value={String(data.open_quotations)}
                  hint={`${formatINR(data.open_quotations_value, { compact: true })} quoted`} icon={<IconFile size={18} />} />
                <StatCard label="Customers" value={String(data.total_customers)} hint={`${data.total_items} catalog items`} icon={<IconUsers size={18} />} />
              </>
            )}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title="Recent documents" action={<Link to="/documents" className="text-sm font-semibold text-orange-600 hover:text-orange-700">View all</Link>} />
              {loading || !data ? <SkeletonRows rows={4} /> : data.recent_documents.length === 0 ? (
                <EmptyState icon={<IconFile />} title="No documents yet"
                  description="Ask the assistant to create your first quotation. It will appear here with its PDF."
                  action={<ButtonLink to="/chat"><IconChat size={18} /> Open assistant</ButtonLink>} />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {data.recent_documents.map((d) => <DocumentRow key={`${d.document_type}-${d.document_number}`} doc={d} />)}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title="Low stock" action={<Link to="/inventory" className="text-sm font-semibold text-orange-600 hover:text-orange-700">Stock</Link>} />
              {loading || !data ? <SkeletonRows rows={3} /> : data.low_stock_items.length === 0 ? (
                <div className="px-5 py-8 text-center">
                  <p className="text-sm font-medium text-slate-900">All items are well stocked</p>
                  <p className="mt-1 text-xs text-slate-500">Items with {formatQty(data.low_stock_threshold)} or fewer units show up here.</p>
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {data.low_stock_items.map((item) => (
                    <li key={item.id} className="flex items-center justify-between gap-3 px-5 py-3">
                      <span className="truncate text-sm font-medium text-slate-800">{item.name}</span>
                      <span className="shrink-0 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold tabular-nums text-red-700">
                        {formatQty(item.quantity_available)} {item.unit}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      )}
    </Page>
  )
}
