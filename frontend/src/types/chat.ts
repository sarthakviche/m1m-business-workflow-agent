// Types matching the backend ChatResponse and data payloads exactly.
// Source of truth: app/api/v1/chat.py ChatResponse model.

export interface QuotationLine {
  item_name: string;
  hsn_code: string | null;
  quantity: number;
  unit: string;
  unit_price: number;
  line_total: number;
}

export interface InvoiceLine {
  item_name: string;
  hsn_code: string | null;
  quantity: number;
  unit: string;
  unit_price: number;
  gst_rate_percent: number;
  line_total: number;
  tax_amount: number;
  line_grand_total: number;
}

export interface QuotationData {
  quotation_id: string;
  quotation_number: string;
  customer_name: string;
  customer_id: string;
  subtotal: number;
  pdf_url: string | null;
  lines: QuotationLine[];
  tenant_name: string | null;
  tenant_address: string | null;
  tenant_gstin: string | null;
}

export interface InvoiceData {
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  customer_id: string;
  subtotal: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  total_tax: number;
  total_amount: number;
  pdf_url: string | null;
  lines: InvoiceLine[];
  quotation_id?: string;
  quotation_number?: string;
  tenant_name: string | null;
  tenant_address: string | null;
  tenant_gstin: string | null;
}

export interface ChatResponse {
  response_text: string;
  intent: 'quotation' | 'invoice' | 'clarify' | 'out_of_scope' | null;
  document_type: 'quotation' | 'invoice' | null;
  document_id: string | null;
  document_number: string | null;
  pdf_url: string | null;
  data: QuotationData | InvoiceData | null;
}

export interface DocumentHistoryItem {
  id: string;
  document_type: 'quotation' | 'invoice';
  document_number: string;
  customer_name: string;
  created_at: string;
  total: number;
  status: string;
  pdf_url?: string | null;
}

export interface DocumentListResponse {
  documents: DocumentHistoryItem[];
}

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  timestamp: Date;
  document_type?: 'quotation' | 'invoice' | 'documents_list';
  document_data?: QuotationData | InvoiceData;
  documents_list?: DocumentHistoryItem[];
  pdf_url?: string | null;
}

