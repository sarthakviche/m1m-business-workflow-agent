// WaMessages — scrollable conversation area

import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../types/chat';
import WaMessageBubble from './WaMessageBubble';
import WaTypingIndicator from './WaTypingIndicator';
import WaDateSeparator from './WaDateSeparator';

interface WaMessagesProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export default function WaMessages({ messages, isLoading }: WaMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="wa-bg wa-scroll flex-1 overflow-y-auto py-2">
      <WaDateSeparator label="Today" />

      {messages.map((msg) => (
        <WaMessageBubble key={msg.id} message={msg} />
      ))}

      {isLoading && <WaTypingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
}
