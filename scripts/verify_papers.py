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


def http_json(url, data=None, tries=6):
    for t in range(tries):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json",
                         "User-Agent": "awesome-ai4ai-verifier"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(4 + 4 * t)
        except Exception:
            time.sleep(4 + 4 * t)
    return None


def arxiv_batch(ids):
    out = {}
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for i in range(0, len(ids), 60):
        url = ("https://export.arxiv.org/api/query?id_list="
               + ",".join(ids[i:i + 60]) + "&max_results=100")
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                tree = ET.parse(r)
        except Exception:
            continue
        for e in tree.getroot().findall("a:entry", ns):
            m = re.search(r"abs/([\d.]+)", e.find("a:id", ns).text or "")
            if m:
                out[m.group(1)] = re.sub(
                    r"\s+", " ", e.find("a:title", ns).text or "").strip()
        time.sleep(3)
    return out


def openalex_match(title):
    """Fallback for entries neither on arXiv nor indexed by Semantic Scholar
    (DOI-only preprints, technical reports). Returns (title, citations)."""
    q = urllib.parse.quote(re.sub(r"[^\w\s]", " ", title)[:200])
    rec = http_json(
        "https://api.openalex.org/works" f"?search={q}&per-page=5",
        tries=3,
    )
    for w in (rec or {}).get("results", []):
        if sim(title, w.get("display_name")) >= 0.9:
            return w["display_name"], w.get("cited_by_count")
    return None, None


def semantic_scholar_id(paper):
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
        if paper.get("arxiv_id"):
            expected_date = "20" + paper["arxiv_id"][:2] + "-" + paper["arxiv_id"][2:4]
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
            failures.append((k, "arXiv id not found: " + p["arxiv_id"]))
        elif sim(p["title"], t) < 0.75:
            failures.append((k, f"arXiv title mismatch: '{t}'"))

    s2_matched = set()
    citation_complete = True
    if UPDATE:
        keys = list(papers)
        ids = [semantic_scholar_id(papers[k]) for k in keys]
        for i in range(0, len(ids), 100):
            recs = http_json(
                "https://api.semanticscholar.org/graph/v1/paper/batch?fields=" + S2_FIELDS,
                json.dumps({"ids": ids[i:i + 100]}).encode())
            if recs is None or len(recs) != len(ids[i:i + 100]):
                citation_complete = False
            recs = recs or []
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

    # Non-arXiv entries: OpenAlex title match. Avoid the rate-limited S2
    # one-title-at-a-time endpoint; arXiv records already use its batch API.
    github_complete = True
    for k, p in papers.items():
        if p.get("arxiv_id") or k in s2_matched:
            continue
        title, cites = openalex_match(p["title"])
        if title:
            if UPDATE and cites is not None:
                # OpenAlex may split a conference version from its preprint.
                # Never let that fallback replace a larger merged count.
                existing = papers[k].get("citations")
                papers[k]["citations"] = max(existing or 0, cites)
        elif (p.get("url") or "").startswith("http"):
            source_only.append(k)
        else:
            failures.append((k, "no S2 / OpenAlex match and no landing URL"))
        time.sleep(0.2)

    # Verify every configured GitHub code URL and refresh stars. Redirected or
    # transferred repositories are normalized to GitHub's canonical html_url.
    for k, p in papers.items():
        if not github_slug(p.get("code")):
            continue
        repo = github_repo(p["code"])
        if not repo:
            github_complete = False
            failures.append((k, "GitHub code repository is unavailable"))
            continue
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
        with open(META, "w") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        print(
            "citations refreshed"
            if citation_complete
            else "partial citation refresh; previous as-of date retained"
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
