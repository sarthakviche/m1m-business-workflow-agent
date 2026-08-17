// DocumentsList — WhatsApp-style document history list for quotations and invoices

import { useState } from "react";
import type { DocumentHistoryItem } from "../types/chat";
import DownloadPdfButton from "./DownloadPdfButton";

interface DocumentsListProps {
  documents: DocumentHistoryItem[];
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

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

type FilterType = "all" | "quotation" | "invoice";

export default function DocumentsList({ documents }: DocumentsListProps) {
  const [filter, setFilter] = useState<FilterType>("all");

  const filteredDocs = documents.filter((doc) => {
    if (filter === "all") return true;
    return doc.document_type === filter;
  });

  const quoteCount = documents.filter((d) => d.document_type === "quotation").length;
  const invCount = documents.filter((d) => d.document_type === "invoice").length;

  return (
    <div className="w-full max-w-[340px] my-1.5 space-y-2.5">
      {/* ── Filter Tabs ── */}
      <div className="flex gap-1.5 p-1 bg-gray-200/70 rounded-xl select-none">
        <button
          onClick={() => setFilter("all")}
          type="button"
          className={[
            "flex-1 text-[11px] font-medium py-1 px-2 rounded-lg transition-all text-center",
            filter === "all"
              ? "bg-white text-gray-900 shadow-sm font-semibold"
              : "text-gray-600 hover:text-gray-900",
          ].join(" ")}
        >
          All ({documents.length})
        </button>
        <button
          onClick={() => setFilter("quotation")}
          type="button"
          className={[
            "flex-1 text-[11px] font-medium py-1 px-2 rounded-lg transition-all text-center",
            filter === "quotation"
              ? "bg-white text-gray-900 shadow-sm font-semibold"
              : "text-gray-600 hover:text-gray-900",
          ].join(" ")}
        >
          Quotes ({quoteCount})
        </button>
        <button
          onClick={() => setFilter("invoice")}
          type="button"
          className={[
            "flex-1 text-[11px] font-medium py-1 px-2 rounded-lg transition-all text-center",
            filter === "invoice"
              ? "bg-white text-gray-900 shadow-sm font-semibold"
              : "text-gray-600 hover:text-gray-900",
          ].join(" ")}
        >
          Invoices ({invCount})
        </button>
      </div>

      {/* ── Empty State ── */}
      {filteredDocs.length === 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-card border border-gray-100 text-center space-y-1">
          <p className="text-sm font-semibold text-gray-800">📄 No documents found</p>
          <p className="text-xs text-gray-500 leading-relaxed">
            {documents.length === 0
              ? "Create a quotation or invoice and your documents will appear here."
              : "No documents match the selected filter."}
          </p>
        </div>
      )}

      {/* ── Document Cards List ── */}
      <div className="space-y-2">
        {filteredDocs.map((doc) => {
          const isInvoice = doc.document_type === "invoice";
          return (
            <div
              key={doc.id || doc.document_number}
              className="bg-white rounded-2xl p-3.5 shadow-card border border-gray-100/90 text-gray-800 text-xs transition-all hover:shadow-md"
            >
              {/* Header: Badge + Date */}
              <div className="flex items-center justify-between gap-2 pb-1.5">
                <span
                  className={[
                    "text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-md",
                    isInvoice
                      ? "bg-m1m-orange text-white"
                      : "bg-gray-100 text-gray-700",
                  ].join(" ")}
                >
                  {isInvoice ? "TAX INVOICE" : "QUOTATION"}
                </span>
                <span className="text-[10px] text-gray-400">
                  {formatDate(doc.created_at)}
                </span>
              </div>

              {/* Document Number & Customer Name */}
              <div className="pt-1">
                <p className="font-mono font-bold text-gray-900 text-xs">
                  {doc.document_number}
                </p>
                <p className="text-gray-600 text-xs truncate mt-0.5">
                  <span className="text-gray-400">Customer: </span>
                  <span className="font-medium text-gray-800">{doc.customer_name}</span>
                </p>
              </div>

              <div className="border-t border-gray-100 my-2" />

              {/* Total & Status */}
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">
                  {isInvoice ? "Grand Total" : "Subtotal"}
                </span>
                <span className="font-bold text-gray-900 font-mono text-sm">
                  {formatCurrency(doc.total)}
                </span>
              </div>

              {/* Download PDF CTA */}
              <DownloadPdfButton pdfUrl={doc.pdf_url} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
