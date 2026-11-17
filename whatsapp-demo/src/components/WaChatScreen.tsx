// WaChatScreen — the complete WhatsApp chat layout
// Shows a realistic phone frame on desktop, full-screen on mobile

import { useState } from 'react';
import WaHeader from './WaHeader';
import WaMessages from './WaMessages';
import WaQuickChips from './WaQuickChips';
import WaComposer from './WaComposer';
import { useChat } from '../hooks/useChat';


export default function WaChatScreen() {
  const { messages, isLoading, sendMessage } = useChat();
  const [injectedText, setInjectedText] = useState<string | undefined>(undefined);

  function handleChipClick(message: string) {
    setInjectedText(message);
  }

  return (
    /*
     * Outer: dark background to simulate a table / phone-on-desk
     * Centre: phone frame on desktop, full-screen on mobile
     */
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      {/*
       * Phone frame:
       * Mobile  → full viewport
       * Desktop → 390×844 centered card with rounded corners + shadow
       */}
      <div
        className={[
          'flex flex-col overflow-hidden',
          'w-full h-screen',
          'sm:w-[390px] sm:h-[844px] sm:rounded-[40px] sm:shadow-2xl sm:ring-4 sm:ring-black/30',
        ].join(' ')}
      >

        {/* Chat header */}
        <WaHeader />

        {/* Messages */}
        <WaMessages messages={messages} isLoading={isLoading} />

        {/* Quick chips */}
        <WaQuickChips onChipClick={handleChipClick} />

        {/* Composer */}
        <WaComposer
          onSend={sendMessage}
          isLoading={isLoading}
          injectedText={injectedText}
          onInjectedTextConsumed={() => setInjectedText(undefined)}
        />

        {/* Home indicator bar (iPhone-like) */}
        <div className="flex-shrink-0 bg-[#f0f0f0] flex items-center justify-center py-1.5 sm:py-2">
          <div className="w-28 h-1 rounded-full bg-gray-400/50" />
        </div>
      </div>
    </div>
  );
}
