// DocumentsList — filterable list of quotation/invoice history cards

import { useState } from 'react';
import type { DocumentHistoryItem } from '../types/chat';
import DownloadPdfButton from './DownloadPdfButton';

interface DocumentsListProps {
  documents: DocumentHistoryItem[];
}

function fmt(amount?: number | null): string {
  if (amount === undefined || amount === null || isNaN(amount)) return '₹0.00';
  return '₹' + amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(dateStr?: string | null): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  } catch {
    return '';
  }
}

type FilterType = 'all' | 'quotation' | 'invoice';

export default function DocumentsList({ documents }: DocumentsListProps) {
  const [filter, setFilter] = useState<FilterType>('all');

  const filtered = documents.filter((d) => filter === 'all' || d.document_type === filter);
  const quoteCount = documents.filter((d) => d.document_type === 'quotation').length;
  const invCount   = documents.filter((d) => d.document_type === 'invoice').length;

  return (
    <div className="w-full max-w-[310px] my-1 space-y-2">
      {/* Filter tabs */}
      <div className="flex gap-1 p-1 bg-gray-200/70 rounded-xl select-none">
        {([['all', `All (${documents.length})`], ['quotation', `Quotes (${quoteCount})`], ['invoice', `Invoices (${invCount})`]] as [FilterType, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            type="button"
            className={[
              'flex-1 text-[11px] font-medium py-1 px-1.5 rounded-lg transition-all text-center',
              filter === key
                ? 'bg-white text-gray-900 shadow-sm font-semibold'
                : 'text-gray-600 hover:text-gray-900',
            ].join(' ')}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Empty state */}
      {filtered.length === 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-card border border-gray-100 text-center space-y-1">
          <p className="text-sm font-semibold text-gray-800">📄 No documents found</p>
          <p className="text-xs text-gray-500 leading-relaxed">
            {documents.length === 0
              ? 'Create a quotation or invoice and your documents will appear here.'
              : 'No documents match the selected filter.'}
          </p>
        </div>
      )}

      {/* Document cards */}
      <div className="space-y-2">
        {filtered.map((doc) => {
          const isInvoice = doc.document_type === 'invoice';
          return (
            <div
              key={doc.id || doc.document_number}
              className="bg-white rounded-2xl p-3.5 shadow-card border border-gray-100 text-gray-800 text-xs"
            >
              {/* Badge + date */}
              <div className="flex items-center justify-between gap-2 pb-1.5">
                <span className={[
                  'text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-md',
                  isInvoice ? 'bg-[#E8792A] text-white' : 'bg-gray-100 text-gray-700',
                ].join(' ')}>
                  {isInvoice ? 'TAX INVOICE' : 'QUOTATION'}
                </span>
                <span className="text-[10px] text-gray-400">{fmtDate(doc.created_at)}</span>
              </div>

              {/* Number + customer */}
              <div className="pt-1">
                <p className="font-mono font-bold text-gray-900 text-xs">{doc.document_number}</p>
                <p className="text-gray-600 text-xs truncate mt-0.5">
                  <span className="text-gray-400">Customer: </span>
                  <span className="font-medium text-gray-800">{doc.customer_name}</span>
                </p>
              </div>

              <div className="border-t border-gray-100 my-2" />

              {/* Total */}
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">{isInvoice ? 'Grand Total' : 'Subtotal'}</span>
                <span className="font-bold text-gray-900 font-mono text-sm">{fmt(doc.total)}</span>
              </div>

              <DownloadPdfButton pdfUrl={doc.pdf_url} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
