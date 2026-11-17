"""
Custom quotation formats
=========================
A business uploads a quotation they already send (PDF, photo, Word or Excel).
Gemini reads it and describes its layout as a QuotationFormat: the title, the
labels they use, the item-table columns in their order, their terms, bank
details and sign-off. Quotations are then rendered from Munim's own template
driven by that description.

Why a description and not an AI-written template: the model never produces
code or HTML that we execute. Every value is plain text, length-limited and
autoescaped when rendered, and every number on the document still comes from
the catalog and the GST calculator. The trade-off is that the result follows
their wording, columns, colours and boilerplate rather than copying the page
pixel for pixel.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import uuid
import zipfile
from typing import List, Literal, Optional
from xml.etree import ElementTree

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.categories import ModelError, RateLimitError, ValidationError
from app.services.ai_quota import reserve_ai_call
from app.services.gemini import DEFAULT_MODEL, GeminiKeyMissingError, get_gemini_client

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

ColumnKey = Literal["index", "item", "hsn", "qty", "unit", "rate", "gst", "amount"]

# Fields a placeholder on their document can map to. "other" is anything we can't fill.
PlaceholderField = Literal[
    "business_name", "business_address", "business_gstin", "business_phone", "business_email",
    "customer_name", "customer_address", "customer_gstin", "customer_phone",
    "quotation_number", "date", "valid_until", "item_table",
    "subtotal", "tax", "grand_total", "amount_in_words", "other",
]
_SUPPORTED_FIELDS = {
    "business_name", "business_address", "business_gstin", "customer_name", "customer_address",
    "customer_gstin", "customer_phone", "quotation_number", "date", "valid_until", "item_table",
    "subtotal", "tax", "grand_total", "amount_in_words",
}

DEFAULT_COLUMNS = [
    {"key": "index", "label": "#"},
    {"key": "item", "label": "Item"},
    {"key": "hsn", "label": "HSN"},
    {"key": "qty", "label": "Qty"},
    {"key": "rate", "label": "Rate (₹)"},
    {"key": "gst", "label": "GST"},
    {"key": "amount", "label": "Amount (₹)"},
]


def _clean(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:limit] or None


class FormatColumn(BaseModel):
    key: ColumnKey
    label: str = Field(min_length=1, max_length=40)

    @field_validator("label", mode="before")
    @classmethod
    def _label(cls, v):
        return _clean(v, 40) or "—"


class Placeholder(BaseModel):
    label: str = Field(max_length=80)
    field: PlaceholderField = "other"

    @field_validator("label", mode="before")
    @classmethod
    def _label(cls, v):
        return _clean(v, 80) or "—"

    @property
    def supported(self) -> bool:
        return self.field in _SUPPORTED_FIELDS


class QuotationFormat(BaseModel):
    """How this business lays out a quotation. Every field is optional text; numbers never come from here."""

    source_filename: Optional[str] = Field(default=None, max_length=120)
    title: str = Field(default="QUOTATION", max_length=40)
    party_label: str = Field(default="Quotation for", max_length=40)
    date_label: str = Field(default="Date", max_length=30)
    valid_until_label: str = Field(default="Valid until", max_length=30)
    columns: List[FormatColumn] = Field(default_factory=lambda: [FormatColumn(**c) for c in DEFAULT_COLUMNS])
    accent_color: Optional[str] = None
    intro_text: Optional[str] = Field(default=None, max_length=400)
    terms: List[str] = Field(default_factory=list, max_length=12)
    bank_details: List[str] = Field(default_factory=list, max_length=8)
    footer_text: Optional[str] = Field(default=None, max_length=200)
    signatory_label: str = Field(default="Authorised signatory", max_length=40)
    validity_days: Optional[int] = Field(default=None, ge=1, le=365)
    show_amount_in_words: bool = True
    show_tax_breakdown: bool = True
    placeholders: List[Placeholder] = Field(default_factory=list, max_length=40)

    @field_validator("title", "party_label", "date_label", "valid_until_label", "signatory_label", mode="before")
    @classmethod
    def _short_text(cls, v, info):
        defaults = {"title": "QUOTATION", "party_label": "Quotation for", "date_label": "Date",
                    "valid_until_label": "Valid until", "signatory_label": "Authorised signatory"}
        return _clean(v, 40) or defaults[info.field_name]

    @field_validator("intro_text", "footer_text", "source_filename", mode="before")
    @classmethod
    def _long_text(cls, v, info):
        return _clean(v, {"intro_text": 400, "footer_text": 200, "source_filename": 120}[info.field_name])

    @field_validator("terms", "bank_details", mode="before")
    @classmethod
    def _lines(cls, v, info):
        limit = 12 if info.field_name == "terms" else 8
        lines = [_clean(x, 200) for x in (v or [])]
        if info.field_name == "terms":
            # The document numbers terms itself: drop "1.", "a)", "•" the sample already had.
            lines = [re.sub(r"^(?:\(?(?:\d{1,2}|[a-zA-Z])[.)]|[•\-*–])\s*", "", x) if x else x for x in lines]
        return [x for x in lines if x][:limit]

    @field_validator("accent_color", mode="before")
    @classmethod
    def _color(cls, v):
        v = (v or "").strip()
        return v.lower() if _HEX_COLOR.fullmatch(v) else None

    @field_validator("columns", mode="before")
    @classmethod
    def _columns(cls, v):
        # Keep their order, drop duplicates, and always show the item and amount.
        seen, out = set(), []
        for col in v or []:
            data = col if isinstance(col, dict) else col.model_dump()
            if data.get("key") in seen:
                continue
            seen.add(data.get("key"))
            out.append(data)
        keys = {c.get("key") for c in out}
        if "item" not in keys:
            out.insert(min(1, len(out)), {"key": "item", "label": "Item"})
        if "amount" not in keys:
            out.append({"key": "amount", "label": "Amount (₹)"})
        return out[:8]

    def render_context(self) -> dict:
        """The plain dict the document templates read."""
        return self.model_dump(exclude={"placeholders", "source_filename"})


class FormatAnalysis(BaseModel):
    format: QuotationFormat
    supported_placeholders: List[Placeholder]
    unsupported_placeholders: List[Placeholder]


def analysis_for(fmt: QuotationFormat) -> FormatAnalysis:
    return FormatAnalysis(
        format=fmt,
        supported_placeholders=[p for p in fmt.placeholders if p.supported],
        unsupported_placeholders=[p for p in fmt.placeholders if not p.supported],
    )


# ── Reading the sample ────────────────────────────────────────────────────────

_MIME_BY_SIGNATURE = (
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def sniff_upload(content: bytes, filename: str) -> str:
    """The real file type from its bytes; never trust the declared type."""
    if not content:
        raise ValidationError(detail="Empty upload", user_message="That file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError(detail=f"Upload of {len(content)} bytes", user_message="That file is larger than 10 MB.")
    for signature, mime in _MIME_BY_SIGNATURE:
        if content.startswith(signature):
            return mime
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"PK\x03\x04"):
        try:
            names = set(zipfile.ZipFile(io.BytesIO(content)).namelist())
        except zipfile.BadZipFile:
            names = set()
        if "word/document.xml" in names:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if "xl/workbook.xml" in names:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    raise ValidationError(
        detail=f"Unsupported quotation sample {filename!r}",
        user_message="Upload your quotation as a PDF, a photo (JPG or PNG), a Word file (.docx) or an Excel file (.xlsx).",
    )


def _xml_text(xml: bytes, tag: str, para: str | None = None) -> List[str]:
    root = ElementTree.fromstring(xml)
    lines: List[str] = []
    if para:
        for p in root.iter():
            if p.tag.endswith("}" + para):
                text = "".join(t.text or "" for t in p.iter() if t.tag.endswith("}" + tag))
                if text.strip():
                    lines.append(text.strip())
    else:
        lines = [t.text.strip() for t in root.iter() if t.tag.endswith("}" + tag) and t.text and t.text.strip()]
    return lines


def office_text(content: bytes, mime: str) -> str:
    """Plain text of a .docx or .xlsx, in reading order, for the model to read."""
    z = zipfile.ZipFile(io.BytesIO(content))
    if mime.endswith("wordprocessingml.document"):
        lines: List[str] = []
        for name in ("word/header1.xml", "word/document.xml", "word/footer1.xml"):
            if name in z.namelist():
                lines += _xml_text(z.read(name), "t", "p")
    else:
        strings = _xml_text(z.read("xl/sharedStrings.xml"), "t") if "xl/sharedStrings.xml" in z.namelist() else []
        lines = []
        sheet = next((n for n in sorted(z.namelist()) if n.startswith("xl/worksheets/sheet")), None)
        if sheet:
            root = ElementTree.fromstring(z.read(sheet))
            for row in (e for e in root.iter() if e.tag.endswith("}row")):
                cells = []
                for c in (e for e in row if e.tag.endswith("}c")):
                    v = next((e.text for e in c.iter() if e.tag.endswith("}v") or e.tag.endswith("}t")), None)
                    if v is None:
                        continue
                    if c.get("t") == "s" and v.isdigit() and int(v) < len(strings):
                        v = strings[int(v)]
                    cells.append(v)
                if cells:
                    lines.append(" | ".join(cells))
    text = "\n".join(lines)[:20_000]
    if not text.strip():
        raise ValidationError(detail="Office file has no text", user_message="That file has no text we can read.")
    return text


PROMPT = """You are reading a sample QUOTATION that an Indian small business sends to its customers.
Describe its FORMAT so the same layout can be produced for new quotations. Do not copy the sample's
customer, items or amounts: those change on every quotation.

Return JSON with:
- title: the document heading exactly as printed (e.g. "QUOTATION", "PROFORMA INVOICE", "Price Quote").
- party_label: the label before the customer's details (e.g. "To", "Quotation for", "Bill To", "M/s").
- date_label: the label printed next to the date (e.g. "Date", "Dated").
- valid_until_label: the label for the validity date, or "Valid until" if none.
- columns: the item table's columns, left to right. key must be one of:
  index (serial number), item (description), hsn (HSN/SAC), qty (quantity), unit (unit/UOM),
  rate (price per unit), gst (tax rate %), amount (line total). label is the header text as printed.
  Skip columns that are none of these (for example discount or image).
- accent_color: the main heading or table-header colour as #RRGGBB, or null if it is black and white.
- intro_text: a fixed opening sentence such as "Dear Sir, we are pleased to quote...", or null.
- terms: each fixed term or condition, one per entry, as printed.
- bank_details: fixed bank or UPI lines (bank name, account number, IFSC, UPI ID), one per entry.
- footer_text: a fixed closing line or footer, or null.
- signatory_label: the text under the signature line (e.g. "Authorised Signatory", "Proprietor").
- validity_days: the number of days the quote is valid if stated, else null.
- show_amount_in_words: true if the total is written in words.
- show_tax_breakdown: true if CGST/SGST/IGST amounts are listed separately.
- placeholders: every variable field on the page (things that change per quotation), as
  {label: the CAPTION printed before the value with its trailing colon removed (e.g. "Quotation No.",
  "GSTIN", "Delivery period"); never the sample's own value such as a name, address or number. When a
  value has no caption, use a 2-3 word description such as "Customer name" or "Customer address".
  List each field once. field: one of business_name, business_address, business_gstin,
  business_phone, business_email, customer_name, customer_address, customer_gstin, customer_phone,
  quotation_number, date, valid_until, item_table, subtotal, tax, grand_total, amount_in_words, other}.
  Use "other" for anything else, such as delivery period, payment terms filled per quote, or reference number.
"""


class _Extraction(BaseModel):
    """The schema Gemini fills: flat, permissive, cleaned by QuotationFormat afterwards."""

    title: Optional[str] = None
    party_label: Optional[str] = None
    date_label: Optional[str] = None
    valid_until_label: Optional[str] = None
    columns: List[FormatColumn] = []
    accent_color: Optional[str] = None
    intro_text: Optional[str] = None
    terms: List[str] = []
    bank_details: List[str] = []
    footer_text: Optional[str] = None
    signatory_label: Optional[str] = None
    validity_days: Optional[int] = None
    show_amount_in_words: Optional[bool] = None
    show_tax_breakdown: Optional[bool] = None
    placeholders: List[Placeholder] = []


def _analyze_sync(content: bytes, mime: str) -> dict:
    from google.genai import errors as genai_errors
    from google.genai import types

    try:
        client = get_gemini_client()
    except GeminiKeyMissingError as exc:
        raise ModelError(detail=str(exc), user_message="Reading quotation formats isn't set up on this server yet.") from exc

    if mime.startswith("application/vnd.openxmlformats"):
        sample = types.Part.from_text(text="Text of the sample quotation:\n\n" + office_text(content, mime))
    else:
        sample = types.Part.from_bytes(data=content, mime_type=mime)

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=[sample, PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_Extraction,
                temperature=0,
                http_options=types.HttpOptions(timeout=60_000),
            ),
        )
    except genai_errors.APIError as exc:
        if getattr(exc, "code", None) == 429:
            raise RateLimitError(detail="Gemini quota exhausted",
                                 user_message="The reader is busy right now. Please try again in a minute.") from exc
        raise ModelError(detail=f"Gemini error {getattr(exc, 'code', '?')}",
                         user_message="Couldn't read that quotation right now. Please try again.") from exc
    try:
        return json.loads((response.text or "").strip() or "{}")
    except ValueError as exc:
        raise ModelError(detail="Unparseable format extraction",
                         user_message="Couldn't make sense of that file. Try a clearer copy.") from exc


def format_from_extraction(raw: dict, filename: Optional[str]) -> QuotationFormat:
    """Validate the model's answer into a safe format; missing or bad values fall back to the defaults."""
    data = {k: v for k, v in (raw or {}).items() if v not in (None, "", [])}
    columns = [c for c in data.pop("columns", []) if isinstance(c, dict) and c.get("key") in ColumnKey.__args__]
    placeholders = [p for p in data.pop("placeholders", []) if isinstance(p, dict) and p.get("label")]
    for p in placeholders:
        if p.get("field") not in PlaceholderField.__args__:
            p["field"] = "other"
    try:
        days = int(data.get("validity_days")) if data.get("validity_days") is not None else None
    except (TypeError, ValueError):
        days = None
    data["validity_days"] = days if days and 1 <= days <= 365 else None
    return QuotationFormat(
        **data,
        columns=columns or DEFAULT_COLUMNS,
        placeholders=placeholders[:40],
        source_filename=filename,
    )


async def analyze_quotation_format(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    content: bytes,
    filename: str,
) -> FormatAnalysis:
    mime = sniff_upload(content, filename)
    if not await reserve_ai_call(session, tenant_id):
        raise RateLimitError(detail="AI quota reached", user_message="Reading files has hit today's limit. Try again tomorrow.")
    raw = await asyncio.to_thread(_analyze_sync, content, mime)
    fmt = format_from_extraction(raw, filename)
    logger.info("quotation_format.analyzed", extra={"columns": len(fmt.columns), "placeholders": len(fmt.placeholders)})
    return analysis_for(fmt)


def load_format(tenant) -> Optional[QuotationFormat]:
    """The tenant's saved format, or None for Munim's standard layout. A corrupt value is ignored."""
    raw = getattr(tenant, "quotation_format", None)
    if not raw:
        return None
    try:
        return QuotationFormat(**raw)
    except Exception:
        logger.warning("quotation_format.invalid_saved_value")
        return None
