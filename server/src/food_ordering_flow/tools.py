"""
Standalone function tools for the Food Ordering Agent.

Functions in this module are decorated with @tool_options for automatic schema
extraction and tool registration with OpenAILLMService via LLMContext(tools=...).
"""

import uuid
from typing import Any, Dict, List, Optional
from pipecat.adapters.schemas.direct_function import tool_options
from config.logger import get_logger
from src.food_ordering_flow.menu import (
    CATEGORIES,
    calculate_choice_extra_price,
    format_kwd,
    get_items_by_category,
    get_valid_customizations,
    resolve_product,
    search_products,
)
from src.food_ordering_flow.state import session_manager
from src.food_ordering_flow.utils import send_rtvi_message as broadcast_rtvi

logger = get_logger(__name__)


async def complete_tool_call(params, result: Any) -> Any:
    """Notify Pipecat LLM service of function tool completion via result_callback."""
    if hasattr(params, "result_callback") and callable(params.result_callback):
        try:
            await params.result_callback(result)
        except Exception as e:
            logger.warning(f"Error executing result_callback: {e}")
    return result


# ── MENU & INFORMATIONAL TOOLS ──────────────────────────────────────────────

@tool_options(cancel_on_interruption=True)
async def get_categories(params) -> dict:
    """List all available menu categories so the customer can explore what food is available."""
    session_manager.state["current_stage"] = "browse_menu"
    await broadcast_rtvi(params, {
        "type": "stage_change",
        "state": session_manager.state,
    })
    return await complete_tool_call(params, {"categories": CATEGORIES})


@tool_options(cancel_on_interruption=True)
async def show_category_items(params, category_name: str) -> dict:
    """
    Show menu items belonging to a specific category (e.g. 'Sides & Salads', 'Chicken Meals', 'Desserts & Drinks').

    Args:
        category_name: Category name to filter and display on the frontend kiosk screen.
    """
    items = get_items_by_category(category_name)
    matched_cat = items[0]["category"] if items else category_name
    session_manager.state["active_category"] = matched_cat
    session_manager.state["current_stage"] = "browse_menu"

    await broadcast_rtvi(params, {
        "type": "menu_display",
        "category": matched_cat,
        "items": items,
        "state": session_manager.state,
    })
    return await complete_tool_call(params, {"category": matched_cat, "items": items})


@tool_options(cancel_on_interruption=True)
async def search_menu(params, query: str) -> dict:
    """
    Search the menu dynamically for items matching the customer's query.

    Args:
        query: Food or beverage search query (e.g. 'spicy', 'mojito', 'fries').
    """
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
    if matched_category:
        session_manager.state["active_category"] = matched_category
    session_manager.state["current_stage"] = "browse_menu"

    await broadcast_rtvi(params, {
        "type": "menu_display",
        "category": matched_category,
        "query": query,
        "items": formatted_items,
        "state": session_manager.state,
    })
    return await complete_tool_call(params, {"query": query, "items": formatted_items})


@tool_options(cancel_on_interruption=True)
async def get_item_details(params, item_name: str) -> dict:
    """
    Look up full details, pricing in KWD, allergens, and calories for a specific product.

    Args:
        item_name: Full or partial product name.
    """
    product = resolve_product(item_name)
    if not product:
        return await complete_tool_call(params, {"name": item_name, "error": "Item not found on the menu."})

    customizations = get_valid_customizations(product["name"])
    session_manager.state["current_item"] = product
    session_manager.state["current_stage"] = "browse_menu"

    await broadcast_rtvi(params, {
        "type": "product_detail",
        "category": product.get("category", ""),
        "item": product,
        "state": session_manager.state,
    })
    res = {
        "item_id": product["id"],
        "name": product["name"],
        "price": product["formatted_price"],
        "description": product["description"],
        "category": product["category"],
        "available_customizations": customizations,
        "allergens": product.get("allergens", []),
        "calories": product.get("calories", 0),
    }
    return await complete_tool_call(params, res)


@tool_options(cancel_on_interruption=True)
async def recommend_items(params, preference: str = "popular") -> dict:
    """
    Recommend popular items or items based on customer preference.

    Args:
        preference: Preferred type of food (e.g. 'popular', 'sides', 'drinks', 'snacks').
    """
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
    return await complete_tool_call(params, {"recommendations": recs})


# ── CUSTOMIZE ITEM TOOL ─────────────────────────────────────────────────────

@tool_options(cancel_on_interruption=True)
async def customize_item(params, item_name: str) -> dict:
    """
    Show available customization options valid ONLY for the selected product.
    Displays valid sizes, meal options, add-ons, sauces, drinks, and extras.

    Args:
        item_name: Product name to customize.
    """
    product = resolve_product(item_name)
    if not product:
        return await complete_tool_call(params, {"name": item_name, "error": "Item not found on the menu."})

    valid_customizations = get_valid_customizations(product["name"])
    session_manager.state["current_item"] = product
    session_manager.state["current_stage"] = "customize_item"

    await broadcast_rtvi(params, {
        "type": "customization_display",
        "item": product,
        "customizations": valid_customizations,
        "state": session_manager.state,
    })

    res = {
        "item_name": product["name"],
        "base_price": product["formatted_price"],
        "valid_customization_groups": valid_customizations,
        "message": f"Presenting customization options for {product['name']}.",
    }
    return await complete_tool_call(params, res)


# ── CART MANAGEMENT TOOLS ───────────────────────────────────────────────────

@tool_options(cancel_on_interruption=True)
async def add_to_cart(
    params, item_name: str, quantity: int = 1, customizations: Optional[dict] = None
) -> dict:
    """
    Add a product with optional customizations and quantity to the customer's cart.

    Args:
        item_name: Name of product to add.
        quantity: Quantity of items to add (default 1).
        customizations: Optional dictionary of customization selections.
    """
    product = resolve_product(item_name)
    if not product:
        return await complete_tool_call(params, {"error": f"Item '{item_name}' was not found on the menu."})

    qty = max(1, quantity)
    custom_dict = customizations or {}
    extra_cost = 0.0

    for opt_group, choice in custom_dict.items():
        if isinstance(choice, str):
            extra_cost += calculate_choice_extra_price(product["name"], choice)
        elif isinstance(choice, list):
            for sub_c in choice:
                extra_cost += calculate_choice_extra_price(product["name"], sub_c)

    base_price = float(product["price"])
    unit_price = base_price + extra_cost
    line_total = unit_price * qty

    cart_item = {
        "item_id": product["id"],
        "name": product["name"],
        "quantity": qty,
        "unit_price": base_price,
        "extra_price": extra_cost,
        "price": unit_price,
        "line_total": line_total,
        "formatted_price": format_kwd(unit_price),
        "formatted_total": format_kwd(line_total),
        "customizations": custom_dict,
    }

    existing = next(
        (
            i for i in session_manager.state["cart"]
            if i["name"] == cart_item["name"] and i.get("customizations") == cart_item["customizations"]
        ),
        None,
    )

    if existing:
        existing["quantity"] += qty
    else:
        session_manager.state["cart"].append(cart_item)

    session_manager.recalculate()
    session_manager.state["current_stage"] = "cart"

    await broadcast_rtvi(params, {
        "type": "cart_update",
        "cart": session_manager.state["cart"],
        "subtotal": session_manager.state["formatted_subtotal"],
        "total": session_manager.state["formatted_total"],
        "state": session_manager.state,
    })

    res = {
        "message": f"Added {qty} x {product['name']} to cart.",
        "cart_item": cart_item,
        "cart_total": session_manager.state["formatted_total"],
    }
    return await complete_tool_call(params, res)


@tool_options(cancel_on_interruption=True)
async def view_cart(params) -> dict:
    """Display current cart contents, item quantities, subtotal, tax, and total."""
    session_manager.recalculate()
    session_manager.state["current_stage"] = "cart"

    await broadcast_rtvi(params, {
        "type": "cart_update",
        "cart": session_manager.state["cart"],
        "subtotal": session_manager.state["formatted_subtotal"],
        "total": session_manager.state["formatted_total"],
        "state": session_manager.state,
    })

    res = {
        "cart": session_manager.state["cart"],
        "item_count": len(session_manager.state["cart"]),
        "subtotal": session_manager.state["formatted_subtotal"],
        "tax": session_manager.state["formatted_tax"],
        "total": session_manager.state["formatted_total"],
    }
    return await complete_tool_call(params, res)


@tool_options(cancel_on_interruption=True)
async def remove_from_cart(params, item_name: str) -> dict:
    """
    Remove an item from the customer's cart by item name.

    Args:
        item_name: Name of product to remove.
    """
    initial_len = len(session_manager.state["cart"])
    session_manager.state["cart"] = [
        i for i in session_manager.state["cart"]
        if item_name.lower() not in i["name"].lower()
    ]
    removed_count = initial_len - len(session_manager.state["cart"])

    session_manager.recalculate()
    session_manager.state["current_stage"] = "cart"

    await broadcast_rtvi(params, {
        "type": "cart_update",
        "cart": session_manager.state["cart"],
        "subtotal": session_manager.state["formatted_subtotal"],
        "total": session_manager.state["formatted_total"],
        "state": session_manager.state,
    })

    res = {
        "message": f"Removed {removed_count} item(s) matching '{item_name}' from cart.",
        "cart_total": session_manager.state["formatted_total"],
    }
    return await complete_tool_call(params, res)


@tool_options(cancel_on_interruption=True)
async def change_cart_quantity(params, item_name: str, new_quantity: int) -> dict:
    """
    Change the quantity of an item in the cart. If quantity is 0 or less, the item is removed.

    Args:
        item_name: Name of product in cart.
        new_quantity: New quantity desired.
    """
    matched_item = next(
        (i for i in session_manager.state["cart"] if item_name.lower() in i["name"].lower()),
        None,
    )
    if not matched_item:
        return await complete_tool_call(params, {"error": f"Item '{item_name}' not found in cart."})

    if new_quantity <= 0:
        session_manager.state["cart"].remove(matched_item)
        msg = f"Removed {matched_item['name']} from cart."
    else:
        matched_item["quantity"] = new_quantity
        msg = f"Updated {matched_item['name']} quantity to {new_quantity}."

    session_manager.recalculate()
    session_manager.state["current_stage"] = "cart"

    await broadcast_rtvi(params, {
        "type": "cart_update",
        "cart": session_manager.state["cart"],
        "subtotal": session_manager.state["formatted_subtotal"],
        "total": session_manager.state["formatted_total"],
        "state": session_manager.state,
    })

    res = {
        "message": msg,
        "cart_total": session_manager.state["formatted_total"],
    }
    return await complete_tool_call(params, res)


@tool_options(cancel_on_interruption=True)
async def modify_cart_customizations(params, item_name: str, customizations: dict) -> dict:
    """
    Modify the customizations of an item already in the cart.

    Args:
        item_name: Product in cart to modify.
        customizations: Dictionary of updated customization options.
    """
    matched_item = next(
        (i for i in session_manager.state["cart"] if item_name.lower() in i["name"].lower()),
        None,
    )
    if not matched_item:
        return await complete_tool_call(params, {"error": f"Item '{item_name}' not found in cart."})

    matched_item["customizations"].update(customizations)

    extra_cost = 0.0
    for opt_group, choice in matched_item["customizations"].items():
        if isinstance(choice, str):
            extra_cost += calculate_choice_extra_price(matched_item["name"], choice)
        elif isinstance(choice, list):
            for sub_c in choice:
                extra_cost += calculate_choice_extra_price(matched_item["name"], sub_c)

    matched_item["extra_price"] = extra_cost
    matched_item["price"] = float(matched_item["unit_price"]) + extra_cost
    matched_item["line_total"] = matched_item["price"] * matched_item["quantity"]

    session_manager.recalculate()
    session_manager.state["current_stage"] = "cart"

    await broadcast_rtvi(params, {
        "type": "cart_update",
        "cart": session_manager.state["cart"],
        "subtotal": session_manager.state["formatted_subtotal"],
        "total": session_manager.state["formatted_total"],
        "state": session_manager.state,
    })

    res = {
        "message": f"Updated customizations for {matched_item['name']}.",
        "item": matched_item,
        "cart_total": session_manager.state["formatted_total"],
    }
    return await complete_tool_call(params, res)


# ── CHECKOUT & PAYMENT TOOLS ────────────────────────────────────────────────

@tool_options(cancel_on_interruption=True)
async def checkout_order(params) -> dict:
    """Review cart breakdown, calculate final subtotal/tax/total, and proceed to checkout stage."""
    if not session_manager.state["cart"]:
        return await complete_tool_call(params, {"error": "Cart is currently empty. Add items before checking out."})

    session_manager.recalculate()
    session_manager.state["current_stage"] = "checkout"

    await broadcast_rtvi(params, {
        "type": "checkout_display",
        "cart": session_manager.state["cart"],
        "subtotal": session_manager.state["formatted_subtotal"],
        "tax": session_manager.state["formatted_tax"],
        "total": session_manager.state["formatted_total"],
        "state": session_manager.state,
    })

    res = {
        "cart_summary": session_manager.state["cart"],
        "subtotal": session_manager.state["formatted_subtotal"],
        "tax": session_manager.state["formatted_tax"],
        "total": session_manager.state["formatted_total"],
        "message": f"Your order total comes to {session_manager.state['formatted_total']}. Would you like to confirm and pay?",
    }
    return await complete_tool_call(params, res)


@tool_options(cancel_on_interruption=True)
async def confirm_payment(params, payment_method: str = "card") -> dict:
    """
    Confirm payment and finalize the order. Generates an order ID and completes the session.

    Args:
        payment_method: Payment method used (e.g. 'card', 'knet', 'cash').
    """
    if not session_manager.state["cart"] and session_manager.state.get("payment_status") != "pending":
        return await complete_tool_call(params, {"error": "No active order to pay for."})

    order_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
    final_total = session_manager.state["formatted_total"]

    session_manager.state["order_id"] = order_id
    session_manager.state["payment_status"] = "paid"
    session_manager.state["current_stage"] = "order_complete"

    await broadcast_rtvi(params, {
        "type": "stage_change",
        "order_id": order_id,
        "state": session_manager.state,
    })

    session_manager.state["cart"] = []
    session_manager.recalculate()

    res = {
        "order_id": order_id,
        "status": "Order Confirmed & Paid",
        "total_paid": final_total,
        "message": f"Thank you! Your order {order_id} for {final_total} has been confirmed. Please pick up your food at the counter!",
    }
    return await complete_tool_call(params, res)


@tool_options(cancel_on_interruption=True)
async def cancel_order(params) -> dict:
    """Cancel the current order and clear the cart completely."""
    session_manager.reset()

    await broadcast_rtvi(params, {
        "type": "stage_change",
        "state": session_manager.state,
    })

    return await complete_tool_call(params, {"message": "Order cancelled. Cart has been cleared."})


# ── RESTAURANT INFORMATIONAL TOOLS ──────────────────────────────────────────

@tool_options(cancel_on_interruption=True)
async def get_restaurant_info(params) -> dict:
    """Provide general restaurant information like name, address, and phone number."""
    return await complete_tool_call(params, {
        "name": "Burger King",
        "address": "Unit 12, City Mall, Ground Floor",
        "phone": "+1-800-BURGERKING",
    })


@tool_options(cancel_on_interruption=True)
async def get_store_hours(params) -> dict:
    """Provide store opening hours."""
    return await complete_tool_call(params, {
        "hours": {
            "Monday–Friday": "10:00 AM – 10:00 PM",
            "Saturday": "9:00 AM – 11:00 PM",
            "Sunday": "9:00 AM – 9:00 PM",
        },
        "currently_open": True,
    })


@tool_options(cancel_on_interruption=True)
async def get_allergen_info(params, item_name: str) -> dict:
    """
    Provide allergen and dietary information for a specific menu item.

    Args:
        item_name: Product name to query for allergens.
    """
    product = resolve_product(item_name)
    if not product:
        return await complete_tool_call(params, {"item_name": item_name, "error": "Item not found."})

    allergens = product.get("allergens", [])
    res = {
        "item_name": product["name"],
        "allergens": allergens,
        "contains_gluten": "gluten" in allergens,
        "contains_dairy": "dairy" in allergens,
        "contains_nuts": "nuts" in allergens,
        "is_vegetarian": not allergens and "chicken" not in product["name"].lower(),
        "is_vegan": not allergens,
    }
    return await complete_tool_call(params, res)


# Export list of all function tools to register with LLMContext
ALL_TOOLS = [
    get_categories,
    show_category_items,
    search_menu,
    get_item_details,
    recommend_items,
    customize_item,
    add_to_cart,
    view_cart,
    remove_from_cart,
    change_cart_quantity,
    modify_cart_customizations,
    checkout_order,
    confirm_payment,
    cancel_order,
    get_restaurant_info,
    get_store_hours,
    get_allergen_info,
]
