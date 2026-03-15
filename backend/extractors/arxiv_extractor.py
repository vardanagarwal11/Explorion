"""
arXiv content extractor for the local pipeline.

Extracts title + abstract from an arXiv paper URL or ID.
Relies on the `arxiv` SDK which is already in requirements.txt.
"""

import logging
import re

import arxiv

logger = logging.getLogger(__name__)

# Accepts full URLs like https://arxiv.org/abs/1706.03762 or bare IDs
_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+/\d{7}(?:v\d+)?)$", re.IGNORECASE)


def _parse_id(url_or_id: str) -> str:
    """Return the bare arXiv ID from a URL or ID string."""
    # Strip query params / fragments
    url_or_id = url_or_id.split("?")[0].split("#")[0].rstrip("/")
    m = _ID_RE.search(url_or_id)
    if m:
        # Strip version suffix (v1, v2 …) for canonical lookup
        return re.sub(r"v\d+$", "", m.group(1))
    return url_or_id  # Return as-is; let arxiv SDK validate


def extract_arxiv(url_or_id: str) -> dict:
    """
    Fetch an arXiv paper and return a dict with its key fields.

    Args:
        url_or_id: Full arXiv URL or bare paper ID (e.g. "1706.03762")

    Returns:
        {
            "id":       <str>,
            "title":    <str>,
            "abstract": <str>,
            "authors":  [<str>, ...],
            "content":  <title> + "\n\n" + <abstract>
        }

    Raises:
        ValueError: if no paper is found for the given ID.
    """
    paper_id = _parse_id(url_or_id)
    logger.info("Fetching arXiv paper: %s", paper_id)

    client = arxiv.Client()
    search = arxiv.Search(id_list=[paper_id])
    results = list(client.results(search))

    if not results:
        raise ValueError(f"No arXiv paper found for id: {paper_id!r}")

    paper = results[0]
    content = paper.title + "\n\n" + paper.summary

    return {
        "id": paper_id,
        "title": paper.title,
        "abstract": paper.summary,
        "authors": [str(a) for a in paper.authors],
        "content": content,
    }
