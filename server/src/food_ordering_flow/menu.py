"""
Burger King Single Source of Truth Menu Module (menu.py).

Provides dynamic lookup methods, menu resolution, valid customization filtering,
and KWD currency formatting (3 decimal places).
"""

from typing import Any, Dict, List, Optional


def format_kwd(amount: float) -> str:
    """Format a monetary amount in Kuwaiti Dinar with exactly 3 decimal places."""
    return f"KWD {max(0.0, float(amount)):.3f}"


CATEGORIES = [
    {
        "id": "T:SM;Id:9",
        "name": "Chicken Meals",
        "name_ar": "وجبات الدجاج",
        "item_count": 2,
    },
    {
        "id": "T:SM;Id:2",
        "name": "Sides & Salads",
        "name_ar": "الطلبات الجانبية و السلطة",
        "item_count": 3,
    },
    {
        "id": "T:SM;Id:5",
        "name": "Desserts & Drinks",
        "name_ar": "الحلو و المشروبات",
        "item_count": 4,
    },
]

MENU_ITEMS = [
    {
        "id": "T:4|Id:6393",
        "name": "Spicy Crispy Fillet Meal",
        "name_ar": "وجبة سبايسي كريسبي فيليه",
        "price": 2.650,
        "formatted_price": "KWD 2.650",
        "category": "Chicken Meals",
        "description": (
            "A spicy golden, crispy yet juicy chicken fillet served on a soft, fluffy potato bun, "
            "topped with Jalapeno, fresh lettuce, and our new signature 'House Sauce' served with fries and a drink."
        ),
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/6393.jpg",
        "allergens": ["gluten", "dairy"],
        "calories": 780,
    },
    {
        "id": "T:4|Id:6030",
        "name": "Chicken Royale Meal",
        "name_ar": "وجبة تشيكن رويال",
        "price": 2.350,
        "formatted_price": "KWD 2.350",
        "category": "Chicken Meals",
        "description": "A crispy chicken patty, fresh lettuce, and mayonnaise in our unique sesame bun served with fries and a drink.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/6030.jpg",
        "allergens": ["gluten", "dairy", "sesame"],
        "calories": 710,
    },
    {
        "id": "T:5|Id:208100",
        "name": "Chicken Fries",
        "name_ar": "تشيكن فرايز",
        "price": 1.000,
        "formatted_price": "KWD 1.000",
        "category": "Sides & Salads",
        "description": "Our famous chicken fries that will leave you craving more served with BBQ sauce.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/208100.jpg",
        "allergens": ["gluten"],
        "calories": 290,
    },
    {
        "id": "T:5|Id:208080",
        "name": "Chicken Tenders 6 Pcs",
        "name_ar": "تندر دجاج 6 قطع",
        "price": 1.000,
        "formatted_price": "KWD 1.000",
        "category": "Sides & Salads",
        "description": "6 pieces of tender, juicy golden chicken tenders.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/208080.jpg",
        "allergens": ["gluten"],
        "calories": 340,
    },
    {
        "id": "T:5|Id:228443",
        "name": "Mozarella Stick - 4 pieces",
        "name_ar": "أصابع جبن الموتزاريلا - 4 قطع",
        "price": 1.000,
        "formatted_price": "KWD 1.000",
        "category": "Sides & Salads",
        "description": "Crispy on the outside, gooey on the inside. Golden-fried mozzarella sticks served with a side of marinara sauce.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/228443.jpg",
        "allergens": ["gluten", "dairy"],
        "calories": 320,
    },
    {
        "id": "T:5|Id:248329",
        "name": "Classic Mojito",
        "name_ar": "كلاسيك موهيتو",
        "price": 0.850,
        "formatted_price": "KWD 0.850",
        "category": "Desserts & Drinks",
        "description": "A classic blend of soda, lime, and mint, creating a crisp and invigorating drink.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248329.jpg",
        "allergens": [],
        "calories": 140,
    },
    {
        "id": "T:5|Id:248330",
        "name": "Blue Lagoon Mojito",
        "name_ar": "بلو لاجون موهيتو",
        "price": 0.850,
        "formatted_price": "KWD 0.850",
        "category": "Desserts & Drinks",
        "description": "A vibrant twist of soda, lime, and blue lagoon mix.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248330.jpg",
        "allergens": [],
        "calories": 150,
    },
    {
        "id": "T:5|Id:248331",
        "name": "King On The Beach Mojito",
        "name_ar": "كنج عالبحر موهيتو",
        "price": 0.850,
        "formatted_price": "KWD 0.850",
        "category": "Desserts & Drinks",
        "description": "A refreshing fusion of soda, lime, and a rich strawberry mix.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248331.jpg",
        "allergens": [],
        "calories": 160,
    },
    {
        "id": "T:5|Id:248284",
        "name": "Coca Cola Zero",
        "name_ar": "كوكاكولا زيرو",
        "price": 0.450,
        "formatted_price": "KWD 0.450",
        "category": "Desserts & Drinks",
        "description": "Refreshing zero sugar Coca Cola.",
        "image_url": "https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248284.jpg",
        "allergens": [],
        "calories": 0,
    },
]

# Customization choices per item
CUSTOMIZATIONS: Dict[str, List[Dict[str, Any]]] = {
    "Spicy Crispy Fillet Meal": [
        {
            "option": "Meal Size Upgrade",
            "choices": [
                {"name": "Go Mega", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Go King", "extra_price": 0.200, "formatted_price": "KWD 0.200"},
            ],
        },
        {
            "option": "Side Selection",
            "choices": [
                {"name": "Fries", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Curly Fries", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Onion Rings", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Fries Ketchup Mayonnaise", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Chili Loaded Fries", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Truffle Loaded Fries", "extra_price": 0.750, "formatted_price": "KWD 0.750"},
                {"name": "Grogu Loaded Fries", "extra_price": 0.750, "formatted_price": "KWD 0.750"},
                {"name": "Mandalorian Loaded Fries", "extra_price": 0.750, "formatted_price": "KWD 0.750"},
            ],
        },
        {
            "option": "Drink Selection",
            "choices": [
                {"name": "Coca Cola", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Coca Cola Zero", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Fanta", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Sprite", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Mineral Water 500 ML", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Chocolate Shake", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Strawberry Shake", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Vanilla Shake", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Classic Mojito", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Blue Lagoon Mojito", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "King On The Beach Mojito", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Grogu's Splash", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
            ],
        },
        {
            "option": "Extras & Add-ons",
            "choices": [
                {"name": "Add Extra Spicy Fillet Patty", "extra_price": 0.600, "formatted_price": "KWD 0.600"},
                {"name": "Cheese Melts – 4 pieces", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Hersheys Pie", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Chicken wings 2 PCs", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Oreo Cake", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Chicken Tenders 4 Pcs", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Jalapeno Cheese Nuggets 4 PCs", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Snack Box", "extra_price": 1.000, "formatted_price": "KWD 1.000"},
            ],
        },
        {
            "option": "Sauces",
            "choices": [
                {"name": "BBQ Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Garlic Mayonaisse Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Fiery Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Marinara Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Chipotle Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Asian Zing Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Habanero Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Buttermilk Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Spicy BBQ Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Mayo'chup Sauce", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "2 Mayo Sachet", "extra_price": 0.050, "formatted_price": "KWD 0.050"},
            ],
        },
    ],
    "Chicken Royale Meal": [
        {
            "option": "Meal Size Upgrade",
            "choices": [
                {"name": "Go Mega", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Go King", "extra_price": 0.200, "formatted_price": "KWD 0.200"},
            ],
        },
        {
            "option": "Side Selection",
            "choices": [
                {"name": "Fries", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Curly Fries", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Onion Rings", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Fries Ketchup Mayonnaise", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Chili Loaded Fries", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Truffle Loaded Fries", "extra_price": 0.750, "formatted_price": "KWD 0.750"},
                {"name": "Grogu Loaded Fries", "extra_price": 0.750, "formatted_price": "KWD 0.750"},
                {"name": "Mandalorian Loaded Fries", "extra_price": 0.750, "formatted_price": "KWD 0.750"},
            ],
        },
        {
            "option": "Drink Selection",
            "choices": [
                {"name": "Coca Cola", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Coca Cola Zero", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Fanta", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Sprite", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Mineral Water 500 ML", "extra_price": 0.000, "formatted_price": "KWD 0.000"},
                {"name": "Chocolate Shake", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Strawberry Shake", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Vanilla Shake", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Classic Mojito", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Blue Lagoon Mojito", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "King On The Beach Mojito", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "Grogu's Splash", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
            ],
        },
        {
            "option": "Extras & Add-ons",
            "choices": [
                {"name": "Add Cheese", "extra_price": 0.200, "formatted_price": "KWD 0.200"},
                {"name": "Cheese Melts – 4 pieces", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Hersheys Pie", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Chicken wings 2 PCs", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Oreo Cake", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Chicken Tenders 4 Pcs", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Jalapeno Cheese Nuggets 4 PCs", "extra_price": 0.500, "formatted_price": "KWD 0.500"},
                {"name": "Snack Box", "extra_price": 1.000, "formatted_price": "KWD 1.000"},
            ],
        },
        {
            "option": "Sauces",
            "choices": [
                {"name": "BBQ Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Garlic Mayonaisse Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Fiery Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Marinara Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Chipotle Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Asian Zing Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Habanero Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Buttermilk Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Spicy BBQ Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Mayo'chup Sauce", "extra_price": 0.250, "formatted_price": "KWD 0.250"},
                {"name": "2 Mayo Sachet", "extra_price": 0.050, "formatted_price": "KWD 0.050"},
            ],
        },
    ],
    "Chicken Fries": [
        {
            "option": "Dipping Sauces",
            "choices": [
                {"name": "BBQ Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Garlic Mayonaisse Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Fiery Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Marinara Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Chipotle Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Asian Zing Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Habanero Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Buttermilk Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Spicy BBQ Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
            ],
        }
    ],
    "Chicken Tenders 6 Pcs": [
        {
            "option": "Dipping Sauces",
            "choices": [
                {"name": "BBQ Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Garlic Mayonaisse Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Fiery Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Marinara Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Chipotle Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Asian Zing Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Habanero Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Buttermilk Ranch Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "Spicy BBQ Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
            ],
        }
    ],
    "Mozarella Stick - 4 pieces": [
        {
            "option": "Dipping Sauces",
            "choices": [
                {"name": "Marinara Sauce", "extra_price": 0.150, "formatted_price": "KWD 0.150"},
                {"name": "BBQ Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Garlic Mayonaisse Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
                {"name": "Fiery Sauce", "extra_price": 0.100, "formatted_price": "KWD 0.100"},
            ],
        }
    ],
}

ITEM_PRICES = {item["name"]: item["price"] for item in MENU_ITEMS}


# ── Helper API functions ─────────────────────────────────────────────────────


def get_menu_payload() -> Dict[str, Any]:
    """Return complete menu payload for frontend dynamic rendering."""
    return {
        "categories": CATEGORIES,
        "items": MENU_ITEMS,
        "customizations": CUSTOMIZATIONS,
    }


def get_categories() -> List[Dict[str, Any]]:
    """Return all menu categories."""
    return CATEGORIES


def get_items_by_category(category_name: str) -> List[Dict[str, Any]]:
    """Return all items belonging to a specific category."""
    cat_name = category_name.lower()
    return [
        item for item in MENU_ITEMS
        if cat_name in item["category"].lower()
    ]


def search_products(query: str) -> List[Dict[str, Any]]:
    """Search products by name, category, or description."""
    q = query.lower().strip()
    return [
        item for item in MENU_ITEMS
        if q in item["name"].lower() or q in item["description"].lower() or q in item["category"].lower()
    ]


def resolve_product(item_name: str) -> Optional[Dict[str, Any]]:
    """Look up product details by exact or partial item name."""
    name_lower = item_name.lower().strip()
    # Exact match first
    matched = next((i for i in MENU_ITEMS if i["name"].lower() == name_lower), None)
    if not matched:
        # Partial match
        matched = next((i for i in MENU_ITEMS if name_lower in i["name"].lower()), None)
    return matched


def get_valid_customizations(item_name: str) -> List[Dict[str, Any]]:
    """Fetch customization options that are valid ONLY for the resolved product."""
    product = resolve_product(item_name)
    if not product:
        return []
    return CUSTOMIZATIONS.get(product["name"], [])


def calculate_choice_extra_price(item_name: str, choice_name: str) -> float:
    """Calculate extra price for a specific customization choice."""
    valid_opts = get_valid_customizations(item_name)
    choice_lower = choice_name.lower().strip()
    for opt_group in valid_opts:
        for choice in opt_group.get("choices", []):
            if choice["name"].lower() == choice_lower:
                return float(choice.get("extra_price", 0.0))
    return 0.0
