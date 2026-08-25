#!/usr/bin/env python3
"""Generate the Awesome AI4AI README from verified structured data."""

import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPERS = json.loads((ROOT / "data" / "papers.json").read_text())
AUDIT = json.loads((ROOT / "data" / "closure_audit.json").read_text())
WEEKLY = json.loads((ROOT / "data" / "weekly_picks.json").read_text())
CATALOG_META = json.loads((ROOT / "data" / "catalog_meta.json").read_text())

VENUE_MONTH = {
    "ICLR": "05", "NeurIPS": "12", "ACL": "07", "EMNLP": "11",
    "ICML": "07", "AAAI": "02", "KDD": "08", "COLM": "10",
}

SECTION_LAYOUT = [
    ("benchmarks", "🧪 Benchmarks", [
        ("benchmarks", None),
    ]),
    ("harness", "🛠️ Harness Design", [
        ("harness-design", None),
    ]),
    ("model", "🧠 Model Design", [
        ("model-design", None),
    ]),
]
SECTION_ART = {
    "benchmarks": (
        "assets/benchmarks.png",
        "92%",
        "Figure 3 from the companion survey: What Is AI4AI? A Taxonomy",
    ),
    "harness": (
        "assets/harness-design.png",
        "92%",
        "Evidence chain for reliable harness interventions",
    ),
    "model": (
        "assets/model-design.png",
        "100%",
        "Model-side interventions across plan, execute, feedback, and repair",
    ),
}
VALID_SECTIONS = {
    "targets/data",
    "targets/weights",
    "targets/harness",
    "targets/substrate",
    "targets/evaluator",
    "targets/research",
    "evidence/benchmarks",
    "evidence/measurement",
    "foundations/long-horizon",
    "foundations/self-improvement",
    "analyses",
}
VALID_COLLECTIONS = {"benchmarks", "harness-design", "model-design"}


def validate():
    required = {
        "title", "venue", "date", "arxiv_id", "url", "citations", "code",
        "sections", "collections",
    }
    failures = []
    for key, paper in PAPERS.items():
        missing = sorted(required - set(paper))
        unknown = sorted(set(paper["sections"]) - VALID_SECTIONS)
        unknown_collections = sorted(
            set(paper.get("collections", [])) - VALID_COLLECTIONS
        )
        if missing:
            failures.append(f"{key}: missing {', '.join(missing)}")
        if unknown:
            failures.append(f"{key}: unknown sections {', '.join(unknown)}")
        if unknown_collections:
            failures.append(
                f"{key}: unknown collections {', '.join(unknown_collections)}"
            )
        if paper["arxiv_id"] and not re.fullmatch(r"\d{4}\.\d{4,5}", paper["arxiv_id"]):
            failures.append(f"{key}: malformed arXiv id {paper['arxiv_id']}")
        if paper["url"] and not paper["url"].startswith(("https://", "http://")):
            failures.append(f"{key}: malformed URL {paper['url']}")
    required_news = {"date", "kind", "source", "title", "url", "why"}
    for index, item in enumerate(WEEKLY.get("items", []), 1):
        missing = sorted(required_news - set(item))
        if missing:
            failures.append(
                f"weekly news item {index}: missing {', '.join(missing)}"
            )
        if item.get("url") and not item["url"].startswith("https://"):
            failures.append(f"weekly news item {index}: malformed URL")
    audit_keys = {record["bib_key"] for record in AUDIT["records"]}
    missing_audit = sorted(audit_keys - set(PAPERS))
    if missing_audit:
        failures.append("audit records missing from catalog: " + ", ".join(missing_audit))
    if failures:
        raise SystemExit("\n".join(failures))


validate()


def sort_date(paper):
    value = str(paper["date"])
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value
    if re.fullmatch(r"\d{4}", value):
        venue = str(paper["venue"]).split(" ", 1)[0]
        return f"{value}-{VENUE_MONTH.get(venue, '06')}"
    return "0000-00"


def display_date(paper):
    if re.fullmatch(r"\d{4}", str(paper["date"])):
        return f"<nobr>{paper['date']}</nobr>"
    value = sort_date(paper)
    value = value if value != "0000-00" else str(paper["date"])
    return f"<nobr>{value}</nobr>"


def effective_year(paper):
    """Group rankings by first public appearance, never later venue year."""
    value = sort_date(paper)
    return int(value[:4]) if value[:4].isdigit() else None


def title_cell(paper):
    title = paper["title"].replace("|", "\\|")
    return f"[**{title}**]({paper['url']})" if paper.get("url") else f"**{title}**"


def code_cell(paper):
    url = paper.get("code")
    if not url:
        return "—"
    if "github.com" in url:
        stars = paper.get("github_stars")
        suffix = f" · ★ {stars:,}" if stars is not None else ""
        return f"[GitHub]({url}){suffix}"
    return f"[Project]({url})"


def paper_table(papers, citations=True):
    headers = ["Paper", "Date"]
    if citations:
        headers.append("Citations")
    headers.append("Code")
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(":--" if header == "Paper" else ":--:" for header in headers) + "|",
    ]
    for paper in papers:
        venue = str(paper["venue"]).replace("|", "\\|")
        cells = [
            f"{title_cell(paper)}<br><sub>{venue}</sub>",
            display_date(paper),
        ]
        if citations:
            cells.append(str(paper["citations"]) if paper["citations"] is not None else "—")
        cells.append(code_cell(paper))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def in_collection(collection):
    papers = [
        paper for paper in PAPERS.values()
        if collection in paper.get("collections", [])
    ]
    return sorted(papers, key=sort_date, reverse=True)


def months_since(value, today):
    year, month = map(int, value.split("-"))
    return max(1, (today.year - year) * 12 + today.month - month)


def rising_stars(limit=10, window=18):
    today = date.fromisoformat(CATALOG_META["citations_as_of"])
    ranked = []
    for paper in PAPERS.values():
        if not paper.get("collections"):
            continue
        value = sort_date(paper)
        if value == "0000-00" or paper["citations"] is None:
            continue
        age = months_since(value, today)
        if age <= window and paper["citations"] > 0:
            ranked.append((paper["citations"] / age, paper))
    ranked.sort(key=lambda item: (-item[0], item[1]["title"]))
    return ranked[:limit]


def top_by_year(year, limit=12):
    papers = [
        paper for paper in PAPERS.values()
        if paper.get("collections")
        and effective_year(paper) == year
        and paper["citations"] is not None
    ]
    return sorted(papers, key=lambda paper: -paper["citations"])[:limit]


audit_records = AUDIT["records"]

header = (ROOT / "scripts" / "header.md").read_text()
featured_marker = "<!--FEATURED_CONTENT-->"
if header.count(featured_marker) != 1:
    raise SystemExit(f"scripts/header.md must contain exactly one {featured_marker} marker")
header_lead, header_remainder = header.split(featured_marker)
parts = [header_lead.rstrip(), ""]

parts += [
    "## 📅 Weekly Update · Monthly Top 10",
    "",
    f"> **Updated {WEEKLY['updated']}** · {WEEKLY['cadence']}",
    ">",
    f"> **How we select:** {WEEKLY['selection']}",
    "",
    "| Date · Type | News | Why it matters |",
    "|:--|:--|:--|",
]
for item in WEEKLY["items"]:
    news_date = item["date"].replace("-", "‑")
    parts.append(
        f"| {news_date}<br><sub>{item['kind']}</sub> | "
        f"[**{item['title']}**]({item['url']})<br><sub>{item['source']}</sub> | "
        f"{item['why']} |"
    )
parts += [
    "",
    "> **Want next month's news?** Watch the repository. Citation counts, rankings, and the "
    "month's top stories refresh every Monday. "
    "[Browse past editions →](highlights/README.md)",
    "",
    "## 📈 Live Rankings",
    "",
    f"> Citation counts are current through **{CATALOG_META['citations_as_of']}** from "
    f"{' and '.join(CATALOG_META['citation_sources'])}. Rankings are discovery aids, "
    "not quality scores; audit evidence remains independent of popularity. "
    f"GitHub stars are snapshots from **{CATALOG_META['github_stars_as_of']}**. "
    f"{CATALOG_META['citation_policy']} {CATALOG_META['year_grouping']}",
    "",
    "### 🔥 Recent Papers by Average Monthly Citations",
    "",
]

rising = rising_stars()
if rising:
    parts += [
        "| Paper | Venue | Date | Citations | Avg. cites/month | Code |",
        "|:--|:--:|:--:|:--:|:--:|:--:|",
    ]
    for velocity, paper in rising:
        parts.append(
            "| " + " | ".join([
                title_cell(paper), str(paper["venue"]), display_date(paper),
                str(paper["citations"]), f"**{velocity:.1f}**",
                code_cell(paper),
            ]) + " |"
        )
else:
    parts.append("_Citation data will appear after the first scheduled refresh._")

parts += ["", "### 🏆 Most-Cited Papers by Year", ""]
years = sorted({
    effective_year(paper)
    for paper in PAPERS.values()
    if paper.get("collections") and effective_year(paper)
}, reverse=True)
for year in years[:4]:
    papers = top_by_year(year)
    if not papers:
        continue
    parts += [
        "<details open markdown=\"1\">" if year == years[0] else "<details markdown=\"1\">",
        f"<summary><b>Top {len(papers)} of {year}</b> by citations</summary>",
        "",
        paper_table(papers, citations=True),
        "",
        "</details>",
        "",
    ]

parts += [header_remainder.strip(), ""]

for section_group, section_title, subsections in SECTION_LAYOUT:
    parts += [f"## {section_title}", ""]
    image_path, image_width, image_alt = SECTION_ART[section_group]
    parts += [
        '<p align="center">',
        f'  <img src="{image_path}" width="{image_width}" alt="{image_alt}">',
        "</p>",
        "",
    ]
    for section, subsection_title in subsections:
        papers = in_collection(section)
        if not papers:
            continue
        if subsection_title:
            parts += [f"### {subsection_title}", ""]
        parts += [
            f"> **{len(papers)} papers** · Survey-curated collection, newest first. "
            "Cross-collection papers may appear in more than one section.",
            "",
            paper_table(papers, citations=True),
            "",
        ]

parts.append((ROOT / "scripts" / "footer.md").read_text().rstrip())
readme = "\n".join(parts) + "\n"

toc = [
    "- [📅 Weekly Update · Monthly Top 10](#-weekly-update--monthly-top-10)",
    "- [📈 Live Rankings](#-live-rankings)",
    "  - [🔥 Recent Papers by Average Monthly Citations](#-recent-papers-by-average-monthly-citations)",
    "  - [🏆 Most-Cited Papers by Year](#-most-cited-papers-by-year)",
    "- [🧪 Benchmarks](#-benchmarks)",
    "- [🛠️ Harness Design](#-harness-design)",
    "- [🧠 Model Design](#-model-design)",
    "- [📚 How We Curate](#-how-we-curate)",
    "- [📄 Citation](#-citation)",
    "- [🤝 Contributing](#-contributing)",
]

readme = readme.replace("<!--TOC-->", "\n".join(toc))
readme = readme.replace("<!--LASTUPDATED-->", WEEKLY["updated"])

(ROOT / "README.md").write_text(readme)
print(
    f"README.md written: {len(PAPERS)} catalog records, "
    f"{sum(bool(paper.get('collections')) for paper in PAPERS.values())} public papers, "
    f"{sum(bool(paper.get('code')) for paper in PAPERS.values())} code links, "
    f"{len(audit_records)} audited systems"
)
