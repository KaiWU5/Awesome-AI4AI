# Data artifacts

This directory contains the structured sources used to generate the public repository.

| File | Role | Maintained by |
|:--|:--|:--|
| `papers.json` | Canonical catalog with public `collections` and fine-grained provenance `sections` | Pull requests + Monday citation refresh |
| `catalog_meta.json` | Public collection policy, survey baseline, citation refresh date, and year grouping | Monday citation refresh |
| `weekly_picks.json` | Current source-linked papers, releases, blogs, and research news | Weekly maintainer review + dated archive in `../highlights/` |
| `closure_audit.json` | Source of truth for the 35-system ownership/evidence audit | Survey audit process |
| `closure_audit.csv` | Flat export of the audit | `scripts/build_evidence.py` |
| `closure_audit_summary.json` | Aggregate stage, target, evidence, and source counts | `scripts/build_evidence.py` |

## Important distinctions

- `collections` drives the three public lists: Benchmarks, Harness Design, and Model Design.
- `sections` preserves finer survey provenance and does not create extra README sections.
- Records with an empty `collections` list are retained only for audit/support provenance.
- One paper may belong to multiple public collections, but appears only once within each list.
- Citation counts are discovery signals, not scientific-quality scores. When
  scholarly indexes split preprint and published versions, the catalog keeps
  the largest title-verified count from its configured sources.
- GitHub code links are repository-root URLs; their star counts refresh with
  citations in the scheduled Monday workflow.
- G/R/H/T are independent evidence coordinates, not a summed leaderboard.
- Stage-ownership counts describe the coded sample, not prevalence in the full field.
- `nr` means not reported or not tested; it does **not** mean demonstrated failure.

Run:

```bash
python scripts/verify_papers.py --offline
python scripts/build_evidence.py
python scripts/build_readme.py
```

to regenerate all public Markdown and derived audit exports.
