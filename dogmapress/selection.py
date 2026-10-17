"""Decide *which* cards to print, independently from storage and rendering."""
import json
from pathlib import Path
from typing import Mapping

from .models import Card, PrintItem, normalize_faction


def parse_quantities(spec: str) -> dict[str, int]:
    """Convert '1:3,2:2' into {'1': 3, '2': 2}."""
    result: dict[str, int] = {}
    if not spec.strip():
        raise ValueError("Quantity list is empty. Example: 1:3,2:2")
    for part in spec.split(","):
        if part.count(":") != 1:
            raise ValueError(f"Invalid item {part!r}; expected ID:COPIES, e.g. 1:3")
        raw_id, raw_count = (v.strip() for v in part.split(":"))
        if not raw_id or not raw_count:
            raise ValueError(f"Invalid item {part!r}; expected ID:COPIES")
        if raw_id in result:
            raise ValueError(f"Duplicate card ID {raw_id!r} in quantities.")
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise ValueError(f"Copies for {raw_id!r} must be a positive integer.") from exc
        if count < 1:
            raise ValueError(f"Copies for {raw_id!r} must be at least 1.")
        result[raw_id] = count
    return result


def load_quantities(path: str | Path) -> dict[str, int]:
    """Read a JSON object like {\"1\": 3, \"2\": 2}."""
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict) or not data:
        raise ValueError("Quantities file must be a nonempty JSON object of ID: copies.")
    # Validation lives in one place to ensure CLI and JSON behave identically.
    return parse_quantities(",".join(f"{key}:{value}" for key, value in data.items()))


def select_cards(
    cards: list[Card],
    *,
    faction: str | None = None,
    copies: int = 1,
    quantities: Mapping[str, int] | None = None,
) -> list[PrintItem]:
    """Build a print job. Quantities select only the listed IDs, in their given order.

    If no quantities are supplied, select all or all within one faction.
    """
    if quantities is not None:
        by_id = {card.id: card for card in cards}
        unknown = [card_id for card_id in quantities if card_id not in by_id]
        if unknown:
            raise ValueError(f"Card ID(s) not in data: {', '.join(unknown)}")
        if not quantities:
            raise ValueError("No card quantities supplied.")
        for card_id, count in quantities.items():
            if type(count) is not int or count < 1:
                raise ValueError(f"Copies for {card_id!r} must be a positive integer.")
        return [PrintItem(by_id[card_id], count) for card_id, count in quantities.items()]

    if copies < 1:
        raise ValueError("Copies per card must be at least 1.")
    chosen = cards if faction is None else [card for card in cards
                                            if card.faction == normalize_faction(faction)]
    if not chosen:
        raise ValueError(f"No cards found for faction {faction!r}.")
    return [PrintItem(card, copies) for card in chosen]
