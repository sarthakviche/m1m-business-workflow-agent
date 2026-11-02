import { useMemo, useState } from 'react'
import { api } from '../api/client'
import DocumentRow from '../components/DocumentRow'
import { IconChat, IconFile } from '../components/icons'
import { ButtonLink, Card, EmptyState, ErrorState, Page, PageHeader, SearchInput, SkeletonRows, Tabs } from '../components/ui'
import { useAsync } from '../hooks/useAsync'

type Filter = 'all' | 'quotation' | 'invoice'

export default function Documents() {
  const { data, error, loading, reload } = useAsync(api.documents)
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')

  const docs = useMemo(() => data ?? [], [data])
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return docs.filter((d) =>
      (filter === 'all' || d.document_type === filter) &&
      (!q || d.document_number.toLowerCase().includes(q) || d.customer_name.toLowerCase().includes(q)))
  }, [docs, filter, query])

  const counts = {
    all: docs.length,
    quotation: docs.filter((d) => d.document_type === 'quotation').length,
    invoice: docs.filter((d) => d.document_type === 'invoice').length,
  }

  return (
    <Page>
      <PageHeader title="Documents" description="Every quotation and GST invoice, with its PDF."
        actions={<ButtonLink to="/chat"><IconChat size={18} /> Create with assistant</ButtonLink>} />

      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between">
          <Tabs value={filter} onChange={setFilter} options={[
            { value: 'all', label: 'All', count: counts.all },
            { value: 'quotation', label: 'Quotations', count: counts.quotation },
            { value: 'invoice', label: 'Invoices', count: counts.invoice },
          ]} />
          <SearchInput value={query} onChange={setQuery} placeholder="Search number or customer" />
        </div>

        {error ? <ErrorState message={error} onRetry={reload} />
          : loading ? <SkeletonRows />
          : docs.length === 0 ? (
            <EmptyState icon={<IconFile />} title="No documents yet"
              description="Quotations and invoices you create with the assistant (on the web or Telegram) show up here."
              action={<ButtonLink to="/chat">Open assistant</ButtonLink>} />
          ) : visible.length === 0 ? (
            <EmptyState icon={<IconFile />} title="No matches" description="Try a different number, customer name or tab." />
          ) : (
            <ul className="divide-y divide-slate-100">
              {visible.map((d) => <DocumentRow key={d.id} doc={d} />)}
            </ul>
          )}
      </Card>
    </Page>
  )
}
