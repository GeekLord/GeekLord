"""
Design system for the GeekLord profile assets.

Every graphic that appears on the public profile README is generated from this
module, so the whole page shares one set of colours, one type scale and one set
of spacing rules. Change a token here and every asset moves together.

Typefaces are subset to only the glyphs an individual graphic actually uses and
embedded as base64 woff2, because browsers deliberately refuse to load external
fonts inside an SVG that is referenced with an <img> tag (which is exactly how
GitHub renders README images).
"""

from __future__ import annotations

import base64
import functools
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).resolve().parent / "fonts"

# --------------------------------------------------------------------------
# Theme tokens
# --------------------------------------------------------------------------

# Palette: wine red on Pampas.
#   Light mode is Pampas paper (#F4F2EE) carrying wine ink (#722F37).
#   Dark mode is a wine cellar: near-black claret surfaces lit by Pampas text,
#   with the wine lifted in lightness so it still reads at small sizes.
# Role names are semantic: `wine` is the primary accent, `rose` the secondary,
# `brass` a warm highlight and `sage` the "live / available" status colour.

DARK = {
    "name": "dark",
    "ink": "#F4F2EE",  # Pampas — primary text
    "ink_soft": "#E2D8CE",  # secondary text
    "muted": "#BCA9A3",  # labels
    "faint": "#A08D89",  # de-emphasised text (still >= 4.5:1 on panel)
    "display": "#F4F2EE",  # the name in the banner
    "canvas": "#1A0E11",
    "panel": "#221318",
    "panel_alt": "#2A171D",
    "line": "#4A2A32",
    "line_soft": "#382027",
    "wine": "#D46B7A",  # wine lifted for a dark ground
    "rose": "#EBA9B0",
    "brass": "#D9AE68",
    "sage": "#A3BF94",
    "chip_bg": "#2A171D",
    "chip_line": "#553039",
    "glow": "0.85",
    "grid": "#3A2229",
    "cell0": "#2C1A1F",
    "cell1": "#55262F",
    "cell2": "#8A3443",
    "cell3": "#C2546A",
    "cell4": "#F0B3B9",
    "shadow": "#0A0506",
}

LIGHT = {
    "name": "light",
    "ink": "#2A1216",  # wine-black
    "ink_soft": "#4E2E33",
    "muted": "#6B5054",
    "faint": "#725A5E",
    "display": "#722F37",  # wine red
    "canvas": "#F4F2EE",  # Pampas
    "panel": "#EFEBE5",
    "panel_alt": "#E8E1D8",
    "line": "#DCD2C6",
    "line_soft": "#E6DED3",
    "wine": "#722F37",
    "rose": "#9C3B4A",
    "brass": "#7C5A1B",
    "sage": "#46663F",
    "chip_bg": "#FAF8F5",
    "chip_line": "#DCCFC4",
    "glow": "0.55",
    "grid": "#DDD3C7",
    "cell0": "#E6DFD5",
    "cell1": "#E5C2C3",
    "cell2": "#C9838C",
    "cell3": "#9C3B4A",
    "cell4": "#5E1F28",
    "shadow": "#D9CEC0",
}

THEMES = {"dark": DARK, "light": LIGHT}

# --------------------------------------------------------------------------
# Typography
# --------------------------------------------------------------------------

FONTS = {
    ("display", 400): "SpaceGrotesk-Regular.ttf",
    ("display", 500): "SpaceGrotesk-Medium.ttf",
    ("display", 600): "SpaceGrotesk-SemiBold.ttf",
    ("display", 700): "SpaceGrotesk-Bold.ttf",
    ("mono", 400): "JetBrainsMono-Regular.ttf",
    ("mono", 600): "JetBrainsMono-SemiBold.ttf",
}

FAMILY_CSS_NAME = {"display": "SpaceGrotesk", "mono": "JetBrainsMono"}


@functools.lru_cache(maxsize=64)
def _load_ttf(path: str) -> TTFont:
    return TTFont(path, lazy=True)


@functools.lru_cache(maxsize=4096)
def text_width(text: str, family: str, weight: int, size: float, tracking: float = 0.0) -> float:
    """Advance width of `text` in user units, matching how a browser lays it out."""
    font = _load_ttf(str(FONT_DIR / FONTS[(family, weight)]))
    upem = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    total = 0
    for char in text:
        glyph = cmap.get(ord(char))
        if glyph is None:
            continue
        total += hmtx[glyph][0]
    width = total / upem * size
    width += tracking * size * max(len(text) - 1, 0)
    return round(width, 2)


@functools.lru_cache(maxsize=512)
def _subset_b64(filename: str, chars: str) -> str:
    """Subset a font to `chars` and return it as a base64 woff2 payload."""
    options = subset.Options()
    options.flavor = "woff2"
    options.desubroutinize = True
    options.drop_tables += ["DSIG"]
    options.layout_features = ["kern", "liga", "calt"]
    options.notdef_outline = True
    options.recalc_bounds = True

    font = subset.load_font(str(FONT_DIR / filename), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=chars)
    subsetter.subset(font)

    buffer = BytesIO()
    subset.save_font(font, buffer, options)
    font.close()
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class FontBook:
    """Collects the characters actually used, then emits minimal @font-face CSS."""

    def __init__(self) -> None:
        self._chars: dict[tuple[str, int], set[str]] = {}

    def use(self, text: str, family: str, weight: int) -> str:
        self._chars.setdefault((family, weight), set()).update(text)
        missing = [
            char for char in text
            if ord(char) not in _load_ttf(str(FONT_DIR / FONTS[(family, weight)])).getBestCmap()
        ]
        if missing:
            raise ValueError(
                f"{FONTS[(family, weight)]} has no glyph for {sorted(set(missing))} "
                f"used in {text!r} — reword the copy or draw the shape as a path."
            )
        return escape(text)

    def css(self, with_theme_media: bool = False) -> str:
        rules = []
        for (family, weight), chars in sorted(self._chars.items()):
            payload = _subset_b64(FONTS[(family, weight)], "".join(sorted(chars)))
            rules.append(
                "@font-face{font-family:'%s';font-style:normal;font-weight:%d;"
                "font-display:block;src:url(data:font/woff2;base64,%s) format('woff2');}"
                % (FAMILY_CSS_NAME[family], weight, payload)
            )
        return "".join(rules)


# --------------------------------------------------------------------------
# Low level drawing helpers
# --------------------------------------------------------------------------


def accent_gradient(theme: dict, gradient_id: str = "accent", x1=0, y1=0, x2=1, y2=1) -> str:
    return (
        f'<linearGradient id="{gradient_id}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
        f'<stop offset="0" stop-color="{theme["wine"]}"/>'
        f'<stop offset="1" stop-color="{theme["rose"]}"/>'
        "</linearGradient>"
    )


def svg_open(width: float, height: float, theme: dict, extra_defs: str = "", title: str = "") -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
        f'style="color:{theme["ink"]}" '
        f'font-family="SpaceGrotesk, Segoe UI, Helvetica, Arial, sans-serif">'
    ]
    if title:
        parts.append(f"<title>{escape(title)}</title>")
    parts.append("<defs>")
    parts.append(accent_gradient(theme))
    parts.append(extra_defs)
    parts.append("</defs>")
    return "".join(parts)


def text(
    x: float,
    y: float,
    content: str,
    *,
    book: FontBook,
    family: str = "display",
    weight: int = 400,
    size: float = 16,
    fill: str = "currentColor",
    anchor: str = "start",
    tracking: float = 0.0,
    opacity: float | None = None,
    extra: str = "",
    gradient: str | None = None,
) -> str:
    body = book.use(content, family, weight)
    attrs = [
        f'x="{x:.2f}"',
        f'y="{y:.2f}"',
        f'font-size="{size:.2f}"',
        f'font-weight="{weight}"',
        f'font-family="{FAMILY_CSS_NAME[family]}, {"monospace" if family == "mono" else "sans-serif"}"',
    ]
    if gradient:
        attrs.append(f'fill="url(#{gradient})"')
    elif fill != "currentColor":
        attrs.append(f'fill="{fill}"')
    else:
        attrs.append('fill="currentColor"')
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if tracking:
        attrs.append(f'letter-spacing="{tracking:.3f}em"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity}"')
    if extra:
        attrs.append(extra)
    return f"<text {' '.join(attrs)}>{body}</text>"


def rect(x, y, w, h, **kwargs) -> str:
    attrs = [f'x="{x:.2f}"', f'y="{y:.2f}"', f'width="{w:.2f}"', f'height="{h:.2f}"']
    for key, value in kwargs.items():
        key = key.rstrip("_").replace("_", "-")
        attrs.append(f'{key}="{value}"')
    return f"<rect {' '.join(attrs)}/>"


def line(x1, y1, x2, y2, *, stroke: str = "currentColor", width: float = 1, opacity: float | None = None,
         dash: str | None = None) -> str:
    attrs = [
        f'x1="{x1:.2f}"', f'y1="{y1:.2f}"', f'x2="{x2:.2f}"', f'y2="{y2:.2f}"',
        f'stroke="{stroke}"', f'stroke-width="{width}"',
    ]
    if opacity is not None:
        attrs.append(f'stroke-opacity="{opacity}"')
    if dash:
        attrs.append(f'stroke-dasharray="{dash}"')
    return f"<line {' '.join(attrs)}/>"


def panel(x, y, w, h, theme: dict, *, radius: float = 18, fill: str | None = None,
          stroke: str | None = None, stroke_opacity: float = 1.0) -> str:
    return rect(
        x, y, w, h, rx=radius,
        fill=fill or theme["panel"],
        stroke=stroke or theme["line"],
        stroke_opacity=stroke_opacity,
    )


def chip(x, y, label: str, theme: dict, book: FontBook, *, size: float = 12.5,
         pad_x: float = 13, height: float = 27, tracking: float = 0.02,
         accent: str | None = None, weight: int = 400, mono: bool = True) -> tuple[str, float]:
    """A small labelled pill. Returns (markup, width_consumed)."""
    family = "mono" if mono else "display"
    label_width = text_width(label, family, weight, size, tracking)
    width = label_width + pad_x * 2
    markup = [
        rect(x, y, width, height, rx=height / 2, fill=theme["chip_bg"],
             stroke=accent or theme["chip_line"], stroke_opacity=0.9 if accent else 1),
        text(x + pad_x, y + height / 2 + size * 0.35, label, book=book, family=family,
             weight=weight, size=size, fill=accent or theme["ink_soft"], tracking=tracking),
    ]
    return "".join(markup), width


def dotted_grid(x, y, cols, rows, gap, radius, colour, opacity=1.0) -> str:
    circles = []
    for row in range(rows):
        for col in range(cols):
            circles.append(
                f'<circle cx="{x + col * gap:.1f}" cy="{y + row * gap:.1f}" r="{radius}" '
                f'fill="{colour}" fill-opacity="{opacity}"/>'
            )
    return "".join(circles)


def wrap_svg(width: float, height: float, body: str, book: FontBook, theme: dict,
             extra_defs: str = "", title: str = "") -> str:
    """Assemble a standalone, self-contained SVG document."""
    css = book.css()
    style = f"<style>{css}</style>" if css else ""
    return svg_open(width, height, theme, extra_defs, title) + style + body + "</svg>"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
