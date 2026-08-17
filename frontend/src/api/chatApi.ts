// chatApi.ts — Typed fetch wrapper for API endpoints

import type { ChatResponse, DocumentHistoryItem, DocumentListResponse } from "../types/chat";

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const response = await fetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "Unknown error");
    throw new Error(`Chat API error ${response.status}: ${detail}`);
  }

  return response.json() as Promise<ChatResponse>;
}

export async function fetchDocuments(): Promise<DocumentHistoryItem[]> {
  const response = await fetch("/api/v1/documents", {
    method: "GET",
    headers: { "Accept": "application/json" },
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "Unknown error");
    throw new Error(`Documents API error ${response.status}: ${detail}`);
  }

  const data = (await response.json()) as DocumentListResponse;
  return data.documents || [];
}

