"""
M1M (Munim.ai) — Catalog import from a price list
===================================================
Turns a photo, PDF or CSV of a business's price list / stock list into
catalog items, in two steps so nothing reaches the database unreviewed:

1. ``extract_catalog`` reads the file: CSVs with recognisable headers are
   parsed directly; photos, PDFs and other CSVs go to Gemini, which only
   transcribes what is printed. Every row is then checked deterministically (price, GST rate,
   HSN, unit) and matched against the existing catalog by exact normalized
   name. Nothing is written.
2. ``apply_catalog_import`` takes the rows the owner reviewed and upserts
   items and stock in one transaction.

Anti-hallucination rules: the model must leave a field null rather than
guess, and values that fail validation are dropped and reported as issues
instead of being "fixed". A missing GST rate is never defaulted here; the
owner picks it in the review step.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.categories import ModelError, RateLimitError, ValidationError
from app.models.item import Item
from app.models.stock import Stock
from app.services.ai_quota import reserve_ai_call
from app.services.gemini import DEFAULT_MODEL, GeminiKeyMissingError, get_gemini_client
from app.services.item_lookup import normalize_item_name

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMPORT_ROWS = 500

SUPPORTED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif",
    "application/pdf", "text/csv", "text/plain",
}

# GST slabs in use (including the 40% slab and legacy 12/28 rates).
VALID_GST_RATES = {Decimal(r) for r in ("0", "0.25", "1.5", "3", "5", "12", "18", "28", "40")}

_UNIT_ALIASES = {
    "pc": "pcs", "pcs": "pcs", "piece": "pcs", "pieces": "pcs", "no": "pcs", "nos": "pcs",
    "number": "pcs", "numbers": "pcs", "unit": "pcs", "units": "pcs", "ea": "pcs", "each": "pcs",
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "mtr": "mtr", "mtrs": "mtr", "m": "mtr", "meter": "mtr", "meters": "mtr", "metre": "mtr", "metres": "mtr",
    "ft": "ft", "feet": "ft", "foot": "ft", "rft": "ft",
    "sqft": "sqft", "sq ft": "sqft", "sq.ft": "sqft",
    "ltr": "ltr", "ltrs": "ltr", "l": "ltr", "litre": "ltr", "litres": "ltr", "liter": "ltr", "liters": "ltr",
    "ml": "ml", "box": "box", "boxes": "box", "set": "set", "sets": "set", "pair": "pair", "pairs": "pair",
    "roll": "roll", "rolls": "roll", "bag": "bag", "bags": "bag", "dozen": "dozen", "dz": "dozen",
    "pkt": "pkt", "packet": "pkt", "packets": "pkt", "bundle": "bundle", "coil": "coil", "ton": "ton", "tonne": "ton",
}

EXTRACTION_PROMPT = """You are reading a business's price list or stock list for an Indian GST billing app.
The file may be a phone photo of a handwritten or printed sheet, a PDF, or a CSV.

Transcribe every product row into `items`:
- name: the product name exactly as written, including size/spec (e.g. "Hex Bolt M10 x 50mm"). Fix nothing but obvious OCR spacing.
- unit_price: the selling price per unit in rupees, as a number without symbols or commas. If several prices are shown (MRP, dealer, retail), use the selling/rate column and mention the choice in `notes`.
- unit: the unit the price is for (pcs, kg, mtr, box, ltr, set...), only if written or clearly implied by a column header.
- hsn_code: only if printed.
- gst_rate_percent: only if printed for that row or for the whole list.
- quantity_available: only if the sheet shows stock on hand. A spec number like "12mm" or "1/2 inch" is NOT a quantity.

Rules:
- NEVER invent or estimate a value. If a field is missing, unreadable or ambiguous, set it to null.
- Skip headers, totals, subtotals, page numbers, addresses, phone numbers and terms.
- Do not merge or split rows. One printed product row = one item.
- If the file is not a price or stock list, return an empty `items` list and say so in `notes`.
"""


# ── Model output schema ───────────────────────────────────────────────────────

class ExtractedCatalogItem(BaseModel):
    name: str
    unit_price: Optional[float] = None
    unit: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate_percent: Optional[float] = None
    quantity_available: Optional[float] = None


class CatalogExtraction(BaseModel):
    items: List[ExtractedCatalogItem] = Field(default_factory=list)
    notes: Optional[str] = None


# ── Preview (step 1 result) ───────────────────────────────────────────────────

@dataclass
class PreviewRow:
    name: str
    unit_price: Optional[Decimal]
    unit: str
    hsn_code: Optional[str]
    gst_rate_percent: Optional[Decimal]
    quantity_available: Optional[Decimal]
    issues: List[str] = field(default_factory=list)
    # "new" | "update" | "unchanged"
    match: str = "new"
    existing_item_id: Optional[uuid.UUID] = None
    existing_unit_price: Optional[Decimal] = None


@dataclass
class CatalogPreview:
    rows: List[PreviewRow]
    notes: Optional[str]
    skipped: int


def catalog_key(name: str) -> str:
    """Key two names must share to be treated as the same catalog item."""
    return " ".join(normalize_item_name(name).split())


def normalize_unit(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = raw.strip().lower().rstrip(".")
    cleaned = re.sub(r"^(per|/)\s*", "", cleaned).strip()
    if not cleaned:
        return None
    return _UNIT_ALIASES.get(cleaned, cleaned[:12])


def _to_decimal(value: Optional[float]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (ArithmeticError, ValueError):
        return None


def _clean_row(raw: ExtractedCatalogItem) -> Optional[PreviewRow]:
    name = " ".join((raw.name or "").split())
    if not name or not catalog_key(name):
        return None

    issues: List[str] = []

    price = _to_decimal(raw.unit_price)
    if price is None:
        issues.append("Price missing")
    elif price <= 0:
        issues.append("Price must be more than zero")
        price = None

    gst = _to_decimal(raw.gst_rate_percent)
    if gst is None:
        issues.append("GST rate missing")
    elif gst not in VALID_GST_RATES:
        issues.append(f"GST rate {gst.normalize()}% is not a GST slab")
        gst = None

    hsn = re.sub(r"\D", "", raw.hsn_code or "") or None
    if hsn and len(hsn) not in (4, 6, 8):
        issues.append(f"HSN '{raw.hsn_code}' should be 4, 6 or 8 digits")
        hsn = None

    unit = normalize_unit(raw.unit)
    if unit is None:
        issues.append("Unit not written; assumed pcs")
        unit = "pcs"

    qty = _to_decimal(raw.quantity_available)
    if qty is not None and qty < 0:
        issues.append("Negative stock ignored")
        qty = None

    return PreviewRow(
        name=name[:200], unit_price=price, unit=unit, hsn_code=hsn,
        gst_rate_percent=gst, quantity_available=qty, issues=issues,
    )


def build_preview(extraction: CatalogExtraction, existing: List[Item]) -> CatalogPreview:
    """Validate extracted rows and match them to the existing catalog."""
    by_key: Dict[str, Item] = {catalog_key(i.name): i for i in existing}
    rows: List[PreviewRow] = []
    seen: set[str] = set()
    skipped = 0

    for raw in extraction.items[:MAX_IMPORT_ROWS]:
        row = _clean_row(raw)
        if row is None:
            skipped += 1
            continue
        key = catalog_key(row.name)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)

        match = by_key.get(key)
        if match is not None:
            row.existing_item_id = match.id
            row.existing_unit_price = match.unit_price
            same = (
                row.unit_price == match.unit_price
                and (row.gst_rate_percent is None or row.gst_rate_percent == match.gst_rate_percent)
                and row.quantity_available is None
            )
            row.match = "unchanged" if same else "update"
        rows.append(row)

    skipped += max(len(extraction.items) - MAX_IMPORT_ROWS, 0)
    return CatalogPreview(rows=rows, notes=extraction.notes, skipped=skipped)


# ── Gemini call ───────────────────────────────────────────────────────────────

def validate_upload(content: bytes, mime_type: str) -> str:
    """Return the canonical MIME type or raise ValidationError."""
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime not in SUPPORTED_MIME_TYPES:
        raise ValidationError(
            detail=f"Unsupported upload type {mime!r}",
            user_message="Upload a photo (JPG, PNG, WEBP, HEIC), a PDF or a CSV file.",
        )
    if not content:
        raise ValidationError(detail="Empty upload", user_message="That file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError(
            detail=f"Upload of {len(content)} bytes exceeds limit",
            user_message="That file is larger than 10 MB. Try a smaller photo or split the PDF.",
        )
    return mime


# Header names (lowercased, punctuation stripped) mapped to fields, for CSV exports.
_CSV_HEADERS = {
    "name": ("item", "item name", "name", "product", "product name", "description", "particulars", "stock item"),
    "unit_price": ("rate", "price", "selling price", "sale price", "unit price", "sales rate", "rate per unit"),
    "unit": ("unit", "uom", "units", "per"),
    "hsn_code": ("hsn", "hsn code", "hsnsac", "hsn sac", "hsn/sac"),
    "gst_rate_percent": ("gst", "gst rate", "gst %", "gst percent", "tax", "tax rate", "igst rate"),
    "quantity_available": ("qty", "quantity", "stock", "closing stock", "in stock", "opening stock", "available"),
}


def _csv_number(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.\-]", "", text or "")
    try:
        return float(cleaned) if cleaned not in ("", ".", "-") else None
    except ValueError:
        return None


def parse_csv_catalog(content: bytes) -> Optional[CatalogExtraction]:
    """Parse a CSV whose header row names the columns; None if headers aren't recognised."""
    text = content.decode("utf-8-sig", errors="replace")
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error:
        return None
    if not rows:
        return None

    columns: Dict[str, int] = {}
    for index, header in enumerate(rows[0]):
        key = re.sub(r"[^\w%/ ]", "", header.lower())
        key = re.sub(r"\b(rs|inr)\b", "", key)  # "Rate (Rs.)" → "rate"
        key = re.sub(r"\s+", " ", key).strip()
        for field_name, aliases in _CSV_HEADERS.items():
            if key in aliases and field_name not in columns:
                columns[field_name] = index
    if "name" not in columns or "unit_price" not in columns:
        return None

    def cell(row: List[str], field_name: str) -> str:
        index = columns.get(field_name)
        return row[index].strip() if index is not None and index < len(row) else ""

    items = [
        ExtractedCatalogItem(
            name=cell(row, "name"),
            unit_price=_csv_number(cell(row, "unit_price")),
            unit=cell(row, "unit") or None,
            hsn_code=cell(row, "hsn_code") or None,
            gst_rate_percent=_csv_number(cell(row, "gst_rate_percent")),
            quantity_available=_csv_number(cell(row, "quantity_available")),
        )
        for row in rows[1:]
        if any(c.strip() for c in row)
    ]
    return CatalogExtraction(items=items, notes=None)


def _extract_sync(content: bytes, mime_type: str) -> CatalogExtraction:
    from google.genai import errors as genai_errors
    from google.genai import types

    try:
        client = get_gemini_client()
    except GeminiKeyMissingError as exc:
        raise ModelError(detail=str(exc), user_message="Reading price lists isn't set up on this server yet.") from exc

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=[types.Part.from_bytes(data=content, mime_type=mime_type), EXTRACTION_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CatalogExtraction,
                temperature=0,
            ),
        )
    except genai_errors.APIError as exc:
        if getattr(exc, "code", None) == 429:
            daily = "PerDay" in str(exc)
            raise RateLimitError(
                detail=f"Gemini {'daily' if daily else 'per-minute'} quota exhausted",
                user_message=(
                    "Photo and PDF reading has hit today's limit. Try again later, or upload a CSV instead."
                    if daily else "The reader is busy right now. Please try again in a minute."
                ),
            ) from exc
        raise ModelError(detail=f"Gemini error {getattr(exc, 'code', '?')}",
                         user_message="Couldn't read that file right now. Please try again.") from exc

    try:
        return CatalogExtraction(**json.loads((response.text or "").strip() or "{}"))
    except (ValueError, TypeError) as exc:
        raise ModelError(detail="Unparseable catalog extraction",
                         user_message="Couldn't make sense of that file. Try a clearer photo.") from exc


async def extract_catalog(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    content: bytes,
    mime_type: str,
) -> CatalogPreview:
    """Read a price list file and return a reviewed-before-save preview."""
    mime = validate_upload(content, mime_type)
    extraction = parse_csv_catalog(content) if mime in ("text/csv", "text/plain") else None
    if extraction is None:
        if not await reserve_ai_call(session, tenant_id):
            raise RateLimitError(
                detail="AI quota reached",
                user_message="Photo and PDF reading has hit today's limit. Try again tomorrow, or upload a CSV instead.",
            )
        extraction = await asyncio.to_thread(_extract_sync, content, mime)
    existing = list((await session.execute(select(Item).where(Item.tenant_id == tenant_id))).scalars())
    preview = build_preview(extraction, existing)
    logger.info("catalog extraction: %d rows, %d skipped", len(preview.rows), preview.skipped)
    return preview


# ── Apply (step 2) ────────────────────────────────────────────────────────────

class CatalogImportRow(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit: str = Field(default="pcs", min_length=1, max_length=12)
    hsn_code: Optional[str] = Field(default=None, pattern=r"^(\d{4}|\d{6}|\d{8})$")
    gst_rate_percent: Decimal
    # None leaves stock as it is (new items start at 0).
    quantity_available: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


async def apply_catalog_import(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    rows: List[CatalogImportRow],
) -> ImportResult:
    """Upsert reviewed rows by normalized name. The caller commits."""
    if not rows:
        raise ValidationError(detail="No rows", user_message="There are no items to save.")
    if len(rows) > MAX_IMPORT_ROWS:
        raise ValidationError(detail="Too many rows", user_message=f"Import up to {MAX_IMPORT_ROWS} items at a time.")
    for row in rows:
        if row.gst_rate_percent not in VALID_GST_RATES:
            raise ValidationError(
                detail=f"Invalid GST rate {row.gst_rate_percent}",
                user_message=f"'{row.name}' has a GST rate that isn't a GST slab.",
            )

    items = list((await session.execute(select(Item).where(Item.tenant_id == tenant_id))).scalars())
    by_key: Dict[str, Item] = {catalog_key(i.name): i for i in items}
    stocks = {
        s.item_id: s
        for s in (await session.execute(select(Stock).where(Stock.tenant_id == tenant_id))).scalars()
    }

    result = ImportResult()
    for row in rows:
        name = " ".join(row.name.split())
        key = catalog_key(name)
        unit = normalize_unit(row.unit) or "pcs"
        item = by_key.get(key)

        if item is None:
            item = Item(
                tenant_id=tenant_id, name=name, unit_price=row.unit_price, unit=unit,
                hsn_code=row.hsn_code, gst_rate_percent=row.gst_rate_percent,
            )
            session.add(item)
            await session.flush()
            by_key[key] = item
            session.add(Stock(item_id=item.id, tenant_id=tenant_id,
                              quantity_available=row.quantity_available or Decimal("0")))
            result.created += 1
            continue

        changed = False
        for attr, value in (("unit_price", row.unit_price), ("unit", unit),
                            ("gst_rate_percent", row.gst_rate_percent)):
            if getattr(item, attr) != value:
                setattr(item, attr, value)
                changed = True
        if row.hsn_code and item.hsn_code != row.hsn_code:
            item.hsn_code = row.hsn_code
            changed = True

        if row.quantity_available is not None:
            stock = stocks.get(item.id)
            if stock is None:
                session.add(Stock(item_id=item.id, tenant_id=tenant_id, quantity_available=row.quantity_available))
                changed = True
            elif stock.quantity_available != row.quantity_available:
                stock.quantity_available = row.quantity_available
                stock.last_updated = datetime.now(timezone.utc)
                changed = True

        if changed:
            result.updated += 1
        else:
            result.unchanged += 1

    await session.flush()
    return result
