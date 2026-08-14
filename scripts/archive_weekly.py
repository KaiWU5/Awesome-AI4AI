#!/usr/bin/env python3
"""Archive the current news digest as a dated, immutable weekly edition."""

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "highlights"
WEEKLY = json.loads((ROOT / "data" / "weekly_picks.json").read_text())
FORCE = "--force" in sys.argv
CHECK = "--check" in sys.argv

date = WEEKLY["updated"]
path = ARCHIVE / f"{date}.md"
fingerprint = hashlib.sha256(
    json.dumps(WEEKLY, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
).hexdigest()
marker = f"<!-- weekly-news-sha256:{fingerprint} -->"
if CHECK:
    if not path.is_file() or marker not in path.read_text():
        raise SystemExit(
            f"{path.relative_to(ROOT)} does not match data/weekly_picks.json"
        )
    print(f"weekly archive matches {path.relative_to(ROOT)}")
    raise SystemExit(0)
if path.exists() and not FORCE:
    raise SystemExit(
        f"{path.relative_to(ROOT)} already exists; weekly editions are immutable "
        "(use --force only to correct the current edition)."
    )

ARCHIVE.mkdir(exist_ok=True)
lines = [
    f"# Awesome AI4AI Weekly News — {date}",
    "",
    marker,
    "",
    "> Source-verified papers, model releases, and research updates from the living companion to "
    "[*On the Eve of AI4AI*](https://github.com/KaiWU5/LongHorizonLLMAgents).",
    "",
    f"**Selection policy:** {WEEKLY['selection']}",
    "",
]
for index, item in enumerate(WEEKLY["items"], 1):
    lines += [
        f"## {index}. {item['title']}",
        "",
        f"[**Read source →**]({item['url']})",
        "",
        f"- **Published:** {item['date']}",
        f"- **Type / source:** {item['kind']} · {item['source']}",
        f"- **Why it matters:** {item['why']}",
        "",
    ]
lines += [
    "---",
    "",
    "[← All weekly editions](README.md) · "
    "[Browse the live catalog](../README.md) · "
    "[Read the evidence audit](../EVIDENCE.md)",
    "",
]
path.write_text("\n".join(lines))

editions = sorted(
    (candidate for candidate in ARCHIVE.glob("????-??-??.md")),
    reverse=True,
)
index_lines = [
    "# 📅 Awesome AI4AI Weekly News Archive",
    "",
    "A permanent record of the repository's human-curated weekly papers, releases, "
    "blogs, and research news. Citation rankings refresh separately in the live README.",
    "",
]
for edition in editions:
    index_lines.append(f"- [{edition.stem}]({edition.name})")
index_lines += [
    "",
    "To publish a new edition, update `data/weekly_picks.json`, then run:",
    "",
    "```bash",
    "python scripts/archive_weekly.py",
    "python scripts/build_readme.py",
    "```",
    "",
]
(ARCHIVE / "README.md").write_text("\n".join(index_lines))

print(f"archived {len(WEEKLY['items'])} news items to {path.relative_to(ROOT)}")
