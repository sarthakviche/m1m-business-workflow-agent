import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { IconUsers } from '../components/icons'
import { Badge, Card, EmptyState, ErrorState, Page, PageHeader, SearchInput, SkeletonRows } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { formatINR, initials } from '../lib/format'

export default function Customers() {
  const { data, error, loading, reload } = useAsync(api.customers)
  const [query, setQuery] = useState('')

  const customers = useMemo(() => data ?? [], [data])
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return customers
    return customers.filter((c) =>
      [c.name, c.gstin, c.phone, c.state].some((v) => v?.toLowerCase().includes(q)))
  }, [customers, query])

  return (
    <Page>
      <PageHeader title="Customers"
        description="Customers are added automatically the first time you quote or bill them." />

      <Card>
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 p-4">
          <p className="hidden text-sm text-slate-500 sm:block">
            {loading ? 'Loading…' : `${customers.length} customer${customers.length === 1 ? '' : 's'}`}
          </p>
          <SearchInput value={query} onChange={setQuery} placeholder="Search name, GSTIN, phone, state" />
        </div>

        {error ? <ErrorState message={error} onRetry={reload} />
          : loading ? <SkeletonRows />
          : customers.length === 0 ? (
            <EmptyState icon={<IconUsers />} title="No customers yet"
              description="Create a quotation or invoice for someone and they'll be saved here." />
          ) : visible.length === 0 ? (
            <EmptyState icon={<IconUsers />} title="No matches" description="No customer matches that search." />
          ) : (
            <ul className="divide-y divide-slate-100">
              {visible.map((c) => (
                <li key={c.id} className="flex items-center gap-3 px-5 py-4 sm:gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
                    {initials(c.name)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-slate-900">{c.name}</p>
                      {c.state && <Badge>{c.state}</Badge>}
                    </div>
                    <p className="mt-0.5 truncate text-sm text-slate-500">
                      {[c.gstin ? `GSTIN ${c.gstin}` : 'No GSTIN', c.phone].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="font-semibold tabular-nums text-slate-900">{formatINR(c.total_billed, { compact: true })}</p>
                    <p className="text-xs text-slate-500">
                      {c.invoice_count} inv · {c.quotation_count} quote{c.quotation_count === 1 ? '' : 's'}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
      </Card>
    </Page>
  )
}
