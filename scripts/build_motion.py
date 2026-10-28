"""
Animated cards for the GeekLord profile.

Every card here moves, and every movement is plain SVG (SMIL <animate> and CSS
keyframes inside the file), so it plays inside GitHub's <img> sandbox with no
script and no network. Like the rest of the profile, each card is generated
twice (dark + light) with identical dimensions.

Cards
  terminal   a shell session that types itself out, line by line, then loops
  orbit      the working stack in three counter-rotating orbits
  rhythm     when the commits land, by hour of day in IST, bars rising in turn
  footer     a slow double wave that closes the page
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from design import (
    DARK,
    THEMES,
    FontBook,
    accent_gradient,
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
CARDS = ROOT / "assets" / "cards"
CANVAS = 1200


def _load(name: str, fallback):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _fmt(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


# --------------------------------------------------------------------------
# 1. Self-typing terminal
# --------------------------------------------------------------------------

TERMINAL_SCRIPT = [
    ("cmd", "whoami"),
    ("out", "Shobhit Kumar Prabhakar · software architect · Lucknow, India"),
    ("cmd", "cat ventures.txt"),
    ("out", "Cyber Mitra Solutions (2005)  ·  AskBurg (2024)  ·  UPIfree (2026)"),
    ("cmd", "uptime --since 2005"),
    ("out", "20+ years · 850+ web platforms · 600+ field instruments · 12+ countries"),
    ("cmd", "ask --how-to-reach"),
    ("out", "+91 79658 52100 · answered 24×7 by my AI assistant"),
]


def build_terminal() -> str:
    width, height = CANVAS, 330
    book = FontBook()
    size = 15
    char_w = text_width("M", "mono", 400, size)
    type_speed = 0.055      # seconds per typed character (commands)
    out_speed = 0.012       # output appears almost at once, like a real shell
    pause_after = 0.55
    hold = 4.5              # seconds the finished screen stays up before looping

    # Build the timeline once; both themes share it.
    timeline = []
    cursor = 0.6
    for kind, content in TERMINAL_SCRIPT:
        chars = len(content)
        speed = type_speed if kind == "cmd" else out_speed
        start, end = cursor, cursor + chars * speed
        timeline.append((kind, content, start, end))
        cursor = end + (pause_after if kind == "out" else 0.35)
    total = cursor + hold

    x0, y0, row = 52, 104, 26
    prompt = "shobhit@geeklord:~$ "
    prompt_w = text_width(prompt, "mono", 400, size)

    outputs = {}
    for t in THEMES.values():
        defs = accent_gradient(t, "accent")
        clips = []
        body = [
            panel(0, 0, width, height, t, radius=22, fill=t["panel"], stroke=t["line"]),
            rect(0, 0, width, 52, rx=22, fill=t["panel_alt"]),
            rect(0, 30, width, 22, fill=t["panel_alt"]),
            line(0, 52, width, 52, stroke=t["line"], width=1),
        ]
        for i, colour in enumerate((t["wine"], t["brass"], t["sage"])):
            body.append(f'<circle cx="{30 + i * 22}" cy="26" r="6.5" fill="{colour}"/>')
        body.append(text(width / 2, 31, "geeklord — zsh — 120×24", book=book, family="mono",
                         size=12, fill=t["muted"], anchor="middle", tracking=0.04))
        body.append(text(width - 28, 31, "LIVE", book=book, family="mono", size=11,
                         fill=t["sage"], anchor="end", tracking=0.16))
        body.append(
            f'<circle cx="{width - 70}" cy="27" r="4" fill="{t["sage"]}">'
            f'<animate attributeName="opacity" values="1;0.25;1" dur="1.6s" '
            f'repeatCount="indefinite"/></circle>')

        last_y = y0
        for index, (kind, content, start, end) in enumerate(timeline):
            y = y0 + index * row
            last_y = y
            if kind == "cmd":
                tx = x0 + prompt_w
                body.append(text(x0, y, "shobhit@geeklord", book=book, family="mono", size=size,
                                 fill=t["sage"]))
                body.append(text(x0 + text_width("shobhit@geeklord", "mono", 400, size), y,
                                 ":~$", book=book, family="mono", size=size, fill=t["rose"]))
                fill, weight = t["ink"], 600
            else:
                tx = x0
                fill, weight = t["ink_soft"], 400
            full_w = text_width(content, "mono", weight, size) + 12

            # Discrete reveal: one step per character for commands, smooth for output.
            ks, vs = ["0", _fmt(start / total)], ["0", "0"]
            if kind == "cmd":
                n = len(content)
                for c in range(1, n + 1):
                    ks.append(_fmt((start + c * (end - start) / n) / total))
                    vs.append(_fmt(full_w * c / n))
                calc = "discrete"
            else:
                ks.append(_fmt(end / total))
                vs.append(_fmt(full_w))
                calc = "linear"
            ks.append("1")
            vs.append(_fmt(full_w))
            if calc == "discrete":
                # discrete wants one keyTime per value; the list above already matches
                pass
            clip_id = f"line{index}"
            clips.append(
                f'<clipPath id="{clip_id}"><rect x="{tx - 1:.1f}" y="{y - size - 2}" '
                f'height="{size + 10}" width="0">'
                f'<animate attributeName="width" dur="{total:.2f}s" repeatCount="indefinite" '
                f'calcMode="{calc}" keyTimes="{";".join(ks)}" values="{";".join(vs)}"/>'
                f'</rect></clipPath>')
            colour = fill if kind == "cmd" else (t["ink_soft"] if index % 4 != 3 else t["brass"])
            if index == 7:
                colour = t["brass"]
            body.append(f'<g clip-path="url(#{clip_id})">'
                        + text(tx, y, content, book=book, family="mono", size=size,
                               weight=weight, fill=colour)
                        + "</g>")

        # Final prompt with a blinking block cursor, shown once the script finishes.
        fy = last_y + row
        appear = _fmt(timeline[-1][3] / total)
        body.append(
            f'<g opacity="0"><animate attributeName="opacity" dur="{total:.2f}s" '
            f'repeatCount="indefinite" calcMode="discrete" keyTimes="0;{appear}" values="0;1"/>'
            + text(x0, fy, "shobhit@geeklord", book=book, family="mono", size=size,
                   fill=t["sage"])
            + text(x0 + text_width("shobhit@geeklord", "mono", 400, size), fy, ":~$",
                   book=book, family="mono", size=size, fill=t["rose"])
            + f'<rect x="{x0 + prompt_w:.1f}" y="{fy - size + 1}" width="{char_w:.1f}" '
              f'height="{size + 3}" fill="{t["rose"]}">'
              f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" '
              f'dur="1s" repeatCount="indefinite"/></rect>'
            + "</g>")

        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t,
                                      defs + "".join(clips),
                                      title="A terminal session introducing Shobhit")
    for name, markup in outputs.items():
        write(CARDS / f"terminal-{name}.svg", markup)
    return "terminal"


# --------------------------------------------------------------------------
# 2. Stack in orbit
# --------------------------------------------------------------------------

ORBITS = [
    # (radius, seconds per revolution, direction, items)
    (92, 38, 1, ["Python", "TypeScript", "PHP"]),
    (150, 56, -1, ["Astro", "React", "Node.js", "WordPress", "PostgreSQL"]),
    (208, 84, 1, ["Claude", "GPT", "Gemini", "RAG", "Agents", "SurveyCTO", "ODK",
                  "AWS", "Docker", "Cloudflare"]),
]


def build_orbit() -> str:
    width, height = CANVAS, 470
    cx, cy = 860, 235
    book = FontBook()
    outputs = {}
    for t in THEMES.values():
        accents = [t["wine"], t["brass"], t["rose"]]
        defs = (
            accent_gradient(t, "accent")
            + f'<radialGradient id="core" cx="0.5" cy="0.5" r="0.5">'
            f'<stop offset="0" stop-color="{t["wine"]}" stop-opacity="0.45"/>'
            f'<stop offset="1" stop-color="{t["wine"]}" stop-opacity="0"/></radialGradient>'
        )
        body = [
            panel(0, 0, width, height, t, radius=22, fill=t["panel"], stroke=t["line"]),
            rect(28, 26, 3, 13, rx=1.5, fill=t["wine"]),
            text(40, 37, "THE STACK IN ORBIT", book=book, family="mono", size=11.5,
                 fill=t["muted"], tracking=0.16),
        ]
        # Left column copy
        body.append(text(52, 132, "Languages at the core.", book=book, weight=600, size=30,
                         fill=t["ink"], tracking=-0.015))
        body.append(text(52, 170, "Platforms around them.", book=book, weight=600, size=30,
                         fill=t["ink"], tracking=-0.015))
        body.append(text(52, 208, "Models on the outside,", book=book, weight=600, size=30,
                         fill=t["wine"], tracking=-0.015))
        body.append(text(52, 246, "swappable by design.", book=book, weight=600, size=30,
                         fill=t["wine"], tracking=-0.015))
        notes = [
            ("inner", "languages I write every week", accents[0]),
            ("middle", "platforms I ship to production", accents[1]),
            ("outer", "AI, data and cloud, no lock-in", accents[2]),
        ]
        for i, (ring, note, colour) in enumerate(notes):
            y = 304 + i * 34
            body.append(f'<circle cx="60" cy="{y - 5}" r="5" fill="none" stroke="{colour}" '
                        f'stroke-width="2"/>')
            body.append(text(76, y, ring.upper(), book=book, family="mono", size=11.5,
                             fill=colour, tracking=0.14))
            body.append(text(150, y, note, book=book, size=15, fill=t["ink_soft"]))

        # Orbit art
        body.append(f'<circle cx="{cx}" cy="{cy}" r="120" fill="url(#core)"/>')
        for ring_i, (radius, period, direction, items) in enumerate(ORBITS):
            colour = accents[ring_i]
            body.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{colour}" '
                        f'stroke-opacity="0.28" stroke-width="1" stroke-dasharray="2 6"/>')
            spin_to = 360 * direction
            group = [f'<g><animateTransform attributeName="transform" type="rotate" '
                     f'from="0 {cx} {cy}" to="{spin_to} {cx} {cy}" dur="{period}s" '
                     f'repeatCount="indefinite"/>']
            for k, label in enumerate(items):
                angle = 2 * math.pi * k / len(items) - math.pi / 2 + ring_i * 0.4
                px, py = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
                w = text_width(label, "mono", 400, 12) + 20
                # Counter-rotate each chip about its own centre so labels stay upright.
                group.append(
                    f'<g><animateTransform attributeName="transform" type="rotate" '
                    f'from="0 {px:.1f} {py:.1f}" to="{-spin_to} {px:.1f} {py:.1f}" '
                    f'dur="{period}s" repeatCount="indefinite"/>'
                    + rect(px - w / 2, py - 12, w, 24, rx=12, fill=t["chip_bg"], stroke=colour,
                           stroke_opacity=0.75)
                    + text(px, py + 4.2, label, book=book, family="mono", size=12,
                           fill=t["ink"], anchor="middle")
                    + "</g>")
            group.append("</g>")
            body.append("".join(group))

        # Core
        body.append(f'<circle cx="{cx}" cy="{cy}" r="38" fill="{t["canvas"]}" '
                    f'stroke="url(#accent)" stroke-width="2.5"/>')
        body.append(
            f'<circle cx="{cx}" cy="{cy}" r="38" fill="none" stroke="{t["rose"]}" '
            f'stroke-width="1.5"><animate attributeName="r" values="38;58" dur="2.8s" '
            f'repeatCount="indefinite"/><animate attributeName="stroke-opacity" values="0.6;0" '
            f'dur="2.8s" repeatCount="indefinite"/></circle>')
        body.append(text(cx, cy + 7, "SKP", book=book, weight=700, size=20, fill=t["display"],
                         anchor="middle", tracking=0.04))

        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="Working stack: languages, platforms and AI in orbit")
    for name, markup in outputs.items():
        write(CARDS / f"orbit-{name}.svg", markup)
    return "orbit"


# --------------------------------------------------------------------------
# 3. Commit rhythm by hour (IST)
# --------------------------------------------------------------------------


def build_rhythm(activity: dict) -> str:
    width, height = CANVAS, 300
    book = FontBook()
    hours = {h["hour"]: h["events"] for h in activity.get("hours", [])}
    counts = [hours.get(h, 0) for h in range(24)]
    peak = max(counts) or 1
    peak_hour = counts.index(max(counts))
    night = sum(counts[h] for h in list(range(21, 24)) + list(range(0, 5)))
    share = round(100 * night / (sum(counts) or 1))

    def clock(h: int) -> str:
        return f"{h:02d}:00"

    gx, gy, gw, gh = 52, 92, width - 104, 150
    slot = gw / 24
    bar_w = slot * 0.62
    outputs = {}
    for t in THEMES.values():
        defs = (
            accent_gradient(t, "accent")
            + f'<linearGradient id="bar" x1="0" y1="1" x2="0" y2="0">'
            f'<stop offset="0" stop-color="{t["wine"]}"/>'
            f'<stop offset="1" stop-color="{t["rose"]}"/></linearGradient>'
        )
        css = (
            "<style>"
            ".b{transform-box:fill-box;transform-origin:50% 100%;transform:scaleY(0);"
            "animation:rise 1.1s cubic-bezier(.2,.8,.2,1) forwards}"
            "@keyframes rise{to{transform:scaleY(1)}}"
            ".sweep{animation:sweep 6s linear infinite}"
            f"@keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({gw:.0f}px)}}}}"
            "@media (prefers-reduced-motion:reduce){.b{animation:none;transform:none}"
            ".sweep{animation:none;opacity:0}}"
            "</style>"
        )
        body = [
            css,
            panel(0, 0, width, height, t, radius=22, fill=t["panel"], stroke=t["line"]),
            rect(28, 26, 3, 13, rx=1.5, fill=t["brass"]),
            text(40, 37, "WHEN THE COMMITS LAND", book=book, family="mono", size=11.5,
                 fill=t["muted"], tracking=0.16),
            text(width - 28, 37, f"IST · last {activity.get('sample', 0)} public events",
                 book=book, family="mono", size=11.5, fill=t["faint"], anchor="end",
                 tracking=0.06),
            text(52, 72, f"Night owl: {share}% of the work lands between 21:00 and 05:00, "
                         f"busiest at {clock(peak_hour)}.",
                 book=book, size=16, fill=t["ink_soft"]),
        ]
        # Night band
        for start, end in ((0, 5), (21, 24)):
            body.append(rect(gx + start * slot, gy - 4, (end - start) * slot, gh + 8, rx=8,
                             fill=t["wine"], fill_opacity=0.07))
        body.append(line(gx, gy + gh, gx + gw, gy + gh, stroke=t["line"], width=1))
        for h, value in enumerate(counts):
            bh = max(3, gh * value / peak)
            x = gx + h * slot + (slot - bar_w) / 2
            delay = 0.15 + h * 0.05
            body.append(rect(x, gy + gh - bh, bar_w, bh, rx=min(5, bar_w / 2),
                             fill="url(#bar)" if value else t["line"],
                             class_="b", style=f"animation-delay:{delay:.2f}s"))
            if h % 3 == 0:
                body.append(text(gx + h * slot + slot / 2, gy + gh + 22, clock(h), book=book,
                                 family="mono", size=11, fill=t["faint"], anchor="middle"))
        # Peak marker
        px = gx + peak_hour * slot + slot / 2
        body.append(f'<circle cx="{px:.1f}" cy="{gy - 10}" r="4" fill="{t["brass"]}">'
                    f'<animate attributeName="r" values="3;6;3" dur="1.8s" '
                    f'repeatCount="indefinite"/></circle>')
        # Scanning line, like a clock hand passing over the day
        body.append(f'<g class="sweep"><rect x="{gx}" y="{gy - 4}" width="2" height="{gh + 8}" '
                    f'fill="{t["rose"]}" fill-opacity="0.55"/></g>')

        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="Commit rhythm by hour of day, IST")
    for name, markup in outputs.items():
        write(CARDS / f"rhythm-{name}.svg", markup)
    return "rhythm"


# --------------------------------------------------------------------------
# 4. Footer wave
# --------------------------------------------------------------------------


def _wave(width: float, base: float, amp: float, phase: float, waves: int = 3) -> str:
    pts = []
    steps = 60
    for i in range(steps + 1):
        x = width * i / steps
        y = base + amp * math.sin(2 * math.pi * waves * i / steps + phase)
        pts.append(f"{x:.1f} {y:.1f}")
    return f"M0 {200} L" + " L".join(pts) + f" L{width:.0f} 200 Z"


def build_footer() -> str:
    width, height = CANVAS, 200
    book = FontBook()
    outputs = {}
    for t in THEMES.values():
        defs = (
            accent_gradient(t, "accent", 0, 0, 1, 0)
            + f'<linearGradient id="wa" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{t["wine"]}" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="{t["rose"]}" stop-opacity="0.55"/></linearGradient>'
            + f'<linearGradient id="wb" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{t["rose"]}" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="{t["wine"]}" stop-opacity="0.35"/></linearGradient>'
        )
        body = []
        for fill, base, amp, dur in (("url(#wb)", 120, 16, 9), ("url(#wa)", 140, 12, 6)):
            frames = [_wave(width, base, amp, p) for p in (0, math.pi / 2, math.pi,
                                                           3 * math.pi / 2, 2 * math.pi)]
            body.append(f'<path d="{frames[0]}" fill="{fill}"><animate attributeName="d" '
                        f'dur="{dur}s" repeatCount="indefinite" values="{";".join(frames)}"/>'
                        f'</path>')
        body.append(text(width / 2, 62, "Thanks for stopping by.", book=book, weight=600,
                         size=30, fill=t["display"], anchor="middle", tracking=-0.015))
        body.append(text(width / 2, 92, "Bring the messy version of the problem.", book=book,
                         size=16, fill=t["muted"], anchor="middle"))
        outputs[t["name"]] = wrap_svg(width, height, "".join(body), book, t, defs,
                                      title="Thanks for stopping by")
    for name, markup in outputs.items():
        write(CARDS / f"footer-{name}.svg", markup)
    return "footer"


def build_all() -> list[str]:
    activity = _load("activity-hours.json", {"hours": [], "sample": 0})
    return [build_terminal(), build_orbit(), build_rhythm(activity), build_footer()]


if __name__ == "__main__":
    print("built:", ", ".join(build_all()))
