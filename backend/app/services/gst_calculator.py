"""
services/gst_calculator.py — Pure deterministic GST tax logic.

This is NEVER an LLM call. It is a stateless function that can be
imported and called with no DB or network access. Unit tests for this
module are the first tests written (Phase 2).

Rules (from TRD Section 6):
  - If business_state == customer_state: split gst_rate_percent into CGST + SGST
  - Else: full gst_rate_percent as IGST, CGST/SGST = 0
  - Rounding: ROUND_HALF_UP to 2 decimal places at LINE level
  - Line-level rounding, then sum — never round only at invoice total
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict


class LineTaxResult(TypedDict):
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total: Decimal


class InvoiceTotals(TypedDict):
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total: Decimal


_CENT = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def calculate_line_tax(
    unit_price: Decimal,
    quantity: Decimal,
    gst_rate_percent: Decimal,
    business_state: str,
    customer_state: str,
) -> LineTaxResult:
    """
    Compute tax for a single invoice/quotation line.

    Args:
        unit_price:       Price per unit (Decimal)
        quantity:         Number of units (Decimal)
        gst_rate_percent: GST rate as a percentage, e.g. Decimal("18") for 18%
        business_state:   Seller's registered state (e.g. "Maharashtra")
        customer_state:   Buyer's state (e.g. "Karnataka")

    Returns:
        LineTaxResult with subtotal, cgst, sgst, igst, total — all Decimal, rounded.

    Raises:
        ValueError: if quantity <= 0 or unit_price <= 0 (zero/negative lines are invalid)
    """
    if quantity <= Decimal("0"):
        raise ValueError(f"quantity must be > 0, got {quantity}")
    if unit_price <= Decimal("0"):
        raise ValueError(f"unit_price must be > 0, got {unit_price}")

    subtotal = _round(unit_price * quantity)
    tax_amount = _round(subtotal * gst_rate_percent / Decimal("100"))

    if business_state.strip().lower() == customer_state.strip().lower():
        # Intra-state: split equally into CGST + SGST
        # If tax_amount is odd-paisa, CGST gets the lower half, SGST gets the extra paisa
        # (deterministic: floor for CGST, remainder for SGST)
        raw_half = tax_amount / Decimal("2")
        cgst = raw_half.quantize(_CENT, rounding=ROUND_HALF_UP)
        sgst = tax_amount - cgst  # exact, no further rounding error
        igst = Decimal("0.00")
    else:
        # Inter-state: full rate as IGST
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
        igst = tax_amount

    total = subtotal + cgst + sgst + igst
    return LineTaxResult(subtotal=subtotal, cgst=cgst, sgst=sgst, igst=igst, total=total)


def calculate_invoice_totals(lines: list[LineTaxResult]) -> InvoiceTotals:
    """
    Sum calculate_line_tax results across all lines.
    Pure summation — no re-rounding of the aggregate totals.
    The input list must already have line-level rounding applied.
    """
    if not lines:
        return InvoiceTotals(
            subtotal=Decimal("0.00"),
            cgst=Decimal("0.00"),
            sgst=Decimal("0.00"),
            igst=Decimal("0.00"),
            total=Decimal("0.00"),
        )

    subtotal = sum((ln["subtotal"] for ln in lines), Decimal("0.00"))
    cgst = sum((ln["cgst"] for ln in lines), Decimal("0.00"))
    sgst = sum((ln["sgst"] for ln in lines), Decimal("0.00"))
    igst = sum((ln["igst"] for ln in lines), Decimal("0.00"))
    total = sum((ln["total"] for ln in lines), Decimal("0.00"))

    return InvoiceTotals(subtotal=subtotal, cgst=cgst, sgst=sgst, igst=igst, total=total)
