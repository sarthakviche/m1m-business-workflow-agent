// WaMessageBubble — renders one chat message in WhatsApp style
// Outgoing (user): green, right-aligned, bubble tail right
// Incoming (assistant): white, left-aligned, bubble tail left
// Supports inline QuotationCard, InvoiceCard, and DocumentsList

import type { ChatMessage, QuotationData, InvoiceData } from '../types/chat';
import QuotationCard from './QuotationCard';
import InvoiceCard from './InvoiceCard';
import DocumentsList from './DocumentsList';

interface WaMessageBubbleProps {
  message: ChatMessage;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

// Renders **bold** markdown
function renderText(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

// Blue WhatsApp double-tick (read)
function DoubleTick() {
  return (
    <svg width="16" height="11" viewBox="0 0 18 11" className="inline-block ml-0.5 flex-shrink-0" aria-hidden>
      <path fill="#53bdeb" d="M17.394.246a.75.75 0 0 0-1.06 0l-8.42 8.42-3.71-3.71a.75.75 0 0 0-1.06 1.06l4.24 4.24a.75.75 0 0 0 1.06 0l8.95-8.95a.75.75 0 0 0 0-1.06z" />
      <path fill="#53bdeb" d="M12.894.246a.75.75 0 0 0-1.06 0l-6.42 6.42-.71-.71a.75.75 0 0 0-1.06 1.06l1.24 1.24a.75.75 0 0 0 1.06 0l6.95-6.95a.75.75 0 0 0 0-1.06z" opacity="0.6" />
    </svg>
  );
}

export default function WaMessageBubble({ message }: WaMessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end px-2 py-0.5">
        <div className="relative max-w-[78%]">
          <div className="bubble-out relative bg-[#d9fdd3] rounded-[7.5px] rounded-tr-none px-3 py-2 shadow-bubble">
            <p className="text-gray-800 text-sm leading-relaxed whitespace-pre-wrap break-words pr-10">
              {message.text}
            </p>
            {/* Time + ticks — bottom right, overlapping text space */}
            <div className="flex items-center justify-end gap-0.5 mt-0.5">
              <span className="text-gray-500 text-[11px]">{formatTime(message.timestamp)}</span>
              <DoubleTick />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Assistant bubble
  return (
    <div className="flex flex-col items-start px-2 py-0.5">
      <div className="relative max-w-[85%]">
        <div className="bubble-in relative bg-white rounded-[7.5px] rounded-tl-none px-3 py-2 shadow-bubble">
          <p className="text-gray-800 text-sm leading-relaxed whitespace-pre-wrap break-words">
            {renderText(message.text)}
          </p>
          <div className="flex justify-end mt-0.5">
            <span className="text-gray-400 text-[11px]">{formatTime(message.timestamp)}</span>
          </div>
        </div>
      </div>

      {/* Quotation card */}
      {message.document_type === 'quotation' && message.document_data && (
        <div className="mt-1 w-full flex justify-start pl-0">
          <QuotationCard data={message.document_data as QuotationData} pdfUrl={message.pdf_url} />
        </div>
      )}

      {/* Invoice card */}
      {message.document_type === 'invoice' && message.document_data && (
        <div className="mt-1 w-full flex justify-start pl-0">
          <InvoiceCard data={message.document_data as InvoiceData} pdfUrl={message.pdf_url} />
        </div>
      )}

      {/* Documents list */}
      {message.document_type === 'documents_list' && message.documents_list && (
        <div className="mt-1 w-full flex justify-start pl-0">
          <DocumentsList documents={message.documents_list} />
        </div>
      )}
    </div>
  );
}
