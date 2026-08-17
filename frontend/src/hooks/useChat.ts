// useChat — conversation state manager
// Stage 3A.1: Connected to backend POST /api/v1/chat + local generic capability greeting for "Hi"

import { useState, useCallback } from "react";
import type { ChatMessage } from "../types/chat";
import { sendChatMessage, fetchDocuments } from "../api/chatApi";

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  text: "Namaste! 🙏\nSay \"Hi\" anytime to see everything I can do for your business.",
  timestamp: new Date(),
};

const HI_CAPABILITY_RESPONSE = `Namaste! 🙏
I'm M1M, your business munim. Reply with a number or just type in your own words:

1️⃣ Create a quotation
2️⃣ Make a GST invoice
3️⃣ Who owes me money?
4️⃣ Check stock
5️⃣ My documents (bills & quotations)
6️⃣ Tally books status
7️⃣ Today's business summary`;

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();

    // Append user message immediately
    const userMsg: ChatMessage = {
      id: makeId(),
      role: "user",
      text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Flow 1: Generic capability greeting for "Hi" handled on frontend
    if (trimmed.toLowerCase() === "hi") {
      await new Promise((resolve) => setTimeout(resolve, 300));
      const assistantMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        text: HI_CAPABILITY_RESPONSE,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsLoading(false);
      return;
    }

    // Flow 2: Stage 5 — Documents / History retrieval
    const normalized = trimmed.toLowerCase();
    if (
      normalized === "5 · documents" ||
      normalized === "5. documents" ||
      normalized === "5" ||
      normalized === "documents" ||
      normalized === "my documents" ||
      normalized === "show my documents"
    ) {
      try {
        const docs = await fetchDocuments();
        const assistantMsg: ChatMessage = {
          id: makeId(),
          role: "assistant",
          text: "Here are your recent documents 📄",
          timestamp: new Date(),
          document_type: "documents_list",
          documents_list: docs,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch {
        const errorMsg: ChatMessage = {
          id: makeId(),
          role: "assistant",
          text: "I couldn't load your documents right now. Please try again in a moment.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Flows 3+: Real FastAPI backend calls for quotation, invoice, and all other business logic

    try {
      const response = await sendChatMessage(text);
      const assistantMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        text: response.response_text || "I processed your request.",
        timestamp: new Date(),
        document_type: response.document_type || undefined,
        document_data: response.data || undefined,
        pdf_url: response.pdf_url || undefined,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        text: "Something went wrong while connecting to the server. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { messages, isLoading, sendMessage };
}


