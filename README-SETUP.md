# How this profile is built

Everything on the public profile page is generated. The README is written once;
the graphics, the statistics and the numbers inside them are rebuilt from the
GitHub API by a scheduled workflow and committed back as plain SVG.

```
data/            live JSON pulled from the GitHub API  (fetch_stats.py)
   ↓
scripts/         design system + asset generators
   ↓
assets/          the SVGs the README points at
site/            the interactive micro-site (optional, see below)
```

## The pieces

| Path | What it does |
| --- | --- |
| `scripts/design.py` | Design tokens (colour, type, spacing) plus the tiny SVG drawing kit: text with real font metrics, pills, panels, dot grids. |
| `scripts/fetch_stats.py` | Reads GraphQL/REST and writes `data/*.json`. Standard library only. |
| `scripts/build_assets.py` | Draws every card in `assets/`: banner, stats, languages, toolkit, timeline, blueprint and the animated contribution crawl. |
| `scripts/build_site.py` | Renders `site/index.html` and subsets the web fonts to the glyphs the page actually uses. |
| `scripts/check.py` | Guardrails — fails the build if any asset becomes broken, non-self-contained or references a missing file. |
| `scripts/fonts/` | Space Grotesk and JetBrains Mono (SIL OFL), committed so builds are reproducible and offline. |
| `.github/workflows/update-profile.yml` | Runs the whole chain daily at 03:17 UTC and commits the diff. |

## Local commands

```bash
make data     # refresh data/*.json  (needs GITHUB_TOKEN or the gh CLI)
make assets   # rebuild assets/  and site/
make check    # verify every generated asset
make serve    # preview the micro-site at http://localhost:8080
make all      # data + assets + check
```

Python 3.11+ with `fonttools` and `brotli` is all that is required:

```bash
pip install fonttools brotli
```

## Two rules the generators follow

**1. A graphic referenced with `<img>` cannot load anything external.**
Browsers refuse network requests from SVG images, so a `<link>` to a web font
silently falls back to Times New Roman. Every typeface is therefore subset to
the glyphs the graphic uses and embedded as base64 woff2 inside the SVG. That is
also why the emoji-free icon set is drawn as SVG paths — an emoji is a font
lookup, and there is no emoji font to look up.

**2. Light mode is a first-class citizen.**
Each card is generated twice, `*-dark.svg` and `*-light.svg`, and the README
selects between them with GitHub's documented `<picture>` / `prefers-color-scheme`
pattern. `check.py` asserts that every pair shares identical dimensions, so the
layout never jumps when a reader switches themes.

## The animated contribution crawl

`assets/crawl-dark.svg` walks a crawler across the real contribution calendar —
one square lights per contribution, column by column, then the card resets.

- Cell order is a serpentine traversal of `data/contribution-calendar.json`.
- Each square's `<animate>` `keyTimes` derive from its distance along that route,
  so the lighting always stays in step with the crawler.
- Intensity colours come from GitHub's own five-level scale.
- `site/crawl.inline.svg` is the same drawing rebuilt with CSS classes, so the
  micro-site re-themes it instantly without reloading a single byte.

If you fork this, `scripts/build_assets.py` is the only file you need to edit to
change the story; `design.py` is the only file you need to edit to change the look.

## The micro-site

`site/` is a standalone page — hero, live numbers, selected work, credentials,
and a sandboxed preview panel for deployed projects. It has no build step and no
frameworks: one HTML file, one stylesheet, one script, fonts subset at build
time. Serve it on GitHub Pages, Netlify or any static host:

```bash
python3 -m http.server 8080 --directory site
```

The demo panel only embeds hosts on its allowlist (`data-allowlist` on the
picker). Sites that send `X-Frame-Options` will refuse to render — the panel says
so and offers a new-tab link, which is why the allowlist is short and deliberate.

## Adding a card

1. Write a `build_<name>()` in `scripts/build_assets.py` that returns a card for
   each entry in `THEMES`, drawing with the helpers from `design.py`.
2. Call it from `main()` and add the pair of files to the README with a
   `<picture>` block.
3. `python scripts/check.py` — it verifies the pair, the dimensions and that the
   README points at files that exist.

Fonts are licensed under the SIL Open Font License 1.1; the subset files in
`scripts/fonts/` are derived from the upstream releases.
