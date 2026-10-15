#!/usr/bin/env python3
"""
Guardrails for the generated profile assets.

Every graphic on the profile is committed as a plain SVG and rendered by GitHub
inside an <img> tag. In that context a browser refuses to load *any* external
resource, so a stray web font or remote image would silently degrade the page.
This script fails loudly instead.

Checks
  1. every SVG parses as XML
  2. no SVG references anything off-disk (only the SVG namespace is allowed)
  3. every @font-face in an SVG is a self-contained data: URI
  4. every data/*.json parses and looks structurally sane
  5. every relative path referenced by README.md exists
  6. every card ships both a dark and a light variant with identical dimensions
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG_NS = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"

ALLOWED_URLS = {SVG_NS, XLINK}
REFERENCE_PATTERN = re.compile(r"""(?:src|xlink:href|href)\s*=\s*["']([^"']+)["']""")
# A remote URL must look like a host: base64 font payloads legitimately contain
# "//" sequences, so require a dotted domain (or localhost) to avoid false hits.
URL_IN_TEXT = re.compile(r"(?:https?:)?//(?:localhost|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})(?:[/?#][^\s\"'<>)]*)?")
FONT_SRC = re.compile(r"src\s*:\s*url\(([^)]+)\)")

problems: list[str] = []
notes: list[str] = []


def fail(message: str) -> None:
    problems.append(message)


def check_svg(path: Path) -> ET.Element | None:
    text = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        fail(f"{path.relative_to(ROOT)}: not valid XML — {error}")
        return None

    for match in REFERENCE_PATTERN.finditer(text):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "//")) and target not in ALLOWED_URLS:
            fail(f"{path.relative_to(ROOT)}: external reference {target[:70]!r}")

    for match in URL_IN_TEXT.finditer(text):
        url = match.group(0)
        if url.rstrip("/") in {SVG_NS, XLINK} or url in {SVG_NS, XLINK}:
            continue
        if "w3.org" in url:  # namespace declarations only
            continue
        fail(f"{path.relative_to(ROOT)}: remote URL in asset {url[:70]!r}")

    for match in FONT_SRC.finditer(text):
        source = match.group(1).strip().strip("'\"")
        if not source.startswith("data:"):
            fail(f"{path.relative_to(ROOT)}: font not embedded ({source[:50]!r})")

    return root


def check_svg_pair(dark: Path, light: Path) -> None:
    dark_root, light_root = check_svg(dark), check_svg(light)
    if dark_root is None or light_root is None:
        return
    for attribute in ("width", "height", "viewBox"):
        a, b = dark_root.get(attribute), light_root.get(attribute)
        if a != b:
            fail(f"{dark.name} / {light.name}: {attribute} differs ({a} vs {b})")


def check_json(path: Path) -> dict | list | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path.relative_to(ROOT)}: {error}")
        return None
    return payload


def check_readme() -> None:
    readme = ROOT / "README.md"
    if not readme.exists():
        fail("README.md is missing")
        return
    text = readme.read_text(encoding="utf-8")

    for match in re.finditer(r'(?:src|srcset)="([^"]+)"', text):
        for candidate in match.group(1).split(","):
            target = candidate.strip().split(" ")[0]
            if not target or target.startswith(("http://", "https://", "data:", "#")):
                continue
            if not (ROOT / target).exists():
                fail(f"README.md references a missing file: {target}")

    # Every theme-aware block must be <picture> with a dark <source> plus a
    # non-SVG-less fallback <img>, otherwise light-mode readers get nothing.
    pictures = re.findall(r"<picture>(.*?)</picture>", text, flags=re.DOTALL)
    if not pictures:
        fail("README.md has no <picture> blocks — dark-mode readers get the wrong artwork")
    for index, block in enumerate(pictures, start=1):
        if "prefers-color-scheme: dark" not in block:
            fail(f"README.md <picture> #{index} has no dark-mode <source>")
        if "<img" not in block:
            fail(f"README.md <picture> #{index} has no fallback <img>")
        sources = re.findall(r'srcset="([^"]+)"', block)
        fallbacks = re.findall(r'<img[^>]*src="([^"]+)"', block)
        if sources and fallbacks and sources[0] == fallbacks[0]:
            fail(f"README.md <picture> #{index} uses one file for both themes")
    notes.append(f"README.md ships {len(pictures)} theme-aware images")


def main() -> int:
    svgs = [path for path in sorted(ROOT.glob("assets/**/*.svg")) if not path.name.startswith("_qa")]
    svgs += [path for path in sorted(ROOT.glob("site/assets/**/*.svg")) if not path.name.startswith("_qa")]

    for path in svgs:
        check_svg(path)

    cards = sorted((ROOT / "assets" / "cards").glob("*-dark.svg"))
    if not cards:
        fail("no dark/light card pairs found in assets/cards")
    for dark in cards:
        light = dark.with_name(dark.name.replace("-dark.svg", "-light.svg"))
        if not light.exists():
            fail(f"{dark.name} has no light-mode twin")
        else:
            check_svg_pair(dark, light)

    payloads = {}
    for path in sorted(ROOT.glob("data/*.json")):
        payloads[path.name] = check_json(path)

    stats = payloads.get("profile-stats.json")
    if isinstance(stats, dict):
        for key in ("login", "contributions", "own_repos", "generated_at"):
            if key not in stats:
                fail(f"profile-stats.json is missing '{key}'")
    calendar = payloads.get("contribution-calendar.json")
    if isinstance(calendar, dict):
        weeks = calendar.get("weeks") or []
        if len(weeks) < 50:
            fail(f"contribution-calendar.json looks truncated ({len(weeks)} weeks)")
        empty = [w for w in weeks if len(w) != 7]
        if empty:
            notes.append(f"{len(empty)} calendar weeks do not have 7 days")
    languages = payloads.get("languages.json")
    if isinstance(languages, dict) and not languages.get("by_repo"):
        fail("languages.json has no by_repo entries")

    check_readme()

    for name in ("index.html", "styles.css", "app.js", "fonts.css"):
        if not (ROOT / "site" / name).exists():
            fail(f"site/{name} is missing — run scripts/build_site.py")
    index = (ROOT / "site" / "index.html").read_text(encoding="utf-8") if (ROOT / "site" / "index.html").exists() else ""
    if index and "class=\"crawl-svg\"" not in index:
        notes.append("site/index.html does not contain the inline contribution crawl")

    print(f"checked {len(svgs)} SVGs, {len(payloads)} data files, README and site")
    for note in notes:
        print(f"  note: {note}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  ✕ {problem}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
