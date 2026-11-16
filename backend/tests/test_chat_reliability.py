"""Regressions from the 16 Nov 2026 demo failure: a near-match customer looped,
"yes" re-created the last document, and the rule fallback misread replies."""

import uuid

from app.agent.graph import _ACKNOWLEDGEMENT, _answer_customer_confirmation
from app.conversation.state import ConversationState
from app.services.intent_classifier import classify_with_rules


def _pending(suggested="Patel Constructions", requested="Patel Corporation"):
    state = ConversationState(conversation_id=uuid.uuid4(), business_id=uuid.uuid4())
    state.pending_intent = "invoice"
    state.clarification_state = "confirm_customer"
    state.extracted_entities = {
        "customer_name": requested,
        "suggested_customer": suggested,
        "line_items": [{"item_name": "MS hex bolts", "quantity": 20}],
    }
    return state


def test_new_customer_reply_finishes_the_document():
    update = _answer_customer_confirmation(_pending(), "This is a new customer.")
    assert update["detected_intent"] == "invoice"
    assert update["extracted_entities"]["new_customer"] is True
    assert update["extracted_entities"]["customer_name"] == "Patel Corporation"
    assert "suggested_customer" not in update["extracted_entities"]


def test_yes_uses_the_suggested_customer():
    for reply in ("yes", "haan wahi", "Patel Constructions"):
        update = _answer_customer_confirmation(_pending(), reply)
        assert update["extracted_entities"]["customer_name"] == "Patel Constructions", reply
        assert update["extracted_entities"]["new_customer"] is False


def test_unrelated_reply_goes_back_to_normal_classification():
    assert _answer_customer_confirmation(_pending(), "price of steel rod") is None


def test_acknowledgements_are_recognised():
    for text in ("yes", "ok", "Thanks!", "theek hai", "done 👍"):
        assert _ACKNOWLEDGEMENT.match(text), text
    for text in ("yes make invoice for Ramesh", "ok 10 bolts"):
        assert not _ACKNOWLEDGEMENT.match(text), text


def test_rules_read_customer_colon_items():
    res = classify_with_rules("Need a invoice for Patel Corporation: 20 MS hex bolts.")
    assert res.intent == "invoice"
    assert res.customer_name == "Patel Corporation"
    assert [(li.item_name, li.quantity) for li in res.line_items] == [("MS hex bolts", 20.0)]


def test_rules_never_turn_a_sentence_into_an_item():
    context = "Assistant: Which items and quantities should be included for **Patel Corporation**?"
    res = classify_with_rules("This is a new customer.", context)
    assert res.line_items == []
