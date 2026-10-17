"""Interactive CLI and noninteractive command-line interface."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from .data import read_data
from .models import PDFOptions, Card, faction_label
from .pdf import generate_pdf
from .selection import load_quantities, parse_quantities, select_cards


def _faction_counts(cards: list[Card]) -> list[tuple[str, int]]:
    counts = Counter(card.faction for card in cards)
    return sorted(counts.items(), key=lambda pair: (pair[0] not in ("A", "D", "N"), pair[0]))


def _interactive_selection(cards: list[Card]) -> tuple[str | None, dict[str, int] | None]:
    print(f"\nLoaded {len(cards)} cards.\n")
    print("1. Print ALL cards (one copy of each)")
    factions = _faction_counts(cards)
    for i, (code, count) in enumerate(factions, start=2):
        code_display = code if code else "empty"
        print(f"{i}. Print {faction_label(code)} [{code_display}] ({count} cards)")
    custom = len(factions) + 2
    listing = custom + 1
    print(f"{custom}. Print specific card IDs with custom quantities")
    print(f"{listing}. List cards and IDs")
    while True:
        choice = input("\nChoose an option: ").strip()
        if choice == "1":
            return None, None
        if choice.isdigit() and 2 <= int(choice) <= len(factions) + 1:
            return factions[int(choice) - 2][0], None
        if choice == str(custom):
            print("Enter quantities like 1:3,2:2 (prints three of #1 and two of #2)")
            try:
                return None, parse_quantities(input("Quantities: ").strip())
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
        if choice == str(listing):
            for card in cards:
                print(f"  #{card.id:>3}  {card.name} [{card.faction or 'empty'}]")
            continue
        print("Unknown menu option. Please try again.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dogmapress", description="Generate printable Devil's Dogma card sheets from CSV.")
    parser.add_argument("--csv", type=Path, default=Path("csv/cards.csv"),
                        help="Input CSV (default: csv/cards.csv)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="Print all cards (default when using flags)")
    mode.add_argument("--faction", help="Faction code/name, e.g. A, D, N, Angelic")
    mode.add_argument("--quantities", metavar="ID:COPIES,...",
                      help="Only listed IDs, e.g. 1:3,2:2")
    mode.add_argument("--quantities-file", type=Path, metavar="FILE.json",
                      help='Read quantities from JSON like {"1":3,"2":2}')
    parser.add_argument("--copies", type=int, default=1,
                        help="Copies of every card in --all or --faction (default: 1)")
    parser.add_argument("--output", type=Path, default=Path("outputs/devils_dogma_print.pdf"),
                        help="Output PDF path")
    parser.add_argument("--assets", type=Path, default=Path("assets"),
                        help="Root artwork directory")
    parser.add_argument("--paper", choices=("a4", "letter"), default="a4")
    parser.add_argument("--gutter-mm", type=float, default=0.2)
    parser.add_argument("--no-guides", action="store_true", help="Disable exterior cut ticks")
    parser.add_argument("--list-factions", action="store_true", help="List faction counts and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        interactive = not (argv if argv is not None else __import__("sys").argv[1:])
        if interactive:
            chosen_csv = input(f"Input CSV [{args.csv}]: ").strip()
            if chosen_csv:
                args.csv = Path(chosen_csv)
        cards = read_data(args.csv)
        if args.list_factions:
            for code, count in _faction_counts(cards):
                print(f"{code or '(empty)'} / {faction_label(code)}: {count}")
            return 0
        if not cards:
            raise ValueError("No cards were found in the input CSV.")
        if args.quantities is not None or args.quantities_file:
            if args.copies != 1:
                raise ValueError("--copies cannot be used with custom quantities.")
            quantities = (parse_quantities(args.quantities) if args.quantities is not None
                          else load_quantities(args.quantities_file))
            selection = select_cards(cards, quantities=quantities)
        elif args.faction is not None:
            selection = select_cards(cards, faction=args.faction, copies=args.copies)
        elif args.all or not interactive:
            selection = select_cards(cards, copies=args.copies)
        else:
            faction, quantities = _interactive_selection(cards)
            selection = (select_cards(cards, quantities=quantities) if quantities is not None
                         else select_cards(cards, faction=faction))

        if interactive:
            chosen_output = input(f"Output PDF [{args.output}]: ").strip()
            if chosen_output:
                args.output = Path(chosen_output)

        output = generate_pdf(
            selection, args.output,
            PDFOptions(paper=args.paper, asset_dir=args.assets,
                       gutter_mm=args.gutter_mm, show_guides=not args.no_guides))
        print(f"\nCreated {output} ({sum(item.copies for item in selection)} cards, "
              f"{(sum(item.copies for item in selection) + 8) // 9} pages)")
        print("Print at 100% / Actual size; disable Fit to Page to preserve dimensions.")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
