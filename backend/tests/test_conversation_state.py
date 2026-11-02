"""
Tests for ContextBuilder and ConversationState (Phase 3)
"""

import uuid
import pytest
from app.conversation.state import ConversationState


def test_conversation_state_update_entities():
    """Test that entities merge correctly across turns."""
    state = ConversationState(
        conversation_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
    )
    
    # Turn 1: Customer name only
    state.update_entities({"customer_name": "Ramesh Traders", "line_items": []})
    assert state.extracted_entities["customer_name"] == "Ramesh Traders"
    assert len(state.extracted_entities["line_items"]) == 0
    
    # Turn 2: Provide items
    state.update_entities({"line_items": [{"item_name": "TMT Steel", "quantity": 10}]})
    assert state.extracted_entities["customer_name"] == "Ramesh Traders" # Preserved!
    assert len(state.extracted_entities["line_items"]) == 1
    
    # Turn 3: Add another item
    state.update_entities({"line_items": [{"item_name": "Cement", "quantity": 5}]})
    assert len(state.extracted_entities["line_items"]) == 2
    assert state.extracted_entities["line_items"][1]["item_name"] == "Cement"
