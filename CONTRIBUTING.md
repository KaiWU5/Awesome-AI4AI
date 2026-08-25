# Contributing to Awesome AI4AI 🚀

We welcome papers, metadata corrections, official code links, and stronger
primary-source evidence. Scholarly entries are title-matched against available
indexes; explicitly labeled first-party reports require manual source review.

## Scope

A paper belongs when it contributes to at least one public collection:

- **Benchmarks** — tasks, environments, evaluation protocols, or integrated AI R&D suites;
- **Harness Design** — runtime programs, tools, memory, control, feedback, verification,
  or self-modifying agent scaffolds;
- **Model Design** — training, post-training, architectures, or learning algorithms
  that change model behavior or weights.

Ordinary static generation, generic long-context work, and one-shot tool use are
out of scope unless they directly support one of these questions.

## Add a paper

1. Add one record to [`data/papers.json`](data/papers.json), keyed by citation key:

```json
"lastname2026shortname": {
  "title": "Exact Paper Title",
  "venue": "ICLR 2026",
  "date": "2026-01",
  "arxiv_id": "2601.12345",
  "url": "https://arxiv.org/abs/2601.12345",
  "citations": null,
  "code": "https://github.com/org/official-repo",
  "sections": ["targets/harness"],
  "collections": ["harness-design"]
}
```

2. Run the standard-library-only checks:

```bash
python scripts/verify_papers.py --offline
python scripts/build_evidence.py
python scripts/build_readme.py
python scripts/archive_weekly.py --check
python scripts/check_repo.py
```

3. Commit the regenerated `README.md` and open a pull request.

PR CI runs these deterministic offline checks and rejects generated files that
do not match the structured source. Maintainers can additionally run
`python scripts/verify_papers.py` for live arXiv/Semantic Scholar/OpenAlex title
checks; this requires network access and may be slow for the full catalog.

For an optional browser preview, run `python scripts/preview_readme.py`. It uses
GitHub's Markdown API when available and writes the ignored `preview_local.html`.

## Public collection keys

| Collection | Use for | Provenance section |
|:--|:--|:--|
| `benchmarks` | Benchmark tasks, environments, protocols, and evaluation suites | `evidence/benchmarks` |
| `harness-design` | Runtime agents, tools, memory, control, feedback, and verification | `targets/harness` |
| `model-design` | Training, post-training, architectures, and learning algorithms | `targets/weights` |

Use more than one collection when a paper genuinely spans them. The `sections`
field retains finer internal provenance; new public submissions should normally
use the matching provenance value above.

## Field rules

- Use the **exact published title**.
- `date` is first public appearance (`YYYY-MM`); use `YYYY` only when the month is unavailable.
- Leave `citations` as `null`; the Monday workflow fills it.
- `code` must be project-designated or maintainer-reviewed, not an arbitrary fork.
- `collections` contains one or more of the three public collection keys.
- A paper may appear in multiple collections when its primary contribution spans them.
- Do not add an `audit` block casually. Changes to stage ownership or G/R/H/T
  require a primary-source locator and rationale in `data/closure_audit.json`.

## Monthly news

Maintainers keep [`data/weekly_picks.json`](data/weekly_picks.json) as the top
ten source-linked papers, releases, blogs, and research news from the trailing
30 days, re-ranked at each weekly refresh: items that aged past 30 days drop
out, the new week's arrivals are considered, and the rest carry forward. Aim for
roughly half flagship model releases and half AI4AI research or harness work.
Prefer official announcements and primary scholarly sources, attribute
performance claims, and include a concise AI4AI relevance note. After updating
the date and items, run `python scripts/archive_weekly.py` once to
publish an immutable edition under [`highlights/`](highlights/README.md).

## Non-negotiables

- No fabricated identifiers, titles, or source claims.
- No credentials, private URLs, internal domains, or absolute local paths.
- No popularity claims presented as scientific quality.
- No RSI label without distinguishing self-reference, fixed evaluators, and
  evidence across accepted successors.
- Never hand-edit generated README tables.
