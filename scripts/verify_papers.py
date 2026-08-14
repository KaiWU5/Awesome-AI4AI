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
    rec = http_json("https://api.openalex.org/works"
                    f"?filter=title.search:{q}&per-page=3", tries=3)
    for w in (rec or {}).get("results", []):
        if sim(title, w.get("display_name")) >= 0.75:
            return w["display_name"], w.get("cited_by_count")
    return None, None


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

    if UPDATE:
        ids = ["ARXIV:" + p["arxiv_id"] for p in with_ax.values()]
        keys = list(with_ax)
        for i in range(0, len(ids), 100):
            recs = http_json(
                "https://api.semanticscholar.org/graph/v1/paper/batch?fields=" + S2_FIELDS,
                json.dumps({"ids": ids[i:i + 100]}).encode()) or []
            for k, rec in zip(keys[i:i + 100], recs):
                if isinstance(rec, dict) and rec.get("citationCount") is not None:
                    papers[k]["citations"] = rec["citationCount"]
            time.sleep(2)

    # non-arXiv entries: S2 title match, then OpenAlex (existence + citations)
    for k, p in papers.items():
        if p.get("arxiv_id"):
            continue
        q = urllib.parse.quote(re.sub(r"[^\w\s]", " ", p["title"])[:200])
        rec = http_json("https://api.semanticscholar.org/graph/v1/paper/search/match"
                        f"?query={q}&fields={S2_FIELDS}")
        data = (rec or {}).get("data") or []
        if data and sim(p["title"], data[0]["title"]) >= 0.75:
            if UPDATE and data[0].get("citationCount") is not None:
                papers[k]["citations"] = data[0]["citationCount"]
            time.sleep(1.2)
            continue
        title, cites = openalex_match(p["title"])
        if title:
            if UPDATE and cites is not None:
                papers[k]["citations"] = cites
        elif (p.get("url") or "").startswith("http"):
            source_only.append(k)
        else:
            failures.append((k, "no S2 / OpenAlex match and no landing URL"))
        time.sleep(1.2)

    if UPDATE:
        with open(DATA, "w") as handle:
            json.dump(papers, handle, indent=1, ensure_ascii=False)
            handle.write("\n")
        with open(META) as handle:
            metadata = json.load(handle)
        metadata["citations_as_of"] = date.today().isoformat()
        with open(META, "w") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        print("citations refreshed")

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
