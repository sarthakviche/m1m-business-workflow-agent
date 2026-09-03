import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_fallback_unsupported_query():
    response = client.post("/chat/message", json={"message": "random invalid query 123", "phone": "9876543210"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "fallback"
    assert data["intent"] == "unsupported_help"
    assert "Munim.ai Business Copilot" in data["reply"]


def test_chat_fallback_pdf_intent():
    response = client.post("/chat/message", json={"message": "generate invoice pdf", "phone": "9876543210"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "fallback"
    assert data["intent"] == "pdf_info"


def test_invalid_customer_uuid_format():
    response = client.get("/customers/invalid-uuid-123?phone=9876543210")
    assert response.status_code == 422
    assert "Invalid customer UUID format." in response.json()["detail"]


def test_invalid_item_uuid_format():
    response = client.get("/items/invalid-uuid-123?phone=9876543210")
    assert response.status_code == 422
    assert "Invalid item UUID format." in response.json()["detail"]


def test_invalid_invoice_uuid_format():
    response = client.get("/invoices/invalid-uuid-123?phone=9876543210")
    assert response.status_code == 422
    assert "Invalid invoice UUID format." in response.json()["detail"]


def test_invalid_quotation_uuid_format():
    response = client.get("/quotations/invalid-uuid-123?phone=9876543210")
    assert response.status_code == 422
    assert "Invalid quotation UUID format." in response.json()["detail"]
