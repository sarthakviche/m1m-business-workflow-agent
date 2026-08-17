// DocumentCard — dispatcher component for Quotation and Invoice cards

import type { QuotationData, InvoiceData } from "../types/chat";
import QuotationCard from "./QuotationCard";
import InvoiceCard from "./InvoiceCard";

interface DocumentCardProps {
  documentType: "quotation" | "invoice";
  data: QuotationData | InvoiceData;
  pdfUrl?: string | null;
}

export default function DocumentCard({
  documentType,
  data,
  pdfUrl,
}: DocumentCardProps) {
  if (!data) return null;

  if (documentType === "quotation") {
    return <QuotationCard data={data as QuotationData} pdfUrl={pdfUrl} />;
  }

  if (documentType === "invoice") {
    return <InvoiceCard data={data as InvoiceData} pdfUrl={pdfUrl} />;
  }

  return null;
}
