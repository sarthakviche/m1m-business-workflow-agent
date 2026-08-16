"""
M1M (Munim.ai) — Deterministic GST Calculator
================================================
Pure Python, deterministic, no external API calls, no database access.

This module is the single source of truth for all GST arithmetic in the
M1M system.  It MUST NOT call Gemini, any LLM, LangGraph, or any network
service — GST math is a legal requirement and must be verifiably correct
by reading this code alone.

Design (per TRD Section 6):
  - All arithmetic uses ``decimal.Decimal`` — never ``float``.
  - Rounding rule: ``ROUND_HALF_UP`` to 2 decimal places at the LINE level.
  - Intra-state  (supplier_state == customer_state):
      CGST = floor-half of total GST (rounded ROUND_HALF_UP)
      SGST = total_gst - CGST          (exact complement — no double-rounding)
      IGST = Decimal("0.00")
  - Inter-state  (supplier_state != customer_state):
      IGST = total_gst
      CGST = SGST = Decimal("0.00")
  - grand_total == taxable_amount + total_tax  (always exact by construction)

Valid GST rates for Indian B2B/B2C invoices: 0, 0.1, 0.25, 1, 1.5, 3, 5,
6, 7.5, 12, 18, 28 (%).  Rates outside this set are rejected to prevent
accidental mis-billing.

Usage
-----
    from app.services.gst_calculator import calculate_gst, GSTResult

    result = calculate_gst(
        taxable_amount=Decimal("10000.00"),
        gst_rate_percent=Decimal("18"),
        supplier_state="Maharashtra",
        customer_state="Karnataka",
    )
    # result.igst == Decimal("1800.00")
    # result.grand_total == Decimal("11800.00")
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

# ─── Constants ─────────────────────────────────────────────────────────────────

# All GST rate slabs permitted under Indian GST law (as of 2024).
# Expressed as Decimal strings for exact comparison.
VALID_GST_RATES: frozenset[Decimal] = frozenset(
    Decimal(r)
    for r in (
        "0", "0.1", "0.25", "1", "1.5", "3",
        "5", "6", "7.5", "12", "18", "28",
    )
)

_ZERO   = Decimal("0.00")
_CENT   = Decimal("0.01")   # quantize target for 2-decimal rounding


# ─── Errors ────────────────────────────────────────────────────────────────────

class GSTValidationError(ValueError):
    """Raised when inputs to the GST calculator are invalid."""


# ─── Result dataclass ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GSTResult:
    """
    Immutable result of a GST calculation.

    Attributes
    ----------
    taxable_amount:
        The pre-tax amount (input, rounded to 2 dp).
    gst_rate:
        The GST rate applied (%, e.g. Decimal("18")).
    tax_type:
        "intra_state" (CGST + SGST) or "inter_state" (IGST).
    cgst:
        Central GST component.
    sgst:
        State GST component.
    igst:
        Integrated GST component.
    total_tax:
        cgst + sgst + igst.
    grand_total:
        taxable_amount + total_tax.
    supplier_state:
        Normalised supplier/business state.
    customer_state:
        Normalised customer state.
    """
    taxable_amount: Decimal
    gst_rate: Decimal
    tax_type: str          # "intra_state" | "inter_state"
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total_tax: Decimal
    grand_total: Decimal
    supplier_state: str
    customer_state: str


# ─── Internal helpers ──────────────────────────────────────────────────────────

def _round2(value: Decimal) -> Decimal:
    """Round to 2 decimal places using ROUND_HALF_UP (GST-compliant)."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _normalise_state(state: str, field_name: str) -> str:
    """Strip whitespace; raise GSTValidationError if empty."""
    normalised = state.strip()
    if not normalised:
        raise GSTValidationError(
            f"'{field_name}' must not be empty — "
            "supplier and customer states are required for GST classification."
        )
    return normalised


def _to_decimal(value: Union[Decimal, int, float, str], field_name: str) -> Decimal:
    """Coerce numeric inputs to Decimal, raising on non-numeric types."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        raise GSTValidationError(
            f"'{field_name}' must be a numeric value, got: {value!r}"
        )


# ─── Public API ────────────────────────────────────────────────────────────────

def calculate_gst(
    taxable_amount: Union[Decimal, int, float, str],
    gst_rate_percent: Union[Decimal, int, float, str],
    supplier_state: str,
    customer_state: str,
) -> GSTResult:
    """
    Compute GST for a given taxable amount and transaction context.

    Parameters
    ----------
    taxable_amount:
        Pre-tax value of the line/invoice (must be >= 0).
        Accepts Decimal, int, float, or numeric string.
    gst_rate_percent:
        Applicable GST rate as a percentage (e.g. 18 for 18%).
        Must be one of the valid Indian GST slabs.
    supplier_state:
        Registered state of the supplying business (e.g. "Maharashtra").
        Compared case-insensitively against customer_state.
    customer_state:
        State of the customer (e.g. "Karnataka").

    Returns
    -------
    GSTResult
        Fully populated, immutable result object.

    Raises
    ------
    GSTValidationError
        On invalid inputs (negative amounts, bad rate, missing states).
    """
    # ── 1. Coerce to Decimal ──────────────────────────────────────────────────
    amt  = _to_decimal(taxable_amount,  "taxable_amount")
    rate = _to_decimal(gst_rate_percent, "gst_rate_percent")

    # ── 2. Validate ───────────────────────────────────────────────────────────
    if amt < _ZERO:
        raise GSTValidationError(
            f"taxable_amount cannot be negative; got {amt}."
        )
    if rate < _ZERO:
        raise GSTValidationError(
            f"gst_rate_percent cannot be negative; got {rate}."
        )
    if rate not in VALID_GST_RATES:
        raise GSTValidationError(
            f"gst_rate_percent {rate} is not a valid Indian GST slab.  "
            f"Allowed values: {sorted(float(r) for r in VALID_GST_RATES)}."
        )

    sup = _normalise_state(supplier_state, "supplier_state")
    cus = _normalise_state(customer_state, "customer_state")

    # ── 3. Round taxable amount to 2 dp ──────────────────────────────────────
    taxable = _round2(amt)

    # ── 4. Compute total GST (line-level, ROUND_HALF_UP) ─────────────────────
    total_gst = _round2(taxable * rate / Decimal("100"))

    # ── 5. Split into CGST/SGST/IGST ─────────────────────────────────────────
    if sup.lower() == cus.lower():                # intra-state
        tax_type = "intra_state"
        cgst = _round2(total_gst / Decimal("2"))
        sgst = total_gst - cgst                   # exact complement — no re-rounding
        igst = _ZERO
    else:                                          # inter-state
        tax_type = "inter_state"
        cgst = _ZERO
        sgst = _ZERO
        igst = total_gst

    # ── 6. Totals (exact by construction) ────────────────────────────────────
    total_tax   = cgst + sgst + igst              # == total_gst by design
    grand_total = taxable + total_tax

    return GSTResult(
        taxable_amount=taxable,
        gst_rate=rate,
        tax_type=tax_type,
        cgst=cgst,
        sgst=sgst,
        igst=igst,
        total_tax=total_tax,
        grand_total=grand_total,
        supplier_state=sup,
        customer_state=cus,
    )


def calculate_line_tax(
    unit_price: Union[Decimal, int, float, str],
    quantity: Union[Decimal, int, float, str],
    gst_rate_percent: Union[Decimal, int, float, str],
    supplier_state: str,
    customer_state: str,
) -> GSTResult:
    """
    Convenience wrapper: compute subtotal from unit_price × quantity first,
    then call ``calculate_gst``.

    This is the primary entry point for invoice-line-level tax calculation
    (per TRD Section 6 ``calculate_line_tax`` contract).

    Parameters
    ----------
    unit_price:
        Price per unit (must be >= 0).
    quantity:
        Number of units (must be >= 0).
    gst_rate_percent:
        Applicable GST rate % — same validation as ``calculate_gst``.
    supplier_state / customer_state:
        Same as ``calculate_gst``.

    Returns
    -------
    GSTResult
        taxable_amount will equal round2(unit_price × quantity).
    """
    up  = _to_decimal(unit_price, "unit_price")
    qty = _to_decimal(quantity,   "quantity")

    if up < _ZERO:
        raise GSTValidationError(
            f"unit_price cannot be negative; got {up}."
        )
    if qty < _ZERO:
        raise GSTValidationError(
            f"quantity cannot be negative; got {qty}."
        )

    subtotal = _round2(up * qty)
    return calculate_gst(subtotal, gst_rate_percent, supplier_state, customer_state)


def calculate_invoice_totals(line_results: list[GSTResult]) -> dict:
    """
    Sum ``GSTResult`` objects across all invoice lines.

    Pure summation — no re-rounding of the aggregate (per TRD Section 6).
    The returned dict mirrors the invoice table columns.

    Parameters
    ----------
    line_results:
        List of ``GSTResult`` from ``calculate_gst`` / ``calculate_line_tax``.

    Returns
    -------
    dict with keys:
        subtotal, cgst_amount, sgst_amount, igst_amount,
        total_tax, total_amount
    """
    subtotal     = sum((r.taxable_amount for r in line_results), _ZERO)
    cgst_amount  = sum((r.cgst           for r in line_results), _ZERO)
    sgst_amount  = sum((r.sgst           for r in line_results), _ZERO)
    igst_amount  = sum((r.igst           for r in line_results), _ZERO)
    total_tax    = cgst_amount + sgst_amount + igst_amount
    total_amount = subtotal + total_tax

    return {
        "subtotal":     subtotal,
        "cgst_amount":  cgst_amount,
        "sgst_amount":  sgst_amount,
        "igst_amount":  igst_amount,
        "total_tax":    total_tax,
        "total_amount": total_amount,
    }
