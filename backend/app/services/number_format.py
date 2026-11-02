"""
M1M (Munim.ai) — Indian number formatting for documents
=========================================================
  format_inr(4230.5)            -> "4,230.50"
  format_inr(1234567)           -> "12,34,567.00"   (lakh / crore grouping)
  format_quantity(Decimal("10.00")) -> "10"
  amount_in_words(Decimal("4230.50"))
      -> "Rupees Four Thousand Two Hundred Thirty and Fifty Paise Only"
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Union

Number = Union[Decimal, int, float, str]

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
         "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _to_paise(value: Number) -> tuple[bool, int, int]:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negative = amount < 0
    paise_total = int(abs(amount) * 100)
    return negative, paise_total // 100, paise_total % 100


def _group_indian(digits: str) -> str:
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    pairs = []
    while len(head) > 2:
        pairs.insert(0, head[-2:])
        head = head[:-2]
    if head:
        pairs.insert(0, head)
    return ",".join(pairs + [tail])


def format_inr(value: Number) -> str:
    negative, rupees, paise = _to_paise(value)
    return f"{'-' if negative else ''}{_group_indian(str(rupees))}.{paise:02d}"


def format_quantity(value: Number) -> str:
    """Drop trailing zeros: 10.00 -> "10", 12.50 -> "12.5"."""
    text = format(Decimal(str(value)).normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _below_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return f"{_TENS[n // 10]} {_ONES[n % 10]}".strip()


def _below_thousand(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = [f"{_ONES[hundreds]} Hundred"] if hundreds else []
    if rest:
        parts.append(_below_hundred(rest))
    return " ".join(parts)


def _integer_in_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    for size, label in ((10_000_000, "Crore"), (100_000, "Lakh"), (1_000, "Thousand")):
        count, n = divmod(n, size)
        if count:
            # Above 99 crore, the crore count itself is spelled in Indian units.
            parts.append(f"{_integer_in_words(count) if count > 999 else _below_thousand(count)} {label}")
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def amount_in_words(value: Number) -> str:
    negative, rupees, paise = _to_paise(value)
    words = f"Rupees {_integer_in_words(rupees)}"
    if paise:
        words += f" and {_below_hundred(paise)} Paise"
    return f"{'Minus ' if negative else ''}{words} Only"
