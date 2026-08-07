"""
Browse Menu node functions with real-time category & item display broadcasts via RTVI.
"""

from typing import TypedDict

from config.logger import get_logger
from pipecat.flows import FlowManager, NodeConfig
from src.food_ordering_flow.menu import (
    CATEGORIES,
    get_items_by_category,
    resolve_product,
)
from src.food_ordering_flow.utils import send_rtvi_message

logger = get_logger(__name__)


# ── Result Types ─────────────────────────────────────────────────────────────


class CategoriesResult(TypedDict):
    categories: list


class CategoryItemsResult(TypedDict):
    category: str
    items: list


class BrowseTransitionResult(TypedDict):
    message: str


class ProductInfoResult(TypedDict):
    name: str
    price: str
    description: str
    category: str


# ── Node Functions ────────────────────────────────────────────────────────────


async def get_categories(
    flow_manager: FlowManager,
) -> tuple[CategoriesResult, None]:
    """List all available menu categories so the customer can explore what food is available."""
    # Transmit menu categories view to client
    await send_rtvi_message(flow_manager, {
        "type": "stage_change",
        "state": flow_manager.state,
    })
    return CategoriesResult(categories=CATEGORIES), None


async def show_category_items(
    flow_manager: FlowManager, category_name: str
) -> tuple[CategoryItemsResult, None]:
    """
    Show menu items belonging to a specific category (e.g. 'Sides & Salads', 'Chicken Meals', 'Desserts & Drinks').

    Args:
        category_name (str): Category to filter and display on the frontend kiosk screen.
    """
    logger.info(f"[browse] show_category_items: '{category_name}'")
    items = get_items_by_category(category_name)
    matched_category = items[0]["category"] if items else category_name

    flow_manager.state["active_category"] = matched_category
    flow_manager.state["current_stage"] = "browse_menu"

    # Transmit category display event to update client UI
    await send_rtvi_message(flow_manager, {
        "type": "menu_display",
        "category": matched_category,
        "items": items,
        "state": flow_manager.state,
    })

    return CategoryItemsResult(category=matched_category, items=items), None


async def select_product_info(
    flow_manager: FlowManager, item_name: str
) -> tuple[ProductInfoResult, None]:
    """
    Look up details and pricing in KWD for a product while browsing and update the kiosk UI.

    Args:
        item_name (str): Product name to query.
    """
    logger.info(f"[browse] select_product_info: '{item_name}'")
    product = resolve_product(item_name)
    if not product:
        return ProductInfoResult(
            name=item_name,
            price="KWD 0.000",
            description="Item not found on the menu.",
            category="",
        ), None

    category_name = product.get("category", "")
    flow_manager.state["active_category"] = category_name
    flow_manager.state["current_stage"] = "browse_menu"

    # Broadcast real-time product detail page event to client
    await send_rtvi_message(flow_manager, {
        "type": "product_detail",
        "category": category_name,
        "item": product,
        "state": flow_manager.state,
    })

    return ProductInfoResult(
        name=product["name"],
        price=product["formatted_price"],
        description=product["description"],
        category=category_name,
    ), None


# ── Edge Functions ────────────────────────────────────────────────────────────


async def go_to_browse(
    flow_manager: FlowManager,
) -> tuple[BrowseTransitionResult, NodeConfig]:
    """
    Transition from Welcome stage to Browse Menu stage so the customer can explore the menu.
    """
    from src.food_ordering_flow.nodes import create_browse_node

    old_stage = flow_manager.state.get("current_stage", "welcome")
    flow_manager.state["current_stage"] = "browse_menu"
    new_stage = flow_manager.state["current_stage"]

    logger.info(f"🔄 [STAGE TRANSITION] {old_stage.upper()} ➔ {new_stage.upper()} | Updated State: {flow_manager.state}")

    # Send real-time stage_change message to web client via RTVI
    await send_rtvi_message(flow_manager, {
        "type": "stage_change",
        "state": flow_manager.state,
    })

    return BrowseTransitionResult(
        message="Moving to Browse Menu stage."
    ), await create_browse_node()
