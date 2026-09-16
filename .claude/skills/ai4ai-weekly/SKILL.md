---
name: ai4ai-weekly
description: Run the weekly Awesome AI4AI refresh — re-rank the month's top-10 news for approval, refresh citations and GitHub stars, rebuild README/EVIDENCE, and publish the dated archive edition. Use when updating the monthly news picks, refreshing citations or stars, or fixing a failed "Weekly AI4AI citation refresh" workflow run.
argument-hint: "[edition date YYYY-MM-DD, defaults to today]"
allowed-tools: Bash(python scripts/*), Bash(git *), Bash(gh *), Read, Write, Edit, WebSearch, WebFetch
---

# Awesome AI4AI weekly refresh

Two independent halves. Do the mechanical half whenever; do the curation half only with the maintainer in the loop.

| Half | What it touches | Needs a human? |
|:--|:--|:--|
| Citations, stars, rankings | `data/papers.json`, `data/catalog_meta.json`, `README.md`, `EVIDENCE.md` | No — fully automatic |
| Monthly news top 10 | `data/weekly_picks.json`, `highlights/` | **Yes — approval gate** |

## Every run must refresh all four README sections

A run is only complete when all four of these are current. All four are emitted by
`scripts/build_readme.py` from `data/papers.json` + `data/weekly_picks.json`, so
they refresh automatically **provided the underlying data actually updated** —
which is the part that silently fails. Verify, don't assume.

| Section | Driven by | Refreshed when |
|:--|:--|:--|
| 📅 Weekly Update · Monthly Top 10 | `data/weekly_picks.json` | Picks approved and rewritten |
| 📈 Live Rankings | `citations` + `github_stars` in `papers.json` | `verify_papers.py --update` succeeds |
| 🔥 Recent Papers by Average Monthly Citations | `citations` + `date` | same |
| 🏆 Most-Cited Papers by Year | `citations` + first-appearance year | same |

Plus **every paper's `citations` and `github_stars`** — all catalog entries, not
just the ones in the ranking tables. The ranking tables are a view over that data;
if the underlying counts are stale, all three ranking sections are quietly wrong.

### Confirm the refresh actually landed

`verify_papers.py --update` can write partial data and still look fine. After
running, check coverage rather than trusting the exit code:

```bash
python - <<'PY'
import json, subprocess
old = json.loads(subprocess.run(['git','show','HEAD:data/papers.json'],
                                capture_output=True, text=True).stdout)
new = json.load(open('data/papers.json'))
ch = sum(1 for k in new if k in old and old[k].get('citations') != new[k].get('citations'))
st = sum(1 for k in new if k in old and old[k].get('github_stars') != new[k].get('github_stars'))
z  = [k for k, v in new.items() if v.get('citations') == 0]
print(f"citations changed: {ch}/{len(new)}   stars changed: {st}")
print(f"zero-citation entries: {len(z)}")
for k in z:
    print("   ", k, new[k]['title'][:60])
PY
```

A well-known paper sitting at 0 citations is the tell. Check it against the live
API before believing it — a real count of 0 is rare for anything published.

### Rate limiting is the usual culprit

Both scholarly indexes throttle hard, and a throttled lookup previously looked
identical to "paper not indexed", zeroing counts for well-cited work.

- **OpenAlex is the primary citation source** — no API key, no signup. It is
  queried first, in bulk, by arXiv DOI. Set `OPENALEX_MAILTO=you@example.com`
  to enter its faster "polite pool"; strongly recommended, costs nothing.
- **`SEMANTIC_SCHOLAR_API_KEY` is optional** ([request form](https://www.semanticscholar.org/product/api#api-key-form);
  select the **Academic Graph API** endpoint — the script only calls
  `/graph/v1/paper/batch`). S2 runs after OpenAlex and can only raise a count, so
  a throttled S2 no longer leaves the catalog stale. Approval can take days;
  the refresh works fine without it.
- **Export `GITHUB_TOKEN`** — unauthenticated GitHub caps at 60 requests/hour.
- `verify_papers.py` now prints a `429` warning to stderr and reports match
  coverage (`citations refreshed (N/M matched ...)`). Treat a low N as a failed run.
- `citations_as_of` / `github_stars_as_of` in `catalog_meta.json` are only stamped
  when the refresh was complete. **If the stamp did not advance, the run failed** —
  re-run before committing rather than publishing stale rankings.

Never pipe the script through `tail`/`head` — that discards its non-zero exit
status and hides the `UNVERIFIED entries` block. Let it print in full.

## Rule 0 — never hand-edit generated files

`README.md`, `EVIDENCE.md`, `data/closure_audit.*`, and `highlights/*.md` are **build artifacts**. Change the data, then rebuild. The section headings, the table of contents, and both ranking tables are all emitted by `scripts/build_readme.py` — editing `README.md` directly gets overwritten and fails PR CI (`verify-pr.yml` runs `git diff --exit-code` on the generated files).

## Also add newly found papers to the catalog body

News curation and the catalog are separate. A paper surfaced while researching
the news half belongs in `data/papers.json` too — the weekly picks age out after
30 days, but the catalog is permanent. **Every run: any AI4AI-relevant paper found
during research gets added to the catalog, whether or not it makes the top 10.**

This is not gated on maintainer approval — the catalog is scope-based, not a
curated top-N. Add it if it fits the survey scope (long-horizon agents, harness
design, model design, benchmarks); skip it otherwise.

Entry schema — every field is required, `code` is `null` when no repo exists:

```json
"karten2026primeagent": {
  "title": "Prime Agent: A Self-Improving RLM Harness",
  "venue": "arXiv",
  "date": "2026-08",
  "arxiv_id": "2608.23552",
  "url": "https://arxiv.org/abs/2608.23552",
  "citations": 0,
  "code": "https://github.com/PrimeIntellect-ai/prime-agent",
  "sections": ["targets/harness"],
  "collections": ["harness-design"]
}
```

- Key convention: `<firstauthor><year><shortname>`, lowercase.
- `sections` must come from the valid set in `scripts/verify_papers.py`
  (`targets/harness`, `evidence/benchmarks`, `foundations/self-improvement`, …).
- `collections` is one or more of `benchmarks`, `harness-design`, `model-design`.
- Leave `citations: 0` and omit `github_stars`; the next `--update` fills both.
- Verify the arXiv id and date against the API before adding — never trust a
  search snippet:

```bash
curl -s "https://export.arxiv.org/api/query?id_list=2608.23552" | grep -E "<title>|<published>"
```

## The news approval gate

The maintainer decides what counts as news. **Never write `data/weekly_picks.json` before they have approved the shortlist.**

1. **Research.** The edition is the **month's top 10**, republished weekly — so each run re-ranks the whole trailing 30 days, not just the new week. Carry forward items that still belong, drop what aged out or got beaten, and add the week's new arrivals. Primary sources only — vendor blogs, arXiv, Hugging Face, official docs and repos. No VentureBeat/TechCrunch/Medium/X threads. Verify each publication date on the source page itself; a search snippet is not proof.

   **Date traps that have bitten before:**
   - `dateModified` is not `datePublished`. A site rebuild restamps every post — Microsoft Research and Factory.ai both showed in-window `dateModified` on articles actually published weeks earlier. Always read `datePublished`, the rendered `<time>` element, or arXiv's `[Submitted on …]` line.
   - arXiv stamps v1 by announcement cycle, so a window ending on a Monday typically has **no** papers dated Sat/Sun/Mon. Do not go hunting for them.
   - Check the arXiv **v1** date, not the latest revision.
2. **Propose.** Present a table of ~12-16 candidates with date, kind, source, title, url, a draft `why`, and a one-line impact rationale. Include more than needed so there is room to cut. Note anything you could not date.
3. **Wait.** The maintainer picks. Do not proceed on assumption.
4. **Write** the approved items into `data/weekly_picks.json`, newest first.

### Balance: roughly half flagship models, half research

The 30-day window means the major labs' flagship releases almost always fall inside it. Target about **5 flagship model releases and 5 AI4AI research/harness items** per edition — that keeps the general-interest stories that draw readers alongside the material the repository exists for.

Carry at most **one entry per lab** — its most recent flagship. Point-releases, quantizations, draft/distilled checkpoints, and availability-on-a-new-cloud announcements are not flagships and face the normal bar.

### Scoring

Six dimensions, the first two weighted highest:

1. **Publisher authority** — the labs above, then top research groups (Stanford, CMU, Berkeley, Tsinghua, MSR, FAIR) and major AI-native companies.
2. **Discussion volume** — HN front page, heavy X/Reddit traffic, fast citation accrual. Treat as a strong positive when present, but *do not penalize its absence* for items published late in the window: a Friday paper has not had time to accumulate discussion, and penalizing that skews every edition toward Monday news.
3. **Concrete verifiable result** — a number on a named benchmark with a reproducible setup, not a capability claim.
4. **Changes what builders do now** — actionable this week, versus interesting to read.
5. **Artifact released** — open weights, code, or a benchmark beats a blog post describing something closed.
6. **Durability** — still cited in six months, or news-cycle noise?

**Impact bar.** Include agent harnesses and tools with adoption potential, research that changes how people build long-horizon agents, and benchmarks likely to become reference points. Exclude incremental point-releases, marketing posts, milestone/download announcements, minor library updates, small leaderboard deltas, and "now available on cloud X". Prefer variety across kinds.

## weekly_picks.json contract

Top level: `updated` (ISO date), `cadence`, `selection`, `items`.

Each item has exactly six keys — `date`, `kind`, `source`, `title`, `url`, `why`:

```json
{
  "date": "2026-08-21",
  "kind": "Model release",
  "source": "Z.ai",
  "title": "GLM-5.3: Frontier Coding with Emergent Cyber Capabilities",
  "url": "https://z.ai/blog/glm-5.3",
  "why": "Z.ai says the unchanged GLM-5.2 base gained stronger long-horizon coding capabilities entirely through scaled post-training."
}
```

Hard constraints, all enforced by `scripts/check_repo.py`:

- **Rolling 30-day window** — every `date` must satisfy `0 <= (updated - date).days <= 30`. Items age out as `updated` advances, so each weekly refresh drops what fell past 30 days and pulls in the new week. Check the oldest items every run.
- **1-10 items**, sorted newest first.
- **`kind` is a closed enum** — exactly one of: `Blog`, `Harness release`, `Model release`, `Model update`, `News`, `Open-weight release`, `Paper`, `Research release`, `Tooling release`.
- **URLs** must start with `https://` and be unique across items.
- **No `|` characters** in `title` or `why` — they are interpolated into a Markdown table unescaped and would break it.
- **Attribute claims** to the publisher ("Anthropic says…", "The authors report…"). Never state a vendor benchmark claim as fact.

## Running the refresh

```bash
.claude/skills/ai4ai-weekly/refresh.sh --update    # maintainer: live citations + stars
.claude/skills/ai4ai-weekly/refresh.sh --offline   # contributor: no network
```

Run from the repository root. The script wraps the canonical five-step pipeline, in this order:

```bash
python scripts/verify_papers.py --update   # or --offline
python scripts/build_evidence.py
python scripts/build_readme.py
python scripts/archive_weekly.py --ensure
python scripts/check_repo.py
```

Order is load-bearing: each step consumes the previous one's output. Finalize `weekly_picks.json` **before** `build_readme.py`.

### --offline vs --update

- `--offline` — schema and link validation only. No network, no writes. What PR CI runs.
- `--update` — the real refresh. Queries Semantic Scholar (batch), OpenAlex (fallback for non-arXiv), and the GitHub API. Writes `citations`, `github_stars`, canonicalized `code` URLs, and stamps `citations_as_of` / `github_stars_as_of` in `catalog_meta.json`. Takes ~2 minutes. **Export both `GITHUB_TOKEN` and `SEMANTIC_SCHOLAR_API_KEY` first** — unauthenticated GitHub is capped at 60 requests/hour (the catalog has more repos than that), and unauthenticated Semantic Scholar returns 429 and leaves citations stale.

Citation counts only ever move up (`max(existing, new)`), so a flaky index cannot erase a count.

### Archive modes

`scripts/archive_weekly.py` publishes `highlights/<updated>.md` with a sha256 fingerprint of `weekly_picks.json`.

| Flag | Behavior |
|:--|:--|
| *(none)* | Publish; refuse if the edition already exists |
| `--ensure` | Publish if missing, no-op if it matches, **fail** if a published edition drifted. Used by CI |
| `--check` | Verify only, never write |
| `--force` | Overwrite — only ever to correct the **current** edition |

Past editions are immutable. If you change `weekly_picks.json` after publishing, re-run with `--force` and rebuild the README, or the fingerprint check fails.

## Expected output

Modified: `data/papers.json`, `data/catalog_meta.json`, `data/weekly_picks.json`, `README.md`, `EVIDENCE.md`, `data/closure_audit.csv`, `data/closure_audit_summary.json`, `highlights/README.md`. New: `highlights/<date>.md`.

Sanity-check before committing:

1. `README.md` shows `Updated <date>` and `current through **<date>**`.
2. `citations_as_of` and `github_stars_as_of` in `catalog_meta.json` both advanced to today. If either did not, the refresh was incomplete — re-run rather than committing stale rankings.
3. The coverage check above reports a plausible number of changed citations, and no well-known paper sits at 0.
4. All four README sections rebuilt: Weekly Update, Live Rankings, Recent Papers by Average Monthly Citations, Most-Cited Papers by Year.

## Recovery

**`<date>.md does not match data/weekly_picks.json`** — the picks file changed without republishing. If the edition is missing entirely, `python scripts/archive_weekly.py --ensure`. If it exists but drifted and the edition is the current one, `--force`, then rerun `build_readme.py`. Never `--force` a past edition.

**`news item N falls outside the rolling 30-day window`** — `updated` advanced past an item's 30-day life. Drop the aged-out items and re-rank the trailing 30 days; do not stretch the window or roll `updated` backwards.

**`GitHub code repository is unavailable`** — usually an unauthenticated rate-limit, not a dead repo. `github_repo()` swallows every exception, so a 403 looks identical to a 404. Export `GITHUB_TOKEN` and retry before concluding the repo is gone.

**A well-cited paper shows `"citations": 0`** — a rate-limited lookup, not an unindexed paper. Confirm against the live API:

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2401.13649?fields=title,citationCount"
```

A `429` response means throttling. Export `SEMANTIC_SCHOLAR_API_KEY` and re-run `--update`. Counts only ever move up (`max(existing, new)`), so a throttled run cannot corrupt good data — it just leaves it stale.

**Wall of `arXiv id not found` covering obviously real ids** (ReAct `2210.03629`, etc.) — the arXiv API was unreachable, not the ids invalid. The script now detects this and skips id verification instead of emitting one failure per entry; if you still see it, check `https://export.arxiv.org/api/query?id_list=2210.03629` by hand and retry when the API recovers.

**`N labeled source-only entries were not found`** — informational, not an error. Those entries are verifiable by their landing URL but carry no scholarly index record. Exit code is still 0.

**Workflow failed but citations looked fine** — the archive gate used to run before the commit step, so a successful refresh got discarded. That is what `--ensure` fixes; if you see it again, check whether the gate regressed to `--check`.

## Verifying before you push

`python scripts/check_repo.py` is the same gate CI runs — window rule, kind enum, fingerprint match, README-vs-data consistency. If it exits 0, the scheduled run will pass. To confirm without waiting for Monday:

```bash
gh workflow run "Weekly AI4AI citation refresh"
gh run watch
```

The scheduled job runs Mondays at 03:00 UTC (`.github/workflows/update-citations.yml`).
