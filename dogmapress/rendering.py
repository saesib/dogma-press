"""Render a single, storage-independent Card onto a PDF canvas."""
from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

from .models import Card, faction_label

# Faction palettes (RGB). Unknown faction codes receive the neutral palette.
THEMES = {
    "A": ("#D4A13D", "#FFF9EC", "#FFFDF8"),
    "D": ("#A1494C", "#FFF1F0", "#FFFCFB"),
    "N": ("#647986", "#F0F6F8", "#FFFFFF"),
    "F": ("#8666A2", "#F7F2FB", "#FFFFFF"),
    "U": ("#678A76", "#F1F8F3", "#FFFFFF"),
}

_FONT_PAIR: tuple[str, str] | None = None


def _fonts() -> tuple[str, str]:
    """Use Unicode-capable fonts already installed by the user; never bundle fonts."""
    global _FONT_PAIR
    if _FONT_PAIR is not None:
        return _FONT_PAIR
    pairs = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ]
    for regular, bold in pairs:
        if Path(regular).is_file() and Path(bold).is_file():
            pdfmetrics.registerFont(TTFont("DogmaRegular", regular))
            pdfmetrics.registerFont(TTFont("DogmaBold", bold))
            _FONT_PAIR = ("DogmaRegular", "DogmaBold")
            return _FONT_PAIR
    _FONT_PAIR = ("Helvetica", "Helvetica-Bold")
    return _FONT_PAIR


def _ascii_safe(text: str) -> str:
    """Replacement only for environments lacking Unicode fonts."""
    return (text.replace("—", "-").replace("–", "-").replace("’", "'")
            .replace("‘", "'").replace("“", '"').replace("”", '"')
            .replace("…", "...").replace("−", "-"))


def _font_text(text: str) -> str:
    return text if _fonts()[0] != "Helvetica" else _ascii_safe(text)


def _paragraph(text: str, width: float, max_height: float, *,
               font_size: float, min_font: float, leading_mult: float = 1.25,
               bold: bool = False) -> tuple[Paragraph, float]:
    """Find the largest font that fits, preserving all text and paragraph breaks."""
    face = _fonts()[1 if bold else 0]
    safe = escape(_font_text(text)).replace("\n", "<br/>")
    current = font_size
    while current >= min_font - 0.001:
        style = ParagraphStyle(
            name="fit", fontName=face, fontSize=current,
            leading=current * leading_mult, textColor=colors.HexColor("#24313D"),
            splitLongWords=True, spaceBefore=0, spaceAfter=0,
        )
        paragraph = Paragraph(safe or " ", style)
        _, height = paragraph.wrap(width, max_height)
        if height <= max_height + 0.01:
            return paragraph, height
        current = round(current - 0.25, 2)
    raise ValueError(f"Text cannot fit onto a card: {text[:65]!r} (length {len(text)}).")


def resolve_card_image(card: Card, asset_dir: Path) -> Path | None:
    """Explicit art -> card-ID art -> faction entity -> generic entity/spell -> blank."""
    files: list[Path] = []
    if card.image_path:
        image = Path(card.image_path)
        files += [image, asset_dir / image, asset_dir / "cards" / image]
    for extension in ("png", "jpg", "jpeg", "webp"):
        files.append(asset_dir / "cards" / f"{card.id}.{extension}")

    kind = card.card_type.strip().lower()
    if kind == "entity":
        flavor = {"A": "angelic", "D": "demonic", "N": "neutral"}.get(card.faction)
        if flavor:
            files += [asset_dir / "defaults" / f"entity_{flavor}.{ext}"
                      for ext in ("png", "jpg", "jpeg", "webp")]
        files += [asset_dir / "defaults" / f"entity.{ext}"
                  for ext in ("png", "jpg", "jpeg", "webp")]
    elif kind == "spell":
        files += [asset_dir / "defaults" / f"spell.{ext}"
                  for ext in ("png", "jpg", "jpeg", "webp")]
    return next((file for file in files if file.is_file()), None)


def _draw_art(c, path: Path, x: float, y: float, w: float, h: float) -> None:
    image = ImageReader(str(path))
    iw, ih = image.getSize()
    if iw <= 0 or ih <= 0:
        return
    # Contain rather than crop: important details on prototype art stay visible.
    scale = min(w / iw, h / ih)
    draw_w, draw_h = iw * scale, ih * scale
    c.drawImage(image, x + (w - draw_w) / 2, y + (h - draw_h) / 2,
                width=draw_w, height=draw_h, mask="auto")


def generate_card(c, card: Card, x: float, y: float, width: float,
                  height: float, asset_dir: Path = Path("assets")) -> None:
    """Draw one card; coordinates are in PDF points, origin at bottom-left."""
    regular, bold = _fonts()
    accent_hex, art_hex, background_hex = THEMES.get(
        card.faction, ("#78828D", "#F1F3F5", "#FFFFFF"))
    accent = colors.HexColor(accent_hex)
    ink = colors.HexColor("#24313D")
    pad = 8
    top = y + height

    c.setFillColor(colors.HexColor(background_hex))
    c.setStrokeColor(colors.HexColor("#3E4650"))
    c.setLineWidth(0.8)
    c.roundRect(x, y, width, height, radius=5, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x + 1, top - 12, width - 2, 11, radius=3.5, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont(bold, 6)
    c.drawString(x + pad, top - 9, "DEVIL'S DOGMA")
    c.drawRightString(x + width - pad, top - 9,
                      _font_text(faction_label(card.faction)).upper())

    # The cost badge is kept clear of the card name, even on two-line titles.
    cost_x, cost_y = x + width - 18, top - 27
    c.setStrokeColor(accent)
    c.setFillColor(colors.white)
    c.circle(cost_x, cost_y, 11, stroke=1, fill=1)
    if card.power_cost:
        c.setFillColor(ink)
        c.setFont(bold, 9.5)
        c.drawCentredString(cost_x, cost_y - 3.5, _font_text(card.power_cost))

    name_width = width - 2 * pad - 30
    title_para, title_height = _paragraph(card.name, name_width, 24,
                                          font_size=10.3, min_font=7.1,
                                          leading_mult=1.1, bold=True)
    title_para.drawOn(c, x + pad, top - 15 - title_height)

    # The art rectangle shrinks on text-heavy cards to prioritize readable rules.
    # The renderer tries full artwork first and progressively makes room for text.
    art_top = top - 44
    has_stats = card.card_type.strip().lower() == "entity" or bool(card.attack or card.defense)
    footer_top = y + (29 if has_stats else 17)
    has_zones = bool(card.allowed_zones)
    art_candidates = (82, 74, 66, 58, 50, 42, 34)
    solution = None
    for art_height in art_candidates:
        art_bottom = art_top - art_height
        type_baseline = art_bottom - 15
        zones_baseline = type_baseline - 14 if has_zones else None
        rules_top = (zones_baseline - 7) if has_zones else (type_baseline - 8)
        available_height = rules_top - footer_top
        if available_height <= 0:
            continue
        try:
            paragraph, text_height = _paragraph(
                card.rule_text, width - 2 * pad - 3, available_height,
                font_size=8.15, min_font=6.3, leading_mult=1.22)
        except ValueError:
            continue
        solution = (art_height, art_bottom, type_baseline,
                    zones_baseline, rules_top, paragraph, text_height)
        break
    if solution is None:
        raise ValueError(f"Rules text for card {card.id} ({card.name}) does not fit.")

    art_height, art_bottom, type_baseline, zones_baseline, rules_top, paragraph, paragraph_height = solution
    art_x, art_width = x + pad, width - 2 * pad
    c.setFillColor(colors.HexColor(art_hex))
    c.setStrokeColor(colors.HexColor("#BCC3C9"))
    c.setLineWidth(0.55)
    c.rect(art_x, art_bottom, art_width, art_height, fill=1, stroke=1)
    image = resolve_card_image(card, Path(asset_dir))
    if image:
        _draw_art(c, image, art_x + 1, art_bottom + 1,
                  art_width - 2, art_height - 2)

    c.setFillColor(accent)
    c.rect(x + pad, type_baseline - 2, width - 2 * pad, 12, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(bold, 7.0)
    type_text = _font_text(card.type_line)
    if pdfmetrics.stringWidth(type_text, bold, 7) > width - 2 * pad - 8:
        para, ph = _paragraph(card.type_line, width - 2 * pad - 8, 11,
                              font_size=7, min_font=5.5, bold=True, leading_mult=1)
        para.style.textColor = colors.white
        para.drawOn(c, x + pad + 4, type_baseline + 9 - ph)
    else:
        c.drawString(x + pad + 4, type_baseline + 1, type_text)

    if has_zones:
        c.setFillColor(colors.HexColor("#596674"))
        c.setFont(regular, 6.25)
        zones = " / ".join(card.allowed_zones)
        zones_text = _font_text("ZONES: " + zones)
        size = 6.25
        while pdfmetrics.stringWidth(zones_text, regular, size) > width - 2 * pad and size > 4.5:
            size -= 0.25
        c.setFont(regular, size)
        c.drawString(x + pad, zones_baseline, zones_text)

    # Newlines and wrapped text are preserved by Paragraph.
    if card.rule_text:
        paragraph.drawOn(c, x + pad + 1, rules_top - paragraph_height)

    c.setStrokeColor(colors.HexColor("#C6CCD2"))
    c.setLineWidth(0.45)
    c.line(x + pad, footer_top - 4, x + width - pad, footer_top - 4)
    c.setFillColor(colors.HexColor("#64707D"))
    c.setFont(regular, 6.0)
    if has_stats:
        c.drawCentredString(x + width / 2, y + 7, "#" + _font_text(card.id))
    else:
        c.drawString(x + pad, y + 7, "#" + _font_text(card.id))

    if has_stats:
        # Display empty values as empty. Inanimate objects often have no ATK.
        c.setFillColor(colors.HexColor("#63707B"))
        c.setFont(regular, 6)
        c.drawString(x + pad, y + 17, "ATK")
        c.drawRightString(x + width - pad, y + 17, "DEF")
        if card.attack:
            c.setFillColor(ink)
            c.setFont(bold, 10)
            c.drawString(x + pad, y + 6, _font_text(card.attack))
        if card.defense:
            c.setFillColor(ink)
            c.setFont(bold, 10)
            c.drawRightString(x + width - pad, y + 6, _font_text(card.defense))
