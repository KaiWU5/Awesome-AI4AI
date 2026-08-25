#!/usr/bin/env python3
"""Fast offline integrity checks for generated Markdown and repository assets."""

import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN = [
    ROOT / "README.md",
    ROOT / "EVIDENCE.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "data" / "README.md",
    *sorted((ROOT / "highlights").glob("*.md")),
]
REQUIRED_ASSETS = {
    "assets/benchmarks.png",
    "assets/harness-design.png",
    "assets/logo.png",
    "assets/methodology.png",
    "assets/model-design.png",
}
VALID_COLLECTIONS = {"benchmarks", "harness-design", "model-design"}
VALID_NEWS_KINDS = {
    "Blog", "Harness release", "Model release", "Model update", "News",
    "Open-weight release", "Paper", "Research release", "Tooling release",
}
SURVEY_COLLECTION_BASELINE = {
    "benchmarks": 111,
    "harness-design": 98,
    "model-design": 26,
}
COLLECTION_HEADINGS = [
    ("benchmarks", "## 🧪 Benchmarks"),
    ("harness-design", "## 🛠️ Harness Design"),
    ("model-design", "## 🧠 Model Design"),
]
VENUE_MONTH = {
    "ICLR": "05", "NeurIPS": "12", "ACL": "07", "EMNLP": "11",
    "ICML": "07", "AAAI": "02", "KDD": "08", "COLM": "10",
}
OLD_BRANDING = (
    "Awesome Long-Horizon",
    "Awesome-Long-Horizon",
    "awesome-long-horizon",
    "Update Till Solved",
)
PRIVATE_MARKERS = {
    "absolute macOS home path": "/" + "Users/",
    "absolute Linux home path": "/" + "home/",
    "local file URL": "file" + "://",
    "corporate email": "@" + "bytedance.com",
    "internal domain": "." + "byted.org",
}
SECRET_PATTERNS = {
    "private key": re.compile(
        r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"
    ),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}
PUBLIC_AUTOMATION_EMAILS = {"cursoragent@cursor.com"}

failures = []


def paper_sort_date(paper):
    value = str(paper["date"])
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value
    if re.fullmatch(r"\d{4}", value):
        venue = str(paper["venue"]).split(" ", 1)[0]
        return f"{value}-{VENUE_MONTH.get(venue, '06')}"
    return "0000-00"


ignored_parts = {".git", ".venv", "__pycache__", ".pytest_cache"}
ignored_files = {".DS_Store", "preview_local.html"}
for path in ROOT.rglob("*"):
    if (
        not path.is_file()
        or path.name in ignored_files
        or ignored_parts.intersection(path.relative_to(ROOT).parts)
    ):
        continue
    payload = path.read_bytes()
    if b"\0" in payload:
        continue
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        continue
    relative = path.relative_to(ROOT)
    for label, marker in PRIVATE_MARKERS.items():
        if marker.lower() in text.lower():
            failures.append(f"{relative} contains {label}")
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            failures.append(f"{relative} contains a possible {label}")

commit_metadata = ""
if (ROOT / ".git").exists():
    try:
        commit_metadata = subprocess.check_output(
            ["git", "log", "-1", "--format=%ae%n%ce%n%B"],
            cwd=ROOT,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        failures.append("could not inspect commit metadata")
for email in re.findall(r"[\w.+-]+@[\w.-]+", commit_metadata):
    if (
        email.lower() not in PUBLIC_AUTOMATION_EMAILS
        and not email.lower().endswith(
            ("@users.noreply.github.com", "@noreply.github.com")
        )
    ):
        failures.append(f"commit metadata exposes a non-noreply email: {email}")

for relative in REQUIRED_ASSETS:
    path = ROOT / relative
    if not path.is_file() or path.stat().st_size == 0:
        failures.append(f"missing asset: {relative}")

for path in MARKDOWN:
    text = path.read_text()
    if "<!--" in text and path.name == "README.md":
        failures.append("README.md still contains generator placeholders")
    for old in OLD_BRANDING:
        if old in text:
            failures.append(f"{path.relative_to(ROOT)} contains old branding: {old}")
    targets = re.findall(r"\]\(([^)]+)\)", text)
    targets += re.findall(r"""src=["']([^"']+)["']""", text)
    for target in targets:
        target = target.strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / unquote(target)).resolve()
        if not resolved.exists():
            failures.append(
                f"{path.relative_to(ROOT)} has missing local target: {target}"
            )

papers = json.loads((ROOT / "data" / "papers.json").read_text())
weekly = json.loads((ROOT / "data" / "weekly_picks.json").read_text())
audit = json.loads((ROOT / "data" / "closure_audit.json").read_text())
catalog_meta = json.loads((ROOT / "data" / "catalog_meta.json").read_text())

if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", catalog_meta.get("citations_as_of", "")):
    failures.append("catalog_meta.json has an invalid citations_as_of date")
if not re.fullmatch(
    r"\d{4}-\d{2}-\d{2}", catalog_meta.get("github_stars_as_of", "")
):
    failures.append("catalog_meta.json has an invalid github_stars_as_of date")
if set(catalog_meta.get("public_collections", [])) != VALID_COLLECTIONS:
    failures.append("catalog_meta.json does not declare the three public collections")
metadata_baseline = catalog_meta.get("survey_baseline", {})
for collection, expected in SURVEY_COLLECTION_BASELINE.items():
    if metadata_baseline.get(collection) != expected:
        failures.append(f"catalog_meta.json has a stale {collection} baseline")
if metadata_baseline.get("unique_papers") != 223:
    failures.append("catalog_meta.json has a stale unique-paper baseline")

try:
    weekly_updated = date.fromisoformat(weekly["updated"])
except (KeyError, ValueError):
    weekly_updated = None
    failures.append("weekly_picks.json has an invalid updated date")
news_items = weekly.get("items", [])
if not 1 <= len(news_items) <= 10:
    failures.append("weekly_picks.json must contain 1–10 news items")
if not weekly.get("selection"):
    failures.append("weekly_picks.json has no selection policy")
required_news_fields = {"date", "kind", "source", "title", "url", "why"}
news_urls = []
for index, item in enumerate(news_items, 1):
    missing_fields = sorted(required_news_fields - set(item))
    if missing_fields:
        failures.append(
            f"weekly news item {index} is missing: {', '.join(missing_fields)}"
        )
        continue
    news_urls.append(item["url"])
    if item["kind"] not in VALID_NEWS_KINDS:
        failures.append(f"weekly news item {index} has an invalid kind: {item['kind']}")
    if not item["url"].startswith("https://"):
        failures.append(f"weekly news item {index} has an invalid URL")
    try:
        published = date.fromisoformat(item["date"])
    except ValueError:
        failures.append(f"weekly news item {index} has an invalid date")
        continue
    if weekly_updated and not 0 <= (weekly_updated - published).days <= 30:
        failures.append(f"news item {index} falls outside the rolling 30-day window")
if len(news_urls) != len(set(news_urls)):
    failures.append("weekly_picks.json contains duplicate news URLs")
current_archive = ROOT / "highlights" / f"{weekly['updated']}.md"
if not current_archive.is_file():
    failures.append(f"current weekly edition is not archived: {current_archive.name}")
else:
    fingerprint = hashlib.sha256(
        json.dumps(
            weekly, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    if f"<!-- weekly-news-sha256:{fingerprint} -->" not in current_archive.read_text():
        failures.append("current weekly archive does not match weekly_picks.json")

audit_keys = [record["bib_key"] for record in audit["records"]]
missing = sorted(set(audit_keys) - set(papers))
if missing:
    failures.append("audit records absent from papers.json: " + ", ".join(missing))

audit_by_key = {record["bib_key"]: record for record in audit["records"]}
for key, record in audit_by_key.items():
    expected = {
        "target": record["target_layer"],
        "evidence": record["evidence_profile"],
        "source_tier": record["verification"]["source_tier"],
        "confidence": record["verification"]["confidence"],
    }
    if papers[key].get("audit") != expected:
        failures.append(f"duplicated audit metadata drifted for: {key}")

for key, paper in papers.items():
    if not re.fullmatch(r"\d{4}(?:-\d{2})?", str(paper["date"])):
        failures.append(f"invalid first-appearance date for {key}: {paper['date']}")
    if paper.get("audit") and key not in audit_by_key:
        failures.append(f"paper has audit metadata without source record: {key}")
    if "github.com" in (paper.get("code") or ""):
        stars = paper.get("github_stars")
        if isinstance(stars, bool) or not isinstance(stars, int) or stars < 0:
            failures.append(f"GitHub code record has no valid star count: {key}")
    collections = paper.get("collections")
    if not isinstance(collections, list):
        failures.append(f"paper has no collections list: {key}")
        continue
    unknown = sorted(set(collections) - VALID_COLLECTIONS)
    if unknown:
        failures.append(f"paper has unknown collections ({', '.join(unknown)}): {key}")
    if len(collections) != len(set(collections)):
        failures.append(f"paper has duplicate collection assignments: {key}")

for collection, minimum in SURVEY_COLLECTION_BASELINE.items():
    count = sum(collection in paper.get("collections", []) for paper in papers.values())
    if count < minimum:
        failures.append(
            f"{collection} collection fell below survey baseline: {count} < {minimum}"
        )

public_papers = sum(bool(paper.get("collections")) for paper in papers.values())
if public_papers < 223:
    failures.append(f"public survey catalog fell below 223 unique papers: {public_papers}")

readme = (ROOT / "README.md").read_text()
news_heading = "## 📅 Weekly Update · Monthly Top 10"
if news_heading not in readme:
    failures.append("README is missing the news heading")
else:
    news_section = readme[
        readme.index(news_heading):readme.index("## 📈 Live Rankings")
    ]
    for item in news_items:
        title = str(item.get("title", "")).replace("|", "\\|")
        fragment = f"[**{title}**]({item.get('url', '')})"
        if news_section.count(fragment) != 1:
            failures.append(f"README does not render news exactly once: {title}")
    if [item.get("date") for item in news_items] != sorted(
        (item.get("date") for item in news_items), reverse=True
    ):
        failures.append("news items are not newest first")

for index, (collection, heading) in enumerate(COLLECTION_HEADINGS):
    if heading not in readme:
        failures.append(f"README is missing collection heading: {heading}")
        continue
    start = readme.index(heading)
    end = (
        readme.index(COLLECTION_HEADINGS[index + 1][1], start)
        if index + 1 < len(COLLECTION_HEADINGS)
        else readme.index("## 📚 How We Curate", start)
    )
    section = readme[start:end]
    if "| Paper | Date | Citations | Code |" not in section:
        failures.append(f"README {collection} table is missing the Citations column")
    mapped = [
        paper for paper in papers.values()
        if collection in paper.get("collections", [])
    ]
    if f"**{len(mapped)} papers**" not in section:
        failures.append(f"README has a stale {collection} paper count")
    positions = []
    for paper in mapped:
        title = str(paper["title"]).replace("|", "\\|")
        fragment = f"[**{title}**]({paper['url']})"
        occurrences = section.count(fragment)
        if occurrences != 1:
            failures.append(
                f"README renders {occurrences} copies of {collection} paper: "
                f"{paper['title']}"
            )
        else:
            positions.append((paper_sort_date(paper), section.index(fragment)))
    ordered_positions = [position for _, position in sorted(
        positions, key=lambda item: item[0], reverse=True
    )]
    if ordered_positions != sorted(ordered_positions):
        failures.append(f"README {collection} collection is not newest first")

for key, paper in papers.items():
    if (
        not paper.get("collections")
        or "github.com" not in (paper.get("code") or "")
    ):
        continue
    expected = f"[GitHub]({paper['code']}) · ★ {paper['github_stars']:,}"
    if expected not in readme:
        failures.append(f"README is missing GitHub stars for: {key}")

if failures:
    raise SystemExit("\n".join(failures))

print(
    f"repository check passed: {len(papers)} papers, "
    f"{public_papers} public, {len(audit['records'])} audit records, "
    f"{len(REQUIRED_ASSETS)} assets"
)
