#!/usr/bin/env python3
"""Render README.md exactly as GitHub would, into a local HTML file.

    python scripts/preview_readme.py        # writes preview_local.html (gitignored)

Uses GitHub's public Markdown API, so the result matches the rendered
repository page (tables, <details> blocks, emoji, heading anchors).
Set GITHUB_TOKEN (e.g. `export GITHUB_TOKEN=$(gh auth token)`) to lift the
60-requests-per-hour anonymous rate limit.
"""
import json
import os
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = "https://cdn.jsdelivr.net/npm/github-markdown-css@5.9.0/github-markdown.css"
OUT = os.path.join(ROOT, "preview_local.html")

PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — local preview</title>
<link rel="stylesheet" href="{css}">
<style>
  body {{ margin: 0; background: #fff; }}
  .markdown-body {{ box-sizing: border-box; max-width: 1012px;
                    margin: 0 auto; padding: 32px 16px 64px; }}
</style></head>
<body><article class="markdown-body">{body}</article></body></html>
"""


def main():
    md = open(os.path.join(ROOT, "README.md")).read()
    headers = {"Content-Type": "application/json",
               "Accept": "application/vnd.github+json",
               "User-Agent": "awesome-ai4ai-preview"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/markdown",
        data=json.dumps({"text": md, "mode": "gfm"}).encode(),
        headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode()
        renderer = "GitHub API"
    except urllib.error.HTTPError as error:
        if error.code != 403:
            raise
        try:
            import markdown
        except ImportError as import_error:
            raise SystemExit(
                "GitHub Markdown API rate-limited the preview. Set GITHUB_TOKEN "
                "or install the optional 'markdown' package."
            ) from import_error
        body = markdown.markdown(
            md, extensions=["extra", "sane_lists"], output_format="html5"
        )
        renderer = "local Python-Markdown fallback"
    with open(OUT, "w") as f:
        f.write(PAGE.format(title="Awesome AI4AI", css=CSS, body=body))
    print(f"wrote {OUT} via {renderer}")


if __name__ == "__main__":
    main()
