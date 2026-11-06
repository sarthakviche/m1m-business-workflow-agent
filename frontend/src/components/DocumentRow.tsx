import { formatDate, formatINR } from '../lib/format'
import { IconDownload, IconFile, IconReceipt } from './icons'
import PdfLink from './PdfLink'
import { StatusBadge } from './ui'

export interface DocumentRowData {
  document_type: 'quotation' | 'invoice'
  document_number: string
  customer_name: string
  total: number
  status: string
  created_at: string | null
  pdf_url?: string | null
}

export default function DocumentRow({ doc }: { doc: DocumentRowData }) {
  const isInvoice = doc.document_type === 'invoice'
  return (
    <li className="flex items-center gap-3 px-5 py-3.5 sm:gap-4">
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${isInvoice ? 'bg-emerald-50 text-emerald-600' : 'bg-orange-50 text-orange-600'}`}>
        {isInvoice ? <IconReceipt size={20} /> : <IconFile size={20} />}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="font-semibold text-slate-900">{doc.document_number}</p>
          <StatusBadge status={doc.status} />
        </div>
        <p className="mt-0.5 truncate text-sm text-slate-500">
          {doc.customer_name} · {isInvoice ? 'Tax invoice' : 'Quotation'} · {formatDate(doc.created_at)}
        </p>
      </div>
      <p className="hidden shrink-0 text-right font-semibold tabular-nums text-slate-900 sm:block">{formatINR(doc.total)}</p>
      {doc.pdf_url ? (
        <PdfLink pdfUrl={doc.pdf_url} label={`Open PDF for ${doc.document_number}`}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition-colors hover:border-orange-200 hover:bg-orange-50 hover:text-orange-600">
          <IconDownload size={18} />
        </PdfLink>
      ) : (
        <span className="h-9 w-9 shrink-0" />
      )}
    </li>
  )
}
