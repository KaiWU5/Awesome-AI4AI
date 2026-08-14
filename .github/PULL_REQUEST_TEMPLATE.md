<!-- Paper tables are generated. Edit structured data, then rebuild. -->

**What this PR changes**

<!-- e.g. "adds two Harness Design papers" or "corrects transfer evidence for xxx" -->

**Checklist**

- [ ] I edited `data/papers.json`, not the README tables
- [ ] Every new paper uses `benchmarks`, `harness-design`, and/or `model-design`
- [ ] `python scripts/verify_papers.py --offline` passes locally
- [ ] `python scripts/build_evidence.py` passes locally
- [ ] `python scripts/build_readme.py` was re-run and the regenerated `README.md` is committed
- [ ] `python scripts/check_repo.py` passes locally
- [ ] Every `code` link points to the official implementation
- [ ] Any G/R/H/T or ownership change includes a primary-source locator and rationale
- [ ] If weekly news changed, I archived the dated edition with `scripts/archive_weekly.py`
