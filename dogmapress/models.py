"""Game-specific, storage-independent data models."""
from dataclasses import dataclass
from pathlib import Path


FACTION_LABELS = {
    "A": "Angelic",
    "D": "Demonic",
    "N": "Neutral",
    # Do not guess the meanings of work-in-progress faction codes.
    "F": "F",
    "U": "U",
    "TBD": "TBD",
    "": "Unassigned",
}

FACTION_ALIASES = {
    "ANGEL": "A", "ANGELS": "A", "ANGELIC": "A",
    "DEMON": "D", "DEMONS": "D", "DEMONIC": "D",
    "NEUTRAL": "N", "UNASSIGNED": "", "BLANK": "",
}


def normalize_faction(value: str) -> str:
    """Accept an existing code or a common human-friendly faction name."""
    normalized = value.strip().upper()
    return FACTION_ALIASES.get(normalized, normalized)


def faction_label(code: str) -> str:
    return FACTION_LABELS.get(code, code or "Unassigned")


@dataclass(frozen=True)
class Card:
    id: str  # String permits future database identifiers as well as CSV integers.
    name: str
    faction: str
    card_type: str
    subtype: str = ""
    power_cost: str = ""
    allowed_zones: tuple[str, ...] = ()
    attack: str = ""
    defense: str = ""
    rule_text: str = ""
    image_path: str = ""  # Optional image reference from an Image/ImagePath CSV column.

    @property
    def type_line(self) -> str:
        return " — ".join(part for part in (self.card_type, self.subtype) if part) or "Type TBD"


@dataclass(frozen=True)
class PrintItem:
    card: Card
    copies: int


@dataclass(frozen=True)
class PDFOptions:
    paper: str = "a4"
    asset_dir: Path = Path("assets")
    show_guides: bool = True
    gutter_mm: float = 0.2
