"""
Global tools — available at every node in the kiosk flow.

All functions return (result, None) so they NEVER cause a node transition.
They answer informational questions and then hand control back to current node.
"""

from typing import TypedDict

from config.logger import get_logger
from pipecat.flows import FlowManager
from src.food_ordering_flow.menu import (
    CUSTOMIZATIONS,
    MENU_ITEMS,
    format_kwd,
    get_valid_customizations,
    resolve_product,
    search_products,
)
from src.food_ordering_flow.utils import send_rtvi_message

logger = get_logger(__name__)


# ── Result Types ─────────────────────────────────────────────────────────────


class MenuSearchResult(TypedDict):
    items: list
    query: str


class ItemDetailsResult(TypedDict):
    item_id: str
    name: str
    price: str
    description: str
    category: str
    available_customizations: list
    allergens: list
    calories: int


class RecommendationsResult(TypedDict):
    items: list


class RestaurantInfoResult(TypedDict):
    name: str
    address: str
    phone: str


class StoreHoursResult(TypedDict):
    hours: dict
    currently_open: bool


class AllergenInfoResult(TypedDict):
    item_name: str
    allergens: list
    contains_gluten: bool
    contains_dairy: bool
    contains_nuts: bool
    is_vegetarian: bool
    is_vegan: bool


class CancelResult(TypedDict):
    message: str


class SupportResult(TypedDict):
    message: str


# ── Tool Functions ────────────────────────────────────────────────────────────


async def search_menu(
    flow_manager: FlowManager, query: str
) -> tuple[MenuSearchResult, None]:
    """Search the menu dynamically for items matching the customer's query."""
    current_stage = flow_manager.state.get("current_stage", "welcome").upper()
    matched = search_products(query)
    formatted_items = [
        {
            "id": i["id"],
            "name": i["name"],
            "name_ar": i.get("name_ar", ""),
            "price": i["formatted_price"],
            "description": i["description"],
            "category": i["category"],
            "image_url": i["image_url"],
        }
        for i in matched
    ]
    matched_category = matched[0]["category"] if matched else None

    # Broadcast menu_display event to client UI via RTVI helper
    await send_rtvi_message(flow_manager, {
        "type": "menu_display",
        "category": matched_category,
        "query": query,
        "items": formatted_items,
        "state": flow_manager.state,
    })

    return MenuSearchResult(items=formatted_items, query=query), None


async def get_item_details(
    flow_manager: FlowManager, item_name: str
) -> tuple[ItemDetailsResult, None]:
    """Look up details for a specific item."""
    current_stage = flow_manager.state.get("current_stage", "welcome").upper()
    logger.info(f"ℹ️ [STAGE: {current_stage}] Tool: get_item_details | item='{item_name}' | State: {flow_manager.state}")
    product = resolve_product(item_name)
    if not product:
        return ItemDetailsResult(
            item_id="",
            name=item_name,
            price="KWD 0.000",
            description="Item not found on the menu.",
            category="",
            available_customizations=[],
            allergens=[],
            calories=0,
        ), None

    customizations = get_valid_customizations(product["name"])

    # Broadcast product_detail event to client UI via RTVI helper
    await send_rtvi_message(flow_manager, {
        "type": "product_detail",
        "category": product.get("category", ""),
        "item": product,
        "state": flow_manager.state,
    })

    return ItemDetailsResult(
        item_id=product["id"],
        name=product["name"],
        price=product["formatted_price"],
        description=product["description"],
        category=product["category"],
        available_customizations=customizations,
        allergens=product.get("allergens", []),
        calories=product.get("calories", 0),
    ), None


async def recommend_items(
    flow_manager: FlowManager, preference: str = "popular"
) -> tuple[RecommendationsResult, None]:
    """Recommend popular items or items based on customer preference."""
    current_stage = flow_manager.state.get("current_stage", "welcome").upper()
    logger.info(f"[STAGE: {current_stage}] Tool: recommend_items | pref='{preference}' | State: {flow_manager.state}")
    recs = [
        {"name": "Spicy Crispy Fillet Meal", "price": "KWD 2.650", "reason": "our signature spicy chicken meal"},
        {"name": "Chicken Royale Meal", "price": "KWD 2.350", "reason": "classic favorite chicken meal"},
        {"name": "Chicken Fries", "price": "KWD 1.000", "reason": "great snack side"},
    ]
    if preference:
        pref = preference.lower()
        if "side" in pref or "snack" in pref:
            recs = [
                {"name": "Chicken Fries", "price": "KWD 1.000", "reason": "famous crispy chicken fries"},
                {"name": "Mozarella Stick - 4 pieces", "price": "KWD 1.000", "reason": "gooey mozzarella sticks"},
            ]
        elif "drink" in pref or "sweet" in pref:
            recs = [
                {"name": "Classic Mojito", "price": "KWD 0.850", "reason": "crisp lime and mint soda"},
                {"name": "Blue Lagoon Mojito", "price": "KWD 0.850", "reason": "vibrant tropical twist"},
            ]
    return RecommendationsResult(items=recs), None


async def get_restaurant_info(
    flow_manager: FlowManager,
) -> tuple[RestaurantInfoResult, None]:
    """Provide general restaurant information like name, address, and phone number."""
    logger.info("[global] get_restaurant_info")
    return RestaurantInfoResult(
        name="Burger King",
        address="Unit 12, City Mall, Ground Floor",
        phone="+1-800-BURGERKING",
    ), None


async def get_store_hours(
    flow_manager: FlowManager,
) -> tuple[StoreHoursResult, None]:
    """Provide store opening hours."""
    logger.info("[global] get_store_hours")
    return StoreHoursResult(
        hours={
            "Monday–Friday": "10:00 AM – 10:00 PM",
            "Saturday": "9:00 AM – 11:00 PM",
            "Sunday": "10:00 AM – 9:00 PM",
        },
        currently_open=True,
    ), None


async def get_allergen_info(
    flow_manager: FlowManager, item_name: str
) -> tuple[AllergenInfoResult, None]:
    """Provide allergen and dietary information for a specific menu item."""
    logger.info(f"[global] get_allergen_info: item='{item_name}'")
    product = resolve_product(item_name)
    if not product:
        return AllergenInfoResult(
            item_name=item_name,
            allergens=[],
            contains_gluten=False,
            contains_dairy=False,
            contains_nuts=False,
            is_vegetarian=False,
            is_vegan=False,
        ), None

    allergens = product.get("allergens", [])
    return AllergenInfoResult(
        item_name=product["name"],
        allergens=allergens,
        contains_gluten="gluten" in allergens,
        contains_dairy="dairy" in allergens,
        contains_nuts="nuts" in allergens,
        is_vegetarian=not allergens and "chicken" not in product["name"].lower(),
        is_vegan=not allergens,
    ), None


async def cancel_order(
    flow_manager: FlowManager,
) -> tuple[CancelResult, None]:
    """Cancel the current order and clear the cart."""
    logger.info("[global] cancel_order — clearing cart and session state")
    flow_manager.state["cart"] = []
    flow_manager.state["current_item"] = {}
    flow_manager.state["subtotal"] = 0.000
    flow_manager.state["tax"] = 0.000
    flow_manager.state["discount_amount"] = 0.000
    flow_manager.state["total"] = 0.000
    flow_manager.state["formatted_subtotal"] = format_kwd(0.0)
    flow_manager.state["formatted_tax"] = format_kwd(0.0)
    flow_manager.state["formatted_discount"] = format_kwd(0.0)
    flow_manager.state["formatted_total"] = format_kwd(0.0)
    flow_manager.state["coupon_code"] = None
    flow_manager.state["payment_intent_id"] = None
    flow_manager.state["order_id"] = None
    return CancelResult(
        message="Order cancelled. Cart has been cleared."
    ), None
