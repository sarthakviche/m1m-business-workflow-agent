// InvoiceCard — WhatsApp-style GST tax invoice preview card

import type { InvoiceData } from "../types/chat";
import DownloadPdfButton from "./DownloadPdfButton";

interface InvoiceCardProps {
  data: InvoiceData;
  pdfUrl?: string | null;
}

function formatCurrency(amount?: number | null): string {
  if (amount === undefined || amount === null || isNaN(amount)) return "₹0.00";
  return (
    "₹" +
    amount.toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

export default function InvoiceCard({ data, pdfUrl }: InvoiceCardProps) {
  if (!data) return null;

  const effectivePdfUrl = pdfUrl || data.pdf_url;
  const lines = data.lines || [];

  const hasCgst = (data.cgst_amount ?? 0) > 0;
  const hasSgst = (data.sgst_amount ?? 0) > 0;
  const hasIgst = (data.igst_amount ?? 0) > 0;

  return (
    <div className="bg-white rounded-2xl p-4 shadow-card border border-gray-100/90 text-gray-800 text-xs w-full max-w-[340px] my-1.5 transition-all">
      {/* ── Top Section: Business Header & Tax Invoice Badge ── */}
      <div className="flex items-start justify-between gap-2 pb-2.5">
        <div className="min-w-0">
          <h4 className="font-bold text-gray-900 text-sm leading-tight truncate">
            {data.tenant_name || "Tax Invoice"}
          </h4>
          {data.tenant_address && (
            <p className="text-[11px] text-gray-500 leading-snug mt-0.5 whitespace-pre-line">
              {data.tenant_address}
            </p>
          )}
          {data.tenant_gstin && (
            <p className="text-[10px] text-gray-400 font-mono mt-0.5">
              GSTIN: {data.tenant_gstin}
            </p>
          )}
        </div>
        <span className="flex-shrink-0 bg-m1m-orange text-white text-[10px] font-semibold tracking-wider uppercase px-2.5 py-1 rounded-md shadow-sm">
          TAX INVOICE
        </span>
      </div>

      <div className="border-t border-gray-100 my-2" />

      {/* ── Customer & Invoice Meta ── */}
      <div className="flex items-center justify-between gap-2 py-1">
        <div className="truncate">
          <span className="text-gray-500">Billed to: </span>
          <span className="font-semibold text-gray-900">{data.customer_name}</span>
        </div>
        <span className="text-[11px] font-mono text-gray-500 font-medium flex-shrink-0">
          {data.invoice_number}
        </span>
      </div>

      <div className="border-t border-gray-100 my-2" />

      {/* ── Items Table ── */}
      <div className="w-full overflow-hidden">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-gray-400 font-semibold border-b border-gray-50 text-[10px]">
              <th className="text-left pb-1.5 font-semibold">ITEM</th>
              <th className="text-center pb-1.5 font-semibold px-1">HSN</th>
              <th className="text-center pb-1.5 font-semibold px-1">QTY</th>
              <th className="text-right pb-1.5 font-semibold">AMOUNT</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50/80">
            {lines.map((line, idx) => (
              <tr key={idx} className="text-gray-700">
                <td className="py-1.5 pr-1 font-medium text-gray-800 break-words max-w-[120px]">
                  {line.item_name}
                </td>
                <td className="py-1.5 px-1 text-center text-gray-500 font-mono text-[10px]">
                  {line.hsn_code || "-"}
                </td>
                <td className="py-1.5 px-1 text-center text-gray-600">
                  {line.quantity}
                </td>
                <td className="py-1.5 pl-1 text-right font-semibold text-gray-900 font-mono">
                  {formatCurrency(line.line_total)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border-t border-gray-100 my-2" />

      {/* ── Tax Breakdown ── */}
      <div className="space-y-1 py-1">
        <div className="flex justify-between items-center text-[11px]">
          <span className="text-gray-500">Taxable value</span>
          <span className="font-mono text-gray-800 font-medium">
            {formatCurrency(data.subtotal)}
          </span>
        </div>

        {hasCgst && (
          <div className="flex justify-between items-center text-[11px]">
            <span className="text-gray-500">CGST</span>
            <span className="font-mono text-gray-700">
              {formatCurrency(data.cgst_amount)}
            </span>
          </div>
        )}

        {hasSgst && (
          <div className="flex justify-between items-center text-[11px]">
            <span className="text-gray-500">SGST</span>
            <span className="font-mono text-gray-700">
              {formatCurrency(data.sgst_amount)}
            </span>
          </div>
        )}

        {hasIgst && (
          <div className="flex justify-between items-center text-[11px]">
            <span className="text-gray-500">IGST</span>
            <span className="font-mono text-gray-700">
              {formatCurrency(data.igst_amount)}
            </span>
          </div>
        )}
      </div>

      <div className="border-t border-gray-100 my-2" />

      {/* ── Total Payable ── */}
      <div className="flex justify-between items-center py-1 text-xs">
        <span className="font-bold text-gray-900">Total payable</span>
        <span className="font-bold text-gray-900 font-mono text-sm">
          {formatCurrency(data.total_amount)}
        </span>
      </div>

      {/* ── PDF Action Button ── */}
      <DownloadPdfButton pdfUrl={effectivePdfUrl} />
    </div>
  );
}
