"""L1 wiki tool — BM25 over markdown files in domain_wiki/.

search_wiki(query: str) -> list[WikiSnippet]
read_wiki_page(path: str) -> str

Uses rank-bm25 over the ~6 markdown files. No embeddings (overkill for this scale).

Owner: Lead 2. PRODUCT_SPEC §5.2 + §6.4.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
