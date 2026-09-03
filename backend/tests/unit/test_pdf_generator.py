from app.services.pdf_generator import generate_invoice_pdf_bytes, generate_quotation_pdf_bytes


def test_invoice_pdf_generation_returns_valid_pdf():
    inv_data = {
        "invoice_number": "INV-TEST-001",
        "created_at": "2026-09-03",
        "due_date": "2026-09-15",
        "status": "unpaid",
        "subtotal": 10000.0,
        "cgst_amount": 900.0,
        "sgst_amount": 900.0,
        "igst_amount": 0.0,
        "total_amount": 11800.0
    }
    cust_data = {
        "name": "Test Customer",
        "phone": "9876543210",
        "address": "Mumbai",
        "gstin": "27ABCDE1234F1Z5",
        "state": "Maharashtra"
    }
    lines = [
        {"item_name": "Laptop", "quantity": 1, "unit_price": 10000.0, "gst_rate_percent": 18, "line_total": 10000.0}
    ]

    pdf_bytes = generate_invoice_pdf_bytes(inv_data, cust_data, lines)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100
    assert pdf_bytes.startswith(b"%PDF")


def test_quotation_pdf_generation_returns_valid_pdf():
    q_data = {
        "quotation_number": "QTN-TEST-001",
        "created_at": "2026-09-03",
        "status": "draft",
        "subtotal": 5000.0
    }
    cust_data = {
        "name": "Test Customer 2",
        "phone": "9876543210",
        "address": "Pune",
        "gstin": "27ABCDE1234F1Z5"
    }
    lines = [
        {"item_name": "Monitor", "quantity": 1, "unit_price": 5000.0, "line_total": 5000.0}
    ]

    pdf_bytes = generate_quotation_pdf_bytes(q_data, cust_data, lines)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100
    assert pdf_bytes.startswith(b"%PDF")
