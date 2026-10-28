"""
Generate every graphic used on the GeekLord profile README and micro-site.

Run locally:   python3 scripts/build_assets.py
Run in CI:     .github/workflows/update-profile.yml (daily, after fetch_stats.py)

Inputs   : data/*.json (produced by scripts/fetch_stats.py)
Outputs  : assets/cards/*.svg, assets/divider.svg, site/* (built by build_site.py)
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import build_motion
from design import (
    DARK,
    LIGHT,
    THEMES,
    FontBook,
    accent_gradient,
    chip,
    dotted_grid,
    line,
    panel,
    rect,
    text,
    text_width,
    wrap_svg,
    write,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
CARDS = ASSETS / "cards"

CANVAS = 1200
FALLBACK_STATS = {
    "login": "GeekLord",
    "name": "Shobhit Kumar Prabhakar",
    "followers": 7,
    "own_repos": 28,
    "public_repos": 78,
    "joined_year": 2010,
    "contributions": 811,
    "commits": 160,
    "pull_requests": 64,
    "issues": 1,
    "private_contributions": 587,
    "generated_at": "2026-10-15T00:00:00Z",
}
PALETTE = {
    # Wine, brass, sage, Pampas-stone, plum, clay, taupe: distinct in lightness
    # as well as hue, so the language bar still separates for colour-blind readers.
    "dark": ["#D46B7A", "#D9AE68", "#A3BF94", "#E9E1D6", "#B48AB0", "#E0906A", "#9C8B86"],
    "light": ["#722F37", "#B08A3E", "#5E7F56", "#C9BBA8", "#6E4566", "#A8552E", "#857570"],
}


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------


def load(name: str, fallback):
    path = DATA / name
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback


def humanise(value: int | float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 10_000:
        return f"{value / 1000:.1f}K".replace(".0K", "K")
    return f"{value:,}"


def wrap_label(value: str, family: str, weight: int, size: float, max_width: float,
               tracking: float = 0.0, max_lines: int = 2) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if text_width(candidate, family, weight, size, tracking) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip() + "…"
    return lines


def updated_stamp(raw: str) -> str:
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        stamp = datetime.now(timezone.utc)
    return stamp.astimezone(timezone.utc).strftime("%d %b %Y")


# --------------------------------------------------------------------------
# 1. Hero banner
# --------------------------------------------------------------------------


def build_banner() -> str:
    width, height = CANVAS, 384
    book = FontBook()
    parts: dict[str, str] = {}

    for theme in THEMES.values():
        t = theme
        defs = (
            accent_gradient(t, "accent")
            + f'<linearGradient id="wash" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{t["wine"]}" stop-opacity="0.16"/>'
            f'<stop offset="0.55" stop-color="{t["wine"]}" stop-opacity="0.05"/>'
            f'<stop offset="1" stop-color="{t["rose"]}" stop-opacity="0.14"/></linearGradient>'
            + f'<radialGradient id="orbA" cx="0.5" cy="0.5" r="0.5">'
            f'<stop offset="0" stop-color="{t["wine"]}" stop-opacity="0.30"/>'
            f'<stop offset="1" stop-color="{t["wine"]}" stop-opacity="0"/></radialGradient>'
            + f'<radialGradient id="orbB" cx="0.5" cy="0.5" r="0.5">'
            f'<stop offset="0" stop-color="{t["rose"]}" stop-opacity="0.22"/>'
            f'<stop offset="1" stop-color="{t["rose"]}" stop-opacity="0"/></radialGradient>'
            + f'<clipPath id="card"><rect x="24" y="24" width="{width - 48}" height="{height - 48}" rx="26"/></clipPath>'
        )
        body = []

        # Solid ground first (Pampas paper / cellar), then the wash + hairlines
        body.append(rect(24, 24, width - 48, height - 48, rx=26, fill=t["canvas"]))
        body.append(rect(24, 24, width - 48, height - 48, rx=26, fill="url(#wash)",
                         stroke=t["line"], stroke_opacity=0.75 if t is DARK else 1))
        body.append(rect(24, 24, width - 48, height - 48, rx=26, fill="none",
                         stroke=t["wine"], stroke_opacity=0.22))
        body.append(line(24 + 26, 24, width - 24 - 26, 24, stroke=t["rose"], width=1.4, opacity=0.5))

        # Ambient art: dot grid + soft orbs + orbit arcs, clipped to the card
        body.append('<g clip-path="url(#card)">')
        body.append(dotted_grid(1044, 250, 9, 8, 13, 1.0, t["grid"], 0.7))
        body.append(f'<ellipse cx="1078" cy="286" rx="150" ry="118" fill="url(#orbA)"/>')
        body.append(f'<ellipse cx="1122" cy="344" rx="128" ry="104" fill="url(#orbB)"/>')
        for radius, opacity in ((74, 0.22), (112, 0.13), (150, 0.07)):
            body.append(
                f'<circle cx="1062" cy="300" r="{radius}" fill="none" stroke="{t["wine"]}" '
                f'stroke-opacity="{opacity}" stroke-width="1"/>'
            )
        body.append(
            f'<circle cx="1062" cy="300" r="4.5" fill="none" stroke="{t["rose"]}" stroke-width="1.5">'
            f'<animate attributeName="r" values="4.5;26" dur="3s" repeatCount="indefinite"/>'
            f'<animate attributeName="stroke-opacity" values="0.8;0" dur="3s" repeatCount="indefinite"/>'
            f'</circle>')
        body.append(f'<circle cx="1062" cy="300" r="4.5" fill="{t["rose"]}"/>')
        # Satellites ride the three orbit rings at different speeds.
        for radius, period, start, colour in ((74, 14, 180, t["wine"]), (112, 22, 0, t["wine"]),
                                              (150, 34, 120, t["rose"])):
            body.append(
                f'<g><animateTransform attributeName="transform" type="rotate" '
                f'from="{start} 1062 300" to="{start + 360} 1062 300" dur="{period}s" '
                f'repeatCount="indefinite"/>'
                f'<circle cx="{1062 + radius}" cy="300" r="3.2" fill="{colour}" fill-opacity="0.95"/></g>')
        body.append('</g>')

        # Eyebrow
        body.append(rect(76, 74, 4, 15, rx=2, fill=t["wine"]))
        body.append(text(
            90, 86.5, "SOFTWARE ARCHITECT  ·  FOUNDER, CYBER MITRA SOLUTIONS", book=book,
            family="mono", size=12.5, fill=t["muted"], tracking=0.14))

        # Availability pill (top right)
        label = "OPEN TO SELECT ENGAGEMENTS"
        pill_w = text_width(label, "mono", 400, 12, 0.12) + 48
        pill_x = width - 66 - pill_w
        body.append(rect(pill_x, 70, pill_w, 30, rx=15, fill=t["chip_bg"], stroke=t["sage"],
                         stroke_opacity=0.55))
        body.append(f'<circle cx="{pill_x + 17}" cy="85" r="4.5" fill="{t["sage"]}">'
                    f'<animate attributeName="fill-opacity" values="1;0.35;1" dur="2s" '
                    f'repeatCount="indefinite"/></circle>')
        body.append(text(pill_x + 30, 89.5, label, book=book, family="mono", size=12,
                         fill=t["ink_soft"], tracking=0.12))

        # Name
        body.append(text(74, 190, "Shobhit Kumar Prabhakar", book=book, weight=600, size=64,
                         fill=t["display"], tracking=-0.022))
        # Tagline
        body.append(text(76, 236, "Complex challenges. Dependable systems.", book=book,
                         weight=500, size=25, fill=t["ink_soft"], tracking=-0.005))
        body.append(text(76, 264, "Engineering durable web platforms, offline-first field-data "
                                  "systems and source-grounded AI.",
                         book=book, size=15.5, fill=t["muted"]))

        # Practice metrics
        y = 296
        x = 76
        for label_text, accent in (
            ("20+ YEARS ENGINEERING", t["wine"]),
            ("850+ WEB PLATFORMS", t["rose"]),
            ("600+ FIELD INSTRUMENTS", t["wine"]),
            ("12+ COUNTRIES", t["rose"]),
        ):
            markup, used = chip(x, y, label_text, t, book, size=12, height=28,
                                accent=accent, weight=400)
            body.append(markup)
            x += used + 10

        parts[t["name"]] = wrap_svg(
            width, height, "".join(body), book, t, defs,
            title="Shobhit Kumar Prabhakar — Software Architect")

    for name, markup in parts.items():
        write(CARDS / f"banner-{name}.svg", markup)
    return "banner"


# --------------------------------------------------------------------------
# 2. Divider
# --------------------------------------------------------------------------


def build_divider() -> str:
    theme = DARK
    defs = (
        f'<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{theme["wine"]}" stop-opacity="0"/>'
        f'<stop offset="0.18" stop-color="{theme["wine"]}" stop-opacity="0.55"/>'
        f'<stop offset="0.5" stop-color="{theme["rose"]}" stop-opacity="0.75"/>'
        f'<stop offset="0.82" stop-color="{theme["wine"]}" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="{theme["wine"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="spark" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.9"/>'
        f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
    )
    body = [
        rect(0, 18, CANVAS, 2.5, rx=1.25, fill="url(#fade)"),
        f'<rect x="-160" y="17.5" width="160" height="3.5" rx="1.75" fill="url(#spark)">'
        f'<animate attributeName="x" values="-160;{CANVAS}" dur="4.5s" repeatCount="indefinite"/>'
        f'</rect>',
        f'<path d="M{CANVAS / 2 - 7} 19.2 l7 -6 l7 6 l-7 6 z" fill="{theme["rose"]}" '
        f'fill-opacity="0.9"><animate attributeName="fill-opacity" values="0.9;0.35;0.9" '
        f'dur="2.4s" repeatCount="indefinite"/></path>',
    ]
    markup = wrap_svg(CANVAS, 40, "".join(body), FontBook(), theme, defs, title="divider")
    write(ASSETS / "divider.svg", markup)
    return "divider"


# --------------------------------------------------------------------------
# 3. Live stats strip
# --------------------------------------------------------------------------


def build_stats(stats: dict) -> str:
    width, height = CANVAS, 196
    book = FontBook()
    metrics = [
        ("CONTRIBUTIONS", humanise(int(stats.get("contributions", 0))), "last 12 months"),
        ("COMMITS", humanise(int(stats.get("commits", 0))), "last 12 months"),
        ("PULL REQUESTS", humanise(int(stats.get("pull_requests", 0))), "last 12 months"),
        ("OWN REPOSITORIES", humanise(int(stats.get("own_repos", 0))), "not counting forks"),
        ("FOLLOWERS", humanise(int(stats.get("followers", 0))), "and counting"),
        ("ON GITHUB SINCE", str(stats.get("joined_year", 2010)),
         f"{date.today().year - int(stats.get('joined_year', 2010))} years of shipping"),
    ]
    outputs = {}
    for theme in THEMES.values():
        t = theme
        defs = accent_gradient(t, "accent")
        body = [
            "<style>.tile{opacity:0;animation:up .7s cubic-bezier(.2,.8,.2,1) forwards}"
            "@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}"
            ".bar{transform-box:fill-box;transform-origin:0 50%;animation:grow 1.2s ease-out forwards}"
            "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
            "@media (prefers-reduced-motion:reduce){.tile{animation:none;opacity:1}.bar{animation:none}}"
            "</style>",
            panel(0, 0, width, height, t, radius=22, fill=t["panel"], stroke=t["line"]),
            rect(28, 26, 3, 13, rx=1.5, fill=t["rose"]),
            text(40, 37, "LIVE FROM GITHUB", book=book, family="mono", size=11.5,
                 fill=t["muted"], tracking=0.16),
        ]
        stamp = f"updated {updated_stamp(stats.get('generated_at', ''))}"
        body.append(text(width - 28, 37, stamp, book=book, family="mono", size=11.5,
                         fill=t["faint"], anchor="end", tracking=0.06))

        inner_x, inner_w = 28, width - 56
        tile_w = inner_w / len(metrics)
        for index, (label, value, note) in enumerate(metrics):
            cx = inner_x + tile_w * index
            if index:
                body.append(line(cx, 66, cx, height - 30, stroke=t["line"], width=1, opacity=0.9))
            pad = 22
            body.append(f'<g class="tile" style="animation-delay:{0.15 + index * 0.12:.2f}s">')
            body.append(rect(cx + pad, 78, 26, 3, rx=1.5, fill="url(#accent)", class_="bar"))
            body.append(text(cx + pad, 126, value, book=book, weight=600, size=35,
                             fill=t["ink"], tracking=-0.02))
            body.append(text(cx + pad, 155, label, book=book, family="mono", size=11,
                             fill=t["ink_soft"], tracking=0.12))
            body.append(text(cx + pad, 172, note, book=book, size=12, fill=t["faint"]))
            body.append("</g>")
        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="GitHub activity — updated daily")
    for name, markup in outputs.items():
        write(CARDS / f"stats-{name}.svg", markup)
    return "stats"


# --------------------------------------------------------------------------
# 4. Language mix
# --------------------------------------------------------------------------


def build_languages(languages) -> str:
    width, height = CANVAS, 214
    book = FontBook()
    if isinstance(languages, dict):
        languages = languages.get("by_repo", [])
    entries = [item for item in languages if item.get("share", 0) > 0][:6]
    if entries:
        rest = sum(item.get("share", 0) for item in languages[6:])
        if rest > 0.5:
            entries = entries + [{"name": "Other", "detail": "misc. repos", "share": rest}]
    total = sum(item["share"] for item in entries) or 1
    for item in entries:
        item["share"] = item["share"] / total * 100

    outputs = {}
    for theme in THEMES.values():
        t = theme
        palette = PALETTE[t["name"]]
        defs = accent_gradient(t, "accent")
        body = [
            panel(0, 0, width, height, t, radius=22),
            rect(28, 26, 3, 13, rx=1.5, fill=t["wine"]),
            text(40, 37, "WHERE THE CODE LIVES", book=book, family="mono", size=11.5,
                 fill=t["muted"], tracking=0.16),
            text(width - 28, 37, "own repositories · by primary language", book=book,
                 family="mono", size=11.5, fill=t["faint"], anchor="end", tracking=0.06),
        ]

        bar_x, bar_y, bar_w, bar_h = 28, 62, width - 56, 26
        cursor = bar_x
        gap = 3
        usable = bar_w - gap * (len(entries) - 1)
        for index, item in enumerate(entries):
            segment = usable * item["share"] / 100
            body.append(rect(cursor, bar_y, segment, bar_h, rx=6, fill=palette[index % len(palette)]))
            cursor += segment + gap

        # Legend wraps automatically into rows of chips with a colour dot.
        legend_y = 118
        legend_x = 28
        row_step = 42
        for index, item in enumerate(entries):
            colour = palette[index % len(palette)]
            label = f'{item["name"]}  ·  {item["share"]:.0f}%'
            label_w = text_width(label, "display", 500, 14.5)
            detail = item.get("detail") or f'{item.get("repos", 0)} repos'
            detail_w = text_width(detail, "mono", 400, 11)
            box_w = max(label_w + 44, detail_w + 30) + 26
            if legend_x + box_w + 12 + detail_w > width - 28:  # chip *and* its note must fit
                legend_x = 28
                legend_y += row_step
            body.append(rect(legend_x, legend_y, box_w, 32, rx=10, fill=t["chip_bg"],
                             stroke=t["chip_line"]))
            body.append(f'<circle cx="{legend_x + 17}" cy="{legend_y + 16}" r="5" fill="{colour}"/>')
            body.append(text(legend_x + 30, legend_y + 21, label, book=book, weight=500,
                             size=14.5, fill=t["ink"]))
            body.append(text(legend_x + box_w + 12, legend_y + 20.5, detail, book=book,
                             family="mono", size=11, fill=t["faint"]))
            legend_x += box_w + text_width(detail, "mono", 400, 11) + 26
        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="Primary language mix")
    for name, markup in outputs.items():
        write(CARDS / f"languages-{name}.svg", markup)
    return "languages"


# --------------------------------------------------------------------------
# 5. Toolkit
# --------------------------------------------------------------------------

TOOLKIT = [
    ("LANGUAGES", ["TypeScript", "JavaScript", "Python", "PHP", "Java", "Shell", "PowerShell", "SQL"]),
    ("WEB & PLATFORMS", ["Astro", "Next.js", "React", "Node.js", "WordPress", "Tailwind CSS",
                         "REST", "GraphQL"]),
    ("FIELD DATA", ["SurveyCTO", "ODK / XLSForm", "JavaRosa", "Stata", "PostgreSQL", "Python ETL"]),
    ("AI & AGENTS", ["Grounded RAG", "Tool-calling agents", "Hybrid search", "Guardrails & evals",
                     "Claude · GPT · Gemini", "ComfyUI"]),
    ("CLOUD & OPS", ["AWS EC2 / S3", "GCP", "Cloudflare", "Docker", "Nginx", "GitHub Actions",
                     "Linux"]),
]


def build_toolkit() -> str:
    width = CANVAS
    row_height = 46
    header = 66
    height = header + row_height * len(TOOLKIT) + 16
    book = FontBook()
    outputs = {}
    for theme in THEMES.values():
        t = theme
        defs = accent_gradient(t, "accent")
        body = [
            panel(0, 0, width, height, t, radius=22),
            rect(28, 26, 3, 13, rx=1.5, fill=t["rose"]),
            text(40, 37, "TOOLKIT & STACK", book=book, family="mono", size=11.5,
                 fill=t["muted"], tracking=0.16),
            text(width - 28, 37, "battle-tested, not aspirational", book=book, family="mono",
                 size=11.5, fill=t["faint"], anchor="end", tracking=0.06),
        ]
        for row_index, (group, tools) in enumerate(TOOLKIT):
            y = header + row_index * row_height
            if row_index:
                body.append(line(28, y - 12, width - 28, y - 12, stroke=t["line_soft"], width=1))
            body.append(text(28, y + 17, group, book=book, family="mono", size=11.5,
                             fill=t["muted"], tracking=0.12))
            x = 232
            for tool in tools:
                markup, used = chip(x, y, tool, t, book, size=12.5, height=28, pad_x=12)
                body.append(markup)
                x += used + 9
        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="Toolkit and stack")
    for name, markup in outputs.items():
        write(CARDS / f"toolkit-{name}.svg", markup)
    return "toolkit"


# --------------------------------------------------------------------------
# 6. Timeline
# --------------------------------------------------------------------------

MILESTONES = [
    ("2005", "Cyber Mitra Solutions", "Engineering practice founded in Lucknow, India."),
    ("2010", "Hello, GitHub", "GeekLord account created — 16 years of public work."),
    ("2013", "Morsel platform", "Research hub for ~400 national studies."),
    ("2018", "Field data at scale", "SurveyCTO / ODK instruments for 12+ countries."),
    ("2021", "Souters LMS", "London executive-training portal, 99.9% uptime."),
    ("2026", "Agentic AI practice", "Grounded RAG and evaluated agent pipelines."),
]


def build_timeline() -> str:
    width, height = CANVAS, 268
    book = FontBook()
    outputs = {}
    for theme in THEMES.values():
        t = theme
        defs = (
            accent_gradient(t, "accent")
            + f'<linearGradient id="axis" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{t["wine"]}"/>'
            f'<stop offset="1" stop-color="{t["rose"]}"/></linearGradient>'
        )
        # Each milestone owns one equal column; labels centred in their column can
        # never spill past the card because the outer columns absorb the margins.
        margin = 38.0
        node_w = (width - margin * 2) / len(MILESTONES)
        x0 = margin + node_w / 2
        x1 = width - margin - node_w / 2
        body = [
            panel(0, 0, width, height, t, radius=22),
            rect(28, 26, 3, 13, rx=1.5, fill=t["wine"]),
            text(40, 37, "TWO DECADES, ONE THREAD", book=book, family="mono", size=11.5,
                 fill=t["muted"], tracking=0.16),
            text(width - 28, 37, "build systems that outlive the launch", book=book,
                 family="mono", size=11.5, fill=t["faint"], anchor="end", tracking=0.06),
            rect(x0, 98, x1 - x0, 2.5, rx=1.25, fill="url(#axis)", opacity=0.85),
        ]
        step = (x1 - x0) / (len(MILESTONES) - 1)
        for index, (year, title, note) in enumerate(MILESTONES):
            cx = x0 + step * index
            colour = t["wine"] if index % 2 == 0 else t["rose"]
            body.append(f'<circle cx="{cx:.1f}" cy="99.25" r="9" fill="{t["panel"]}"/>')
            body.append(f'<circle cx="{cx:.1f}" cy="99.25" r="5.5" fill="{colour}"/>')
            if index == len(MILESTONES) - 1:
                body.append(f'<circle cx="{cx:.1f}" cy="99.25" r="13" fill="none" '
                            f'stroke="{colour}" stroke-opacity="0.45" stroke-width="1.5"/>')
            body.append(line(cx, 110, cx, 128, stroke=t["line"], width=1))
            body.append(text(cx, 150, year, book=book, family="mono", weight=600,
                             size=15, fill=colour, anchor="middle", tracking=0.06))
            for title_line, label in enumerate(
                    wrap_label(title, "display", 600, 15, node_w - 10, max_lines=2)):
                body.append(text(cx, 175 + title_line * 19, label, book=book, weight=600,
                                 size=15, fill=t["ink"], anchor="middle"))
            for line_index, label in enumerate(
                    wrap_label(note, "display", 400, 12.5, node_w - 6, max_lines=2)):
                body.append(text(cx, 196 + line_index * 17, label, book=book, size=12.5,
                                 fill=t["muted"], anchor="middle"))
        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="Career timeline")
    for name, markup in outputs.items():
        write(CARDS / f"timeline-{name}.svg", markup)
    return "timeline"


# --------------------------------------------------------------------------
# 7. Engineering blueprint
# --------------------------------------------------------------------------

BLUEPRINT = [
    ("FIELD DATA", "wine", [
        ("01", "Offline capture", "SurveyCTO · ODK · XLSForm"),
        ("02", "In-form validation", "calculates · constraints"),
        ("03", "Daily audits", "Python QC pipelines"),
        ("04", "Clean delivery", "protected research lake"),
    ]),
    ("WEB PLATFORMS", "rose", [
        ("01", "Design system", "tokens · components"),
        ("02", "Sub-second delivery", "Astro · React · Vite"),
        ("03", "Hardened infra", "AWS · Cloudflare · Nginx"),
        ("04", "Zero-downtime release", "GitHub Actions CI/CD"),
    ]),
    ("AI SYSTEMS", "wine", [
        ("01", "Private corpus", "docs · PDFs · catalogues"),
        ("02", "Hybrid retrieval", "embeddings + BM25"),
        ("03", "Guardrails & evals", "schemas · cost caps"),
        ("04", "Cited answers", "verified, no guesswork"),
    ]),
]


def build_blueprint() -> str:
    width = CANVAS
    row_h = 84
    header = 74
    height = header + row_h * len(BLUEPRINT) + 6
    book = FontBook()
    outputs = {}
    for theme in THEMES.values():
        t = theme
        defs = accent_gradient(t, "accent")
        body = [
            panel(0, 0, width, height, t, radius=22),
            rect(28, 26, 3, 13, rx=1.5, fill=t["wine"]),
            text(40, 37, "ENGINEERING BLUEPRINT", book=book, family="mono", size=11.5,
                 fill=t["muted"], tracking=0.16),
            text(width - 28, 37, "three production pipelines, stripped to essentials", book=book,
                 family="mono", size=11.5, fill=t["faint"], anchor="end", tracking=0.06),
        ]
        node_x0, node_x1 = 214, width - 28
        node_w = 214
        arrow = (node_x1 - node_x0 - node_w * 4) / 3
        for row_index, (name, accent_key, nodes) in enumerate(BLUEPRINT):
            y = header + row_index * row_h
            accent = t[accent_key]
            body.append(text(28, y + 34, name, book=book, family="mono", weight=600, size=11.5,
                             fill=accent, tracking=0.14))
            body.append(rect(28, y + 44, 120, 2, rx=1, fill=accent, opacity=0.35))
            for index, (step, title, subtitle) in enumerate(nodes):
                x = node_x0 + index * (node_w + arrow)
                body.append(rect(x, y, node_w, 62, rx=12, fill=t["panel_alt"], stroke=t["line"]))
                body.append(rect(x + 14, y + 13, 22, 2, rx=1, fill=accent))
                body.append(text(x + 14, y + 34, step, book=book, family="mono", size=10.5,
                                 fill=t["faint"], tracking=0.1))
                body.append(text(x + 42, y + 34, title, book=book, weight=600, size=14.5,
                                 fill=t["ink"]))
                body.append(text(x + 14, y + 52, subtitle, book=book, family="mono", size=10.5,
                                 fill=t["muted"]))
                if index < len(nodes) - 1:
                    ax = x + node_w + 6
                    body.append(line(ax, y + 31, ax + arrow - 16, y + 31, stroke=t["line"],
                                     width=1.4))
                    tip = ax + arrow - 16
                    body.append(f'<path d="M{tip:.1f} {y + 26.5:.1f} l7 4.5 l-7 4.5 z" '
                                f'fill="{t["faint"]}"/>')
        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="Engineering blueprint")
    for name, markup in outputs.items():
        write(CARDS / f"blueprint-{name}.svg", markup)
    return "blueprint"


# --------------------------------------------------------------------------
# 8. Contribution crawl (animated, theme-aware, data driven)
# --------------------------------------------------------------------------


def traversal(calendar: dict) -> tuple[list[dict], int, int]:
    """Cells in the order a crawler visits them: down column 1, up column 2, ..."""
    weeks = calendar.get("weeks") or []
    if not weeks:
        weeks = [[{"date": "", "count": 0, "level": 0} for _ in range(7)] for _ in range(53)]
    ordered: list[dict] = []
    for week_index, week in enumerate(weeks):
        days = range(7) if week_index % 2 == 0 else range(6, -1, -1)
        for day_index in days:
            day = week[day_index] if day_index < len(week) else {"count": 0, "level": 0}
            ordered.append({"week": week_index, "day": day_index,
                            "date": day.get("date", ""),
                            "count": int(day.get("count", 0)),
                            "level": max(0, min(4, int(day.get("level", 0))))})
    return ordered, len(weeks), 7


def calendar_facts(calendar: dict) -> dict:
    """Totals, streaks and high scores read straight off the daily series."""
    days: list[dict] = []
    for week in calendar.get("weeks") or []:
        for day in week:
            if day.get("date"):
                days.append(day)
    days.sort(key=lambda day: day["date"])
    if not days:
        return {"total": int(calendar.get("total") or 0), "streak": 0, "best": 0,
                "span": "", "active_days": 0}

    total = sum(int(day.get("count", 0)) for day in days)
    best = max(int(day.get("count", 0)) for day in days)
    streak = running = 0
    for day in days:
        if int(day.get("count", 0)) > 0:
            running += 1
            streak = max(streak, running)
        else:
            running = 0
    active = sum(1 for day in days if int(day.get("count", 0)) > 0)

    def pretty(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError:
            return value

    return {
        "total": total,
        "streak": streak,
        "best": best,
        "active_days": active,
        "span": f"{pretty(days[0]['date'])} to {pretty(days[-1]['date'])}",
        "days": len(days),
    }


class CrawlGeometry:
    """Shared geometry + timing for the animated contribution grid."""

    def __init__(self, calendar: dict, width: int = CANVAS) -> None:
        self.cells, self.weeks, self.days = traversal(calendar)
        self.cell = 11.5
        self.gap = 3.0
        self.step = self.cell + self.gap
        self.grid_w = self.weeks * self.step - self.gap
        self.grid_h = self.days * self.step - self.gap
        self.width = width
        self.pad = 34
        self.grid_x = self.pad
        self.top = 96
        self.rule_y = self.top + self.grid_h + 22
        self.height = self.rule_y + 78
        self.sweep = 21.0
        self.cycle = 27.0
        self.reset_at = 0.94
        self.stats_x = self.pad + self.grid_w + 46
        self.travelled: list[float] = []
        total = 0.0
        for index, cell in enumerate(self.cells):
            if index:
                prev = self.cells[index - 1]
                dx = (cell["week"] - prev["week"]) * self.step
                dy = (cell["day"] - prev["day"]) * self.step
                total += math.hypot(dx, dy)
            self.travelled.append(total)
        self.total_distance = total or 1.0

    def point(self, cell: dict) -> tuple[float, float]:
        return (cell["week"] * self.step + self.cell / 2,
                cell["day"] * self.step + self.cell / 2)

    def route(self) -> str:
        points = [self.point(cell) for cell in self.cells]
        return " ".join([f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
                        + [f"L {x:.2f} {y:.2f}" for x, y in points[1:]])

    def pop_time(self, index: int) -> float:
        return self.travelled[index] / self.total_distance * self.sweep


def build_crawl(calendar: dict, *, inline: bool = False, static: bool = False) -> str:
    """Animated contribution grid driven by the real contribution calendar.

    stand-alone SVG (README) -> theme-baked colours, SMIL animation
    inline SVG (micro-site)  -> CSS classes so the site theme re-paints it
    static=True              -> frozen mid-sweep frame, for visual QA
    """
    geo = CrawlGeometry(calendar)
    facts = calendar_facts(calendar)
    book = FontBook()
    heading = "CONTRIBUTION CRAWL"
    sub = "a crawler eats one square per contribution"
    span = f"{facts['span']}  ·  {facts['active_days']} active days" if facts["span"] else ""
    stats = [
        ("TOTAL CONTRIBUTIONS", f"{facts['total']:,}"),
        ("LONGEST DAILY STREAK", f"{facts['streak']} days"),
        ("BUSIEST SINGLE DAY", f"{facts['best']}"),
    ]

    def stat_column(t: dict, css: bool) -> str:
        out = [line(geo.stats_x - 26, geo.top - 6, geo.stats_x - 26, geo.rule_y + 34,
                    stroke=t["line"] if not css else "var(--line)", width=1)]
        y = geo.top + 10
        for label, value in stats:
            out.append(text(geo.stats_x, y + 26, value, book=book, weight=600, size=30,
                            fill=t["ink"] if not css else "currentColor", tracking=-0.02))
            out.append(text(geo.stats_x, y + 45, label, book=book, family="mono", size=10.5,
                            fill=t["muted"] if not css else "currentColor", tracking=0.13))
            y += 58
        return "".join(out)

    def legend(t: dict, css: bool, x: float, baseline: float) -> tuple[str, float]:
        """Five-step intensity key, matching the steps GitHub itself uses."""
        out = [text(x, baseline, "LESS", book=book, family="mono", size=10,
                    fill=t["faint"] if not css else "currentColor", tracking=0.12)]
        cursor = x + text_width("LESS", "mono", 400, 10, 0.12) + 12
        for level in range(5):
            fill = f"var(--cell{level})" if css else t[f"cell{level}"]
            out.append(rect(cursor, baseline - 10, 13, 13, rx=3, fill=fill))
            cursor += 17
        out.append(text(cursor + 1, baseline, "MORE", book=book, family="mono", size=10,
                        fill=t["faint"] if not css else "currentColor", tracking=0.12))
        return "".join(out), cursor + 1 + text_width("MORE", "mono", 400, 10, 0.12)

    def build_body(t: dict, css: bool, frozen: bool) -> str:
        ramp = ([f"var(--cell{n})" for n in range(5)] if css
                else [t["cell0"], t["cell1"], t["cell2"], t["cell3"], t["cell4"]])
        head_fill = f"var(--accent)" if css else ramp[4]
        body: list[str] = []
        if css:
            body.append(rect(0, 0, geo.width, geo.height, rx=22, fill="var(--panel)",
                             stroke="var(--line)"))
        else:
            body.append(panel(0, 0, geo.width, geo.height, t, radius=22))
        body.append(rect(geo.pad, 32, 3, 13, rx=1.5,
                         fill="var(--accent)" if css else t["wine"]))
        body.append(text(geo.pad + 12, 43, heading, book=book, family="mono", size=11.5,
                         fill=t["muted"] if not css else "currentColor", tracking=0.16))
        body.append(text(geo.width - geo.pad, 43, sub, book=book, family="mono", size=11.5,
                         fill=t["faint"] if not css else "currentColor", anchor="end",
                         tracking=0.05))

        for index, cell in enumerate(geo.cells):
            x = geo.grid_x + cell["week"] * geo.step
            y = geo.top + cell["day"] * geo.step
            level = cell["level"]
            if frozen:
                shown = level if geo.pop_time(index) <= geo.sweep * 0.62 else 0
                body.append(rect(x, y, geo.cell, geo.cell, rx=2.8,
                                 fill=ramp[shown] if not css else ramp[shown]))
                continue
            if css:
                # The keyframes light a cell at 1.4% of the cycle; shift each cell
                # by that much so it pops exactly when the crawler reaches it.
                delay = geo.pop_time(index) - 0.014 * geo.cycle
                delay -= geo.cycle * math.ceil(delay / geo.cycle) if delay > 0 else 0
                body.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{geo.cell}" '
                            f'height="{geo.cell}" rx="2.8" class="cell l{level}" '
                            f'style="animation-delay:{delay:.3f}s"/>')
                continue
            body.append(rect(x, y, geo.cell, geo.cell, rx=2.8, fill=ramp[0]))
            if level <= 0:
                continue
            start = geo.pop_time(index) / geo.cycle
            end = min(start + 0.35 / geo.cycle, geo.reset_at - 0.001)
            body.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{geo.cell}" height="{geo.cell}" rx="2.8" '
                f'fill="{ramp[0]}"><animate attributeName="fill" dur="{geo.cycle}s" '
                f'repeatCount="indefinite" values="{ramp[0]};{ramp[0]};{ramp[level]};'
                f'{ramp[level]};{ramp[0]}" keyTimes="0;{start:.5f};{end:.5f};'
                f'{geo.reset_at:.3f};1"/></rect>'
            )

        body.append(stat_column(t, css))

        # keyPoints/keyTimes hold the head still after it finishes the sweep, so
        # its arrival at each square matches that square's lighting time exactly.
        motion = (f'dur="{geo.cycle}s" repeatCount="indefinite" path="{geo.route()}" '
                  f'keyPoints="0;1;1" keyTimes="0;{geo.sweep / geo.cycle:.4f};1" '
                  f'calcMode="linear"')
        glow_attrs = 'class="crawl-glow"' if css else f'fill="{head_fill}" fill-opacity="0.22"'
        core_attrs = 'class="crawl-head"' if css else f'fill="{head_fill}"'
        head = (f'<circle r="9" {glow_attrs}><animateMotion {motion}/></circle>'
                f'<circle r="4.6" {core_attrs}><animateMotion {motion}/>'
                + ("" if frozen or css else
                   f'<animate attributeName="opacity" dur="{geo.cycle}s" '
                   f'repeatCount="indefinite" values="1;1;0;0;1" '
                   f'keyTimes="0;{geo.sweep / geo.cycle:.4f};'
                   f'{geo.sweep / geo.cycle + 0.025:.4f};{geo.reset_at:.3f};1"/>')
                + "</circle>")
        body.append(f'<g transform="translate({geo.grid_x:.2f},{geo.top:.2f})">{head}</g>')

        body.append(rect(geo.grid_x, geo.rule_y, geo.grid_w, 3, rx=1.5,
                         fill=t["line"] if not css else "var(--line)"))
        if frozen:
            done = geo.grid_w * 0.62
            body.append(rect(geo.grid_x, geo.rule_y, done, 3, rx=1.5, fill="url(#accent)"))
        else:
            body.append(
                f'<rect x="{geo.grid_x:.2f}" y="{geo.rule_y:.2f}" height="3" rx="1.5" width="0" '
                f'fill="url(#accent)"><animate attributeName="width" dur="{geo.cycle}s" '
                f'repeatCount="indefinite" values="0;{geo.grid_w:.1f};{geo.grid_w:.1f};0" '
                f'keyTimes="0;{geo.sweep / geo.cycle:.4f};{geo.reset_at:.3f};1"/></rect>'
            )
        body.append(text(geo.grid_x, geo.rule_y + 34, span, book=book, family="mono", size=11.5,
                         fill=t["muted"] if not css else "currentColor", tracking=0.05))
        span_w = text_width(span, "mono", 400, 11.5, 0.05)
        key, _ = legend(t, css, geo.grid_x + span_w + 30, geo.rule_y + 34)
        body.append(key)
        return "".join(body)

    def wrap(t: dict, body: str, defs: str, css: bool) -> str:
        style = f"<style>{book.css()}</style>"
        root = 'class="crawl-svg"' if css else f'style="color:{t["ink"]}"'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{geo.width:.0f}" '
                f'height="{geo.height:.0f}" viewBox="0 0 {geo.width:.0f} {geo.height:.0f}" '
                f'role="img" {root} '
                f'font-family="SpaceGrotesk, Segoe UI, Helvetica, Arial, sans-serif">'
                f"<title>{heading} · {facts['total']:,} contributions</title>"
                f"<defs>{defs}{style}</defs>{body}</svg>")

    for theme in THEMES.values():
        t = theme
        write(ASSETS / f"crawl-{t['name']}.svg",
              wrap(t, build_body(t, False, False), accent_gradient(t, "accent"), False))

    if static:
        t = DARK
        write(ASSETS / "_qa-crawl-frame.svg",
              wrap(t, build_body(t, False, True), accent_gradient(t, "accent"), False))
    if inline:
        site_defs = (
            '<linearGradient id="accent" x1="0" y1="0" x2="1" y2="1">'
            '<stop class="grad-a" offset="0"/><stop class="grad-b" offset="1"/></linearGradient>'
        )
        write(ROOT / "site" / "crawl.inline.svg",
              wrap(DARK, build_body(DARK, True, False), site_defs, True))
    return "crawl"


# --------------------------------------------------------------------------
# README heading icons
# --------------------------------------------------------------------------

# One mid-wine stroke that clears 3:1 on both GitHub page grounds
# (white #FFFFFF and dark #0D1117), so a single file serves both themes.
ICON_STROKE = "#B5505F"
README_ICONS = ("clipboard", "bolt", "robot", "building", "chat", "wallet", "mic", "image",
                "film", "ballot", "search", "disk", "cap", "globe", "chart", "toolbox",
                "mail", "phone", "pen", "pin")


def build_icons() -> str:
    from build_site import ICONS  # same hand-drawn set the micro-site uses

    for name in README_ICONS:
        write(ASSETS / "icons" / f"{name}.svg",
              '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
              f'fill="none" stroke="{ICON_STROKE}" stroke-width="1.7" stroke-linecap="round" '
              f'stroke-linejoin="round">{ICONS[name]}</svg>')
    return "icons"


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main() -> None:
    stats = load("profile-stats.json", FALLBACK_STATS)
    languages = load("languages.json", [])
    calendar = load("contribution-calendar.json", {"total": 0, "weeks": []})

    built = [
        build_banner(),
        build_divider(),
        build_stats(stats),
        build_languages(languages),
        build_toolkit(),
        build_timeline(),
        build_blueprint(),
        build_crawl(calendar, inline=True),
        build_icons(),
    ]
    built += build_motion.build_all()
    print("built:", ", ".join(built))
    for path in sorted(CARDS.glob("*.svg")) + sorted(ASSETS.glob("*.svg")):
        print(f"  {path.relative_to(ROOT)}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
