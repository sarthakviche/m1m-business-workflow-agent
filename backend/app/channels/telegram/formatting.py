"""
Munim.ai — Telegram message formatting
========================================
Agent responses use a small Markdown subset (**bold**, _italic_, `code`).
Telegram's HTML parse mode is the most forgiving target: everything is
escaped first, then only those three constructs are turned into tags.
"""

from __future__ import annotations

import html
import re
from typing import List

# Telegram rejects messages longer than 4096 characters (counted after entity parsing).
TELEGRAM_MAX_MESSAGE_CHARS = 4096

_BOLD = re.compile(r"\*\*(.+?)\*\*")
# Underscores inside words (item_code, snake_case) must stay literal.
_ITALIC = re.compile(r"(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])")
_CODE = re.compile(r"`([^`\n]+)`")


def to_telegram_html(text: str) -> str:
    escaped = html.escape(text or "", quote=False)
    escaped = _CODE.sub(r"<code>\1</code>", escaped)
    escaped = _BOLD.sub(r"<b>\1</b>", escaped)
    escaped = _ITALIC.sub(r"<i>\1</i>", escaped)
    return escaped


def to_plain_text(text: str) -> str:
    """Strip the Markdown markers; used when Telegram rejects the HTML."""
    plain = _BOLD.sub(r"\1", text or "")
    plain = _ITALIC.sub(r"\1", plain)
    return _CODE.sub(r"\1", plain)


def split_message(text: str, limit: int = TELEGRAM_MAX_MESSAGE_CHARS) -> List[str]:
    """
    Split raw (pre-formatting) text into chunks under ``limit``.

    Splits on line boundaries so formatting markers, which never span lines,
    stay balanced within a chunk. A safety margin leaves room for HTML tags.
    """
    budget = max(limit - 512, 1)
    chunks: List[str] = []
    current = ""
    for line in (text or "").split("\n"):
        while len(line) > budget:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:budget])
            line = line[budget:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > budget:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current or not chunks:
        chunks.append(current)
    return [c for c in chunks if c.strip()] or [""]
