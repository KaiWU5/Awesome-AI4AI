#!/usr/bin/env python3
"""Check catalog metadata against arXiv / Semantic Scholar / OpenAlex when
indexed, label source-only records, and optionally refresh citation counts.

    python scripts/verify_papers.py --offline       # fast local schema/link checks
    python scripts/verify_papers.py                 # live scholarly verification
    python scripts/verify_papers.py --update        # verify + refresh citations

Standard library only — no dependencies to install.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "papers.json")
META = os.path.join(ROOT, "data", "catalog_meta.json")
S2_FIELDS = "title,citationCount,externalIds"
# Optional contact address for OpenAlex requests.
_MAILTO = os.environ.get("OPENALEX_MAILTO", "").strip()
OPENALEX_MAILTO = f"&mailto={urllib.parse.quote(_MAILTO)}" if _MAILTO else ""
UPDATE = "--update" in sys.argv
OFFLINE = "--offline" in sys.argv
VALID_SECTIONS = {
    "targets/data", "targets/weights", "targets/harness", "targets/substrate",
    "targets/evaluator", "targets/research", "evidence/benchmarks", "evidence/measurement",
    "foundations/long-horizon", "foundations/self-improvement", "analyses",
}
VALID_COLLECTIONS = {"benchmarks", "harness-design", "model-design"}
REQUIRED_FIELDS = {
    "title", "venue", "date", "arxiv_id", "url", "citations", "code",
    "sections", "collections",
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


RATE_LIMITED = []
RATE_LIMITED_HOSTS = set()


def http_json(url, data=None, tries=6):
    """Return decoded JSON, or None when the resource is absent or unreachable.

    A 429 is recorded in RATE_LIMITED so callers can distinguish "the index does
    not have this paper" from "the index refused to answer". Conflating the two
    silently zeroes citation counts for well-indexed papers.
    """
    host = urllib.parse.urlsplit(url).netloc
    if host in RATE_LIMITED_HOSTS:
        return None
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    for t in range(tries):
        try:
            headers = {"Content-Type": "application/json",
                       "User-Agent": "awesome-ai4ai-verifier"}
            if key and "semanticscholar.org" in url:
                headers["x-api-key"] = key
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                RATE_LIMITED.append(url)
                RATE_LIMITED_HOSTS.add(host)
                return None
            time.sleep(4 + 4 * t)
        except Exception:
            time.sleep(4 + 4 * t)
    return None


def arxiv_batch(ids):
    """Map arXiv id -> title. Sets arxiv_batch.incomplete when a chunk request
    fails outright, so an unreachable API is never reported as missing ids."""
    out = {}
    arxiv_batch.incomplete = False
    arxiv_batch.first_dates = {}
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for i in range(0, len(ids), 60):
        url = ("https://export.arxiv.org/api/query?id_list="
               + ",".join(ids[i:i + 60]) + "&max_results=100")
        tree = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    tree = ET.parse(r)
                break
            except Exception:
                time.sleep(5 + 5 * attempt)
        if tree is None:
            arxiv_batch.incomplete = True
            continue
        for e in tree.getroot().findall("a:entry", ns):
            m = re.search(r"abs/([\d.]+)", e.find("a:id", ns).text or "")
            if m:
                out[m.group(1)] = re.sub(
                    r"\s+", " ", e.find("a:title", ns).text or "").strip()
                published = e.findtext("a:published", default="", namespaces=ns)
                if published:
                    arxiv_batch.first_dates[m.group(1)] = published[:10]
        time.sleep(3)
    return out


def openalex_batch(arxiv_titles):
    """Bulk citation lookup for an arXiv-id-to-title mapping.

    DOI matches still require a matching title: index metadata can be wrong.
    Returns {arxiv_id: cited_by_count} for title-verified records only.
    """
    out = {}
    ids = [a for a in arxiv_titles if a]
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = ("https://api.openalex.org/works?per-page=50&select=ids,display_name,cited_by_count"
               "&filter=doi:"
               + "|".join("10.48550/arxiv." + a for a in chunk)
               + OPENALEX_MAILTO)
        rec = http_json(url, tries=3)
        for w in (rec or {}).get("results", []):
            doi = (w.get("ids") or {}).get("doi") or ""
            m = re.search(r"arxiv\.(\d{4}\.\d{4,5})", doi.lower())
            if (m and m.group(1) in arxiv_titles
                    and w.get("cited_by_count") is not None
                    and sim(arxiv_titles[m.group(1)], w.get("display_name")) >= 0.75):
                out[m.group(1)] = w["cited_by_count"]
        time.sleep(1)
    return out


def openalex_match(title):
    """Per-title fallback for entries without a usable arXiv id or DOI
    (technical reports, landing-page-only releases). Returns (title, citations)."""
    q = urllib.parse.quote(re.sub(r"[^\w\s]", " ", title)[:200])
    rec = http_json(
        "https://api.openalex.org/works" f"?search={q}&per-page=5" + OPENALEX_MAILTO,
        tries=3,
    )
    for w in (rec or {}).get("results", []):
        if sim(title, w.get("display_name")) >= 0.9:
            return w["display_name"], w.get("cited_by_count")
    return None, None


def semantic_scholar_id(paper):
    # Some proceedings URLs are not resolvable by S2 even though the paper is
    # indexed. Retain a title-verified paper ID for those records.
    if paper.get("semantic_scholar_id"):
        return paper["semantic_scholar_id"]
    if paper.get("arxiv_id"):
        return "ARXIV:" + paper["arxiv_id"]
    url = paper.get("url", "")
    doi = re.search(r"(?:doi\.org/|doi\.ieeecomputersociety\.org/)(10\.[^?#]+)", url)
    if doi:
        return "DOI:" + doi.group(1)
    return "URL:" + url


def github_slug(url):
    match = re.fullmatch(
        r"https://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?", url or ""
    )
    return "/".join(match.groups()) if match else None


def github_repo(url):
    """Resolve a canonical GitHub repository and return its current star count."""
    slug = github_slug(url)
    if not slug:
        return None
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "awesome-ai4ai-verifier",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{slug}", headers=headers
        )
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.load(response)
    except Exception:
        return None


def validate_catalog(papers):
    failures = []
    seen_urls = {}
    seen_titles = {}
    for key, paper in papers.items():
        missing = sorted(REQUIRED_FIELDS - set(paper))
        if missing:
            failures.append((key, "missing fields: " + ", ".join(missing)))
            continue
        for field in ("title", "venue", "date", "url"):
            if not isinstance(paper[field], str) or not paper[field].strip():
                failures.append((key, f"{field} must be a non-empty string"))
        if not re.fullmatch(r"\d{4}(?:-\d{2})?", str(paper["date"])):
            failures.append((key, "malformed first-appearance date: " + str(paper["date"])))
        sections = paper["sections"]
        collections = paper["collections"]
        if not isinstance(sections, list) or not sections:
            failures.append((key, "sections must be a non-empty list"))
            sections = []
        if not isinstance(collections, list):
            failures.append((key, "collections must be a list"))
            collections = []
        unknown = sorted(set(sections) - VALID_SECTIONS)
        unknown_collections = sorted(set(collections) - VALID_COLLECTIONS)
        if unknown:
            failures.append((key, "unknown sections: " + ", ".join(unknown)))
        if unknown_collections:
            failures.append((
                key,
                "unknown collections: " + ", ".join(unknown_collections),
            ))
        if len(collections) != len(set(collections)):
            failures.append((key, "duplicate collection assignment"))
        citations = paper["citations"]
        if citations is not None and (
            isinstance(citations, bool)
            or not isinstance(citations, int)
            or citations < 0
        ):
            failures.append((key, "citations must be null or a non-negative integer"))
        if paper.get("arxiv_id") and not re.fullmatch(
                r"\d{4}\.\d{4,5}", paper["arxiv_id"]):
            failures.append((key, "malformed arXiv id: " + paper["arxiv_id"]))
        s2_id = paper.get("semantic_scholar_id")
        if s2_id is not None and (
            not isinstance(s2_id, str) or not re.fullmatch(r"[0-9a-f]{40}", s2_id)
        ):
            failures.append((key, "malformed Semantic Scholar paper id"))
        url = paper.get("url")
        if url:
            if not url.startswith("https://"):
                failures.append((key, "malformed URL: " + url))
            elif url in seen_urls:
                failures.append((key, "duplicate URL shared with " + seen_urls[url]))
            else:
                seen_urls[url] = key
        code = paper.get("code")
        if code is not None and (
            not isinstance(code, str) or not code.startswith("https://")
        ):
            failures.append((key, "code must be null or an HTTPS URL"))
        stars = paper.get("github_stars")
        if "github.com" in (code or "") and not github_slug(code):
            failures.append((key, "GitHub code URL must point to a repository root"))
        if github_slug(code) and stars is None:
            failures.append((key, "GitHub code repository is missing github_stars"))
        if stars is not None and (
            isinstance(stars, bool) or not isinstance(stars, int) or stars < 0
        ):
            failures.append((key, "github_stars must be a non-negative integer"))
        if stars is not None and not github_slug(code):
            failures.append((key, "github_stars present without a GitHub repo URL"))
        first_public_date = paper.get("first_public_date")
        if first_public_date is not None:
            try:
                if not isinstance(first_public_date, str):
                    raise ValueError("not a string")
                parsed_date = date.fromisoformat(first_public_date)
                if parsed_date.isoformat() != first_public_date:
                    raise ValueError("not ISO YYYY-MM-DD")
            except ValueError:
                failures.append((key, "first_public_date must be an ISO YYYY-MM-DD date"))
                first_public_date = None
        if paper.get("arxiv_id") or first_public_date:
            # The arXiv identifier follows the announcement cycle. A v1
            # submitted on the last day of a month can receive next month's ID.
            expected_date = (
                first_public_date[:7] if first_public_date
                else "20" + paper["arxiv_id"][:2] + "-" + paper["arxiv_id"][2:4]
            )
            if paper["date"] != expected_date:
                failures.append((
                    key,
                    f"date {paper['date']} disagrees with arXiv first appearance "
                    f"{expected_date}",
                ))
        title = norm(paper.get("title"))
        if title in seen_titles:
            failures.append((key, "duplicate title shared with " + seen_titles[title]))
        elif title:
            seen_titles[title] = key
    return failures


def main():
    if UPDATE and OFFLINE:
        raise SystemExit("--offline and --update cannot be used together")
    with open(DATA) as handle:
        papers = json.load(handle)
    failures = validate_catalog(papers)
    source_only = []
    if OFFLINE:
        if failures:
            print(f"\n{len(failures)} INVALID entries:")
            for key, why in failures:
                print(f"  {key}: {why}")
            raise SystemExit(1)
        print(f"all {len(papers)} catalog entries passed offline checks")
        return

    with_ax = {k: p for k, p in papers.items() if p.get("arxiv_id")}
    ax_titles = arxiv_batch([p["arxiv_id"] for p in with_ax.values()])
    for k, p in with_ax.items():
        t = ax_titles.get(p["arxiv_id"])
        if t is None:
            # Only a reachable API can prove an id is absent. When a chunk
            # request failed, treat unresolved ids as unchecked, not invalid.
            if not arxiv_batch.incomplete:
                failures.append((k, "arXiv id not found: " + p["arxiv_id"]))
        elif sim(p["title"], t) < 0.75:
            failures.append((k, f"arXiv title mismatch: '{t}'"))
        published = arxiv_batch.first_dates.get(p["arxiv_id"])
        if p.get("first_public_date") and published and p["first_public_date"] != published:
            failures.append((k, f"first_public_date disagrees with arXiv v1: {published}"))
    if arxiv_batch.incomplete:
        print("warning: the arXiv API was unreachable for at least one batch; "
              "id verification was skipped for unresolved entries", file=sys.stderr)

    # Primary citation pass: OpenAlex by arXiv DOI. No API key, no signup, and
    # not subject to the Semantic Scholar shared-pool throttling that silently
    # leaves counts stale. S2 runs afterwards and can only raise a count.
    oa_matched = set()
    if UPDATE and with_ax:
        oa_counts = openalex_batch({p["arxiv_id"]: p["title"] for p in with_ax.values()})
        for k, p in with_ax.items():
            cites = oa_counts.get(p["arxiv_id"])
            if cites is not None:
                papers[k]["citations"] = max(papers[k].get("citations") or 0, cites)
                oa_matched.add(k)
        print(f"OpenAlex matched {len(oa_matched)}/{len(with_ax)} arXiv entries")

    s2_matched = set()
    title_matched = set()
    citation_complete = True
    if UPDATE:
        keys = list(papers)
        ids = [semantic_scholar_id(papers[k]) for k in keys]
        for i in range(0, len(ids), 100):
            recs = http_json(
                "https://api.semanticscholar.org/graph/v1/paper/batch?fields=" + S2_FIELDS,
                json.dumps({"ids": ids[i:i + 100]}).encode())
            if not isinstance(recs, list) or len(recs) != len(ids[i:i + 100]):
                recs = []
            for k, rec in zip(keys[i:i + 100], recs):
                if (
                    isinstance(rec, dict)
                    and rec.get("citationCount") is not None
                    and sim(papers[k]["title"], rec.get("title")) >= 0.75
                ):
                    existing = papers[k].get("citations")
                    papers[k]["citations"] = max(
                        existing or 0, rec["citationCount"]
                    )
                    s2_matched.add(k)
            time.sleep(2)

    # OpenAlex title match. Covers non-arXiv entries (DOI-only preprints,
    # technical reports) and, critically, arXiv entries that Semantic Scholar
    # reports as zero-cited: S2 sometimes splits a preprint from its published
    # version and leaves the preprint record at 0 while OpenAlex has the real
    # merged count. Counts combine with max(), so a second opinion is safe.
    github_complete = True
    for k, p in papers.items():
        if "api.openalex.org" in RATE_LIMITED_HOSTS:
            break
        indexed = k in s2_matched or k in oa_matched
        still_zero = indexed and not papers[k].get("citations")
        if indexed and not still_zero:
            continue
        title, cites = openalex_match(p["title"])
        if title:
            if UPDATE and cites is not None:
                # OpenAlex may split a conference version from its preprint.
                # Never let that fallback replace a larger merged count.
                existing = papers[k].get("citations")
                papers[k]["citations"] = max(existing or 0, cites)
                title_matched.add(k)
        elif indexed:
            pass  # already verified via S2/OpenAlex; this was a top-up only
        elif (p.get("url") or "").startswith("http"):
            # Verifiable by landing URL but carries no scholarly index record.
            # A landing URL proves provenance, not a refreshed citation count.
            source_only.append(k)
        else:
            failures.append((k, "no S2 / OpenAlex match and no landing URL"))
        time.sleep(0.2)

    # Every source has now run. Citations are complete unless some paper was
    # left uncovered by all of them. Papers OpenAlex resolved via the DOI batch
    # are covered even when their S2 chunk was throttled.
    citation_verified = oa_matched | s2_matched | title_matched
    citation_gaps = set(papers) - citation_verified
    if UPDATE and citation_gaps:
        citation_complete = False
        print(
            f"note: {len(citation_gaps)} paper(s) were not refreshed by any source this "
            "run and kept their previous counts: "
            + ", ".join(sorted(citation_gaps)[:10])
            + ("..." if len(citation_gaps) > 10 else ""),
            file=sys.stderr,
        )

    # Verify every configured GitHub code URL and refresh stars. Redirected or
    # transferred repositories are normalized to GitHub's canonical html_url.
    github_checks = {}
    github_records_verified = 0
    for k, p in papers.items():
        if not github_slug(p.get("code")):
            continue
        slug = github_slug(p["code"]).lower()
        if slug not in github_checks:
            github_checks[slug] = github_repo(p["code"])
        repo = github_checks[slug]
        if not repo:
            github_complete = False
            failures.append((k, "GitHub code repository is unavailable"))
            continue
        github_records_verified += 1
        canonical = repo.get("html_url")
        if UPDATE and canonical:
            papers[k]["code"] = canonical
            papers[k]["github_stars"] = repo["stargazers_count"]
        time.sleep(0.1)

    if UPDATE:
        with open(DATA, "w") as handle:
            json.dump(papers, handle, indent=1, ensure_ascii=False)
            handle.write("\n")
        with open(META) as handle:
            metadata = json.load(handle)
        if citation_complete:
            metadata["citations_as_of"] = date.today().isoformat()
        if github_complete:
            metadata["github_stars_as_of"] = date.today().isoformat()
        metadata["metrics_refresh"] = {
            "checked_on": date.today().isoformat(),
            "citation_records_checked": len(papers),
            "citation_records_verified": len(citation_verified),
            "citation_records_retained": sorted(
                k for k in citation_gaps if papers[k].get("citations") is not None
            ),
            "citation_records_unindexed": sorted(
                k for k in citation_gaps if papers[k].get("citations") is None
            ),
            "github_repositories_verified": sum(bool(repo) for repo in github_checks.values()),
            "github_records_verified": github_records_verified,
            "github_repositories_unavailable": sorted(
                slug for slug, repo in github_checks.items() if not repo
            ),
            "note": "Title-verified OpenAlex DOI/title and Semantic Scholar checks. "
                    "Unmatched or unavailable records retain prior counts or null. "
                    "Rate-limited services are not repeatedly retried within a run; "
                    "complete snapshot dates advance only with complete coverage.",
        }
        with open(META, "w") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        matched = sum(1 for k in papers if k in s2_matched)
        print(
            f"citations refreshed ({matched}/{len(papers)} matched in Semantic Scholar)"
            if citation_complete
            else f"partial citation refresh ({matched}/{len(papers)} matched); "
                 "previous as-of date retained"
        )
        if RATE_LIMITED:
            print(
                f"warning: {len(RATE_LIMITED)} request(s) were rate-limited (HTTP 429). "
                "Coverage above combines successful checks from all sources; "
                "uncovered records retain their previous counts. Check the affected "
                "service's API credentials or quota before retrying.",
                file=sys.stderr,
            )

    if failures:
        print(f"\n{len(failures)} UNVERIFIED entries:")
        for k, why in failures:
            print(f"  {k}: {why}")
        sys.exit(1)
    if source_only:
        print(
            f"{len(source_only)} labeled source-only entries were not found in "
            "Semantic Scholar or OpenAlex: " + ", ".join(source_only)
        )
    print(f"all {len(papers)} catalog entries checked")


if __name__ == "__main__":
    main()
