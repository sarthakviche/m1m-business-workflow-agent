"""
Munim.ai — Telegram channel adapter.

  client.py      Thin async Bot API client (httpx).
  types.py       Pydantic models for the subset of Update we consume.
  formatting.py  Agent Markdown → Telegram HTML, message splitting.
  handler.py     Update processing: dedup, commands, linking, orchestrator.
  router.py      FastAPI webhook + link-code endpoints.
"""
