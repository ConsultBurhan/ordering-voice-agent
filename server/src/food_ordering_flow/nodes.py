"""
NodeConfig factory functions for the kiosk ordering flow.

Simplified 2-node graph for step-by-step development & debugging:
  Welcome → Browse Menu
"""

from pipecat.flows import NodeConfig

from src.food_ordering_flow.prompts import (
    BROWSE_TASK,
    KIOSK_PERSONA,
    WELCOME_TASK,
)

# ── Global tools ─────────────────────────────────────────────────────────────

def _global_functions() -> list:
    """Return the list of global informational tool functions available at welcome & browse."""
    from src.food_ordering_flow.functions.global_tools import (
        get_allergen_info,
        get_item_details,
        get_restaurant_info,
        get_store_hours,
        recommend_items,
        search_menu,
    )
    return [
        search_menu,
        get_item_details,
        recommend_items,
        get_restaurant_info,
        get_store_hours,
        get_allergen_info,
    ]


# ── Async Node Factories (Welcome & Browse Menu Only) ─────────────────────────


async def create_welcome_node() -> NodeConfig:
    """
    Welcome node — greet the customer and listen for order intent.
    Transitions to Browse Menu node when customer mentions ordering or browsing.
    """
    from src.food_ordering_flow.functions.browse import (
        get_categories,
        go_to_browse,
    )

    return NodeConfig(
        name="welcome",
        role_message=KIOSK_PERSONA,
        task_messages=[{"role": "user", "content": WELCOME_TASK}],
        functions=[
            get_categories,
            go_to_browse,
            *_global_functions(),
        ],
    )


async def create_browse_node() -> NodeConfig:
    """
    Browse Menu node — help the customer explore menu categories, products, prices, and recommendations.
    """
    from src.food_ordering_flow.functions.browse import (
        get_categories,
        select_product_info,
        show_category_items,
    )

    return NodeConfig(
        name="browse_menu",
        task_messages=[{"role": "user", "content": BROWSE_TASK}],
        functions=[
            get_categories,
            show_category_items,
            select_product_info,
            *_global_functions(),
        ],
    )
