import csv
from contextlib import ExitStack
from io import BytesIO
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reportlab.pdfgen import canvas

from dogmapress.data import CSVCardSource, read_csv, read_data
from dogmapress.models import Card, PDFOptions
from dogmapress.pdf import generate_pdf
from dogmapress.rendering import generate_card, resolve_card_image
from dogmapress.selection import parse_quantities, select_cards


class CardDataTests(unittest.TestCase):
    def setUp(self):
        self.cards = read_data(Path(__file__).resolve().parents[1] / "csv" / "cards.csv")

    def test_csv_matches_uploaded_data(self):
        self.assertEqual(len(self.cards), 52)
        self.assertEqual(self.cards[0].id, "1")
        self.assertEqual(self.cards[0].faction, "D")
        self.assertEqual(self.cards[0].allowed_zones, ("Frontline", "Midline"))
        self.assertIn("\n", self.cards[0].rule_text)
        self.assertNotIn("TBD", {card.faction for card in self.cards})

    def test_all_one_each(self):
        selected = select_cards(self.cards)
        self.assertEqual(len(selected), 52)
        self.assertEqual(sum(x.copies for x in selected), 52)

    def test_faction_filter_and_full_name(self):
        self.assertEqual(len(select_cards(self.cards, faction="angelic")), 22)
        self.assertEqual(len(select_cards(self.cards, faction="D")), 18)
        self.assertEqual(len(select_cards(self.cards, faction="N")), 5)
        with self.assertRaisesRegex(ValueError, "No cards found"):
            select_cards(self.cards, faction="TBD")
        self.assertEqual(len(select_cards(self.cards, faction="unassigned")), 1)

    def test_custom_quantities(self):
        quantities = parse_quantities("1:3,2:2")
        selected = select_cards(self.cards, quantities=quantities)
        self.assertEqual([(item.card.id, item.copies) for item in selected],
                         [("1", 3), ("2", 2)])

    def test_missing_id_error(self):
        with self.assertRaisesRegex(ValueError, "not in data"):
            select_cards(self.cards, quantities={"999": 1})

    def test_invalid_quantities(self):
        for value in ("1:0", "1:-2", "1:foo", "1", "1:2,1:3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_quantities(value)

    def test_duplicate_csv_id_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "example.csv"
            path.write_text("ID,Name,Faction,Type\n1,One,A,Entity\n1,Two,D,Spell\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                read_csv(path)

    def test_tbd_faction_rows_are_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "example.csv"
            path.write_text(
                "ID,Name,Faction,Type\n1,Keep me,A,Entity\n2,Skip me, tBd ,Entity\n",
                encoding="utf-8",
            )

            cards = read_csv(path)

            self.assertEqual([card.id for card in cards], ["1"])

    def test_art_fallback_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "defaults").mkdir()
            (root / "cards").mkdir()
            default_art = root / "defaults" / "entity_demonic.png"
            default_art.touch()
            self.assertEqual(resolve_card_image(self.cards[0], root), default_art)
            card_art = root / "cards" / "1.jpg"
            card_art.touch()
            self.assertEqual(resolve_card_image(self.cards[0], root), card_art)
            self.assertIsNone(resolve_card_image(self.cards[1], root))

    def test_attack_and_defense_are_aligned_to_opposite_bottom_corners(self):
        pdf = canvas.Canvas(BytesIO())
        recorded = {}
        x, y, width, height = 10, 20, 180, 250
        with ExitStack() as stack:
            for method_name in ("drawString", "drawRightString", "drawCentredString"):
                original = getattr(pdf, method_name)

                def record_and_draw(x, y, text, *, _method=method_name, _original=original):
                    recorded[text] = (_method, x, y)
                    _original(x, y, text)

                stack.enter_context(patch.object(
                    pdf, method_name, side_effect=record_and_draw))

            generate_card(pdf, Card(
                id="42", name="Test Entity", faction="D", card_type="Entity",
                attack="7", defense="9",
            ), x, y, width, height, asset_dir=Path("missing-assets"))

            self.assertEqual(recorded["ATK"], ("drawString", x + 8, y + 17))
            self.assertEqual(recorded["7"], ("drawString", x + 8, y + 6))
            self.assertEqual(recorded["DEF"], ("drawRightString", x + width - 8, y + 17))
            self.assertEqual(recorded["9"], ("drawRightString", x + width - 8, y + 6))
            self.assertEqual(recorded["#42"],
                             ("drawCentredString", x + width / 2, y + 7))

    def test_pdf_smoke(self):
        with tempfile.TemporaryDirectory() as folder:
            result = generate_pdf(select_cards(self.cards, quantities={"1": 3, "2": 2}),
                                  Path(folder) / "nested" / "test.pdf",
                                  PDFOptions(asset_dir=Path(folder) / "no_assets"))
            self.assertTrue(result.exists())
            self.assertGreater(result.stat().st_size, 1000)
            self.assertEqual(result.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
