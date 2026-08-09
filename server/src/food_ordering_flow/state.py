"""
Shared kiosk session state manager.
"""

import uuid
from typing import Any, Dict, List, Optional
from src.food_ordering_flow.menu import format_kwd


class SessionStateManager:
    """Session state store for the food ordering kiosk."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.state: Dict[str, Any] = self._initial_state()

    def _initial_state(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_stage": "welcome",
            "active_category": "Chicken Meals",
            "cart": [],
            "current_item": {},
            "subtotal": 0.0,
            "tax": 0.0,
            "discount_amount": 0.0,
            "total": 0.0,
            "formatted_subtotal": format_kwd(0.0),
            "formatted_tax": format_kwd(0.0),
            "formatted_discount": format_kwd(0.0),
            "formatted_total": format_kwd(0.0),
            "currency": "KWD",
            "order_id": None,
            "payment_status": "pending",
        }

    def reset(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Reset session state for a new conversation."""
        if session_id:
            self.session_id = session_id
        self.state = self._initial_state()
        return self.state

    def recalculate(self) -> Dict[str, Any]:
        """Recalculate subtotal, tax, discount, and total for the current cart."""
        cart = self.state.get("cart", [])
        subtotal = sum(float(item.get("total_price", 0.0)) for item in cart)
        discount = float(self.state.get("discount_amount", 0.0))
        tax = (subtotal - discount) * 0.05 if (subtotal - discount) > 0 else 0.0
        total = max(0.0, subtotal - discount + tax)

        self.state["subtotal"] = round(subtotal, 3)
        self.state["tax"] = round(tax, 3)
        self.state["total"] = round(total, 3)
        self.state["formatted_subtotal"] = format_kwd(subtotal)
        self.state["formatted_tax"] = format_kwd(tax)
        self.state["formatted_discount"] = format_kwd(discount)
        self.state["formatted_total"] = format_kwd(total)
        return self.state


session_manager = SessionStateManager()
