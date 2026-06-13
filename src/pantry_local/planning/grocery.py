"""Grocery list: net of pantry, grouped by store channel + aisle, with the
card-routing hint (design.md Section 4).

The store graph is three nodes with different cadences: Patel Brothers (~monthly,
shelf-stable Indian staples), ShopRite/Instacart (weekly perishables, delivery
default), Costco (opportunistic bulk). The list never generates a Costco trip; it
appends sublists. A one-line credit-card recommendation rides each channel.

No circular scraping, no cross-store unit-price optimizer — by design those are
deleted (the binding constraint is hours, not dollars).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import MealPlan
from ..ontology import normalize, lookup, CHANNEL_PATEL, CHANNEL_SHOPRITE, CHANNEL_COSTCO
from ..pantry.state import Pantry
from ..knowledge.substitutions import resolve_missing

# Static card lookup. The portfolio (Platinum / CSR / Venture X / Bilt) has no
# strong grocery-category earner, so the recommendation is the least-bad option
# per channel plus a flag that a grocery card may be worth adding.
_CARD_BY_CHANNEL = {
    CHANNEL_SHOPRITE: "CSR (3x dining doesn't apply; use best flat-rate) "
                      "— portfolio lacks a US-supermarket multiplier.",
    CHANNEL_PATEL: "Any flat-rate card; small spend, in-person.",
    CHANNEL_COSTCO: "Costco-compatible Visa (Venture X is Visa) — Amex not accepted.",
}

_CHANNEL_LABEL = {
    CHANNEL_PATEL: "Patel Brothers (Indian grocery, ~monthly, in person)",
    CHANNEL_SHOPRITE: "ShopRite / Instacart (weekly, delivery)",
    CHANNEL_COSTCO: "Costco (opportunistic bulk — append only)",
}

# Categorical price/quality gap: always restock at Patel's, never ShopRite.
_PATEL_PREFERRED_AISLES = {"dals", "spices", "grains"}


@dataclass
class GroceryItem:
    canonical: str
    aisle: str
    needed_by: list[str] = field(default_factory=list)  # recipe ids that need it
    patel_preferred: bool = False


@dataclass
class GroceryChannel:
    channel: str
    label: str
    card_hint: str
    items: list[GroceryItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "channel": self.channel,
            "label": self.label,
            "card_hint": self.card_hint,
            "items": [
                {"canonical": i.canonical, "aisle": i.aisle,
                 "needed_by": i.needed_by, "patel_preferred": i.patel_preferred}
                for i in sorted(self.items, key=lambda x: (x.aisle, x.canonical))
            ],
        }


@dataclass
class GroceryList:
    channels: list[GroceryChannel] = field(default_factory=list)
    skipped_unknown: list[str] = field(default_factory=list)

    def all_items(self) -> list[GroceryItem]:
        return [i for ch in self.channels for i in ch.items]

    def to_dict(self) -> dict:
        return {
            "channels": [ch.to_dict() for ch in self.channels],
            "skipped_unknown": self.skipped_unknown,
        }


def grocery_list(plan: MealPlan, store: RecipeStore, pantry: Pantry) -> GroceryList:
    pantry_cans = pantry.canonicals()
    # canonical -> (aisle, channel, [recipe ids])
    needed: dict[str, dict] = {}
    skipped: list[str] = []

    for meal in plan.meals:
        recipe = store.get(meal.recipe_id)
        if not recipe:
            continue
        for ing in recipe.ingredients:
            if ing.optional:
                continue
            canonical = normalize(ing.name)
            if not canonical:
                skipped.append(ing.name)
                continue
            if resolve_missing(canonical, pantry_cans) is not None:
                continue  # have it or a substitute
            ref = lookup(canonical)
            channel = ref.channel if ref else CHANNEL_SHOPRITE
            aisle = ref.aisle if ref else "other"
            entry = needed.setdefault(
                canonical, {"aisle": aisle, "channel": channel, "recipes": []}
            )
            if recipe.id not in entry["recipes"]:
                entry["recipes"].append(recipe.id)

    channels: dict[str, GroceryChannel] = {}
    for ch in (CHANNEL_SHOPRITE, CHANNEL_PATEL, CHANNEL_COSTCO):
        channels[ch] = GroceryChannel(ch, _CHANNEL_LABEL[ch], _CARD_BY_CHANNEL[ch])

    for canonical, info in needed.items():
        patel_pref = info["aisle"] in _PATEL_PREFERRED_AISLES
        item = GroceryItem(
            canonical=canonical,
            aisle=info["aisle"],
            needed_by=info["recipes"],
            patel_preferred=patel_pref,
        )
        channels[info["channel"]].items.append(item)

    # Drop empty channels for a clean list.
    out = [ch for ch in channels.values() if ch.items]
    return GroceryList(channels=out, skipped_unknown=sorted(set(skipped)))
