# Data artifacts

This directory contains the structured sources used to generate the public repository.

| File | Role | Maintained by |
|:--|:--|:--|
| `papers.json` | Canonical catalog with public `collections` and fine-grained provenance `sections` | Pull requests + maintainer citation refresh |
| `catalog_meta.json` | Public collection policy, survey baseline, citation refresh date, and year grouping | Maintainer citation refresh |
| `weekly_picks.json` | Current source-linked papers, releases, blogs, and research news | Weekly maintainer review + dated archive in `../highlights/` |
| `closure_audit.json` | Source of truth for the 35-system ownership/evidence audit | Survey audit process |
| `closure_audit.csv` | Flat export of the audit | `scripts/build_evidence.py` |
| `closure_audit_summary.json` | Aggregate stage, target, evidence, and source counts | `scripts/build_evidence.py` |

## Important distinctions

- `collections` drives the three complete public lists under [`catalog/`](../catalog/README.md): Benchmarks, Harness Design, and Model Design. The root README previews the latest 20 papers per collection.
- `sections` preserves finer survey provenance and does not create extra README sections.
- Records with an empty `collections` list are retained only for audit/support provenance.
- One paper may belong to multiple public collections, but appears only once within each list.
- Citation counts are discovery signals, not scientific-quality scores. When
  scholarly indexes split preprint and published versions, the catalog keeps
  the largest title-verified count from its configured sources.
- An optional `first_public_date` stores the primary-source v1 submission date
  as `YYYY-MM-DD`; `date` stores its month for display and ranking. An arXiv ID
  can use the following announcement month, so do not infer first appearance
  from the ID when a verified submission date is available. Live verification
  checks this field against the arXiv Atom feed's `published` date.
- An optional `semantic_scholar_id` stores a title-verified 40-character paper
  ID when Semantic Scholar cannot resolve the paper's proceedings URL. The
  refresh uses this ID directly and still checks the returned title.
- GitHub code links are repository-root URLs; their star counts refresh with
  citations when maintainers run `python scripts/verify_papers.py --update`.
- Optional `research_refresh` and `metrics_refresh` entries in `catalog_meta.json`
  describe the latest literature pass and metric coverage. A checked date is
  distinct from `citations_as_of`: unresolved previously cited records retain
  their older values, and source-only records without an index match remain
  unknown. Preserve these coverage distinctions when regenerating the README.
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
