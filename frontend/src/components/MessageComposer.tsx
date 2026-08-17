// MessageComposer — bottom input bar with emoji, text field, attach, and mic

import { useState, useRef, useEffect } from "react";

interface MessageComposerProps {
  onSend: (text: string) => void;
  isLoading: boolean;
  injectedText?: string;
  onInjectedTextConsumed?: () => void;
}

export default function MessageComposer({
  onSend,
  isLoading,
  injectedText,
  onInjectedTextConsumed,
}: MessageComposerProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // When a chip injects text, populate the composer and focus
  useEffect(() => {
    if (injectedText !== undefined && injectedText !== "") {
      setText(injectedText);
      onInjectedTextConsumed?.();
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [injectedText, onInjectedTextConsumed]);

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setText("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  // Auto-grow textarea (max 5 rows)
  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  const canSend = text.trim().length > 0 && !isLoading;

  return (
    <div className="flex-shrink-0 bg-m1m-chat px-3 py-2.5 shadow-composer">
      <div className="flex items-end gap-2.5">
        {/* Composer box */}
        <div className="flex-1 flex items-end gap-2 bg-white rounded-[26px] px-3.5 py-2 shadow-sm min-h-[46px]">
          {/* Emoji icon */}
          <button
            aria-label="Emoji"
            className="text-gray-400 hover:text-gray-600 flex-shrink-0 pb-0.5 transition-colors"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              <line x1="9" y1="9" x2="9.01" y2="9"/>
              <line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
          </button>

          {/* Text input */}
          <textarea
            ref={textareaRef}
            id="message-composer-input"
            rows={1}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Message"
            disabled={isLoading}
            className="flex-1 resize-none outline-none text-sm text-gray-800 placeholder-gray-400 bg-transparent leading-relaxed max-h-[120px] py-0.5 disabled:opacity-60"
          />

          {/* Attachment icon */}
          <button
            aria-label="Attach file"
            className="text-gray-400 hover:text-gray-600 flex-shrink-0 pb-0.5 transition-colors"
          >
            <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
        </div>

        {/* Send / Mic button — green circle */}
        <button
          id="send-message-button"
          aria-label={canSend ? "Send message" : "Voice input"}
          onClick={canSend ? handleSubmit : undefined}
          className={[
            "w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 shadow-md transition-all active:scale-95",
            isLoading
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-m1m-green hover:bg-green-500 cursor-pointer",
          ].join(" ")}
        >
          {canSend ? (
            /* Send arrow */
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          ) : (
            /* Mic icon */
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/>
              <path d="M19 10v2a7 7 0 01-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
