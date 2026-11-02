"""
Munim.ai — Telegram Bot API types
===================================
Only the fields the adapter reads are modelled; unknown fields are ignored so
new Bot API releases never break parsing.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _TelegramModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TelegramUser(_TelegramModel):
    id: int
    is_bot: bool = False
    first_name: str = ""
    last_name: Optional[str] = None
    username: Optional[str] = None

    @property
    def display_name(self) -> str:
        full = " ".join(p for p in (self.first_name, self.last_name) if p)
        return full or (f"@{self.username}" if self.username else str(self.id))


class TelegramChat(_TelegramModel):
    id: int
    type: str  # 'private' | 'group' | 'supergroup' | 'channel'


class TelegramMessage(_TelegramModel):
    message_id: int
    date: int
    chat: TelegramChat
    from_user: Optional[TelegramUser] = Field(default=None, alias="from")
    text: Optional[str] = None


class TelegramUpdate(_TelegramModel):
    update_id: int
    message: Optional[TelegramMessage] = None


class BotCommand(_TelegramModel):
    command: str
    description: str


def parse_updates(payload: list) -> List[TelegramUpdate]:
    return [TelegramUpdate.model_validate(u) for u in payload]
