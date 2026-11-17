import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { IconBox, IconUpload } from '../components/icons'
import { Badge, ButtonLink, Card, EmptyState, ErrorState, Page, PageHeader, SearchInput, SkeletonRows, Tabs } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { formatINR, formatQty } from '../lib/format'

type Filter = 'all' | 'low'

export default function Inventory() {
  const { data, error, loading, reload } = useAsync(api.items)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('all')

  const items = useMemo(() => data ?? [], [data])
  const lowCount = items.filter((i) => i.low_stock).length
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items.filter((i) =>
      (filter === 'all' || i.low_stock) &&
      (!q || i.name.toLowerCase().includes(q) || i.hsn_code?.toLowerCase().includes(q)))
  }, [items, query, filter])

  return (
    <Page>
      <PageHeader title="Stock" description="Your catalog with selling price, GST rate and units in stock. Invoices reduce stock automatically."
        actions={<ButtonLink to="/inventory/import"><IconUpload size={18} /> Import price list</ButtonLink>} />

      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between">
          <Tabs value={filter} onChange={setFilter} options={[
            { value: 'all', label: 'All items', count: items.length },
            { value: 'low', label: 'Low stock', count: lowCount },
          ]} />
          <SearchInput value={query} onChange={setQuery} placeholder="Search item or HSN" />
        </div>

        {error ? <ErrorState message={error} onRetry={reload} />
          : loading ? <SkeletonRows />
          : items.length === 0 ? (
            <EmptyState icon={<IconBox />} title="Your catalog is empty"
              description="Snap a photo of your rate list and Munim adds every item, price and GST rate for you to check."
              action={<ButtonLink to="/inventory/import"><IconUpload size={18} /> Import price list</ButtonLink>} />
          ) : visible.length === 0 ? (
            <EmptyState icon={<IconBox />} title={filter === 'low' ? 'Nothing is running low' : 'No matches'}
              description={filter === 'low' ? 'Every item has more than 10 units in stock.' : 'No item matches that search.'} />
          ) : (
            <>
              {/* Table on wider screens */}
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <th scope="col" className="px-5 py-3">Item</th>
                      <th scope="col" className="px-5 py-3">HSN</th>
                      <th scope="col" className="px-5 py-3 text-right">Price</th>
                      <th scope="col" className="px-5 py-3 text-right">GST</th>
                      <th scope="col" className="px-5 py-3 text-right">In stock</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {visible.map((i) => (
                      <tr key={i.id} className="hover:bg-slate-50/60">
                        <td className="px-5 py-3.5 font-medium text-slate-900">{i.name}</td>
                        <td className="px-5 py-3.5 tabular-nums text-slate-500">{i.hsn_code ?? '—'}</td>
                        <td className="px-5 py-3.5 text-right tabular-nums text-slate-900">
                          {formatINR(i.unit_price)}<span className="text-slate-400"> / {i.unit}</span>
                        </td>
                        <td className="px-5 py-3.5 text-right tabular-nums text-slate-600">{formatQty(i.gst_rate_percent)}%</td>
                        <td className="px-5 py-3.5 text-right">
                          {i.low_stock
                            ? <Badge tone="red">{formatQty(i.quantity_available)} {i.unit}</Badge>
                            : <span className="tabular-nums text-slate-900">{formatQty(i.quantity_available)} {i.unit}</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Cards on phones */}
              <ul className="divide-y divide-slate-100 md:hidden">
                {visible.map((i) => (
                  <li key={i.id} className="flex items-center justify-between gap-3 px-4 py-3.5">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-900">{i.name}</p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {formatINR(i.unit_price)} / {i.unit} · GST {formatQty(i.gst_rate_percent)}%{i.hsn_code ? ` · HSN ${i.hsn_code}` : ''}
                      </p>
                    </div>
                    <Badge tone={i.low_stock ? 'red' : 'neutral'}>{formatQty(i.quantity_available)} {i.unit}</Badge>
                  </li>
                ))}
              </ul>
            </>
          )}
      </Card>
    </Page>
  )
}
