"""Ingredient ontology: normalize raw ingredient names to canonical pantry items.

This is the shared vocabulary that the diet/toddler constraint checks, the recipe
corpus, and the grocery list all key off of. Each canonical ingredient carries the
metadata the rest of the system needs:

- ``aisle``: grocery category, used to group the shopping list.
- ``perishable``: drives weekly-vs-monthly cadence and the phone-scan target set.
- ``channel``: default store channel (see design.md Section 4 store graph).
- ``protein_class``: groups protein sources for the dal-rice repetition check
  (design.md Section 5). ``None`` for non-protein items.

The ontology is intentionally small and hand-maintained for v0; it covers the
household's actual Bengali-vegetarian baseline rather than aiming for completeness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

# Store channels (design.md Section 4).
CHANNEL_PATEL = "patel"  # Indian grocery, ~monthly, in person
CHANNEL_SHOPRITE = "shoprite"  # weekly perishables + mainstream staples, delivery
CHANNEL_COSTCO = "costco"  # opportunistic bulk

# Protein classes for the repetition check. Dal varieties collapse into one class
# on purpose; paneer/chana/rajma/tofu/yogurt each count separately.
PROTEIN_DAL = "dal"
PROTEIN_PANEER = "paneer"
PROTEIN_CHANA = "chana"
PROTEIN_RAJMA = "rajma"
PROTEIN_TOFU = "tofu"
PROTEIN_YOGURT = "yogurt"
PROTEIN_LEGUME_OTHER = "legume_other"


@dataclass(frozen=True)
class Ingredient:
    canonical: str
    aliases: tuple[str, ...] = ()
    aisle: str = "other"
    perishable: bool = False
    channel: str = CHANNEL_SHOPRITE
    protein_class: str | None = None
    # Nutrition tags used by the nutrition evaluator (advisory only).
    iron_rich: bool = False
    vitamin_c_rich: bool = False
    b12_source: bool = False
    vitamin_d_source: bool = False


# --- The canonical ingredient table -----------------------------------------

_INGREDIENTS: tuple[Ingredient, ...] = (
    # Dals / legumes (Patel, shelf-stable, iron-rich, protein=dal)
    Ingredient("masoor dal", ("red lentil", "red lentils", "masoor"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_DAL, iron_rich=True),
    Ingredient("toor dal", ("arhar dal", "pigeon pea", "toovar", "tuvar"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_DAL, iron_rich=True),
    Ingredient("moong dal", ("mung dal", "green gram", "yellow moong"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_DAL, iron_rich=True),
    Ingredient("chana dal", ("bengal gram", "split chickpea"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_DAL, iron_rich=True),
    Ingredient("urad dal", ("black gram", "split black lentil"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_DAL, iron_rich=True),
    Ingredient("chickpeas", ("chana", "kabuli chana", "garbanzo", "garbanzo beans"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_CHANA, iron_rich=True),
    Ingredient("rajma", ("kidney beans", "red kidney bean"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_RAJMA, iron_rich=True),
    Ingredient("lobia", ("black eyed peas", "cowpea"),
               aisle="dals", channel=CHANNEL_PATEL, protein_class=PROTEIN_LEGUME_OTHER, iron_rich=True),

    # Grains / flours (Patel, shelf-stable)
    Ingredient("basmati rice", ("rice", "white rice"),
               aisle="grains", channel=CHANNEL_PATEL),
    Ingredient("atta", ("whole wheat flour", "chapati flour", "roti flour"),
               aisle="grains", channel=CHANNEL_PATEL),
    Ingredient("besan", ("gram flour", "chickpea flour"),
               aisle="grains", channel=CHANNEL_PATEL, iron_rich=True),
    Ingredient("poha", ("flattened rice", "beaten rice"),
               aisle="grains", channel=CHANNEL_PATEL),
    Ingredient("suji", ("semolina", "rava"),
               aisle="grains", channel=CHANNEL_PATEL),

    # Dairy (ShopRite/Costco, perishable, B12)
    Ingredient("milk", ("whole milk", "dudh"),
               aisle="dairy", perishable=True, channel=CHANNEL_COSTCO,
               b12_source=True, vitamin_d_source=True),
    Ingredient("yogurt", ("dahi", "curd", "plain yogurt"),
               aisle="dairy", perishable=True, channel=CHANNEL_SHOPRITE,
               protein_class=PROTEIN_YOGURT, b12_source=True),
    Ingredient("paneer", ("indian cottage cheese", "cottage cheese (paneer)"),
               aisle="dairy", perishable=True, channel=CHANNEL_COSTCO,
               protein_class=PROTEIN_PANEER, b12_source=True),
    Ingredient("butter", ("makhan",),
               aisle="dairy", perishable=True, channel=CHANNEL_SHOPRITE),
    Ingredient("ghee", ("clarified butter",),
               aisle="dairy", channel=CHANNEL_PATEL),  # shelf-stable
    Ingredient("tofu", ("bean curd", "firm tofu"),
               aisle="dairy", perishable=True, channel=CHANNEL_SHOPRITE,
               protein_class=PROTEIN_TOFU, iron_rich=True),

    # Produce (ShopRite, perishable)
    Ingredient("onion", ("onions", "pyaaz", "red onion"),
               aisle="produce", perishable=True),
    Ingredient("tomato", ("tomatoes", "tamatar"),
               aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("potato", ("potatoes", "aloo", "alu"),
               aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("ginger", ("adrak",), aisle="produce", perishable=True),
    Ingredient("garlic", ("lehsun", "lasun"), aisle="produce", perishable=True),
    Ingredient("green chili", ("green chilli", "hari mirch", "serrano"),
               aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("cilantro", ("coriander leaves", "dhania", "fresh coriander"),
               aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("spinach", ("palak", "baby spinach"),
               aisle="produce", perishable=True, iron_rich=True, vitamin_c_rich=True),
    Ingredient("methi", ("fenugreek leaves", "fresh methi"),
               aisle="produce", perishable=True, channel=CHANNEL_PATEL, iron_rich=True),
    Ingredient("cauliflower", ("gobi", "phool gobi"),
               aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("eggplant", ("brinjal", "baingan", "aubergine"),
               aisle="produce", perishable=True),
    Ingredient("okra", ("bhindi", "lady finger"),
               aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("peas", ("matar", "green peas", "frozen peas"),
               aisle="frozen", perishable=True),
    Ingredient("carrot", ("carrots", "gajar"), aisle="produce", perishable=True),
    Ingredient("bell pepper", ("capsicum", "shimla mirch"),
               aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("bottle gourd", ("lauki", "doodhi"), aisle="produce", perishable=True),
    Ingredient("lemon", ("lime", "nimbu"), aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("curry leaves", ("kadi patta",),
               aisle="produce", perishable=True, channel=CHANNEL_PATEL),
    Ingredient("grapes", (), aisle="produce", perishable=True, vitamin_c_rich=True),
    Ingredient("cherry tomato", ("cherry tomatoes",),
               aisle="produce", perishable=True, vitamin_c_rich=True),

    # Spices (Patel, shelf-stable)
    Ingredient("cumin seeds", ("jeera", "cumin"), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("mustard seeds", ("rai", "sarso"), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("turmeric", ("haldi", "turmeric powder"), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("red chili powder", ("lal mirch", "chili powder", "cayenne"),
               aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("coriander powder", ("dhania powder",), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("garam masala", (), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("asafoetida", ("hing",), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("panch phoron", ("bengali five spice",), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("bay leaf", ("tej patta",), aisle="spices", channel=CHANNEL_PATEL),
    Ingredient("salt", ("namak",), aisle="spices", channel=CHANNEL_SHOPRITE),
    Ingredient("sugar", ("cheeni",), aisle="spices", channel=CHANNEL_SHOPRITE),

    # Oils / condiments
    Ingredient("mustard oil", (), aisle="condiments", channel=CHANNEL_PATEL),
    Ingredient("vegetable oil", ("cooking oil", "sunflower oil", "canola oil"),
               aisle="condiments", channel=CHANNEL_SHOPRITE),
    Ingredient("coconut milk", (), aisle="condiments", channel=CHANNEL_SHOPRITE),
    Ingredient("tamarind", ("imli",), aisle="condiments", channel=CHANNEL_PATEL),

    # Nuts (daycare-relevant; see toddler module)
    Ingredient("cashews", ("kaju", "cashew"), aisle="nuts", channel=CHANNEL_PATEL),
    Ingredient("almonds", ("badam", "almond"), aisle="nuts", channel=CHANNEL_PATEL),
    Ingredient("peanuts", ("groundnut", "moongphali", "peanut"),
               aisle="nuts", channel=CHANNEL_PATEL),
)


# --- Lookup index ------------------------------------------------------------

def _build_alias_index() -> dict[str, Ingredient]:
    index: dict[str, Ingredient] = {}
    for ing in _INGREDIENTS:
        keys = (ing.canonical,) + ing.aliases
        for key in keys:
            index[key.lower()] = ing
    return index


_ALIAS_INDEX = _build_alias_index()
# Longest aliases first so multi-word matches win over single-word substrings.
_ALIAS_KEYS_BY_LEN = sorted(_ALIAS_INDEX.keys(), key=len, reverse=True)

_PARENS = re.compile(r"\([^)]*\)")
_NONWORD = re.compile(r"[^a-z0-9\s]")


def _clean(raw: str) -> str:
    text = raw.lower().strip()
    text = _PARENS.sub(" ", text)
    text = _NONWORD.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(raw_name: str) -> str | None:
    """Return the canonical ingredient name for a raw string, or None if unknown.

    Tries an exact alias hit first, then a substring match (longest alias wins),
    so "2 cups chopped red onion" resolves to "onion".
    """
    cleaned = _clean(raw_name)
    if not cleaned:
        return None
    if cleaned in _ALIAS_INDEX:
        return _ALIAS_INDEX[cleaned].canonical
    padded = f" {cleaned} "
    for key in _ALIAS_KEYS_BY_LEN:
        if f" {key} " in padded:
            return _ALIAS_INDEX[key].canonical
    return None


def lookup(canonical: str) -> Ingredient | None:
    return _ALIAS_INDEX.get(canonical.lower())


def all_ingredients() -> tuple[Ingredient, ...]:
    return _INGREDIENTS
