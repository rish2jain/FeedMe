"""Instacart staging (design.md Section 4).

Instacart's Developer Platform exposes an MCP server with a `create-shopping-list`
tool that maps line items to real products at a chosen retailer and returns a
shopping-list page URL; a human taps through store selection and checkout. This is
the "agent prepares, human executes" purchase gate.

This module builds the exact payload that tool expects from a GroceryList and
returns a staging object. The actual MCP call is made by the orchestrator (the
`pantry-local` server calls Instacart's MCP server). When no client is wired in,
``stage_shopping_list`` returns the payload plus a placeholder URL so the rest of
the pipeline is testable end-to-end without network or credentials.

Only the delivery-default channels (ShopRite/mainstream) are staged to Instacart;
Patel and Costco are in-person trips and are returned as human-readable sublists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..ontology import CHANNEL_SHOPRITE
from ..planning.grocery import GroceryList


@dataclass
class InstacartStaging:
    payload: dict
    url: str
    in_person_sublists: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "payload": self.payload,
            "url": self.url,
            "in_person_sublists": self.in_person_sublists,
        }


def _title_case(canonical: str) -> str:
    return canonical.title()


def build_payload(grocery: GroceryList, title: str = "FeedMe weekly list") -> dict:
    """Build the `create-shopping-list` payload from the delivery channels."""
    line_items = []
    for ch in grocery.channels:
        if ch.channel != CHANNEL_SHOPRITE:
            continue
        for item in ch.items:
            line_items.append({
                "name": _title_case(item.canonical),
                "quantity": 1,
                "display_text": _title_case(item.canonical),
            })
    return {
        "title": title,
        "link_type": "shopping_list",
        "line_items": line_items,
    }


def stage_shopping_list(
    grocery: GroceryList,
    title: str = "FeedMe weekly list",
    mcp_client: Callable[[dict], str] | None = None,
) -> InstacartStaging:
    """Stage the delivery list to Instacart.

    ``mcp_client`` is an optional callable that takes the payload and returns a
    shopping-list URL (the real Instacart MCP `create-shopping-list` call). When
    omitted, a deterministic placeholder URL is returned so the human-review gate
    and downstream flow remain testable.
    """
    payload = build_payload(grocery, title)

    # In-person channels are surfaced as sublists, never staged to delivery.
    in_person: dict[str, list[str]] = {}
    for ch in grocery.channels:
        if ch.channel == CHANNEL_SHOPRITE:
            continue
        in_person[ch.label] = [
            _title_case(i.canonical) + ("  [Patel-preferred]" if i.patel_preferred else "")
            for i in sorted(ch.items, key=lambda x: (x.aisle, x.canonical))
        ]

    if mcp_client is not None:
        url = mcp_client(payload)
    else:
        url = "https://customers.instacart.com/store/shopping_lists/STAGED_LOCALLY"

    return InstacartStaging(payload=payload, url=url, in_person_sublists=in_person)
