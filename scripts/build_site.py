"""
Build the GeekLord profile micro-site.

  python3 scripts/build_site.py

Produces (everything committed, nothing fetched at runtime):

  site/index.html      the page
  site/fonts.css       fonts subset to the exact glyphs the page uses, base64 woff2
  site/assets/         copies of the generated SVG cards
  site/data/           copies of the JSON that powers the live widgets
  site/crawl.inline.svg  the theme-aware contribution animation, inlined into the page

The site is a nice-to-have: the profile README never depends on it. It exists so
there is something interactive to show when someone wants to dig deeper, plus one
sandboxed preview panel for the projects that are actually deployed somewhere.
"""

from __future__ import annotations

import base64
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
FONTS = Path(__file__).resolve().parent / "fonts"

from fontTools import subset  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from io import BytesIO  # noqa: E402

# --------------------------------------------------------------------------
# Content — every claim here traces back to shobhit.net, the GitHub API or
# the repositories themselves. Update this block, not the prose below.
# --------------------------------------------------------------------------

PRACTICE = [
    {
        "icon": "clipboard",
        "title": "Field data systems",
        "blurb": "Fault-tolerant mobile data collection for research that cannot afford bad numbers.",
        "points": [
            "Complex XLSForm architecture with nested repeat groups",
            "Multi-language instruments (English, Hindi, Swahili, French, Arabic)",
            "Automated daily quality audits and anomaly detection",
            "Protected delivery into clean research lakes",
        ],
        "stack": ["SurveyCTO", "ODK", "JavaRosa", "XLSForm", "PostgreSQL", "Python ETL"],
    },
    {
        "icon": "bolt",
        "title": "Web platforms",
        "blurb": "High-availability applications engineered for the tenth year, not the launch day.",
        "points": [
            "Astro, Next.js and React with sub-second delivery",
            "Custom PHP/WordPress architectures without page-builder bloat",
            "REST and GraphQL APIs, schema design, integrations",
            "Hardened cloud infrastructure and zero-downtime deploys",
        ],
        "stack": ["Astro", "React", "Node.js", "PHP", "AWS", "Docker", "Nginx"],
    },
    {
        "icon": "robot",
        "title": "Practical AI",
        "blurb": "Agentic systems anchored to your documents, with the guardrails to prove it.",
        "points": [
            "Hybrid retrieval (embeddings + BM25) with citation verification",
            "Tool-calling agents against real APIs and databases",
            "Evaluation suites, cost controls, no vendor lock-in",
            "Structured extraction from PDFs into verified JSON",
        ],
        "stack": ["RAG", "Agents", "Guardrails", "Claude · GPT · Gemini"],
    },
]

WORK = [
    {
        "title": "Global Field Research Data Suite",
        "client": "International research consortia & NGOs",
        "region": "Global · 12+ countries",
        "year": "2018 – present",
        "outcome": "1.5M+ high-integrity submissions across 600+ instruments",
        "body": "Enterprise SurveyCTO, ODK and XLSForm infrastructure powering health, "
                "agriculture and socio-economic research — with supervisor auditing and "
                "protected data delivery built in.",
        "stack": ["SurveyCTO", "ODK", "Python", "PostgreSQL"],
        "links": [("Case study", "https://shobhit.net/portfolio/field-research-data-suite/"),
                  ("Live", "https://cybermitra.com/")],
    },
    {
        "title": "Souters Training Portal & Executive LMS",
        "client": "Souters Training Ltd",
        "region": "London, UK",
        "year": "2010 · platform 2021",
        "outcome": "99.9% uptime in production since 2021",
        "body": "Accredited executive training and legal education portal with custom course "
                "booking and automated enrolment pipelines, running sub-second under real traffic.",
        "stack": ["WordPress", "PHP", "Stripe", "Custom booking engine"],
        "links": [("Case study", "https://shobhit.net/portfolio/souters-training/"),
                  ("Live", "https://www.souterstraining.com/")],
    },
    {
        "title": "Morsel Research Web & Cloud Data Hub",
        "client": "Morsel Research & Development",
        "region": "New Delhi & Lucknow",
        "year": "2013 – present",
        "outcome": "Institutional platform for studies covering ~20M respondents",
        "body": "Corporate portal, secure research repository and digital field-operations "
                "infrastructure for India's primary data collection and public policy research work.",
        "stack": ["WordPress", "PHP", "AWS EC2/S3", "GDPR InfoSec"],
        "links": [("Case study", "https://shobhit.net/portfolio/morsel-india-platform/"),
                  ("Live", "https://morselindia.in/")],
    },
    {
        "title": "Field-tooling & agent experiments",
        "client": "Open source",
        "region": "github.com/GeekLord",
        "year": "ongoing",
        "outcome": "28 own repositories and counting",
        "body": "SurveyCTO voting field plugins, XLSForm-to-codebook utilities, Zoom bulk joiner, "
                "Cloudflare DNS updater, a Windows maintenance kit, an AI photo editor — plus a "
                "browser recreation of the Windows 98 defragmenter, purely for the joy of it.",
        "stack": ["Python", "TypeScript", "PowerShell", "JavaScript"],
        "links": [("Repositories", "https://github.com/GeekLord?tab=repositories"),
                  ("Sarvam AI CLI suite", "https://github.com/GeekLord/sarvam-ai_api_tools")],
    },
]

CREDENTIALS = [
    ("Nebius Academy", "shield", "Nebius Agentic AI Builder Certification", "Intermediate",
     "Architecting agentic AI workflows, RAG pipelines and tool-augmented agents with live web search and vector databases.",
     "https://www.credly.com/badges/68270912-06ac-42f7-a647-972ea1145e77/public_url"),
    ("Nebius Academy", "compass", "Nebius AI Leader Certification", "Foundational",
     "Enterprise AI product strategy, vendor and cost evaluation, and controlling AI output against mission-critical objectives.",
     "https://www.credly.com/badges/90080792-8f6a-4f5e-934c-1e24194875c3/public_url"),
    ("Google Cloud", "cloud", "Prompt Design in Vertex AI", "Skill badge",
     "Hands-on challenge lab: prompt engineering and multimodal generation with Gemini models in Vertex AI.",
     "https://www.credly.com/badges/c93f7b4e-c037-4d14-a78c-843be69fbfd0/public_url"),
    ("Harvey Academy", "scales", "Level 1 Legal Engineer", "Foundational",
     "Legal-specific AI risk, matching AI surfaces to practice areas, and driving adoption through facilitation and change management.",
     "https://www.credly.com/badges/83820826-787a-4a60-9064-9cd3cd2cb492/public_url"),
    ("Harvey Academy", "ruler", "Level 1 Foundations", "Foundational",
     "Evaluating AI output with professional judgment, extraction prompts for consistency and a rigorous verification framework.",
     "https://www.credly.com/badges/50667369-7550-435a-9ee9-ae9de0b9d326/public_url"),
    ("Anthropic · Claude Academy", "spark", "15 course completion badges", "2026",
     "Claude Code 101, Claude Platform 101, Model Context Protocol, Claude Cowork and the full AI Fluency series.",
     "https://shobhit.net/about/#claude-academy"),
    ("CSSC", "target", "Six Sigma White Belt", "Quality control",
     "Lean quality-control foundations applied to delivery processes and defect prevention.",
     "https://shobhit.net/about/#credentials"),
    ("IIT Bombay · Kharagpur · Kanpur", "cap", "GATE qualified 3× in Information Technology", "National exam",
     "Engineering aptitude certified by India's national Graduate Aptitude Test in Engineering.",
     "https://shobhit.net/about/#credentials"),
]

FACTS = [
    ("20+", "years engineering"),
    ("850+", "web platforms"),
    ("600+", "field instruments"),
    ("12+", "countries deployed"),
]

CONTACT = [
    ("mail", "Email", "shobhit@shobhit.net", "mailto:shobhit@shobhit.net"),
    ("phone", "Phone · 24×7, AI-answered", "+91 79658 52100", "tel:+917965852100"),
    ("globe", "Website", "shobhit.net", "https://shobhit.net/"),
    ("building", "Studio", "cybermitra.com", "https://cybermitra.com/"),
    ("pen", "Blog", "geeklord.com", "https://geeklord.com/"),
    ("badge", "Credentials", "credly.com/users/geeklord", "https://www.credly.com/users/geeklord/badges"),
]


ICONS = {
    # 24x24 stroke icons; drawn as paths so they inherit the text colour and
    # never depend on an emoji font being installed.
    "clipboard": '<path d="M9 4h6v2.2H9z"/><path d="M7 5.5H6a2 2 0 0 0-2 2V19a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5a2 2 0 0 0-2-2h-1"/><path d="M9 12.5h6M9 16.5h4"/>',
    "bolt": '<path d="M13.5 3 5.8 13.2h4.6L9.7 21l7.7-10.2h-4.6z"/>',
    "robot": '<rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 4.5V8"/><circle cx="9" cy="13" r="1.3"/><circle cx="15" cy="13" r="1.3"/><path d="M9.5 16.6h5"/>',
    "shield": '<path d="M12 3.5 5.5 6v6c0 4.2 2.8 7.4 6.5 9 3.7-1.6 6.5-4.8 6.5-9V6z"/><path d="m9.3 12.2 2 2 3.4-3.6"/>',
    "compass": '<circle cx="12" cy="12" r="8.5"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
    "cloud": '<path d="M7.5 18.5h9.8a3.7 3.7 0 0 0 .3-7.4 5.3 5.3 0 0 0-10.2-1.3 4.1 4.1 0 0 0 .1 8.7z"/>',
    "scales": '<path d="M12 4v16M7 20h10"/><path d="m4.5 8 3-3 3 3"/><path d="M4.5 8a3 3 0 0 0 6 0"/><path d="m13.5 8 3-3 3 3"/><path d="M13.5 8a3 3 0 0 0 6 0"/>',
    "ruler": '<rect x="3.5" y="8.5" width="17" height="7" rx="1.6"/><path d="M8 8.5v3M12 8.5v4M16 8.5v3"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/>',
    "cap": '<path d="M3 9.5 12 5l9 4.5-9 4.5z"/><path d="M7 11.7V16c0 1.4 2.2 2.6 5 2.6s5-1.2 5-2.6v-4.3"/><path d="M20 10v5"/>',
    "arrow": '<path d="M5 12h13"/><path d="m13 7 5 5-5 5"/>',
    "external": '<path d="M14 5h5v5"/><path d="M19 5l-7.5 7.5"/><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>',
    "mail": '<rect x="3.5" y="5.5" width="17" height="13" rx="2.5"/><path d="m4.5 7.5 7.5 6 7.5-6"/>',
    "phone": '<path d="M6.5 4.5h3l1.5 4-2 1.5a10.5 10.5 0 0 0 5 5l1.5-2 4 1.5v3a2 2 0 0 1-2.2 2A15.5 15.5 0 0 1 4.5 6.7a2 2 0 0 1 2-2.2z"/>',
    "globe": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17"/><path d="M12 3.5c2.4 2.3 3.6 5.2 3.6 8.5s-1.2 6.2-3.6 8.5c-2.4-2.3-3.6-5.2-3.6-8.5S9.6 5.8 12 3.5z"/>',
    "building": '<path d="M5 20V6.5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2V20"/><path d="M15 11h2.5a2 2 0 0 1 2 2v7"/><path d="M3.5 20h17"/><path d="M8.5 8.5h3M8.5 12h3M8.5 15.5h3"/>',
    "pen": '<path d="M4.5 19.5 5.7 15 16 4.7a2.1 2.1 0 0 1 3 3L8.7 18z"/><path d="M14.5 6.2 17.8 9.5"/>',
    "badge": '<circle cx="12" cy="10" r="5.5"/><path d="m9 15-1.5 5.5 4.5-2.3 4.5 2.3L15 15"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "spark": '<path d="M12 4v4M12 16v4M4 12h4M16 12h4"/><path d="m7.5 7.5 2 2M14.5 14.5l2 2M16.5 7.5l-2 2M9.5 14.5l-2 2"/>',
}


def icon(name: str, *, size: int = 20, css_class: str = "ico") -> str:
    body = ICONS[name]
    return (f'<svg class="{css_class}" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{body}</svg>')


PALETTE = {
    "dark": ["#8B6BFF", "#35D6F2", "#42D392", "#F2B33D", "#6E8BFF", "#FF7AB8", "#7E8FAE"],
}

TEXT_FILES = {"SpaceGrotesk": {
    400: "SpaceGrotesk-Regular.ttf",
    500: "SpaceGrotesk-Medium.ttf",
    600: "SpaceGrotesk-SemiBold.ttf",
    700: "SpaceGrotesk-Bold.ttf",
}, "JetBrainsMono": {
    400: "JetBrainsMono-Regular.ttf",
    600: "JetBrainsMono-SemiBold.ttf",
}}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def load(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def human_bytes(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f} MB"
    if count >= 1_000:
        return f"{count / 1_000:.0f} KB"
    return f"{count} B"


def esc(value) -> str:
    return escape(str(value))


def external(url: str) -> str:
    """Blank target + noopener for off-site links, nothing for local ones."""
    return ' target="_blank" rel="noopener"' if str(url).startswith("http") else ""


def subset_font(filename: str, characters: str) -> str:
    options = subset.Options()
    options.flavor = "woff2"
    options.desubroutinize = True
    options.layout_features = ["kern", "liga", "calt"]
    options.notdef_outline = True
    font = subset.load_font(str(FONTS / filename), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=characters)
    subsetter.subset(font)
    buffer = BytesIO()
    subset.save_font(font, buffer, options)
    font.close()
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def write_fonts_css(html: str) -> None:
    """Subset each weight to the glyphs actually present in the built page."""
    characters = "".join(sorted(set(html) | set("0123456789%·—→×")))
    rules = []
    for family, weights in TEXT_FILES.items():
        for weight, filename in weights.items():
            payload = subset_font(filename, characters)
            rules.append(
                "@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:swap;"
                "src:url(data:font/woff2;base64,%s) format('woff2');}" % (family, weight, payload)
            )
    (SITE / "fonts.css").write_text("\n".join(rules) + "\n", encoding="utf-8")


def copy_assets(needed: set[str]) -> list[str]:
    """Copy only the graphics the page actually references — the language and
    crawler cards are rebuilt as live HTML/SVG there, so shipping them would be
    dead weight."""
    # Start from a clean slate so removed cards do not linger in the deploy.
    if (SITE / "assets").exists():
        shutil.rmtree(SITE / "assets")
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    names = []
    for source in sorted(ASSETS.rglob("*.svg")):
        if str(source.relative_to(ASSETS)) not in needed:
            continue
        target = SITE / "assets" / source.relative_to(ASSETS)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        names.append(str(target.relative_to(SITE)))
    for source in sorted(DATA.glob("*.json")):
        shutil.copy2(source, SITE / "data" / source.name)
        names.append(f"data/{source.name}")
    return names


def theme_img(dark: str, light: str, alt: str, *, css_class: str = "") -> str:
    klass = f"figure {css_class}".strip()
    return (
        f'<figure class="{klass}">'
        f'<img class="only-dark" src="{dark}" alt="{esc(alt)}" loading="lazy" decoding="async">'
        f'<img class="only-light" src="{light}" alt="{esc(alt)}" loading="lazy" decoding="async">'
        f"</figure>"
    )


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------


def hero(stats: dict) -> str:
    chips = "".join(
        f'<div class="tile"><b>{esc(value)}</b><span>{esc(label)}</span></div>'
        for value, label in FACTS
    )
    return f"""
<section class="hero wrap" id="top">
  {theme_img("assets/cards/banner-dark.svg", "assets/cards/banner-light.svg",
             "Shobhit Kumar Prabhakar — Software Architect")}
  <div class="center reveal">
    <p class="lede" style="margin:0 auto .8em">
      I take direct personal responsibility for mission-critical software: sub-second web
      platforms, offline-first field-data instruments deployed in 12+ countries, and grounded
      AI workflows that cite their sources instead of guessing.
    </p>
    <div class="hero-meta">
      <span class="pulse"><i></i> Open to select engagements</span>
      <span class="chip">Lucknow, India · IST (UTC+5:30)</span>
      <span class="chip">Phone answered 24×7 by my AI assistant</span>
    </div>
    <div class="btn-row" style="justify-content:center;margin-top:22px">
      <a class="btn primary" href="#work">See selected work</a>
      <a class="btn" href="https://shobhit.net/services/">Services</a>
      <a class="btn ghost" href="#contact">Start a project</a>
    </div>
    <div class="tiles" style="margin-top:30px">{chips}</div>
  </div>
</section>
"""


def live_section(stats: dict, calendar: dict, languages: dict, crawl_svg: str) -> str:
    def rel_time(raw: str) -> str:
        try:
            stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return "unknown"
        days = (datetime.now(timezone.utc) - stamp).days
        if days <= 0:
            return "today"
        if days == 1:
            return "yesterday"
        return f"{days} days ago"

    stat_rows = "".join(
        f'<div class="stat-row"><b>{esc(value)}</b><span>{esc(label)}</span></div>'
        for value, label in [
            (f"{stats.get('contributions', 0):,}", "contributions"),
            (f"{stats.get('commits', 0):,}", "commits"),
            (f"{stats.get('pull_requests', 0):,}", "pull requests"),
            (f"{stats.get('own_repos', 0)}", "own repositories"),
            (f"{stats.get('stars', 0)}", "stars across own repos"),
            (f"{stats.get('followers', 0)}", "followers"),
            (f"{stats.get('joined_year', 2010)}", "on GitHub since"),
        ]
    )

    palette = PALETTE["dark"]
    entries = list(languages.get("by_repo", []))[:7]
    language_bar = "".join(
        f'<span style="flex:{entry.get("share", 1):.2f} 1 0;background:{palette[index % len(palette)]}" '
        f'title="{esc(entry["name"])} {entry.get("share", 0):.0f}%"></span>'
        for index, entry in enumerate(entries)
    )
    # Largest codebases by bytes — a different, useful cut of the same data.
    biggest = [entry for entry in languages.get("by_bytes", []) if entry.get("bytes", 0) > 0][:6]
    byte_rows = "".join(
        f'<span class="lang-item" style="border-style:dashed"><i style="background:{palette[(index + 3) % len(palette)]}"></i>'
        f'<b>{esc(entry["name"])}</b><small>{esc(human_bytes(entry["bytes"]))}</small></span>'
        for index, entry in enumerate(biggest)
    )

    language_items = "".join(
        f'<span class="lang-item"><i style="background:{palette[index % len(palette)]}"></i>'
        f'<b>{esc(entry["name"])}</b><small>{entry.get("share", 0):.0f}% · {esc(entry.get("detail", ""))}</small></span>'
        for index, entry in enumerate(entries)
    )
    return f"""
<section class="section" id="live">
  <div class="wrap">
    <p class="eyebrow">Live from GitHub</p>
    <h2>Numbers that update themselves</h2>
    <p class="lede">A scheduled workflow re-reads the GitHub API every day, rebuilds these
      graphics from scratch and commits them back to the repository. Nothing on this page is
      typed by hand, and nothing is fetched from a third-party image host.</p>

    <div class="grid two reveal" style="margin-top:28px">
      <div class="card" style="grid-column:1/-1;padding:18px">{crawl_svg}</div>
      <div class="card">
        <h3>Last twelve months</h3>
        <div class="stat-rows">{stat_rows}</div>
        <p class="lab-note" style="margin:16px 0 0">
          data captured {esc(rel_time(stats.get('generated_at', '')))}
          · {esc(stats.get('login', 'GeekLord'))} on GitHub since {esc(stats.get('joined_year', 2010))}
        </p>
      </div>
      <div class="card">
        <h3>Where the code lives</h3>
        <p class="dim" style="font-size:14.5px;margin-bottom:14px">
          {esc(languages.get('basis', 'own repositories'))} — forked repositories are excluded,
          so this is the language mix of work I actually own.
        </p>
        {language_bar}
        <div class="lang-list">{language_items}</div>
        <h4 style="margin:22px 0 10px;font-size:15px">Largest codebases by bytes</h4>
        <div class="lang-list">{byte_rows}</div>
      </div>
    </div>
  </div>
</section>
"""


def practice_section() -> str:
    cards = []
    for item in PRACTICE:
        points = "".join(f"<li>{esc(point)}</li>" for point in item["points"])
        stack = "".join(f'<span class="chip">{esc(tech)}</span>' for tech in item["stack"])
        cards.append(f"""
      <article class="card hoverable reveal">
        <div class="icon">{icon(item['icon'], size=22)}</div>
        <h3>{esc(item['title'])}</h3>
        <p>{esc(item['blurb'])}</p>
        <ul class="ticks">{points}</ul>
        <div class="chips">{stack}</div>
      </article>""")
    return f"""
<section class="section" id="practice">
  <div class="wrap">
    <p class="eyebrow">Practice areas</p>
    <h2>Three things, done properly</h2>
    <p class="lede">Twenty years of delivery distilled into three disciplines — pick one, or
      bring a problem that spans all three.</p>
    <div class="grid three" style="margin-top:28px">{''.join(cards)}</div>
  </div>
</section>
"""


def method_section() -> str:
    def steps(name: str, items: list[tuple[str, str]]) -> str:
        rows = "".join(
            f'<div class="step"><div><h4>{esc(title)}</h4><p>{esc(subtitle)}</p></div></div>'
            for title, subtitle in items
        )
        return f'<div><h3>{esc(name)}</h3><div class="steps">{rows}</div></div>'

    columns = [
        ("Field data pipeline", [
            ("Offline capture", "SurveyCTO, ODK and XLSForm instruments collect answers without a network."),
            ("In-form validation", "Skip logic, constraints and calculations reject impossible answers at the door."),
            ("Automated daily audits", "Python pipelines check enumerator pacing, duration and audio spot-checks."),
            ("Clean delivery", "Validated data lands in a protected research lake with discrepancy reports."),
        ]),
        ("Web platform pipeline", [
            ("Design system first", "Tokens and components agreed before a single page is built."),
            ("Sub-second delivery", "Astro, React and disciplined assets against real-world Core Web Vitals."),
            ("Hardened infrastructure", "AWS, Cloudflare and Nginx configured for hostile traffic, not demos."),
            ("Zero-downtime releases", "CI/CD pipelines where a deploy is a non-event."),
        ]),
        ("AI workflow pipeline", [
            ("Private corpus", "Your documents, catalogues and reports become the only source of truth."),
            ("Hybrid retrieval", "Embeddings plus BM25 keyword search, so exact identifiers are never missed."),
            ("Guardrails and evals", "Schemas, refusal rules, cost caps and benchmark scoring from day one."),
            ("Cited answers", "Every response carries a verifiable citation or it does not ship."),
        ]),
    ]
    return f"""
<section class="section" id="method">
  <div class="wrap">
    <p class="eyebrow">How systems get built</p>
    <h2>The same four moves, every time</h2>
    <p class="lede">Different domains, one method: make the failure modes impossible before
      making the features impressive.</p>
    <div class="grid three" style="margin-top:28px">
      {''.join(steps(name, items) for name, items in columns)}
    </div>
    <div class="reveal" style="margin-top:34px">
      {theme_img("assets/cards/blueprint-dark.svg", "assets/cards/blueprint-light.svg",
                 "Engineering blueprint across field data, web platforms and AI systems")}
      {theme_img("assets/cards/timeline-dark.svg", "assets/cards/timeline-light.svg",
                 "Two decades of milestones")}
      {theme_img("assets/cards/toolkit-dark.svg", "assets/cards/toolkit-light.svg",
                 "Toolkit and stack")}
    </div>
  </div>
</section>
"""


def work_section() -> str:
    cards = []
    for job in WORK:
        stack = "".join(f'<span class="chip">{esc(tech)}</span>' for tech in job["stack"])
        links = " · ".join(
            f'<a href="{esc(url)}"{external(url)}>{esc(label)} {icon("arrow", size=14, css_class="ico ico-inline")}</a>'
            for label, url in job["links"]
        )
        cards.append(f"""
      <article class="card hoverable project reveal">
        <header>
          <h3>{esc(job['title'])}</h3>
          <span class="meta">{esc(job['client'])} · {esc(job['region'])} · {esc(job['year'])}</span>
        </header>
        <p>{esc(job['body'])}</p>
        <p class="outcome">{icon("spark", size=15, css_class="ico ico-inline")} {esc(job['outcome'])}</p>
        <div class="chips">{stack}</div>
        <div class="links">{links}</div>
      </article>""")
    return f"""
<section class="section" id="work">
  <div class="wrap">
    <p class="eyebrow">Selected work</p>
    <h2>Systems currently in production</h2>
    <p class="lede">A short list, deliberately: platforms and instruments that are running today,
      with outcomes the client can verify.</p>
    <div class="grid two" style="margin-top:28px">{''.join(cards)}</div>
    <p class="dim reveal" style="margin-top:22px">
      There are 27 production deployments documented in the portfolio —
      <a href="https://shobhit.net/portfolio/">browse all of them {icon("arrow", size=14, css_class="ico ico-inline")}</a>
    </p>
  </div>
</section>
"""


def credentials_section() -> str:
    issuers = []
    for issuer, *_ in CREDENTIALS:
        if issuer not in issuers:
            issuers.append(issuer)
    buttons = '<button data-filter="all" aria-pressed="true">All</button>' + "".join(
        f'<button data-filter="{esc(issuer)}" aria-pressed="false">{esc(issuer)}</button>'
        for issuer in issuers
    )
    cards = "".join(f"""
      <article class="card cred reveal" data-issuer="{esc(issuer)}">
        <div class="seal">{icon(seal, size=20)}</div>
        <div>
          <h4>{esc(title)}</h4>
          <div class="issuer">{esc(issuer)} · {esc(level)}</div>
          <p>{esc(detail)}</p>
          <p style="margin-top:10px"><a href="{esc(url)}" target="_blank" rel="noopener">Verify {icon("external", size=14, css_class="ico ico-inline")}</a></p>
        </div>
      </article>""" for issuer, seal, title, level, detail, url in CREDENTIALS)

    return f"""
<section class="section" id="credentials">
  <div class="wrap">
    <p class="eyebrow">Verified credentials</p>
    <h2>Certified, and kept current</h2>
    <p class="lede">Every badge below links to its issuer's own verification record — no
      screenshots, no unverifiable claims.</p>
    <div class="filters" style="margin-top:22px">{buttons}</div>
    <div class="grid three">{cards}</div>
    <div class="card reveal" style="margin-top:20px;display:flex;flex-wrap:wrap;gap:26px;align-items:center">
      <div><b>B.Tech, Information Technology</b><br><span class="dim">First Division Honours</span></div>
      <div><b>GATE (IT) qualified 3×</b><br><span class="dim">IIT Bombay, Kharagpur &amp; Kanpur</span></div>
      <div><b>Six Sigma White Belt</b><br><span class="dim">The Council for Six Sigma Certification</span></div>
    </div>
  </div>
</section>
"""


def lab_section(stats: dict) -> str:
    demos = [
        ("https://geeklord.github.io/Win98-Defrag-Simulator/", "Win98 Defrag Simulator — GitHub Pages"),
        ("https://free-image-analyzer.netlify.app/", "Free Image Analyzer — Netlify"),
        ("https://geeklord.github.io/", "geeklord.github.io"),
    ]
    allowlist = "geeklord.github.io free-image-analyzer.netlify.app"
    options = "".join(f'<option value="{esc(url)}">{esc(label)}</option>' for url, label in demos)
    return f"""
<section class="section" id="lab">
  <div class="wrap">
    <p class="eyebrow">Lab</p>
    <h2>When do the commits actually happen?</h2>
    <p class="lede">This chart is drawn in your browser from the same JSON the graphics above are
      built from — bucketed into my working hours in IST, so you can see whether a "quick reply"
      is realistic in your time zone.</p>

    <div class="card reveal" style="margin-top:24px">
      <div class="clock" role="img" aria-label="Public GitHub activity by hour of day, IST"></div>
      <div class="clock-axis">{''.join(f'<span>{h:02d}</span>' for h in range(24))}</div>
      <p class="lab-note" data-clock-note style="margin:14px 0 0">Loading activity data…</p>
    </div>

    <h3 style="margin-top:44px">Live demo panel</h3>
    <p class="lede" style="font-size:17px">A sandboxed browser for the projects that are actually
      deployed. Only allowlisted hosts can load here; everything else is refused before a request
      is made. Some sites block framing outright — use the open button when that happens.</p>

    <div class="lab-bar reveal" style="margin-top:18px">
      <select data-demo-picker data-allowlist="{esc(allowlist)}" aria-label="Choose a deployed project">{options}</select>
      <button class="btn" data-frame-reload type="button">Reload</button>
      <button class="btn" data-frame-open type="button">Open in a new tab {icon("external", size=15, css_class="ico ico-inline")}</button>
      <span class="lab-note" data-frame-status>waiting</span>
    </div>

    <div class="frame reveal" data-frame>
      <iframe title="Embedded project preview" loading="lazy" referrerpolicy="no-referrer"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"></iframe>
      <div class="overlay"><b>Pick a project to load.</b><span>Nothing loads until you ask for it.</span></div>
    </div>
    <p class="lab-note" data-frame-title style="margin-top:10px">not loaded</p>
  </div>
</section>
"""


def contact_section(stats: dict) -> str:
    tiles = "".join(f"""
      <div class="card reveal">
        <div class="icon">{icon(name, size=22)}</div>
        <div class="issuer">{esc(label)}</div>
        <p style="margin:6px 0 0;font-size:16px">
          <a href="{esc(href)}">{esc(value)}</a>
          <span class="copy"><button type="button" data-copy="{esc(value if '@' in value or value.startswith('+') else href)}">copy</button></span>
        </p>
      </div>""" for name, label, value, href in CONTACT)

    return f"""
<section class="section" id="contact">
  <div class="wrap">
    <p class="eyebrow">Working together</p>
    <h2>Bring the messy version of the problem</h2>
    <p class="lede">I take on a small number of engagements at a time and work on them personally —
      architecture, build, or rescue. Tell me what you are building, your timeline, and any
      technical or field constraints.</p>

    <div class="grid three" style="margin-top:26px">{tiles}</div>

    <div class="card reveal" style="margin-top:26px">
      <blockquote class="quote" style="margin:0">
        Shobhit designed and maintained our mission-critical training booking platform with
        extraordinary attention to performance, security, and uptime. Over 15 years, his technical
        stewardship has been exemplary and dependable.
      </blockquote>
      <p class="dim" style="margin:14px 0 0">— Peter Souters, Director, Souters Training (London)</p>
    </div>

    <div class="btn-row reveal" style="margin-top:24px">
      <a class="btn primary" href="https://shobhit.net/contact/">Send a project brief</a>
      <a class="btn" href="mailto:shobhit@shobhit.net">Email directly</a>
      <a class="btn ghost" href="https://shobhit.net/portfolio/">Read the case studies</a>
    </div>
  </div>
</section>
"""


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def build_page(stats: dict, calendar: dict, languages: dict) -> str:
    crawl_svg = (SITE / "crawl.inline.svg").read_text(encoding="utf-8")
    crawl_svg = crawl_svg.replace('<?xml version="1.0" encoding="UTF-8"?>', "").strip()
    crawl_svg = crawl_svg.replace('<title>', '<title>', 1)
    built = stats.get("generated_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))

    nav_items = [("work", "Work"), ("practice", "Practice"), ("method", "Method"),
                 ("credentials", "Credentials"), ("lab", "Lab"), ("contact", "Contact")]
    nav = "".join(f'<a href="#{slug}">{label}</a>' for slug, label in nav_items)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shobhit Kumar Prabhakar · GeekLord — Software Architect</title>
<meta name="description" content="Software architect engineering dependable web platforms, offline-first field-data systems and grounded AI workflows. Founder of Cyber Mitra Solutions, Lucknow, India.">
<meta name="author" content="Shobhit Kumar Prabhakar">
<meta name="theme-color" content="#0b1220" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta property="og:type" content="profile">
<meta property="og:title" content="Shobhit Kumar Prabhakar · GeekLord — Software Architect">
<meta property="og:description" content="Complex challenges. Dependable systems. Web platforms, field-data instruments and grounded AI workflows.">
<meta property="og:url" content="https://github.com/GeekLord">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='9' fill='%238B6BFF'/><text x='16' y='22' font-size='17' font-family='monospace' text-anchor='middle' fill='white'>G</text></svg>">
<link rel="stylesheet" href="styles.css">
</head>
<body>

<header class="topbar">
  <div class="wrap">
    <a class="brand" href="#top"><span class="mark">GL</span><span class="name">Shobhit Kumar Prabhakar</span></a>
    <nav class="nav">{nav}</nav>
    <div class="theme-toggle" role="group" aria-label="Colour theme">
      <button type="button" data-theme-set="auto" aria-pressed="true">Auto</button>
      <button type="button" data-theme-set="dark" aria-pressed="false">Dark</button>
      <button type="button" data-theme-set="light" aria-pressed="false">Light</button>
    </div>
  </div>
</header>

<main>
{hero(stats)}
{live_section(stats, calendar, languages, crawl_svg)}
{work_section()}
{practice_section()}
{method_section()}
{credentials_section()}
{lab_section(stats)}
{contact_section(stats)}
</main>

<footer class="site">
  <div class="wrap">
    <p class="dim" style="margin:0">
      Shobhit Kumar Prabhakar · GeekLord · Cyber Mitra Solutions, Lucknow, India
    </p>
    <p class="dim" style="margin:0">
      Graphics and data regenerated from the GitHub API ·
      <span data-built="{esc(built)}">{esc(built)}</span> ·
      <a href="https://github.com/GeekLord/GeekLord">repository</a>
    </p>
  </div>
</footer>

<script src="app.js" defer></script>
</body>
</html>
"""


def main() -> None:
    stats = load(DATA / "profile-stats.json", {})
    calendar = load(DATA / "contribution-calendar.json", {"total": 0, "weeks": []})
    languages = load(DATA / "languages.json", {})

    if not (SITE / "crawl.inline.svg").exists():
        raise SystemExit("Run scripts/build_assets.py first — site/crawl.inline.svg is missing.")

    html = build_page(stats, calendar, languages)
    needed = set(re.findall(r'assets/([A-Za-z0-9_./-]+\.svg)', html))
    copied = copy_assets(needed)
    (SITE / "index.html").write_text(html, encoding="utf-8")
    write_fonts_css(html)

    print(f"wrote site/index.html ({(SITE / 'index.html').stat().st_size / 1024:.1f} KB)")
    print(f"wrote site/fonts.css ({(SITE / 'fonts.css').stat().st_size / 1024:.1f} KB, "
          f"subset to {len(set(html))} unique characters)")
    print(f"copied {len(copied)} asset/data files:")
    for name in copied:
        print(f"  {name}")


if __name__ == "__main__":
    main()
