#!/usr/bin/env python3
"""Archive the current news digest as a dated, immutable weekly edition.

    python scripts/archive_weekly.py            # publish the current edition
    python scripts/archive_weekly.py --ensure   # publish only if not yet archived
    python scripts/archive_weekly.py --check    # verify without writing
    python scripts/archive_weekly.py --force    # correct the current edition

--ensure is the idempotent form used by CI: it publishes a missing edition,
succeeds quietly when the edition already matches, and still fails when a
published edition has drifted from data/weekly_picks.json.
"""

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "highlights"
WEEKLY = json.loads((ROOT / "data" / "weekly_picks.json").read_text())
FORCE = "--force" in sys.argv
CHECK = "--check" in sys.argv
ENSURE = "--ensure" in sys.argv

date = WEEKLY["updated"]
path = ARCHIVE / f"{date}.md"
fingerprint = hashlib.sha256(
    json.dumps(WEEKLY, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
).hexdigest()
marker = f"<!-- weekly-news-sha256:{fingerprint} -->"
if CHECK or ENSURE:
    if path.is_file():
        if marker in path.read_text():
            print(f"weekly archive matches {path.relative_to(ROOT)}")
            raise SystemExit(0)
        # A published edition drifted from the picks file. Never silently
        # rewrite it; correcting the current edition is a deliberate --force.
        raise SystemExit(
            f"{path.relative_to(ROOT)} does not match data/weekly_picks.json"
        )
    if CHECK:
        raise SystemExit(
            f"{path.relative_to(ROOT)} does not match data/weekly_picks.json"
        )
    # --ensure publishes a missing edition, then falls through to the writer.
if path.exists() and not FORCE:
    raise SystemExit(
        f"{path.relative_to(ROOT)} already exists; weekly editions are immutable "
        "(use --force only to correct the current edition)."
    )

ARCHIVE.mkdir(exist_ok=True)
lines = [
    f"# Awesome AI4AI Monthly News — {date}",
    "",
    marker,
    "",
    "> Source-verified papers, model releases, and research updates from the living companion to "
    "[*AI4AI Survey: From Long-Horizon Agents to Recursive Self-Improvement—Definitions, Reliable Horizons, and Open Problems*](https://www.preprints.org/manuscript/202608.2108/v1).",
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
    "[← All editions](README.md) · "
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
    "# 📅 Awesome AI4AI Monthly News Archive",
    "",
    "A permanent record of the repository's human-curated top papers, releases, "
    "blogs, and research news. Each edition is a dated snapshot of the month's "
    "selection at that refresh. Citation rankings refresh separately in the live README.",
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
