"""
Shared kiosk session state for the Welcome & Browse Menu flow.
"""

from typing import TypedDict


class KioskState(TypedDict, total=False):
    """Minimal session state stored in flow_manager.state."""

    session_id: str
    current_stage: str


def initial_state(session_id: str) -> KioskState:
    """Return a fresh, clean KioskState for a new session."""
    return KioskState(
        session_id=session_id,
        current_stage="welcome",
    )


def recalculate_order_state(state: KioskState) -> KioskState:
    """Helper to maintain state cleanliness."""
    if "current_stage" not in state:
        state["current_stage"] = "welcome"
    return state
