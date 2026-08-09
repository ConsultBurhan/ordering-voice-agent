"""
Real-time Menu Sync FrameProcessor for Pipecat Voice Pipeline.

Inspects streaming LLMTextFrames in real time as spoken text flows to TTS,
matching mentioned categories or menu items and broadcasting RTVI UI events to the web kiosk client.
"""

import re
from typing import Optional, Set

from config.logger import get_logger
from pipecat.frames.frames import (
    Frame,
    LLMTextFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from src.food_ordering_flow.menu import CATEGORIES, MENU_ITEMS

logger = get_logger(__name__)


# Category keyword mappings
CATEGORY_KEYWORDS = {
    "Chicken Meals": ["chicken meal", "chicken meals", "chicken burger", "chicken fillet", "chicken royale"],
    "Sides & Salads": ["side", "sides", "salad", "salads", "fries", "tenders", "mozzarella", "sticks"],
    "Desserts & Drinks": ["drink", "drinks", "beverage", "dessert", "desserts", "mojito", "coca cola", "soda"],
}


class MenuSyncProcessor(FrameProcessor):
    """
    Inline pipeline frame observer injected between LLM and TTS.
    Analyzes spoken text in real time to synchronize kiosk UI navigation with voice output.
    """

    def __init__(self, rtvi=None, flow_manager=None, worker=None, **kwargs):
        super().__init__(**kwargs)
        self.rtvi = rtvi
        self.flow_manager = flow_manager
        self.worker = worker
        self._turn_text_buffer = ""
        self._matched_in_turn: Set[str] = set()

    @property
    def state(self) -> dict:
        if self.worker and hasattr(self.worker, "state"):
            return self.worker.state
        if self.flow_manager and hasattr(self.flow_manager, "state"):
            return self.flow_manager.state
        from src.food_ordering_flow.state import session_manager
        return session_manager.state

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Reset turn cache when user speaks
        if isinstance(frame, UserStoppedSpeakingFrame):
            self._turn_text_buffer = ""
            self._matched_in_turn.clear()

        elif isinstance(frame, LLMTextFrame):
            text = frame.text or ""
            self._turn_text_buffer += " " + text.lower()
            await self._evaluate_text_buffer()

        await self.push_frame(frame, direction)

    async def _evaluate_text_buffer(self) -> None:
        """Evaluate accumulated spoken text for product items and category matches."""
        current_text = self._turn_text_buffer

        # 1. Product Item Matching (High Priority)
        for item in MENU_ITEMS:
            item_name = item["name"]
            item_key = f"item:{item_name}"
            if item_key in self._matched_in_turn:
                continue

            # Match product full name or distinctive keywords
            name_lower = item_name.lower()
            keywords = [name_lower]
            if "spicy" in name_lower and "fillet" in name_lower:
                keywords.append("spicy crispy")
            elif "royale" in name_lower:
                keywords.append("royale")
            elif "chicken fries" in name_lower:
                keywords.append("chicken fries")
            elif "tenders" in name_lower:
                keywords.append("tenders")
            elif "mozarella" in name_lower or "mozzarella" in name_lower:
                keywords.append("mozzarella")
            elif "mojito" in name_lower:
                keywords.append("mojito")

            if any(kw in current_text for kw in keywords):
                self._matched_in_turn.add(item_key)
                logger.info(f"⚡ [MenuSyncProcessor] Live Spoken Product Match: '{item_name}'")

                self.state["active_category"] = item["category"]

                await self._broadcast_rtvi({
                    "type": "product_detail",
                    "category": item["category"],
                    "item": item,
                    "state": self.state,
                })
                return

        # 2. Category Tab Matching
        for cat in CATEGORIES:
            cat_name = cat["name"]
            cat_key = f"category:{cat_name}"
            if cat_key in self._matched_in_turn:
                continue

            keywords = CATEGORY_KEYWORDS.get(cat_name, [cat_name.lower()])
            if any(kw in current_text for kw in keywords):
                self._matched_in_turn.add(cat_key)
                logger.info(f"⚡ [MenuSyncProcessor] Live Spoken Category Match: '{cat_name}'")

                self.state["active_category"] = cat_name

                await self._broadcast_rtvi({
                    "type": "menu_display",
                    "category": cat_name,
                    "state": self.state,
                })
                return

    async def _broadcast_rtvi(self, payload: dict) -> None:
        """Send RTVI server message to web kiosk client."""
        try:
            if self.rtvi:
                await self.rtvi.send_server_message(payload)
            elif self.worker and hasattr(self.worker, "rtvi") and self.worker.rtvi:
                await self.worker.rtvi.send_server_message(payload)
        except Exception as e:
            logger.warning(f"MenuSyncProcessor RTVI broadcast error: {e}")
