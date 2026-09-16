#!/usr/bin/env bash
# Rebuild the Awesome AI4AI catalog, rankings, evidence, and weekly archive.
#
#   refresh.sh --update    maintainer: live citation + GitHub star refresh
#   refresh.sh --offline   contributor: schema and link checks only, no network
#
# Curation is deliberately not automated here. Finalize data/weekly_picks.json
# (with maintainer approval) before running, since build_readme.py reads it.
set -euo pipefail

MODE="${1:---offline}"
case "$MODE" in
  --update|--offline) ;;
  *)
    echo "usage: $(basename "$0") [--update|--offline]" >&2
    exit 2
    ;;
esac

cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

if [ "$MODE" = "--update" ] && [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "warning: GITHUB_TOKEN is unset; GitHub allows only 60 requests/hour" >&2
  echo "         unauthenticated, which usually fails the star refresh." >&2
fi

if [ "$MODE" = "--update" ] && [ -z "${OPENALEX_MAILTO:-}" ]; then
  echo "note: OPENALEX_MAILTO is unset. OpenAlex is the primary citation source;" >&2
  echo "      setting it to your email joins the faster 'polite pool' (free, no" >&2
  echo "      signup) and makes the refresh noticeably more reliable." >&2
fi

echo "==> verify_papers.py $MODE"
python scripts/verify_papers.py "$MODE"

echo "==> build_evidence.py"
python scripts/build_evidence.py

echo "==> build_readme.py"
python scripts/build_readme.py

echo "==> archive_weekly.py --ensure"
python scripts/archive_weekly.py --ensure

echo "==> check_repo.py"
python scripts/check_repo.py

echo
echo "Refresh complete. Review the diff before committing:"
echo "  git diff --stat"
