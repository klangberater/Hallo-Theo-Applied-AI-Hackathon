"""L1 wiki tool — BM25 over the German policy + procedure markdown files.

Tiny scale (~6 files), so we tokenize on first call and cache in memory.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi


WIKI_ROOT = Path(__file__).resolve().parent.parent.parent / "domain_wiki"


def _tokenize(text: str) -> list[str]:
    # Lowercase + split on non-alphanumeric. Good enough for short German docs.
    return [t for t in re.split(r"[^\w]+", text.lower()) if t]


@lru_cache(maxsize=1)
def _build_index() -> tuple[list[Path], BM25Okapi]:
    paths = sorted(WIKI_ROOT.rglob("*.md"))
    docs = [p.read_text(encoding="utf-8") for p in paths]
    tokenized = [_tokenize(d) for d in docs]
    return paths, BM25Okapi(tokenized)


def search_wiki(query: str, k: int = 3) -> list[dict]:
    """Return top-k wiki snippets matching the query."""
    paths, bm25 = _build_index()
    if not paths:
        return []
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(paths, scores, strict=True), key=lambda x: x[1], reverse=True)
    out: list[dict] = []
    for path, score in ranked[:k]:
        if score <= 0:
            continue
        text = path.read_text(encoding="utf-8")
        # Snippet: first 400 chars after the first ## heading, or top of file.
        snippet = text[:600]
        out.append({
            "path": str(path.relative_to(WIKI_ROOT)),
            "score": float(score),
            "snippet": snippet,
        })
    return out


def read_wiki_page(path: str) -> str:
    """Read full text of a wiki page. `path` is relative to domain_wiki/."""
    full = WIKI_ROOT / path
    if not full.exists() or not full.is_file():
        raise FileNotFoundError(f"wiki page not found: {path}")
    # Block path traversal: must resolve inside WIKI_ROOT.
    try:
        full.resolve().relative_to(WIKI_ROOT.resolve())
    except ValueError as e:
        raise FileNotFoundError(f"wiki path outside root: {path}") from e
    return full.read_text(encoding="utf-8")
