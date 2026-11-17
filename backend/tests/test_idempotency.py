"""
Tests for Idempotency (Phase 4)
"""
import uuid
import pytest
from app.idempotency.store import IdempotencyStore


@pytest.mark.asyncio
async def test_idempotency_flow():
    """Verify idempotency store deduplicates requests."""
    store = IdempotencyStore()
    business_id = uuid.uuid4()
    key = "whatsapp-msg-12345"
    
    # 1. Initially nothing
    res = await store.get(key, business_id, None)
    assert res is None
    
    # 2. Mark as processing
    await store.set(key, business_id, "processing", None)
    res = await store.get(key, business_id, None)
    assert res["status"] == "processing"
    
    # 3. Mark as completed
    await store.set(key, business_id, "completed", {"invoice_id": "INV-123"})
    res = await store.get(key, business_id, None)
    assert res["status"] == "completed"
    assert res["result"]["invoice_id"] == "INV-123"
    
    # 4. Another business with the same key should not collide
    other_business = uuid.uuid4()
    res = await store.get(key, other_business, None)
    assert res is None
