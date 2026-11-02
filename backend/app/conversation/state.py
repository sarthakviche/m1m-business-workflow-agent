"""
Munim.ai — Conversation State Model
=====================================
Structured state for an active conversation, replacing raw history.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _item_key(line_item: Dict[str, Any]) -> str:
    return " ".join(str(line_item.get("item_name") or "").lower().split())


def merge_line_items(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge line items by normalized item name.

    The classifier sees the full conversation, so a follow-up turn may repeat
    items from earlier turns. Appending blindly would double them; instead an
    item named again replaces the earlier line (latest quantity wins) and new
    items are appended in order.
    """
    merged = list(existing)
    positions = {_item_key(li): idx for idx, li in enumerate(merged)}
    for li in new:
        key = _item_key(li)
        if key in positions:
            # A repeat without a quantity must not erase one already given.
            if li.get("quantity") is None and merged[positions[key]].get("quantity") is not None:
                continue
            merged[positions[key]] = li
        else:
            positions[key] = len(merged)
            merged.append(li)
    return merged


@dataclass
class ConversationState:
    """
    Tracks the structured state of an ongoing conversation.
    """
    conversation_id: uuid.UUID
    business_id: uuid.UUID

    # What the user is trying to do
    pending_intent: Optional[str] = None
    pending_workflow: Optional[str] = None

    # Entities extracted so far across multiple turns
    extracted_entities: Dict[str, Any] = field(default_factory=dict)

    # What we still need from the user
    missing_fields: List[str] = field(default_factory=list)

    # Output of the last tool execution
    last_tool_result: Optional[Dict[str, Any]] = None

    # Where we are in the clarification cycle
    clarification_state: Optional[str] = None

    # Bounded LLM summary of older turns
    conversation_summary: str = ""
    active_turn_count: int = 0

    def update_entities(self, new_entities: dict) -> None:
        """Merge newly extracted entities into the state."""
        for k, v in new_entities.items():
            if v is not None:
                if k == "line_items" and isinstance(v, list):
                    self.extracted_entities[k] = merge_line_items(self.extracted_entities.get(k) or [], v)
                else:
                    self.extracted_entities[k] = v

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable form (UUIDs as strings) for persistence."""
        data = asdict(self)
        data["conversation_id"] = str(self.conversation_id)
        data["business_id"] = str(self.business_id)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        known["conversation_id"] = uuid.UUID(str(known["conversation_id"]))
        known["business_id"] = uuid.UUID(str(known["business_id"]))
        return cls(**known)
