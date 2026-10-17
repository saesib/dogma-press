"""Load cards through a CardSource. Swap adapters without changing consumers."""
import csv
from pathlib import Path
from typing import Protocol

from .models import Card, normalize_faction


class CardSource(Protocol):
    def read_cards(self) -> list[Card]: ...


class CSVCardSource:
    REQUIRED_COLUMNS = {"id", "name", "faction", "type"}

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read_cards(self) -> list[Card]:
        with self.path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise ValueError("CSV is empty or has no header row.")
            column_names = {(key or "").strip().lower() for key in reader.fieldnames}
            missing = self.REQUIRED_COLUMNS - column_names
            if missing:
                raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")

            cards: list[Card] = []
            known_ids: set[str] = set()
            for line_no, record in enumerate(reader, start=2):
                if not any(value and value.strip() for value in record.values() if isinstance(value, str)):
                    continue  # Empty lines in CSV should not become cards.

                row = {str(k).strip().lower(): (v or "").strip()
                       for k, v in record.items() if k is not None}
                faction = normalize_faction(row.get("faction", ""))
                if faction == "TBD":
                    continue
                card_id = row.get("id", "")
                if not card_id:
                    raise ValueError(f"Missing card ID near CSV record {line_no}.")
                if card_id in known_ids:
                    raise ValueError(f"Duplicate card ID {card_id!r} near CSV record {line_no}.")
                known_ids.add(card_id)

                zones = tuple(part.strip() for part in row.get("allowedzones", "").split(";")
                              if part.strip())
                cards.append(Card(
                    id=card_id,
                    name=row.get("name", "") or f"Untitled #{card_id}",
                    faction=faction,
                    card_type=row.get("type", ""),
                    subtype=row.get("subtype", ""),
                    power_cost=row.get("powercost", ""),
                    allowed_zones=zones,
                    attack=row.get("attack", ""),
                    defense=row.get("defense", ""),
                    rule_text=row.get("ruletext", ""),
                    image_path=(row.get("imagepath") or row.get("image")
                                or row.get("artwork") or ""),
                ))
            return cards


def read_csv(path: str | Path) -> list[Card]:
    """Read a CSV and turn rows into normalized Card objects."""
    return CSVCardSource(path).read_cards()


def read_data(source: CardSource | str | Path) -> list[Card]:
    """Storage-agnostic entrypoint: read_data(CSVCardSource(path)) today.

    A future SQLCardSource simply needs a read_cards() method returning Card objects.
    Paths are accepted as a convenience and treated as CSV files.
    """
    if isinstance(source, (str, Path)):
        source = CSVCardSource(source)
    return source.read_cards()
