"""
Tests for price-list import over Telegram (photo/PDF/CSV → review → buttons → save).

Reuses the Telegram test fixtures: an isolated SQLite DB and a fake Bot API
client. Gemini is replaced by a stub so the flow, not the model, is tested.
"""

from __future__ import annotations

import itertools
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx
import pytest
from sqlalchemy import select

from app.channels.pending_import import import_key, pending_imports
from app.channels.telegram.catalog_import import UNSUPPORTED_FILE_TEXT
from app.channels.telegram.client import TelegramAPIError, TelegramClient
from app.channels.telegram.formatting import to_telegram_html
from app.channels.telegram.handler import NOT_LINKED_TEXT, TelegramUpdateHandler
from app.channels.telegram.types import TelegramUpdate
from app.errors.categories import RateLimitError
from app.models.item import Item
from app.models.stock import Stock
from app.services import catalog_import
from app.services.catalog_import import CatalogExtraction, ExtractedCatalogItem
from tests.test_telegram_channel import (  # noqa: F401 — session_factory is a fixture
    OTHER_TENANT_ID,
    TENANT_ID,
    USER_ID,
    FakeTelegramClient,
    link_user,
    session_factory,
)

_update_ids = itertools.count(50_000)
_callback_ids = itertools.count(1)

PHOTO_BYTES = b"\xff\xd8\xff\xe0 jpeg"


def _message(user_id: int = USER_ID, **content: Any) -> Dict[str, Any]:
    return {
        "message_id": 7,
        "date": 1_700_000_000,
        "chat": {"id": user_id, "type": "private"},
        "from": {"id": user_id, "is_bot": False, "first_name": "Sarthak"},
        **content,
    }


def photo_update(user_id: int = USER_ID) -> TelegramUpdate:
    return TelegramUpdate.model_validate({
        "update_id": next(_update_ids),
        "message": _message(user_id, photo=[
            {"file_id": "small", "width": 90, "height": 120},
            {"file_id": "large", "width": 960, "height": 1280, "file_size": 200_000},
        ]),
    })


def document_update(mime: str, name: str, size: int = 1000) -> TelegramUpdate:
    return TelegramUpdate.model_validate({
        "update_id": next(_update_ids),
        "message": _message(document={"file_id": "doc", "file_name": name, "mime_type": mime, "file_size": size}),
    })


def tap(data: str, user_id: int = USER_ID, update_id: Optional[int] = None) -> TelegramUpdate:
    return TelegramUpdate.model_validate({
        "update_id": update_id if update_id is not None else next(_update_ids),
        "callback_query": {
            "id": f"cb{next(_callback_ids)}",
            "from": {"id": user_id, "is_bot": False, "first_name": "Sarthak"},
            "message": _message(user_id, text="summary"),
            "data": data,
        },
    })


def buttons(message: Dict[str, Any]) -> Dict[str, str]:
    """Button label → callback data for a sent message."""
    rows = message.get("reply_markup", {}).get("inline_keyboard", [])
    return {b["text"]: b["callback_data"] for row in rows for b in row}


@pytest.fixture
def stub_gemini(monkeypatch):
    calls = []

    def fake_extract(content: bytes, mime_type: str) -> CatalogExtraction:
        calls.append((content, mime_type))
        return CatalogExtraction(items=[
            ExtractedCatalogItem(name="MS Hex Bolt M10", unit_price=4.75, unit="pcs", gst_rate_percent=18),
            ExtractedCatalogItem(name="Spring Washer 10mm", unit_price=0.8, unit="pcs", gst_rate_percent=None),
            ExtractedCatalogItem(name="Anchor 12*100", unit_price=None, unit="pcs", gst_rate_percent=18),
        ], notes="Used the Rate column.")

    monkeypatch.setattr(catalog_import, "_extract_sync", fake_extract)
    return calls


def _handler(factory, **files: bytes):
    client = FakeTelegramClient(files={"large": PHOTO_BYTES, "doc": b"Item,Rate,GST\nNut M10,1.2,18\n", **files})
    return TelegramUpdateHandler(client, factory), client


async def _items(factory, tenant_id=TENANT_ID) -> Dict[str, Item]:
    async with factory() as s:
        return {i.name: i for i in (await s.execute(select(Item).where(Item.tenant_id == tenant_id))).scalars()}


async def test_photo_is_summarised_with_buttons_and_nothing_is_saved(session_factory, stub_gemini):
    await link_user(session_factory)
    handler, client = _handler(session_factory)

    await handler.handle(photo_update())

    assert client.downloads == ["large"]  # highest resolution
    assert stub_gemini == [(PHOTO_BYTES, "image/jpeg")]
    summary = client.messages[-1]
    assert "Found 3 items" in summary["text"]
    assert "MS Hex Bolt M10: ₹4.75/pcs · GST 18% · <i>updates ₹4.25</i>" in summary["text"]
    assert "Anchor 12×100: no price on the list, will be skipped" in summary["text"]
    assert "1 item has no GST rate" in summary["text"]
    assert {"GST 5%", "GST 18%", "✖️ Discard"} <= set(buttons(summary))
    assert not any(label.startswith("✅") for label in buttons(summary))  # can't save until GST is set
    assert set(await _items(session_factory)) == {"TMT Steel Rod 12mm", "MS Hex Bolt M10"}


async def test_pick_gst_then_save_writes_catalog_once(session_factory, stub_gemini):
    await link_user(session_factory)
    handler, client = _handler(session_factory)
    await handler.handle(photo_update())
    summary_id = len(client.messages)

    await handler.handle(tap(buttons(client.messages[-1])["GST 18%"]))
    assert summary_id in client.keyboards_removed
    assert "Set <b>GST 18%</b> on 1 item" in client.messages[-1]["text"]
    save = buttons(client.messages[-1])["✅ Save 2 items"]

    save_update = tap(save)
    await handler.handle(save_update)
    assert "Catalog updated:</b> 1 added, 1 updated." in client.messages[-1]["text"]
    assert "1 item without a price was skipped." in client.messages[-1]["text"]

    items = await _items(session_factory)
    assert items["MS Hex Bolt M10"].unit_price == Decimal("4.75")
    assert items["Spring Washer 10mm"].gst_rate_percent == Decimal("18")
    assert "Anchor 12*100" not in items
    async with session_factory() as s:
        washer_stock = (await s.execute(
            select(Stock.quantity_available).where(Stock.item_id == items["Spring Washer 10mm"].id))).scalar_one()
    assert washer_stock == Decimal("0")

    # A second tap on the same Save button (or a redelivered update) changes nothing.
    await handler.handle(tap(save))
    await handler.handle(save_update)
    assert "expired" in client.messages[-1]["text"]
    assert len(await _items(session_factory)) == 3


async def test_discard_saves_nothing(session_factory, stub_gemini):
    await link_user(session_factory)
    handler, client = _handler(session_factory)
    await handler.handle(photo_update())

    await handler.handle(tap(buttons(client.messages[-1])["✖️ Discard"]))

    assert "Nothing was saved" in client.messages[-1]["text"]
    assert set(await _items(session_factory)) == {"TMT Steel Rod 12mm", "MS Hex Bolt M10"}
    async with session_factory() as s:
        assert await pending_imports.get(s, import_key("telegram", TENANT_ID, USER_ID), TENANT_ID) is None


async def test_new_list_replaces_the_previous_one(session_factory, stub_gemini):
    await link_user(session_factory)
    handler, client = _handler(session_factory)
    await handler.handle(photo_update())
    old_discard = buttons(client.messages[-1])["✖️ Discard"]

    await handler.handle(document_update("text/csv", "list.csv"))

    assert "Nut M10: ₹1.20/pcs · GST 18%" in client.messages[-1]["text"]
    assert len(stub_gemini) == 1  # the CSV was parsed without the model
    await handler.handle(tap(old_discard))
    assert "expired" in client.messages[-1]["text"]


async def test_buttons_only_act_for_the_linked_tenant(session_factory, stub_gemini):
    await link_user(session_factory)
    await link_user(session_factory, tenant_id=OTHER_TENANT_ID, user_id=777)
    handler, client = _handler(session_factory)
    await handler.handle(photo_update())
    discard = buttons(client.messages[-1])["✖️ Discard"]

    await handler.handle(tap(discard, user_id=777))

    assert "expired" in client.messages[-1]["text"]
    async with session_factory() as s:
        assert await pending_imports.get(s, import_key("telegram", TENANT_ID, USER_ID), TENANT_ID) is not None


async def test_unlinked_chat_cannot_import(session_factory, stub_gemini):
    handler, client = _handler(session_factory)
    await handler.handle(photo_update())
    await handler.handle(tap("imp:save:whatever"))

    assert [m["text"] for m in client.messages] == [to_telegram_html(NOT_LINKED_TEXT)] * 2
    assert client.downloads == [] and stub_gemini == []


async def test_unsupported_and_oversized_files_are_refused_before_download(session_factory, stub_gemini):
    await link_user(session_factory)
    handler, client = _handler(session_factory)

    await handler.handle(document_update("application/vnd.ms-excel", "list.xls"))
    assert client.last_text == UNSUPPORTED_FILE_TEXT
    await handler.handle(document_update("application/pdf", "big.pdf", size=50 * 1024 * 1024))
    assert "over 10 MB" in client.last_text
    assert client.downloads == []


async def test_model_errors_are_reported_in_plain_words(session_factory, monkeypatch):
    await link_user(session_factory)
    handler, client = _handler(session_factory)

    def quota(content, mime):
        raise RateLimitError(user_message="Photo and PDF reading has hit today's limit.")

    monkeypatch.setattr(catalog_import, "_extract_sync", quota)
    await handler.handle(photo_update())
    assert client.last_text == "Photo and PDF reading has hit today's limit."


async def test_client_download_checks_size_and_hides_token():
    token = "123:SECRET"
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path.endswith("/getFile"):
            return httpx.Response(200, json={"ok": True, "result": {"file_path": "photos/a.jpg", "file_size": 3}})
        return httpx.Response(200, content=b"abc")

    client = TelegramClient(token, http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    assert await client.download_file("f1", max_bytes=10) == b"abc"
    assert requests[-1] == f"https://api.telegram.org/file/bot{token}/photos/a.jpg"

    with pytest.raises(TelegramAPIError) as exc:
        await client.download_file("f1", max_bytes=2)
    assert exc.value.error_code == 413
    assert "SECRET" not in str(exc.value)
    await client.aclose()
