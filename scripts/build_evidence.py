#!/usr/bin/env python3
"""Build public AI4AI audit artifacts from data/closure_audit.json."""

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "closure_audit.json"
CSV_PATH = ROOT / "data" / "closure_audit.csv"
SUMMARY_PATH = ROOT / "data" / "closure_audit_summary.json"
EVIDENCE_PATH = ROOT / "EVIDENCE.md"

data = json.loads(SOURCE.read_text())
records = data["records"]
stages = ("goal", "plan", "execute", "feedback", "repair")
coordinates = ("G", "R", "H", "T")


def nested_counts(keys, accessor):
    return {
        key: dict(sorted(Counter(accessor(record, key) for record in records).items()))
        for key in keys
    }


summary = {
    "schema_version": "2.0.0",
    "frozen_on": data["metadata"]["frozen_on"],
    "last_verified": data["metadata"]["last_verified"],
    "n_records": len(records),
    "stage_counts": nested_counts(stages, lambda record, stage: record["stage_ownership"][stage]),
    "target_counts": dict(sorted(Counter(record["target_layer"] for record in records).items())),
    "evidence_counts": nested_counts(
        coordinates, lambda record, coordinate: record["evidence_profile"][coordinate]
    ),
    "source_tier_counts": dict(
        sorted(Counter(record["verification"]["source_tier"] for record in records).items())
    ),
    "confidence_counts": dict(
        sorted(Counter(record["verification"]["confidence"] for record in records).items())
    ),
}
SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

columns = [
    "record_id", "system", "release_year", "bib_key", "source_url", "target",
    *stages, *coordinates, "source_tier", "confidence", "source_locator", "rationale",
]
with CSV_PATH.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow({
            "record_id": record["record_id"],
            "system": record["name"],
            "release_year": record["year"],
            "bib_key": record["bib_key"],
            "source_url": record["source_url"],
            "target": record["target_layer"],
            **record["stage_ownership"],
            **record["evidence_profile"],
            "source_tier": record["verification"]["source_tier"],
            "confidence": record["verification"]["confidence"],
            "source_locator": record["verification"]["source_locator"],
            "rationale": record["verification"]["rationale"],
        })


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def ownership(value):
    return {"human": "Hum", "mixed": "Mix", "system": "Sys"}[value]


def evidence(value):
    return {"y": "✅", "n": "❌", "nr": "—"}[value]


lines = [
    "# 🔬 AI4AI Stage-Ownership & Improvement-Evidence Audit",
    "",
    "> Companion evidence artifact for *AI4AI Survey: From Long-Horizon Agents to Recursive Self-Improvement—Definitions, Reliable Horizons, and Open Problems*. "
    "This is an evidence-weighted 35-system sample, **not** a prevalence estimate.",
    "",
    f"**Frozen:** {data['metadata']['frozen_on']} · "
    f"**Last verified:** {data['metadata']['last_verified']} · "
    f"**Schema:** {data['metadata']['schema_version']}",
    "",
    "## Headline",
    "",
    "| Systems | Goal system-owned | Execution system-owned | Repair system-owned | Feedback system-owned | Matched human evidence |",
    "|:--:|:--:|:--:|:--:|:--:|:--:|",
    (
        f"| **{len(records)}** | "
        f"**{summary['stage_counts']['goal'].get('system', 0)}** | "
        f"**{summary['stage_counts']['execute'].get('system', 0)}** | "
        f"**{summary['stage_counts']['repair'].get('system', 0)}** | "
        f"**{summary['stage_counts']['feedback'].get('system', 0)}** | "
        f"**{summary['evidence_counts']['H'].get('y', 0)}** |"
    ),
    "",
    "## Coding legend",
    "",
    "- **Ownership:** Hum = human/design-time artifact, Mix = mixed, Sys = system.",
    "- **Evidence:** G = measured gain, R = retention/compounding, "
    "H = budget-matched human comparison, T = controlled held-out transfer.",
    "- ✅ demonstrated · ❌ explicitly tested but not demonstrated · — not reported/tested.",
    "- **R is deliberately broad:** it can denote repeated accepted gains or an explicit "
    "capability-preservation test; R alone does not establish cross-generation RSI.",
    "",
    "The full operational rules are stored in "
    "[`data/closure_audit.json`](data/closure_audit.json). "
    "Every row includes a primary-source locator, rationale, source tier, and confidence.",
    "",
    "## Full audit",
    "",
    "| System | Target | Goal | Plan | Exec | Feedback | Repair | G | R | H | T | Source | Confidence |",
    "|:--|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--|:--:|",
]

for record in records:
    row = [
        f"[{safe(record['name'])}]({record['source_url']})",
        safe(record["target_layer"]),
        *(ownership(record["stage_ownership"][stage]) for stage in stages),
        *(evidence(record["evidence_profile"][coordinate]) for coordinate in coordinates),
        safe(record["verification"]["source_tier"]),
        safe(record["verification"]["confidence"]),
    ]
    lines.append("| " + " | ".join(row) + " |")

lines += [
    "",
    "## Rebuild",
    "",
    "```bash",
    "python scripts/build_evidence.py",
    "```",
    "",
    "The command regenerates this page, the flat "
    "[CSV export](data/closure_audit.csv), and the "
    "[aggregate JSON](data/closure_audit_summary.json).",
    "",
]
EVIDENCE_PATH.write_text("\n".join(lines))

print(f"Wrote {CSV_PATH.name}, {SUMMARY_PATH.name}, and {EVIDENCE_PATH.name}.")
