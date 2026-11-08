"""Regression checks for citation provenance and partial-refresh bookkeeping."""
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch


class RefreshDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 8)


class VerifyPapersTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "verify_papers.py"
        spec = importlib.util.spec_from_file_location("verifier_under_test", path)
        self.v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.v)

    def test_doi_match_with_wrong_title_is_rejected(self):
        self.v.http_json = Mock(return_value={"results": [
            {"ids": {"doi": "https://doi.org/10.48550/arxiv.2501.00001"},
             "display_name": "Correct Agent Benchmark", "cited_by_count": 3},
            {"ids": {"doi": "https://doi.org/10.48550/arxiv.2501.00002"},
             "display_name": "Unrelated Atomic Collider Results", "cited_by_count": 999},
        ]})
        with patch.object(self.v.time, "sleep"):
            counts = self.v.openalex_batch({
                "2501.00001": "Correct Agent Benchmark",
                "2501.00002": "Another Agent Benchmark",
            })
        self.assertEqual(counts, {"2501.00001": 3})

    def test_rate_limit_stops_only_the_affected_service(self):
        limited = "https://api.semanticscholar.org/graph/v1/paper/batch"
        error = urllib.error.HTTPError(limited, 429, "Too Many Requests", {}, None)
        with patch.object(self.v.urllib.request, "urlopen", side_effect=[
            error, io.BytesIO(b'{"ok": true}')
        ]) as request, patch.object(self.v.time, "sleep") as sleep:
            self.assertIsNone(self.v.http_json(limited))
            self.assertIsNone(self.v.http_json(limited + "?fields=title"))
            self.assertEqual(self.v.http_json("https://api.openalex.org/works"), {"ok": True})
        self.assertEqual(request.call_count, 2)
        sleep.assert_not_called()

    def refresh_fixture(self, *, complete=False, github_available=True):
        v = self.v
        papers = {}
        for key, title, ident, citations in [
            ("a", "Correct Agent Benchmark", "2501.00001", 10),
            ("b", "Another Agent Benchmark", "2501.00002", None),
            ("c", "Recovered Tool Agent", "2501.00003", None),
            ("d", "Source Only Study", None, 17),
        ]:
            papers[key] = {
                "title": title, "venue": "arXiv" if ident else "Report",
                "date": "2025-01" if ident else "2025", "arxiv_id": ident,
                "url": "https://arxiv.org/abs/" + ident if ident else "https://example.org/study",
                "citations": citations, "code": None,
                "sections": ["targets/harness"], "collections": ["harness-design"],
            }
        for key in ["a", "b"]:
            papers[key].update(code="https://github.com/owner/shared", github_stars=5)

        def arxiv_batch(ids):
            return {p["arxiv_id"]: p["title"] for p in papers.values() if p["arxiv_id"]}

        arxiv_batch.incomplete = False
        arxiv_batch.first_dates = {}
        v.arxiv_batch = arxiv_batch
        v.openalex_batch = Mock(return_value={
            "2501.00001": 3, **({"2501.00002": 20} if complete else {})
        })
        # A successful S2 response containing nulls must still leave coverage gaps.
        v.http_json = Mock(return_value=[None] * len(papers))
        v.openalex_match = lambda title: (
            (title, 0) if title == "Recovered Tool Agent"
            else (title, 17) if complete and title == "Source Only Study"
            else (None, None)
        )
        v.github_repo = Mock(return_value=(
            {"html_url": "https://github.com/owner/shared", "stargazers_count": 42}
            if github_available else None
        ))
        v.UPDATE, v.OFFLINE = True, False
        v.date = RefreshDate
        with tempfile.TemporaryDirectory() as directory:
            v.DATA = str(Path(directory) / "papers.json")
            v.META = str(Path(directory) / "catalog_meta.json")
            Path(v.DATA).write_text(json.dumps(papers))
            Path(v.META).write_text(json.dumps({
                "citations_as_of": "2026-10-17", "github_stars_as_of": "2026-11-03"
            }))
            with patch.object(v.time, "sleep"), patch("sys.stdout", new=io.StringIO()), \
                    patch("sys.stderr", new=io.StringIO()):
                if github_available:
                    v.main()
                else:
                    with self.assertRaises(SystemExit) as stopped:
                        v.main()
                    self.assertEqual(stopped.exception.code, 1)
            result = json.loads(Path(v.DATA).read_text())
            metadata = json.loads(Path(v.META).read_text())
        v.github_repo.assert_called_once()
        return result, metadata

    def test_partial_refresh_preserves_known_counts_and_unknowns(self):
        papers, meta = self.refresh_fixture()
        self.assertEqual(papers["a"]["citations"], 10)
        self.assertIsNone(papers["b"]["citations"])
        self.assertEqual(papers["c"]["citations"], 0)
        self.assertEqual(papers["d"]["citations"], 17)
        self.assertEqual(meta["citations_as_of"], "2026-10-17")
        self.assertEqual(meta["github_stars_as_of"], "2026-11-08")
        self.assertEqual(meta["metrics_refresh"]["citation_records_verified"], 2)
        self.assertEqual(meta["metrics_refresh"]["citation_records_retained"], ["d"])
        self.assertEqual(meta["metrics_refresh"]["citation_records_unindexed"], ["b"])

    def test_complete_refresh_advances_date_including_verified_zero(self):
        papers, meta = self.refresh_fixture(complete=True)
        self.assertEqual(papers["c"]["citations"], 0)
        self.assertEqual(meta["citations_as_of"], "2026-11-08")
        self.assertEqual(meta["metrics_refresh"]["citation_records_verified"], 4)

    def test_unavailable_github_retains_star_count_and_snapshot_date(self):
        papers, meta = self.refresh_fixture(github_available=False)
        self.assertEqual(papers["a"]["github_stars"], 5)
        self.assertEqual(meta["github_stars_as_of"], "2026-11-03")
        self.assertEqual(meta["metrics_refresh"]["github_repositories_unavailable"], ["owner/shared"])


if __name__ == "__main__":
    unittest.main()
