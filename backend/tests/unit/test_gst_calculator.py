from decimal import Decimal
from app.services.gst_calculator import calculate_line_tax, calculate_invoice_totals


def test_intra_state_gst_calculation():
    res = calculate_line_tax(
        unit_price=Decimal("1000.00"),
        quantity=Decimal("2"),
        gst_rate_percent=Decimal("18.00"),
        business_state="Maharashtra",
        customer_state="Maharashtra"
    )
    assert res["subtotal"] == Decimal("2000.00")
    assert res["cgst"] == Decimal("180.00")
    assert res["sgst"] == Decimal("180.00")
    assert res["igst"] == Decimal("0.00")
    assert res["total"] == Decimal("2360.00")


def test_inter_state_gst_calculation():
    res = calculate_line_tax(
        unit_price=Decimal("1000.00"),
        quantity=Decimal("2"),
        gst_rate_percent=Decimal("18.00"),
        business_state="Maharashtra",
        customer_state="Karnataka"
    )
    assert res["subtotal"] == Decimal("2000.00")
    assert res["cgst"] == Decimal("0.00")
    assert res["sgst"] == Decimal("0.00")
    assert res["igst"] == Decimal("360.00")
    assert res["total"] == Decimal("2360.00")


def test_invoice_totals_aggregation():
    l1 = calculate_line_tax(Decimal("500.00"), Decimal("1"), Decimal("18.00"), "Maharashtra", "Maharashtra")
    l2 = calculate_line_tax(Decimal("1000.00"), Decimal("2"), Decimal("18.00"), "Maharashtra", "Maharashtra")
    
    totals = calculate_invoice_totals([l1, l2])
    assert totals["subtotal"] == Decimal("2500.00")
    assert totals["cgst"] == Decimal("225.00")
    assert totals["sgst"] == Decimal("225.00")
    assert totals["total"] == Decimal("2950.00")
