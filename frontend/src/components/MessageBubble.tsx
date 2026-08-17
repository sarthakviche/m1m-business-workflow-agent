// MessageBubble — User (green, right-aligned) / Assistant (white, left-aligned) + Document Cards / List

import type { ChatMessage } from "../types/chat";
import DocumentCard from "./DocumentCard";
import DocumentsList from "./DocumentsList";

interface MessageBubbleProps {
  message: ChatMessage;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
}

// Simple markdown-bold renderer: **text** -> <strong>text</strong>
function renderText(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-1">
        <div className="relative max-w-[78%]">
          <div className="bubble-user relative bg-m1m-green-bubble rounded-bubble rounded-br-sm px-3.5 py-2 shadow-bubble">
            <p className="text-gray-800 text-sm leading-relaxed whitespace-pre-wrap break-words">
              {message.text}
            </p>
            <div className="flex items-center justify-end gap-1 mt-1">
              <span className="text-gray-500 text-[10px]">{formatTime(message.timestamp)}</span>
              {/* Double-tick read indicator */}
              <svg width="16" height="11" viewBox="0 0 16 11" className="text-blue-500 fill-current">
                <path d="M11.071.653a.75.75 0 00-1.06 1.06L14.132 5.8a.75.75 0 01.061.972l-.061.07-4.121 4.087a.75.75 0 001.05 1.071l4.123-4.09a2.25 2.25 0 000-3.183L11.07.653z"/>
                <path d="M6.517.653a.75.75 0 00-1.06 1.06L9.578 5.8a.75.75 0 01.061.972l-.061.07-4.121 4.087a.75.75 0 001.05 1.071L10.63 7.84 6.517.653z" opacity="0.6"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start px-4 py-1">
      {/* Assistant Text Bubble */}
      <div className="relative max-w-[85%] sm:max-w-[78%]">
        <div className="bubble-assistant relative bg-white rounded-bubble rounded-bl-sm px-3.5 py-2 shadow-bubble">
          <p className="text-gray-800 text-sm leading-relaxed whitespace-pre-wrap break-words">
            {renderText(message.text)}
          </p>
          <div className="flex justify-end mt-1">
            <span className="text-gray-400 text-[10px]">{formatTime(message.timestamp)}</span>
          </div>
        </div>
      </div>

      {/* Single Document Card (Quotation / Invoice) */}
      {(message.document_type === "quotation" || message.document_type === "invoice") &&
        message.document_data && (
          <div className="mt-1.5 w-full flex justify-start">
            <DocumentCard
              documentType={message.document_type}
              data={message.document_data}
              pdfUrl={message.pdf_url}
            />
          </div>
        )}

      {/* Document History List */}
      {message.document_type === "documents_list" && message.documents_list && (
        <div className="mt-1.5 w-full flex justify-start">
          <DocumentsList documents={message.documents_list} />
        </div>
      )}
    </div>
  );
}


