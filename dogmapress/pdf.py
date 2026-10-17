"""Position rendered cards onto a cut-ready print sheet."""
from pathlib import Path
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import PDFOptions, PrintItem
from .rendering import generate_card

CARD_WIDTH = 63 * mm
CARD_HEIGHT = 88 * mm
COLUMNS = 3
ROWS = 3
PER_PAGE = COLUMNS * ROWS
PAPERS = {"a4": A4, "letter": letter}


def _draw_cut_marks(c: canvas.Canvas, x: float, y: float,
                    w: float, h: float, gutter: float) -> None:
    """Subtle exterior tick marks, kept within gaps and page margins."""
    length = min(1.7 * mm, gutter * 0.43)
    c.setStrokeColorRGB(0.42, 0.45, 0.48)
    c.setLineWidth(0.3)
    for cx, direction in ((x, -1), (x + w, 1)):
        for cy, vertical in ((y, -1), (y + h, 1)):
            c.line(cx + direction * (0.35 * mm), cy,
                   cx + direction * length, cy)
            c.line(cx, cy + vertical * (0.35 * mm),
                   cx, cy + vertical * length)


def generate_pdf(items: list[PrintItem], output: str | Path,
                 options: PDFOptions | None = None) -> Path:
    """Render a 3x3 print sheet with exact 63x88 mm card dimensions."""
    options = options or PDFOptions()
    if not items or sum(item.copies for item in items) < 1:
        raise ValueError("Cannot generate an empty PDF.")
    if options.paper.lower() not in PAPERS:
        raise ValueError("Paper must be 'a4' or 'letter'.")
    if options.gutter_mm < 0:
        raise ValueError("Gutter size cannot be negative.")
    for item in items:
        if not isinstance(item.copies, int) or item.copies < 1:
            raise ValueError(f"Invalid copies for {item.card.name!r}.")

    page_w, page_h = PAPERS[options.paper.lower()]
    gutter = options.gutter_mm * mm
    layout_w = COLUMNS * CARD_WIDTH + (COLUMNS - 1) * gutter
    layout_h = ROWS * CARD_HEIGHT + (ROWS - 1) * gutter
    if layout_w > page_w or layout_h > page_h:
        raise ValueError("Cards do not fit on this paper with the current gutter.")
    left = (page_w - layout_w) / 2
    bottom = (page_h - layout_h) / 2
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(destination), pagesize=(page_w, page_h), pageCompression=1)
    c.setTitle("Devil's Dogma - Print-and-Play Cards")
    c.setAuthor("DogmaPress")
    index = 0
    for item in items:
        for _ in range(item.copies):
            if index and index % PER_PAGE == 0:
                c.showPage()
            position = index % PER_PAGE
            col, row = position % COLUMNS, position // COLUMNS
            x = left + col * (CARD_WIDTH + gutter)
            y = page_h - bottom - CARD_HEIGHT - row * (CARD_HEIGHT + gutter)
            try:
                generate_card(c, item.card, x, y, CARD_WIDTH, CARD_HEIGHT,
                              asset_dir=options.asset_dir)
            except Exception as exc:
                raise RuntimeError(f"Failed to render #{item.card.id} {item.card.name}: {exc}") from exc
            if options.show_guides:
                _draw_cut_marks(c, x, y, CARD_WIDTH, CARD_HEIGHT, gutter)
            index += 1
    c.save()
    return destination
