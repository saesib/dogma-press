# DogmaPress

A small Python utility to turn **Devil's Dogma TCG** card records into **print-and-play PDF sheets**. Card data is independent of input format and PDF layout, allowing a future SQL adapter or new visual layouts.

## Quick start (Windows / macOS / Linux)

Requires Python **3.10+**.

```bash
python -m pip install -r requirements.txt
python main.py
```

On Windows, `py` can be used instead of `python`. The interactive CLI uses `csv/cards.csv` by default. The provided ZIP contains your uploaded CSV in that folder to let you try it immediately (the folder is Git-ignored).

## Noninteractive commands

```bash
# One of every card
python main.py --all --output outputs/all_cards.pdf

# Angelic / Demonic / Neutral, one each
python main.py --faction A --output outputs/angels.pdf
python main.py --faction D --output outputs/demons.pdf
python main.py --faction N --output outputs/neutral.pdf

# Two of every Angelic card
python main.py --faction angelic --copies 2 --output outputs/two_angels.pdf

# Card #1 three times and card #2 twice (ONLY these cards)
python main.py --quantities "1:3,2:2" --output outputs/my_deck.pdf

# The same idea from a JSON file
python main.py --quantities-file sample_quantities.json

# Input from somewhere else
python main.py --csv path/to/cards.csv --all

# View all currently represented factions, including unfinished ones
python main.py --list-factions

# US paper and no exterior cut guides
python main.py --all --paper letter --no-guides
```

## Printing multiple copies and Legends

DogmaPress supports printing multiple copies of cards, with an optional override for Legend cards.

A card is a Legend if its `Subtype` includes `Legend` (case-insensitive), e.g. `Demon - Legend`. `--legend-copies` applies to `--all` and `--faction` jobs; explicit `--quantities` always win.

### Examples

```bash
# Three copies of every Demonic card
python main.py --faction D --copies 3

# Three copies of every Demonic card, but only one of each Legend
python main.py --faction D --copies 3 --legend-copies 1
```

Use **Print at Actual Size / 100%**, not *Fit to Page*, to preserve card dimensions.

## Design and code organization

```text
dogma-press/
├── main.py                    # Tiny CLI entrypoint
├── dogmapress/
│   ├── models.py              # Card, PrintItem, PDFOptions
│   ├── data.py                # CardSource interface, CSV reader, read_data()
│   ├── selection.py           # All / faction / custom ID-quantity jobs
│   ├── rendering.py           # generate_card() and artwork resolution
│   ├── pdf.py                 # generate_pdf() and printable page layout
│   └── cli.py                 # argparse and interactive CLI
├── csv/cards.csv             # Your uploaded CSV (ignored by Git)
├── assets/
│   ├── cards/                # Individual card pictures, e.g. 1.png
│   └── defaults/             # Entity/spell fallback art
├── outputs/                   # Generated PDFs (ignored by Git)
├── sample_quantities.json
└── tests/
```

The data flow is:

`CSVCardSource → list[Card] → select_cards() → list[PrintItem] → generate_pdf() → generate_card()`

A future `SQLCardSource` only needs to implement `read_cards() -> list[Card]`. PDF generation takes `Card` objects, not CSV rows.

## Artwork fallback rules

For each card, the first existing image wins:

1. Optional CSV column `Image`, `ImagePath`, or `Artwork` (an explicit path relative to the project or `assets/`/`assets/cards/`).
2. `assets/cards/<ID>.png` or `.jpg`, `.jpeg`, `.webp` (for example `assets/cards/1.png`).
3. For Entities: `assets/defaults/entity_angelic.png`, `entity_demonic.png`, or `entity_neutral.png` according to faction; otherwise `entity.png`. Extension variants are also supported.
4. For Spells: `assets/defaults/spell.png` (or extension variants).
5. **No image:** a clean, empty artwork rectangle. There is no required artwork file.

Add assets when you have them. **There are no generated/stock images** in this prototype.

## CSV format

Required columns: `ID`, `Name`, `Faction`, `Type`. The parser recognizes optional `Subtype`, `PowerCost`, `AllowedZones`, `Attack`, `Defense`, `RuleText`, and `ImagePath` / `Image` / `Artwork`.

- `AllowedZones`: semicolon-separated zones like `Frontline;Midline`.
- `Faction`: short codes such as `A`, `D`, `N`, or full names `Angelic`, `Demonic`, `Neutral`.
- Rows whose faction is `TBD` (case-insensitive) are ignored when importing the CSV. Other unknown and empty factions are retained and can be selected by their exact code in the CLI (or from the menu).
- Missing optional data leaves blank fields and still generates a card.
- The CSV reader checks required headers, duplicate IDs, and missing IDs, and preserves multiline rules text.

## Print options

- A4 (default) or US Letter.
- Standard card frame dimensions: **63 × 88 mm**.
- 3 columns × 3 rows = **9 cards per page**, with configurable gap (`--gutter-mm`, default 2.5).
- Thin card outlines and exterior cut marks (disable exterior marks with `--no-guides`).
- Rules font size and artwork space adapt automatically to fit text; it raises an error rather than knowingly clipping overlong rules.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Starting a Git repository

```bash
git init
git add .
git commit -m "Initial DogmaPress prototype"
```

`csv/` and `outputs/` are in `.gitignore`, so the included sample card database and generated printouts will **not** be committed. Put public fixtures in a separate tracked folder if you want collaborators to have test data.

## Future extensions

Because the project separates the core stages, we can add SQLite/PostgreSQL, a deck-list importer, card backs, bleed margins, alternate templates, a GUI, or different card sizes without changing the other modules.

For example, adding SQL later looks like this conceptually:

```python
class SQLCardSource:
    def __init__(self, connection):
        self.connection = connection

    def read_cards(self) -> list[Card]:
        # Query DB records and return normalized Card(...) objects.
        ...

cards = read_data(SQLCardSource(connection))
# select_cards(), generate_card(), and generate_pdf() do not change.
```
