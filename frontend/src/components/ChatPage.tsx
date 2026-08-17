// ChatPage — root layout: phone-container on desktop, full-screen on mobile

import { useState } from "react";
import ChatHeader from "./ChatHeader";
import ChatMessages from "./ChatMessages";
import QuickActionChips from "./QuickActionChips";
import MessageComposer from "./MessageComposer";
import { useChat } from "../hooks/useChat";

export default function ChatPage() {
  const { messages, isLoading, sendMessage } = useChat();
  const [injectedText, setInjectedText] = useState<string | undefined>(undefined);

  function handleChipClick(message: string) {
    setInjectedText(message);
  }

  return (
    /*
     * Outer wrapper: black background on desktop so the phone-card stands out.
     * On mobile the card fills the full viewport.
     */
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      {/*
       * Phone-card container:
       * - On mobile: fills viewport edge-to-edge (w-full, h-screen)
       * - On desktop: fixed 390px wide phone frame centered on dark background
       */}
      <div
        className={[
          "flex flex-col overflow-hidden bg-white",
          // Mobile: full screen
          "w-full h-screen",
          // Desktop: phone card
          "sm:w-[390px] sm:h-[844px] sm:rounded-3xl sm:shadow-2xl",
        ].join(" ")}
      >
        {/* Fixed header */}
        <ChatHeader />

        {/* Scrollable conversation */}
        <ChatMessages messages={messages} isLoading={isLoading} />

        {/* Quick-action chips */}
        <QuickActionChips onChipClick={handleChipClick} />

        {/* Message composer */}
        <MessageComposer
          onSend={sendMessage}
          isLoading={isLoading}
          injectedText={injectedText}
          onInjectedTextConsumed={() => setInjectedText(undefined)}
        />
      </div>
    </div>
  );
}
