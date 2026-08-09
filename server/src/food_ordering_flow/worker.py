"""
Single Unified LLMContextWorker Food Ordering Voice Agent.

Replaces the multi-node Pipecat Flows graph with one direct LLM Context Worker
equipped with all tools: menu search, item customization, cart management, checkout, and informational queries.
"""

import uuid
from typing import Any, Dict, List, Optional

from config.logger import get_logger
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_response_universal import (
    LLMAssistantAggregatorParams,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.services.llm_service import LLMService
from pipecat.workers.llm import LLMContextWorker, tool, LLMWorker
from src.food_ordering_flow.menu import (
    CATEGORIES,
    CUSTOMIZATIONS,
    MENU_ITEMS,
    calculate_choice_extra_price,
    format_kwd,
    get_items_by_category,
    get_valid_customizations,
    resolve_product,
    search_products,
)

logger = get_logger(__name__)


class FoodOrderingWorker(LLMWorker):
    """
    Unified voice ordering agent using Pipecat's LLMWorker.
    Manages session state and exposes all kiosk functions directly via @tool decorators.
    """

    def __init__(
        self,
        name: str = "food-ordering-agent",
        *,
        llm: LLMService,
        pipeline: Pipeline | None = None,
        active: bool = False,
        bridged: tuple[str, ...] | None = None,
        defer_tool_frames: bool = False,
        session_id: Optional[str] = None,
        context: LLMContext | None = None,
    ):
        """Initialize the FoodOrderingWorker (LLMWorker).

        Args:
            name: Unique name for this worker. Defaults to "food-ordering-agent".
            llm: The LLM service instance.
            pipeline: Optional pipeline override.
            active: Whether the worker starts active. Defaults to False.
            bridged: Bridge configuration forwarded to ``PipelineWorker``.
                Pass ``()`` to wrap the pipeline with bus edges so it
                can exchange frames with another bridged worker.
            defer_tool_frames: Whether to defer frames queued during
                tool execution until all tools complete. Defaults to True.
            session_id: Optional unique conversation session ID.
            context: Optional pre-built ``LLMContext``.
        """
        super().__init__(
            name=name,
            llm=llm,
            pipeline=pipeline,
            active=active,
            bridged=bridged,
            defer_tool_frames=defer_tool_frames,
        )
        self._context = context or LLMContext()
        self.session_id = session_id or str(uuid.uuid4())
        self.state: Dict[str, Any] = {
            "session_id": self.session_id,
            "current_stage": "welcome",
            "active_category": "Chicken Meals",
            "cart": [],
            "current_item": {},
            "subtotal": 0.000,
            "tax": 0.000,
            "discount_amount": 0.000,
            "total": 0.000,
            "formatted_subtotal": format_kwd(0.0),
            "formatted_tax": format_kwd(0.0),
            "formatted_discount": format_kwd(0.0),
            "formatted_total": format_kwd(0.0),
            "currency": "KWD",
            "order_id": None,
            "payment_status": "pending",
        }

    @property
    def context(self) -> LLMContext:
        """The ``LLMContext`` owned or referenced by this worker."""
        return self._context

    async def broadcast_rtvi(self, payload: dict) -> None:
        """Broadcast real-time RTVI server message to the client web application."""
        if hasattr(self, "rtvi") and self.rtvi:
            try:
                await self.rtvi.send_server_message(payload)
            except Exception as e:
                logger.warning(f"Could not send RTVI message: {e}")

    def _recalculate_cart_totals(self) -> None:
        """Recompute cart line totals, subtotal, tax, and overall total."""
        subtotal = 0.0
        for item in self.state["cart"]:
            base_p = float(item.get("unit_price", 0.0))
            extra_p = float(item.get("extra_price", 0.0))
            qty = int(item.get("quantity", 1))
            unit_total = base_p + extra_p
            line_tot = unit_total * qty
            item["price"] = unit_total
            item["line_total"] = line_tot
            item["formatted_price"] = format_kwd(unit_total)
            item["formatted_total"] = format_kwd(line_tot)
            subtotal += line_tot

        tax = subtotal * 0.0  # 0% tax standard for local fast food
        total = max(0.0, subtotal + tax - float(self.state.get("discount_amount", 0.0)))

        self.state["subtotal"] = subtotal
        self.state["tax"] = tax
        self.state["total"] = total
        self.state["formatted_subtotal"] = format_kwd(subtotal)
        self.state["formatted_tax"] = format_kwd(tax)
        self.state["formatted_total"] = format_kwd(total)

    # ── MENU & INFORMATIONAL TOOLS ──────────────────────────────────────────────

    @tool
    async def get_categories(self, params) -> dict:
        """List all available menu categories so the customer can explore what food is available."""
        self.state["current_stage"] = "browse_menu"
        await self.broadcast_rtvi({
            "type": "stage_change",
            "state": self.state,
        })
        return {"categories": CATEGORIES}

    @tool
    async def show_category_items(self, params, category_name: str) -> dict:
        """
        Show menu items belonging to a specific category (e.g. 'Sides & Salads', 'Chicken Meals', 'Desserts & Drinks').

        Args:
            category_name: Category name to filter and display on the frontend kiosk screen.
        """
        items = get_items_by_category(category_name)
        matched_cat = items[0]["category"] if items else category_name
        self.state["active_category"] = matched_cat
        self.state["current_stage"] = "browse_menu"

        await self.broadcast_rtvi({
            "type": "menu_display",
            "category": matched_cat,
            "items": items,
            "state": self.state,
        })
        return {"category": matched_cat, "items": items}

    @tool
    async def search_menu(self, params, query: str) -> dict:
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
            self.state["active_category"] = matched_category
        self.state["current_stage"] = "browse_menu"

        await self.broadcast_rtvi({
            "type": "menu_display",
            "category": matched_category,
            "query": query,
            "items": formatted_items,
            "state": self.state,
        })
        return {"query": query, "items": formatted_items}

    @tool
    async def get_item_details(self, params, item_name: str) -> dict:
        """
        Look up full details, pricing in KWD, allergens, and calories for a specific product.

        Args:
            item_name: Full or partial product name.
        """
        product = resolve_product(item_name)
        if not product:
            return {"name": item_name, "error": "Item not found on the menu."}

        customizations = get_valid_customizations(product["name"])
        self.state["current_item"] = product
        self.state["current_stage"] = "browse_menu"

        await self.broadcast_rtvi({
            "type": "product_detail",
            "category": product.get("category", ""),
            "item": product,
            "state": self.state,
        })
        return {
            "item_id": product["id"],
            "name": product["name"],
            "price": product["formatted_price"],
            "description": product["description"],
            "category": product["category"],
            "available_customizations": customizations,
            "allergens": product.get("allergens", []),
            "calories": product.get("calories", 0),
        }

    @tool
    async def recommend_items(self, params, preference: str = "popular") -> dict:
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
        return {"recommendations": recs}

    # ── CUSTOMIZE ITEM TOOL ─────────────────────────────────────────────────────

    @tool
    async def customize_item(self, params, item_name: str) -> dict:
        """
        Show available customization options valid ONLY for the selected product.
        Displays valid sizes, meal options, add-ons, sauces, drinks, and extras.

        Args:
            item_name: Product name to customize.
        """
        product = resolve_product(item_name)
        if not product:
            return {"name": item_name, "error": "Item not found on the menu."}

        valid_customizations = get_valid_customizations(product["name"])
        self.state["current_item"] = product
        self.state["current_stage"] = "customize_item"

        await self.broadcast_rtvi({
            "type": "customization_display",
            "item": product,
            "customizations": valid_customizations,
            "state": self.state,
        })

        return {
            "item_name": product["name"],
            "base_price": product["formatted_price"],
            "valid_customization_groups": valid_customizations,
            "message": f"Presenting customization options for {product['name']}.",
        }

    # ── CART MANAGEMENT TOOLS ───────────────────────────────────────────────────

    @tool
    async def add_to_cart(
        self, params, item_name: str, quantity: int = 1, customizations: Optional[dict] = None
    ) -> dict:
        """
        Add a product with optional customizations and quantity to the customer's cart.

        Args:
            item_name: Name of product to add.
            quantity: Quantity of items to add (default 1).
            customizations: Optional dictionary of customization selections (e.g. {'Meal Size Upgrade': 'Go King', 'Side Selection': 'Curly Fries', 'Drink Selection': 'Coca Cola'}).
        """
        product = resolve_product(item_name)
        if not product:
            return {"error": f"Item '{item_name}' was not found on the menu."}

        qty = max(1, quantity)
        custom_dict = customizations or {}
        extra_cost = 0.0

        # Calculate extra cost of selected customization choices
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

        # Check if identical item with same customizations already exists in cart
        existing = next(
            (
                i for i in self.state["cart"]
                if i["name"] == cart_item["name"] and i.get("customizations") == cart_item["customizations"]
            ),
            None,
        )

        if existing:
            existing["quantity"] += qty
        else:
            self.state["cart"].append(cart_item)

        self._recalculate_cart_totals()
        self.state["current_stage"] = "cart"

        await self.broadcast_rtvi({
            "type": "cart_update",
            "cart": self.state["cart"],
            "subtotal": self.state["formatted_subtotal"],
            "total": self.state["formatted_total"],
            "state": self.state,
        })

        return {
            "message": f"Added {qty} x {product['name']} to cart.",
            "cart_item": cart_item,
            "cart_total": self.state["formatted_total"],
        }

    @tool
    async def view_cart(self, params) -> dict:
        """
        Display current cart contents, item quantities, individual prices, subtotal, tax, total, and applied customizations.
        """
        self._recalculate_cart_totals()
        self.state["current_stage"] = "cart"

        await self.broadcast_rtvi({
            "type": "cart_update",
            "cart": self.state["cart"],
            "subtotal": self.state["formatted_subtotal"],
            "total": self.state["formatted_total"],
            "state": self.state,
        })

        return {
            "cart": self.state["cart"],
            "item_count": len(self.state["cart"]),
            "subtotal": self.state["formatted_subtotal"],
            "tax": self.state["formatted_tax"],
            "total": self.state["formatted_total"],
        }

    @tool
    async def remove_from_cart(self, params, item_name: str) -> dict:
        """
        Remove an item from the customer's cart by item name.

        Args:
            item_name: Name of product to remove.
        """
        initial_len = len(self.state["cart"])
        self.state["cart"] = [
            i for i in self.state["cart"]
            if item_name.lower() not in i["name"].lower()
        ]
        removed_count = initial_len - len(self.state["cart"])

        self._recalculate_cart_totals()
        self.state["current_stage"] = "cart"

        await self.broadcast_rtvi({
            "type": "cart_update",
            "cart": self.state["cart"],
            "subtotal": self.state["formatted_subtotal"],
            "total": self.state["formatted_total"],
            "state": self.state,
        })

        return {
            "message": f"Removed {removed_count} item(s) matching '{item_name}' from cart.",
            "cart_total": self.state["formatted_total"],
        }

    @tool
    async def change_cart_quantity(self, params, item_name: str, new_quantity: int) -> dict:
        """
        Change the quantity of an item in the cart. If quantity is 0 or less, the item is removed.

        Args:
            item_name: Name of product in cart.
            new_quantity: New quantity desired.
        """
        matched_item = next(
            (i for i in self.state["cart"] if item_name.lower() in i["name"].lower()),
            None,
        )
        if not matched_item:
            return {"error": f"Item '{item_name}' not found in cart."}

        if new_quantity <= 0:
            self.state["cart"].remove(matched_item)
            msg = f"Removed {matched_item['name']} from cart."
        else:
            matched_item["quantity"] = new_quantity
            msg = f"Updated {matched_item['name']} quantity to {new_quantity}."

        self._recalculate_cart_totals()
        self.state["current_stage"] = "cart"

        await self.broadcast_rtvi({
            "type": "cart_update",
            "cart": self.state["cart"],
            "subtotal": self.state["formatted_subtotal"],
            "total": self.state["formatted_total"],
            "state": self.state,
        })

        return {
            "message": msg,
            "cart_total": self.state["formatted_total"],
        }

    @tool
    async def modify_cart_customizations(self, params, item_name: str, customizations: dict) -> dict:
        """
        Modify the customizations of an item already in the cart.

        Args:
            item_name: Product in cart to modify.
            customizations: Dictionary of updated customization options.
        """
        matched_item = next(
            (i for i in self.state["cart"] if item_name.lower() in i["name"].lower()),
            None,
        )
        if not matched_item:
            return {"error": f"Item '{item_name}' not found in cart."}

        matched_item["customizations"].update(customizations)

        # Recalculate extra price
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

        self._recalculate_cart_totals()
        self.state["current_stage"] = "cart"

        await self.broadcast_rtvi({
            "type": "cart_update",
            "cart": self.state["cart"],
            "subtotal": self.state["formatted_subtotal"],
            "total": self.state["formatted_total"],
            "state": self.state,
        })

        return {
            "message": f"Updated customizations for {matched_item['name']}.",
            "item": matched_item,
            "cart_total": self.state["formatted_total"],
        }

    # ── CHECKOUT & PAYMENT TOOLS ────────────────────────────────────────────────

    @tool
    async def checkout_order(self, params) -> dict:
        """
        Review cart breakdown, calculate final subtotal/tax/total, and proceed to checkout stage.
        """
        if not self.state["cart"]:
            return {"error": "Cart is currently empty. Add items before checking out."}

        self._recalculate_cart_totals()
        self.state["current_stage"] = "checkout"

        await self.broadcast_rtvi({
            "type": "checkout_display",
            "cart": self.state["cart"],
            "subtotal": self.state["formatted_subtotal"],
            "tax": self.state["formatted_tax"],
            "total": self.state["formatted_total"],
            "state": self.state,
        })

        return {
            "cart_summary": self.state["cart"],
            "subtotal": self.state["formatted_subtotal"],
            "tax": self.state["formatted_tax"],
            "total": self.state["formatted_total"],
            "message": f"Your order total comes to {self.state['formatted_total']}. Would you like to confirm and pay?",
        }

    @tool
    async def confirm_payment(self, params, payment_method: str = "card") -> dict:
        """
        Confirm payment and finalize the order. Generates an order ID and completes the session.

        Args:
            payment_method: Payment method used (e.g. 'card', 'knet', 'cash').
        """
        if not self.state["cart"] and self.state.get("payment_status") != "pending":
            return {"error": "No active order to pay for."}

        order_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
        final_total = self.state["formatted_total"]

        self.state["order_id"] = order_id
        self.state["payment_status"] = "paid"
        self.state["current_stage"] = "order_complete"

        await self.broadcast_rtvi({
            "type": "stage_change",
            "order_id": order_id,
            "state": self.state,
        })

        # Clear cart for next order
        self.state["cart"] = []
        self.state["subtotal"] = 0.0
        self.state["tax"] = 0.0
        self.state["total"] = 0.0
        self.state["formatted_subtotal"] = format_kwd(0.0)
        self.state["formatted_tax"] = format_kwd(0.0)
        self.state["formatted_total"] = format_kwd(0.0)

        return {
            "order_id": order_id,
            "status": "Order Confirmed & Paid",
            "total_paid": final_total,
            "message": f"Thank you! Your order {order_id} for {final_total} has been confirmed. Please pick up your food at the counter!",
        }

    @tool
    async def cancel_order(self, params) -> dict:
        """Cancel the current order and clear the cart completely."""
        self.state["cart"] = []
        self.state["current_item"] = {}
        self.state["subtotal"] = 0.0
        self.state["tax"] = 0.0
        self.state["total"] = 0.0
        self.state["formatted_subtotal"] = format_kwd(0.0)
        self.state["formatted_tax"] = format_kwd(0.0)
        self.state["formatted_total"] = format_kwd(0.0)
        self.state["current_stage"] = "welcome"
        self.state["order_id"] = None
        self.state["payment_status"] = "pending"

        await self.broadcast_rtvi({
            "type": "stage_change",
            "state": self.state,
        })

        return {"message": "Order cancelled. Cart has been cleared."}

    # ── RESTAURANT INFORMATIONAL TOOLS ──────────────────────────────────────────

    @tool
    async def get_restaurant_info(self, params) -> dict:
        """Provide general restaurant information like name, address, and phone number."""
        return {
            "name": "Burger King",
            "address": "Unit 12, City Mall, Ground Floor",
            "phone": "+1-800-BURGERKING",
        }

    @tool
    async def get_store_hours(self, params) -> dict:
        """Provide store opening hours."""
        return {
            "hours": {
                "Monday–Friday": "10:00 AM – 10:00 PM",
                "Saturday": "9:00 AM – 11:00 PM",
                "Sunday": "9:00 AM – 9:00 PM",
            },
            "currently_open": True,
        }

    @tool
    async def get_allergen_info(self, params, item_name: str) -> dict:
        """
        Provide allergen and dietary information for a specific menu item.

        Args:
            item_name: Product name to query for allergens.
        """
        product = resolve_product(item_name)
        if not product:
            return {"item_name": item_name, "error": "Item not found."}

        allergens = product.get("allergens", [])
        return {
            "item_name": product["name"],
            "allergens": allergens,
            "contains_gluten": "gluten" in allergens,
            "contains_dairy": "dairy" in allergens,
            "contains_nuts": "nuts" in allergens,
            "is_vegetarian": not allergens and "chicken" not in product["name"].lower(),
            "is_vegan": not allergens,
        }
