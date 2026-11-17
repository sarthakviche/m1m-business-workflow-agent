"""
Munim.ai — Messaging channel adapters (Telegram today, WhatsApp next).

Each adapter converts its platform's payloads into a NormalizedMessage,
resolves the tenant server-side from a linked ChannelIdentity, runs the
shared MunimOrchestrator, and renders the OrchestratorResult back.
"""
