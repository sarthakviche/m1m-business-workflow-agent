// WaComposer — WhatsApp-style message input bar
// Emoji | text field | attachment | send-or-mic

import { useState, useRef, useEffect } from 'react';

interface WaComposerProps {
  onSend: (text: string) => void;
  isLoading: boolean;
  injectedText?: string;
  onInjectedTextConsumed?: () => void;
}

export default function WaComposer({
  onSend,
  isLoading,
  injectedText,
  onInjectedTextConsumed,
}: WaComposerProps) {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  // Initialize Speech Recognition
  useEffect(() => {
    // @ts-ignore - Vendor prefixes
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-IN';

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        
        // When final, append it. For interim, we could show it, but for simplicity
        // we'll just set the text when final.
        if (finalTranscript) {
           setText(prev => (prev ? prev + ' ' + finalTranscript : finalTranscript).trim());
        }
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error', event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  // Inject chip text into the composer
  useEffect(() => {
    if (injectedText !== undefined && injectedText !== '') {
      setText(injectedText);
      onInjectedTextConsumed?.();
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [injectedText, onInjectedTextConsumed]);

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setText('');
    // Reset height
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }

  function handleMicClick() {
    if (!recognitionRef.current) {
      alert("Voice input is not supported in your browser. Please try Chrome, Edge, or Safari.");
      return;
    }
    
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Could not start recording:", err);
      }
    }
  }

  const canSend = text.trim().length > 0 && !isLoading;

  return (
    <div className="flex-shrink-0 bg-[#f0f0f0] px-2 py-2">
      <div className="flex items-end gap-2">
        {/* Input pill */}
        <div className={`flex-1 flex items-end gap-1.5 bg-white rounded-[26px] px-3 py-2 shadow-sm min-h-[46px] transition-all ${isRecording ? 'ring-2 ring-red-400' : ''}`}>
          {/* Emoji */}
          <button
            aria-label="Emoji"
            className="text-gray-400 hover:text-gray-600 flex-shrink-0 pb-0.5 transition-colors"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M8 14s1.5 2 4 2 4-2 4-2" />
              <line x1="9" y1="9" x2="9.01" y2="9" />
              <line x1="15" y1="9" x2="15.01" y2="9" />
            </svg>
          </button>

          {/* Text area */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={isRecording ? "Listening..." : "Message"}
            disabled={isLoading}
            className="flex-1 resize-none outline-none text-sm text-gray-800 placeholder-gray-400 bg-transparent leading-relaxed max-h-[120px] py-0.5 disabled:opacity-60"
          />

          {/* Attachment */}
          <button
            aria-label="Attach file"
            className="text-gray-400 hover:text-gray-600 flex-shrink-0 pb-0.5 transition-colors"
          >
            <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
            </svg>
          </button>
        </div>

        {/* Send / Mic */}
        <button
          aria-label={canSend ? 'Send message' : (isRecording ? 'Stop recording' : 'Voice input')}
          onClick={canSend ? handleSubmit : handleMicClick}
          className={[
            'w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 shadow-md transition-all active:scale-95',
            isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : canSend
                ? 'bg-[#25D366] hover:bg-[#1ebe5d] cursor-pointer'
                : isRecording
                  ? 'bg-red-500 hover:bg-red-600 animate-pulse cursor-pointer'
                  : 'bg-[#25D366] hover:bg-[#1ebe5d] cursor-pointer',
          ].join(' ')}
        >
          {canSend ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          ) : isRecording ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="6" y="6" width="12" height="12" rx="2" ry="2" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
              <path d="M19 10v2a7 7 0 01-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
