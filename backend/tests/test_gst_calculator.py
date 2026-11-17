"""
M1M Sprint 1 Step 3 — GST Calculator Unit Tests
=================================================

All tests are pure unit tests — no database, no Gemini, no network.

Coverage matrix (matches Sprint 1 Step 3 requirements + TRD Section 6):

  A.  Intra-state 18%  — CGST + SGST split, IGST = 0
  B.  Inter-state 18%  — IGST only, CGST = SGST = 0
  C.  Intra-state 5%
  D.  Inter-state 12%
  E.  Fractional-paise rounding (odd-paise split determinism)
  F.  Zero taxable amount
  G.  Invalid negative taxable amount
  H.  Invalid negative GST rate
  I.  Missing / empty states
  J.  total_tax == cgst + sgst + igst  (invariant, all cases)
  K.  grand_total == taxable_amount + total_tax  (invariant, all cases)
  L.  Zero GST rate (0%)
  M.  GST rate 0.1% (lowest non-zero slab)
  N.  GST rate 28%  (highest slab)
  O.  Invalid GST rate (not a recognised Indian slab)
  P.  Case-insensitive state comparison
  Q.  Whitespace-stripped state comparison
  R.  calculate_line_tax — unit_price × quantity → subtotal → GST
  S.  calculate_line_tax — negative unit_price rejected
  T.  calculate_line_tax — negative quantity rejected
  U.  calculate_invoice_totals — multi-line summation
  V.  Numeric string / int / float inputs coerced correctly

Run from backend/ directory:
  pytest tests/test_gst_calculator.py -v
"""

import pytest
from decimal import Decimal

from app.services.gst_calculator import (
    GSTResult,
    GSTValidationError,
    calculate_gst,
    calculate_invoice_totals,
    calculate_line_tax,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def D(s) -> Decimal:
    """Shorthand for Decimal conversion in assertions."""
    return Decimal(str(s))


def _assert_invariants(result: GSTResult) -> None:
    """
    J + K: Assert the two accounting identities that must ALWAYS hold.
    Called after every successful calculation.
    """
    assert result.total_tax == result.cgst + result.sgst + result.igst, (
        f"total_tax ({result.total_tax}) != cgst+sgst+igst "
        f"({result.cgst}+{result.sgst}+{result.igst})"
    )
    assert result.grand_total == result.taxable_amount + result.total_tax, (
        f"grand_total ({result.grand_total}) != "
        f"taxable_amount ({result.taxable_amount}) + total_tax ({result.total_tax})"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# A. Intra-state 18%
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntraState18:
    """
    Case A: Same state, 18% GST.
    taxable = 10000, supplier = Maharashtra, customer = Maharashtra
    Expected: CGST = 900, SGST = 900, IGST = 0, total_tax = 1800, grand = 11800
    """
    TAXABLE  = D("10000.00")
    RATE     = D("18")
    SUPPLIER = "Maharashtra"
    CUSTOMER = "Maharashtra"

    def setup_method(self):
        self.result = calculate_gst(
            self.TAXABLE, self.RATE, self.SUPPLIER, self.CUSTOMER
        )

    def test_tax_type(self):
        assert self.result.tax_type == "intra_state"

    def test_cgst(self):
        assert self.result.cgst == D("900.00")

    def test_sgst(self):
        assert self.result.sgst == D("900.00")

    def test_igst_is_zero(self):
        assert self.result.igst == D("0.00")

    def test_total_tax(self):
        assert self.result.total_tax == D("1800.00")

    def test_grand_total(self):
        assert self.result.grand_total == D("11800.00")

    def test_invariants(self):
        _assert_invariants(self.result)


# ═══════════════════════════════════════════════════════════════════════════════
# B. Inter-state 18%
# ═══════════════════════════════════════════════════════════════════════════════

class TestInterState18:
    """
    Case B: Different states, 18% GST.
    taxable = 10000, supplier = Maharashtra, customer = Karnataka
    Expected: CGST = 0, SGST = 0, IGST = 1800, total_tax = 1800, grand = 11800
    """
    TAXABLE  = D("10000.00")
    RATE     = D("18")
    SUPPLIER = "Maharashtra"
    CUSTOMER = "Karnataka"

    def setup_method(self):
        self.result = calculate_gst(
            self.TAXABLE, self.RATE, self.SUPPLIER, self.CUSTOMER
        )

    def test_tax_type(self):
        assert self.result.tax_type == "inter_state"

    def test_cgst_is_zero(self):
        assert self.result.cgst == D("0.00")

    def test_sgst_is_zero(self):
        assert self.result.sgst == D("0.00")

    def test_igst(self):
        assert self.result.igst == D("1800.00")

    def test_total_tax(self):
        assert self.result.total_tax == D("1800.00")

    def test_grand_total(self):
        assert self.result.grand_total == D("11800.00")

    def test_invariants(self):
        _assert_invariants(self.result)


# ═══════════════════════════════════════════════════════════════════════════════
# C. Intra-state 5%
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntraState5:
    """
    Case C: Same state, 5% GST.
    taxable = 5000, supplier = Gujarat, customer = Gujarat
    total GST = 5000 * 5% = 250 → CGST = 125, SGST = 125
    """
    def setup_method(self):
        self.result = calculate_gst(D("5000.00"), D("5"), "Gujarat", "Gujarat")

    def test_tax_type(self):
        assert self.result.tax_type == "intra_state"

    def test_cgst(self):
        assert self.result.cgst == D("125.00")

    def test_sgst(self):
        assert self.result.sgst == D("125.00")

    def test_igst_is_zero(self):
        assert self.result.igst == D("0.00")

    def test_total_tax(self):
        assert self.result.total_tax == D("250.00")

    def test_grand_total(self):
        assert self.result.grand_total == D("5250.00")

    def test_invariants(self):
        _assert_invariants(self.result)


# ═══════════════════════════════════════════════════════════════════════════════
# D. Inter-state 12%
# ═══════════════════════════════════════════════════════════════════════════════

class TestInterState12:
    """
    Case D: Different states, 12% GST.
    taxable = 8000, supplier = Tamil Nadu, customer = Rajasthan
    IGST = 8000 * 12% = 960
    """
    def setup_method(self):
        self.result = calculate_gst(D("8000.00"), D("12"), "Tamil Nadu", "Rajasthan")

    def test_tax_type(self):
        assert self.result.tax_type == "inter_state"

    def test_cgst_is_zero(self):
        assert self.result.cgst == D("0.00")

    def test_sgst_is_zero(self):
        assert self.result.sgst == D("0.00")

    def test_igst(self):
        assert self.result.igst == D("960.00")

    def test_total_tax(self):
        assert self.result.total_tax == D("960.00")

    def test_grand_total(self):
        assert self.result.grand_total == D("8960.00")

    def test_invariants(self):
        _assert_invariants(self.result)


# ═══════════════════════════════════════════════════════════════════════════════
# E. Fractional-paise rounding — odd-paise intra-state split
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoundingOddPaise:
    """
    Case E: Taxable amount that produces an odd total_gst (cannot split evenly).

    taxable = 100.00, rate = 3%
    total_gst = 100.00 * 3 / 100 = 3.00  → even split: CGST = SGST = 1.50  ✓

    Tricky case — use an amount where total_gst has fractional paise:
    taxable = 100.01, rate = 3%
    raw gst = 3.0003 → ROUND_HALF_UP → 3.00 → even split again

    The real fractional-paise case:
    taxable = 166.67, rate = 3%
    raw gst = 166.67 * 0.03 = 5.0001 → ROUND_HALF_UP → 5.00 → CGST=2.50, SGST=2.50

    Genuine odd-paise:
    taxable = 333.33, rate = 3%
    raw gst = 333.33 * 0.03 = 9.9999 → ROUND_HALF_UP → 10.00 → CGST=5.00, SGST=5.00

    To force odd-paise total_gst we need tax = X.005 exactly (rounds up to X.01):
    taxable = 1 / 0.18 * 0.005... complex.  Use a known case:
    taxable = 83.33, rate = 12%
    raw gst = 83.33 * 0.12 = 9.9996 → rounds to 10.00 → even

    Simplest guaranteed odd-total: rate 1%, taxable 1.00:
    total_gst = 0.01 → CGST = round(0.005) = 0.01 ROUND_HALF_UP → 0.01, SGST = 0.00
    """

    def test_odd_paise_split_cgst_gets_rounded_up(self):
        """
        taxable=1.00, rate=1%: total_gst = 0.01 (1 paise)
        CGST = round(0.005) = 0.01 (ROUND_HALF_UP rounds .5 up)
        SGST = 0.01 - 0.01 = 0.00
        """
        result = calculate_gst(D("1.00"), D("1"), "Delhi", "Delhi")
        assert result.total_tax == D("0.01")
        assert result.cgst      == D("0.01")
        assert result.sgst      == D("0.00")
        assert result.igst      == D("0.00")
        _assert_invariants(result)

    def test_cgst_plus_sgst_always_equals_total_gst(self):
        """
        For any intra-state calculation:
        cgst + sgst must equal total_tax (no paise lost or gained).
        """
        result = calculate_gst(D("7.00"), D("5"), "Kerala", "Kerala")
        # total_gst = 0.35, CGST = round(0.175) = 0.18, SGST = 0.35 - 0.18 = 0.17
        assert result.cgst + result.sgst == result.total_tax
        _assert_invariants(result)

    def test_half_paise_rounds_cgst_up(self):
        """
        taxable=7.00, rate=5%: total_gst = 0.35
        CGST = round(0.175) = 0.18  (ROUND_HALF_UP)
        SGST = 0.35 - 0.18  = 0.17  (exact complement — no re-rounding)
        grand = 7.00 + 0.35 = 7.35
        """
        result = calculate_gst(D("7.00"), D("5"), "Kerala", "Kerala")
        assert result.cgst == D("0.18")
        assert result.sgst == D("0.17")
        assert result.total_tax == D("0.35")
        assert result.grand_total == D("7.35")
        _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# F. Zero taxable amount
# ═══════════════════════════════════════════════════════════════════════════════

class TestZeroAmount:
    """Case F: zero taxable amount is allowed (free/gifted line)."""

    def test_zero_intra_state(self):
        result = calculate_gst(D("0.00"), D("18"), "Maharashtra", "Maharashtra")
        assert result.taxable_amount == D("0.00")
        assert result.total_tax      == D("0.00")
        assert result.grand_total    == D("0.00")
        assert result.cgst           == D("0.00")
        assert result.sgst           == D("0.00")
        _assert_invariants(result)

    def test_zero_inter_state(self):
        result = calculate_gst(D("0.00"), D("12"), "Goa", "Uttarakhand")
        assert result.igst        == D("0.00")
        assert result.grand_total == D("0.00")
        _assert_invariants(result)

    def test_zero_integer_input(self):
        result = calculate_gst(0, D("18"), "Maharashtra", "Maharashtra")
        assert result.total_tax == D("0.00")
        _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# G. Negative taxable amount → error
# ═══════════════════════════════════════════════════════════════════════════════

class TestNegativeAmount:
    """Case G: negative taxable_amount must raise GSTValidationError."""

    def test_negative_amount_raises(self):
        with pytest.raises(GSTValidationError, match="taxable_amount cannot be negative"):
            calculate_gst(D("-1.00"), D("18"), "Maharashtra", "Maharashtra")

    def test_negative_amount_minus_100(self):
        with pytest.raises(GSTValidationError):
            calculate_gst(-100, D("18"), "Maharashtra", "Karnataka")

    def test_negative_string_input_raises(self):
        with pytest.raises(GSTValidationError):
            calculate_gst("-500.00", D("18"), "Delhi", "Delhi")


# ═══════════════════════════════════════════════════════════════════════════════
# H. Negative GST rate → error
# ═══════════════════════════════════════════════════════════════════════════════

class TestNegativeRate:
    """Case H: negative gst_rate_percent must raise GSTValidationError."""

    def test_negative_rate_raises(self):
        with pytest.raises(GSTValidationError, match="gst_rate_percent cannot be negative"):
            calculate_gst(D("1000.00"), D("-5"), "Maharashtra", "Maharashtra")

    def test_minus_18_raises(self):
        with pytest.raises(GSTValidationError):
            calculate_gst(1000, -18, "Kerala", "Kerala")


# ═══════════════════════════════════════════════════════════════════════════════
# I. Missing / empty states → error
# ═══════════════════════════════════════════════════════════════════════════════

class TestMissingStates:
    """Case I: blank or whitespace-only states must raise GSTValidationError."""

    def test_empty_supplier_state_raises(self):
        with pytest.raises(GSTValidationError, match="supplier_state"):
            calculate_gst(D("1000.00"), D("18"), "", "Karnataka")

    def test_whitespace_supplier_state_raises(self):
        with pytest.raises(GSTValidationError, match="supplier_state"):
            calculate_gst(D("1000.00"), D("18"), "   ", "Karnataka")

    def test_empty_customer_state_raises(self):
        with pytest.raises(GSTValidationError, match="customer_state"):
            calculate_gst(D("1000.00"), D("18"), "Maharashtra", "")

    def test_whitespace_customer_state_raises(self):
        with pytest.raises(GSTValidationError, match="customer_state"):
            calculate_gst(D("1000.00"), D("18"), "Maharashtra", "\t")

    def test_both_empty_raises(self):
        with pytest.raises(GSTValidationError):
            calculate_gst(D("500.00"), D("5"), "", "")


# ═══════════════════════════════════════════════════════════════════════════════
# J + K.  Accounting invariants (parameterised)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("taxable,rate,sup,cus", [
    ("10000.00", "18", "Maharashtra", "Maharashtra"),
    ("10000.00", "18", "Maharashtra", "Karnataka"),
    ("5000.00",  "5",  "Gujarat",     "Gujarat"),
    ("8000.00",  "12", "Tamil Nadu",  "Rajasthan"),
    ("7.00",     "5",  "Kerala",      "Kerala"),
    ("1.00",     "1",  "Delhi",       "Delhi"),
    ("0.00",     "18", "Goa",         "Goa"),
    ("999999.99","28", "UP",          "Bihar"),
])
def test_invariants_all_cases(taxable, rate, sup, cus):
    """J + K: total_tax == sum of components, grand_total == taxable + tax."""
    result = calculate_gst(D(taxable), D(rate), sup, cus)
    _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# L. Zero GST rate (0%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestZeroRate:
    """Case L: 0% is a valid slab (essential commodities)."""

    def test_zero_rate_intra(self):
        result = calculate_gst(D("5000.00"), D("0"), "Maharashtra", "Maharashtra")
        assert result.total_tax == D("0.00")
        assert result.grand_total == D("5000.00")
        _assert_invariants(result)

    def test_zero_rate_inter(self):
        result = calculate_gst(D("5000.00"), D("0"), "Maharashtra", "Gujarat")
        assert result.igst == D("0.00")
        _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# M. Lowest non-zero slab: 0.1%
# ═══════════════════════════════════════════════════════════════════════════════

def test_rate_0_1_percent():
    """Case M: 0.1% is a valid slab (certain rough diamonds/precious stones)."""
    result = calculate_gst(D("10000.00"), D("0.1"), "Maharashtra", "Gujarat")
    assert result.igst == D("10.00")
    _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# N. Highest slab: 28%
# ═══════════════════════════════════════════════════════════════════════════════

def test_rate_28_percent():
    """Case N: 28% (luxury/demerit goods)."""
    result = calculate_gst(D("1000.00"), D("28"), "Delhi", "Delhi")
    assert result.total_tax == D("280.00")
    assert result.cgst == D("140.00")
    assert result.sgst == D("140.00")
    _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# O. Invalid GST rate not in recognised slabs
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("bad_rate", ["10", "15", "20", "25", "2", "4", "9", "99"])
def test_invalid_rate_rejected(bad_rate):
    """Case O: rates not in Indian GST slab list must raise GSTValidationError."""
    with pytest.raises(GSTValidationError, match="not a valid Indian GST slab"):
        calculate_gst(D("1000.00"), D(bad_rate), "Maharashtra", "Maharashtra")


# ═══════════════════════════════════════════════════════════════════════════════
# P. Case-insensitive state comparison
# ═══════════════════════════════════════════════════════════════════════════════

def test_state_comparison_case_insensitive_intra():
    """Case P: 'MAHARASHTRA' == 'maharashtra' → intra-state."""
    result = calculate_gst(D("1000.00"), D("18"), "MAHARASHTRA", "maharashtra")
    assert result.tax_type == "intra_state"
    assert result.igst == D("0.00")
    _assert_invariants(result)


def test_state_comparison_case_insensitive_inter():
    """Case P: 'Maharashtra' != 'karnataka' → inter-state even with mixed case."""
    result = calculate_gst(D("1000.00"), D("18"), "Maharashtra", "KARNATAKA")
    assert result.tax_type == "inter_state"
    assert result.cgst == D("0.00")
    _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# Q. Whitespace-stripped state names
# ═══════════════════════════════════════════════════════════════════════════════

def test_state_whitespace_stripped_intra():
    """Case Q: leading/trailing spaces in state names are ignored."""
    result = calculate_gst(D("1000.00"), D("18"), "  Maharashtra  ", " Maharashtra")
    assert result.tax_type == "intra_state"
    assert result.supplier_state == "Maharashtra"
    assert result.customer_state == "Maharashtra"
    _assert_invariants(result)


def test_state_whitespace_stripped_inter():
    """Case Q: states with whitespace stripped still classify correctly."""
    result = calculate_gst(D("1000.00"), D("18"), " Gujarat ", " Kerala ")
    assert result.tax_type == "inter_state"
    _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# R.  calculate_line_tax — unit_price × quantity → GST
# ═══════════════════════════════════════════════════════════════════════════════

class TestCalculateLineTax:
    """Case R: wrapper that computes subtotal from unit_price × quantity."""

    def test_basic_line_intra(self):
        """200 units @ 50 each = 10000, 18% intra → CGST=900, SGST=900."""
        result = calculate_line_tax(D("50.00"), D("200"), D("18"), "Maharashtra", "Maharashtra")
        assert result.taxable_amount == D("10000.00")
        assert result.cgst == D("900.00")
        assert result.sgst == D("900.00")
        assert result.igst == D("0.00")
        _assert_invariants(result)

    def test_basic_line_inter(self):
        """10 units @ 1000 each = 10000, 18% inter → IGST=1800."""
        result = calculate_line_tax(D("1000.00"), D("10"), D("18"), "Maharashtra", "Karnataka")
        assert result.taxable_amount == D("10000.00")
        assert result.igst == D("1800.00")
        _assert_invariants(result)

    def test_fractional_quantity(self):
        """2.5 kg @ 400.00/kg = 1000.00, 5% intra → CGST=25, SGST=25."""
        result = calculate_line_tax(D("400.00"), D("2.5"), D("5"), "Gujarat", "Gujarat")
        assert result.taxable_amount == D("1000.00")
        assert result.cgst == D("25.00")
        assert result.sgst == D("25.00")
        _assert_invariants(result)

    def test_fractional_price(self):
        """Integer arithmetic: 3 units @ 33.33 = 99.99, 18%."""
        result = calculate_line_tax(D("33.33"), D("3"), D("18"), "Delhi", "Delhi")
        assert result.taxable_amount == D("99.99")
        expected_tax = (D("99.99") * D("18") / D("100")).quantize(
            D("0.01"), rounding=__import__("decimal").ROUND_HALF_UP
        )
        assert result.total_tax == expected_tax
        _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# S + T. calculate_line_tax — negative unit_price / quantity rejected
# ═══════════════════════════════════════════════════════════════════════════════

def test_line_tax_negative_unit_price_raises():
    """Case S: negative unit_price must raise GSTValidationError."""
    with pytest.raises(GSTValidationError, match="unit_price cannot be negative"):
        calculate_line_tax(D("-50.00"), D("10"), D("18"), "Maharashtra", "Maharashtra")


def test_line_tax_negative_quantity_raises():
    """Case T: negative quantity must raise GSTValidationError."""
    with pytest.raises(GSTValidationError, match="quantity cannot be negative"):
        calculate_line_tax(D("50.00"), D("-10"), D("18"), "Maharashtra", "Maharashtra")


# ═══════════════════════════════════════════════════════════════════════════════
# U. calculate_invoice_totals — multi-line summation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCalculateInvoiceTotals:
    """Case U: summing multiple lines, mixed intra/inter handled correctly."""

    def test_two_intra_state_lines(self):
        """
        Line 1: 10000 @ 18% intra → CGST=900, SGST=900
        Line 2:  5000 @ 5%  intra → CGST=125, SGST=125
        Totals: subtotal=15000, cgst=1025, sgst=1025, igst=0,
                total_tax=2050, total_amount=17050
        """
        line1 = calculate_gst(D("10000.00"), D("18"), "Maharashtra", "Maharashtra")
        line2 = calculate_gst(D("5000.00"),  D("5"),  "Maharashtra", "Maharashtra")
        totals = calculate_invoice_totals([line1, line2])
        assert totals["subtotal"]     == D("15000.00")
        assert totals["cgst_amount"]  == D("1025.00")
        assert totals["sgst_amount"]  == D("1025.00")
        assert totals["igst_amount"]  == D("0.00")
        assert totals["total_tax"]    == D("2050.00")
        assert totals["total_amount"] == D("17050.00")

    def test_two_inter_state_lines(self):
        """
        Line 1: 10000 @ 18% inter → IGST=1800
        Line 2:  8000 @ 12% inter → IGST=960
        Totals: subtotal=18000, igst=2760, total_amount=20760
        """
        line1 = calculate_gst(D("10000.00"), D("18"), "Maharashtra", "Karnataka")
        line2 = calculate_gst(D("8000.00"),  D("12"), "Maharashtra", "Karnataka")
        totals = calculate_invoice_totals([line1, line2])
        assert totals["subtotal"]     == D("18000.00")
        assert totals["igst_amount"]  == D("2760.00")
        assert totals["cgst_amount"]  == D("0.00")
        assert totals["sgst_amount"]  == D("0.00")
        assert totals["total_amount"] == D("20760.00")

    def test_single_line_totals(self):
        """Single-line invoice: totals should match the single GSTResult."""
        line = calculate_gst(D("10000.00"), D("18"), "Maharashtra", "Maharashtra")
        totals = calculate_invoice_totals([line])
        assert totals["subtotal"]     == line.taxable_amount
        assert totals["cgst_amount"]  == line.cgst
        assert totals["sgst_amount"]  == line.sgst
        assert totals["igst_amount"]  == line.igst
        assert totals["total_tax"]    == line.total_tax
        assert totals["total_amount"] == line.grand_total

    def test_empty_line_list_returns_zeros(self):
        """Empty invoice lines → all zeros."""
        totals = calculate_invoice_totals([])
        assert totals["subtotal"]     == D("0.00") or totals["subtotal"] == D("0")
        assert totals["total_amount"] == totals["subtotal"]

    def test_totals_accounting_identity(self):
        """total_amount == subtotal + total_tax for multi-line."""
        lines = [
            calculate_gst(D("10000.00"), D("18"), "Maharashtra", "Maharashtra"),
            calculate_gst(D("5000.00"),  D("5"),  "Maharashtra", "Maharashtra"),
            calculate_gst(D("2000.00"),  D("12"), "Maharashtra", "Maharashtra"),
        ]
        totals = calculate_invoice_totals(lines)
        assert totals["total_amount"] == totals["subtotal"] + totals["total_tax"]
        assert totals["total_tax"] == (
            totals["cgst_amount"] + totals["sgst_amount"] + totals["igst_amount"]
        )


# ═══════════════════════════════════════════════════════════════════════════════
# V. Numeric string / int / float inputs coerced correctly
# ═══════════════════════════════════════════════════════════════════════════════

def test_string_input_coercion():
    """Case V: string "10000" and string "18" should work identically to Decimal."""
    result = calculate_gst("10000", "18", "Maharashtra", "Maharashtra")
    assert result.taxable_amount == D("10000.00")
    assert result.total_tax      == D("1800.00")
    _assert_invariants(result)


def test_integer_input_coercion():
    """Case V: plain Python int inputs."""
    result = calculate_gst(10000, 18, "Maharashtra", "Maharashtra")
    assert result.total_tax == D("1800.00")
    _assert_invariants(result)


def test_float_input_coercion():
    """Case V: float inputs (converted via str→Decimal to avoid binary FP errors)."""
    result = calculate_gst(10000.0, 18.0, "Maharashtra", "Maharashtra")
    assert result.total_tax == D("1800.00")
    _assert_invariants(result)


# ═══════════════════════════════════════════════════════════════════════════════
# Additional edge cases from TRD Section 6 notes
# ═══════════════════════════════════════════════════════════════════════════════

def test_gst_result_is_immutable():
    """GSTResult is a frozen dataclass — attempts to mutate must raise."""
    result = calculate_gst(D("1000.00"), D("18"), "MH", "MH")
    with pytest.raises((AttributeError, TypeError)):
        result.cgst = D("999.00")  # type: ignore[misc]


def test_no_gemini_call():
    """
    Sentinel test: the gst_calculator module must NOT import google.genai,
    openai, anthropic, requests, httpx, or any HTTP client.
    This guards against accidental LLM dependency being introduced.
    """
    import importlib
    import sys

    # Force a fresh import check on the module's import graph
    import app.services.gst_calculator as mod
    source_file = mod.__file__

    with open(source_file, encoding="utf-8") as f:
        source = f.read()

    forbidden_imports = ["google.genai", "openai", "anthropic", "requests", "httpx", "aiohttp"]
    for forbidden in forbidden_imports:
        assert forbidden not in source, (
            f"gst_calculator.py must not import '{forbidden}' — "
            "GST math must be a pure deterministic function with no external calls."
        )


def test_result_fields_present():
    """GSTResult exposes all required fields per Sprint 1 Step 3 spec."""
    result = calculate_gst(D("10000.00"), D("18"), "Maharashtra", "Maharashtra")
    required_fields = [
        "taxable_amount", "gst_rate", "tax_type",
        "cgst", "sgst", "igst",
        "total_tax", "grand_total",
        "supplier_state", "customer_state",
    ]
    for field in required_fields:
        assert hasattr(result, field), f"GSTResult is missing field: {field}"
