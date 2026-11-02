import { documentUrl } from '../../api/client'
import type { InvoiceData, QuotationData } from '../../types/chat'
import { formatINR, formatQty } from '../../lib/format'
import { IconDownload, IconFile, IconReceipt } from '../icons'

interface Props {
  documentType: 'quotation' | 'invoice'
  data: QuotationData | InvoiceData
  pdfUrl?: string | null
}

function TotalRow({ label, value, strong = false }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-4 ${strong ? 'pt-2 text-base font-bold text-slate-900' : 'text-sm text-slate-600'}`}>
      <span>{label}</span>
      <span className="tabular-nums">{formatINR(value)}</span>
    </div>
  )
}

/** Summary of a document the assistant just created, built from the tool result (not the LLM). */
export default function DocumentResultCard({ documentType, data, pdfUrl }: Props) {
  const isInvoice = documentType === 'invoice'
  const invoice = isInvoice ? (data as InvoiceData) : null
  const number = isInvoice ? (data as InvoiceData).invoice_number : (data as QuotationData).quotation_number
  const href = pdfUrl ?? data.pdf_url

  return (
    <div className="w-full max-w-md overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
        <span className={`flex h-9 w-9 items-center justify-center rounded-xl ${isInvoice ? 'bg-emerald-50 text-emerald-600' : 'bg-orange-50 text-orange-600'}`}>
          {isInvoice ? <IconReceipt size={18} /> : <IconFile size={18} />}
        </span>
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{isInvoice ? 'Tax invoice' : 'Quotation'}</p>
          <p className="truncate font-semibold text-slate-900">{number} · {data.customer_name}</p>
        </div>
      </div>

      <ul className="divide-y divide-slate-100 px-4">
        {data.lines.map((line, i) => (
          <li key={i} className="flex justify-between gap-4 py-2.5 text-sm">
            <div className="min-w-0">
              <p className="truncate font-medium text-slate-800">{line.item_name}</p>
              <p className="text-xs text-slate-500">
                {formatQty(Number(line.quantity))} {line.unit} × {formatINR(Number(line.unit_price))}
                {line.hsn_code ? ` · HSN ${line.hsn_code}` : ''}
              </p>
            </div>
            <span className="shrink-0 font-medium tabular-nums text-slate-900">{formatINR(Number(line.line_total))}</span>
          </li>
        ))}
      </ul>

      <div className="space-y-1 border-t border-slate-100 bg-slate-50/60 px-4 py-3">
        <TotalRow label="Subtotal" value={data.subtotal} strong={!invoice} />
        {invoice && (
          <>
            {invoice.igst_amount > 0 ? (
              <TotalRow label="IGST" value={invoice.igst_amount} />
            ) : (
              <>
                <TotalRow label="CGST" value={invoice.cgst_amount} />
                <TotalRow label="SGST" value={invoice.sgst_amount} />
              </>
            )}
            <TotalRow label="Total" value={invoice.total_amount} strong />
          </>
        )}
      </div>

      {href && (
        <a href={documentUrl(href)} target="_blank" rel="noreferrer"
          className="flex items-center justify-center gap-2 border-t border-slate-100 px-4 py-3 text-sm font-semibold text-orange-600 transition-colors hover:bg-orange-50">
          <IconDownload size={18} /> Download PDF
        </a>
      )}
    </div>
  )
}
