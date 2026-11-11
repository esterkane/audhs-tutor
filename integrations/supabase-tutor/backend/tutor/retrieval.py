"""Retrieval behind the search_docs tool.

`Retriever` is the seam (ADR-001): the tutor depends only on the protocol, so a host app can plug in
a `QdrantRetriever` for its own corpus. `PgHybridRetriever` calls `tutor.hybrid_search` (RRF of
HNSW cosine + FTS, one row per distinct chunk text) on the local Supabase Postgres.
"""
from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import Protocol

import httpx
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.tutor.embedding_space import (
    NOMIC,
    OPENAI,
    RECORDED_SQL,
    checked_vectors,
    ollama_payload,
    resolve_model,
)
from backend.tutor.postgres_chrome import NAV_QUERY, PG17_PAGE, pure_manual_chrome
from backend.tutor.schemas import Chunk
from backend.tutor.sdk_scope import SdkScope, url_pattern

# search_docs exposes a fixed `products` enum (prompts/tools.md); the corpus stores the URL-derived
# product (scripts/ingest_llms.py: product_of). Each tool value expands to the stored values it covers.
# Unknown values pass through unchanged. Pages kept from llms-full.txt are stored as 'full' and only
# match unfiltered searches, because that file carries no per-page URL to derive a product from.
PRODUCT_ALIASES: dict[str, tuple[str, ...]] = {
    "kb": ("kb", "troubleshooting"),
    "database": ("database", "cron", "queues"),
    "platform": ("platform", "deployment", "hosting"),
    "observability": ("observability", "monitoring-and-debugging"),
    "ai": ("ai", "ai-tools"),
    "api": ("api", "graphql"),
    "other": ("other", "getting-started", "integrations", "resources"),
}

# hnsw.ef_search and hnsw.iterative_scan are pinned on tutor.hybrid_search itself
# (migration 20261021020000), so filtered searches keep their semantic hits for every caller.
RERANK_POOL = 30


class Embedder(Protocol):
    model: str

    async def embed_query(self, text: str) -> list[float]: ...


class Retriever(Protocol):
    async def search(self, query: str, k: int = 8, products: Sequence[str] | None = None, *, sdk_scope: SdkScope | None = None) -> list[Chunk]: ...


class Reranker(Protocol):
    async def rerank(self, query: str, chunks: list[Chunk], k: int) -> list[Chunk]: ...


async def _query_model(pool: AsyncConnectionPool | None, provider: str) -> str:
    recorded: list[str | None] = []
    if pool is not None:
        async with pool.connection() as conn:
            cursor = await conn.execute(RECORDED_SQL)
            recorded = [row[0] for row in await cursor.fetchall()]
    return resolve_model(provider, os.environ.get("EMBEDDINGS_MODEL"), recorded)


class OllamaEmbedder:
    """Use the local corpus model and its query-specific format."""

    model = NOMIC

    def __init__(self, base_url: str | None = None, client: httpx.AsyncClient | None = None, pool: AsyncConnectionPool | None = None) -> None:
        self.pool = pool
        self.url = (base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")) + "/api/embed"
        self.client = client or httpx.AsyncClient(timeout=60)

    async def embed_query(self, text: str) -> list[float]:
        self.model = await _query_model(self.pool, "ollama")
        r = await self.client.post(self.url, json=ollama_payload([text], self.model, query=True))
        r.raise_for_status()
        return checked_vectors(r.json()["embeddings"], 1)[0]


class OpenAIEmbedder:
    """text-embedding-3-small truncated to 768 dims so the column type never changes (ADR-003)."""

    model = OPENAI

    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None, pool: AsyncConnectionPool | None = None) -> None:
        self.pool = pool
        self.api_key = api_key or os.environ["OPENAI_API_KEY"]
        self.client = client or httpx.AsyncClient(timeout=60)

    async def embed_query(self, text: str) -> list[float]:
        await _query_model(self.pool, "openai")
        r = await self.client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "text-embedding-3-small", "input": [text], "dimensions": 768},
        )
        r.raise_for_status()
        return checked_vectors([entry["embedding"] for entry in r.json()["data"]], 1)[0]


def embedder_from_env(pool: AsyncConnectionPool | None = None) -> Embedder:
    provider = os.environ.get("EMBEDDINGS_PROVIDER", "ollama")
    if provider == "ollama":
        return OllamaEmbedder(pool=pool)
    if provider == "openai":
        return OpenAIEmbedder(pool=pool)
    raise ValueError(f"unknown EMBEDDINGS_PROVIDER {provider!r}")


def expand_products(products: Sequence[str] | None) -> list[str] | None:
    if not products:
        return None
    out: list[str] = []
    for p in products:
        for stored in PRODUCT_ALIASES.get(p, (p,)):
            if stored not in out:
                out.append(stored)
    return out


def sqlstate_codes(query: str) -> tuple[str, ...]:
    """Explicit SQLSTATE names/lists or a bare code, never unrelated row counts."""
    start = re.compile(r"\bSQLSTATE(?:\s+codes?)?\s*[:=]?\s*['\"\[]?([0-9a-z]{5})\b", re.I)
    follow = re.compile(r"^\s*['\"\]]?\s*(?:,|/|and\b|or\b|und\b|oder\b)\s*['\"\[]?([0-9a-z]{5})\b", re.I)
    found: list[str] = []
    bare = query.strip().upper()
    if re.fullmatch(r"[0-9A-Z]{5}", bare) and any(c.isdigit() for c in bare):
        found.append(bare)
    for match in start.finditer(query):
        code = match[1].upper()
        if not any(c.isdigit() for c in code):
            continue
        found.append(code)
        rest = query[match.end():]
        while (next_code := follow.match(rest)) is not None:
            code = next_code[1].upper()
            if not any(c.isdigit() for c in code):
                break
            found.append(code)
            rest = rest[next_code.end():]
    return tuple(dict.fromkeys(found))


def named_condition_codes(content: str, query: str) -> tuple[str, ...]:
    """Resolve comparison names from exact official rows, never a built-in answer table."""
    normalized = re.sub(r"[_-]+", " ", query.casefold())
    normalized = re.sub(r"\s+", " ", normalized)
    found: list[str] = []
    for line in content.splitlines():
        row = re.fullmatch(r"\|\s*([0-9A-Z]{5})\s*\|\s*([a-z][a-z0-9_]*)\s*\|", line, re.I)
        if row is None:
            continue
        words = row[2].casefold().split("_")
        pattern = r"\b" + r"\s+".join(re.escape(word) for word in words) + r"\b"
        # Natural wording may insert 'constraint' before the catalogue's 'violation'.
        if words[-1] == "violation" and len(words) > 1:
            pattern = pattern.replace(r"\s+violation", r"\s+(?:constraint\s+)?violation")
        if re.search(pattern, normalized):
            found.append(row[1].upper())
    return tuple(dict.fromkeys(found))


def sqlstate_excerpt(content: str, codes: tuple[str, ...]) -> str | None:
    """Quote exact reference rows/header/class, preserving real source identity."""
    labels = set(codes)
    classes = {code[:2] for code in codes}
    header: list[str] = []
    selected: list[str] = []
    for line in content.splitlines():
        if re.match(r"^\|\s*Error\s*Code\s*\|\s*Condition\s*Name\s*\|", line, re.I):
            header.append(line)
        row = re.fullmatch(r"\|\s*([0-9A-Z]{5})\s*\|\s*([a-z][a-z0-9_]*)\s*\|", line, re.I)
        category = re.match(r"^\|\s*Class\s*([0-9A-Z]{2})\b", line, re.I)
        if ((row and row[1].upper() in labels) or (category and category[1].upper() in classes)):
            selected.append(line)
    return "\n".join(header[:1] + selected) if selected else None



class PgHybridRetriever:
    """search_docs over tutor.hybrid_search. The pool must point at the local tutor database."""

    def __init__(self, pool: AsyncConnectionPool, embedder: Embedder, reranker: Reranker | None = None) -> None:
        self.pool = pool
        self.embedder = embedder
        self.reranker = reranker

    async def search(self, query: str, k: int = 8, products: Sequence[str] | None = None, *, sdk_scope: SdkScope | None = None) -> list[Chunk]:
        codes = sqlstate_codes(query)
        embedding = await self.embedder.embed_query(query)
        if sdk_scope is not None:
            return await self._sdk_matches(query, embedding, k, products, sdk_scope)
        hide_chrome = not NAV_QUERY.search(query)
        fetch_k = max(k, RERANK_POOL) if self.reranker else k
        async with self.pool.connection() as conn:
            cur = conn.cursor(row_factory=dict_row)
            await cur.execute(
                "select * from tutor.hybrid_search(%s, %s::extensions.vector, %s, %s)",
                (query, str(embedding), fetch_k, expand_products(products)),
            )
            chunks = [Chunk(**row) for row in await cur.fetchall()]
            if hide_chrome and any(pure_manual_chrome(hit.url, hit.content) for hit in chunks):
                manual_pages = list(dict.fromkeys(hit.url for hit in chunks if PG17_PAGE.fullmatch(hit.url)))
                # RRF already considers up to 60 lexical and 60 dense candidates. Read its
                # remaining candidates only when site navigation consumed a returned slot.
                await cur.execute(
                    "select * from tutor.hybrid_search(%s, %s::extensions.vector, %s, %s)",
                    (query, str(embedding), max(fetch_k, 120), expand_products(products)),
                )
                chunks = [Chunk(**row) for row in await cur.fetchall()
                          if not pure_manual_chrome(row["url"], row["content"])][:fetch_k]
                if len(chunks) < k and manual_pages:
                    # The entire lexical pool can be navigation when a query names a version.
                    # Search the bodies of the same ranked pages using the same query vector.
                    filters = expand_products(products)
                    await cur.execute(
                        "select c.id as chunk_id,s.url,c.anchor,c.heading_path,c.content,s.tier,s.fetched_at,"
                        "1.0/(1.0+(c.embedding <=> %s::extensions.vector)) as score "
                        "from tutor.docs_chunk c join tutor.docs_source s on s.id=c.source_id "
                        "where s.status='active' and s.url=any(%s) and c.embedding is not null "
                        "and (%s::text[] is null or c.meta->>'product'=any(%s::text[])) "
                        "order by c.embedding <=> %s::extensions.vector,c.id limit %s",
                        (str(embedding), manual_pages, filters, filters, str(embedding), 4 * k),
                    )
                    seen = {hit.chunk_id for hit in chunks}
                    for row in await cur.fetchall():
                        if row["chunk_id"] not in seen and not pure_manual_chrome(row["url"], row["content"]):
                            chunks.append(Chunk(**row))
                            if len(chunks) >= k:
                                break
            anchors: list[Chunk] = []

            if codes:
                filters = expand_products(products)
                await cur.execute(
                    "select c.content from tutor.docs_chunk c "
                    "join tutor.docs_source s on s.id=c.source_id where s.status='active' "
                    "and s.url='https://www.postgresql.org/docs/' || "
                    "(current_setting('server_version_num')::int / 10000)::text || '/errcodes-appendix.html' "
                    "and (%s::text[] is null or s.product=any(%s::text[])) "
                    "order by c.ord limit 256",
                    (filters, filters),
                )
                compared = [code for row in await cur.fetchall()
                            for code in named_condition_codes(row["content"], query)]
                codes = tuple(dict.fromkeys((*codes, *compared)))
                code_pattern = r"(?m)^\|[ \t]*(" + "|".join(codes) + r")[ \t]*\|"
                class_pattern = (r"(?m)^\|[ \t]*Class[ \t]*("
                                 + "|".join(dict.fromkeys(c[:2] for c in codes)) + r")\M")
                filters = expand_products(products)
                await cur.execute(
                    "select c.id as chunk_id, s.url, c.anchor, c.heading_path, c.content, "
                    "s.tier, s.fetched_at, 1.0::float8 as score from tutor.docs_chunk c "
                    "join tutor.docs_source s on s.id=c.source_id where s.status='active' "
                    "and s.url='https://www.postgresql.org/docs/' || "
                    "(current_setting('server_version_num')::int / 10000)::text || '/errcodes-appendix.html' "
                    "and (c.content ~ %s or c.content ~ %s) "
                    "and (%s::text[] is null or s.product=any(%s::text[])) "
                    "order by case when c.content ~ %s then 0 else 1 end, c.ord limit %s",
                    (code_pattern, class_pattern, filters, filters, code_pattern, fetch_k),
                )
                anchors = [Chunk(**row) for row in await cur.fetchall()]
                seen = set()
                kept: list[Chunk] = []
                for hit in [*anchors, *chunks]:
                    if hit.chunk_id in seen:
                        continue
                    seen.add(hit.chunk_id)
                    if re.fullmatch(r"https://www\.postgresql\.org/docs/[0-9]+/errcodes-appendix\.html", hit.url):
                        excerpt = sqlstate_excerpt(hit.content, codes)
                        if excerpt is None:
                            has_rows = any(re.fullmatch(
                                r"\|\s*([0-9A-Z]{5})\s*\|\s*([a-z][a-z0-9_]*)\s*\|", line, re.I
                            ) for line in hit.content.splitlines())
                            if has_rows:
                                continue  # Other codes' rows are not evidence for this identity.
                            # Keep general explanation and unknown formats rather than suppressing them.
                        else:
                            hit = hit.model_copy(update={"content": excerpt})
                    kept.append(hit)
                anchor_ids = {hit.chunk_id for hit in anchors}
                anchors = [hit for hit in kept if hit.chunk_id in anchor_ids][:k]
                chunks = [hit for hit in kept if hit.chunk_id not in anchor_ids]
            elif (k > 1 and (not products or "database" in products)
                  and re.search(r"\b(?:postgres(?:ql)?|security[\s_-]+definer|row[\s_-]+level[\s_-]+security|RLS)\b", query, re.I)):
                # Framework documentation can omit or overstate engine exceptions. Reserve
                # evidence from the version-matched engine manual, keeping framework context.
                filters = expand_products(products)
                await cur.execute(
                    "select chunk_id, url, anchor, heading_path, content, tier, fetched_at, score from ("
                    "select c.id as chunk_id, s.url, c.anchor, c.heading_path, c.content, s.tier, s.fetched_at, "
                    "1.0/(1.0+(c.embedding <=> %s::extensions.vector)) as score, "
                    "row_number() over(partition by s.url order by c.embedding <=> %s::extensions.vector) as page_rank "
                    "from tutor.docs_chunk c join tutor.docs_source s on s.id=c.source_id "
                    "where s.status='active' and c.embedding is not null "
                    "and s.url like 'https://www.postgresql.org/docs/' || "
                    "(current_setting('server_version_num')::int / 10000)::text || '/%%' "
                    "and (%s::text[] is null or s.product=any(%s::text[]))) ranked "
                    "where page_rank=1 order by score desc limit %s",
                    (str(embedding), str(embedding), filters, filters, min(2, k - 1)),
                )
                anchors = [Chunk(**row) for row in await cur.fetchall()]
                anchor_ids = {hit.chunk_id for hit in anchors}
                chunks = [hit for hit in chunks if hit.chunk_id not in anchor_ids]
            operators = [op for op in ("<->", "<=>", "<#>") if op in query]
            if (operators and len(anchors) < k
                    and re.search(r"\b(?:pgvector|vectors?|embeddings?|vektoren?)\b", query, re.IGNORECASE)):
                # Punctuation is poorly represented by lexical search. Reserve actual indexed
                # operator references without expanding product scope or synthesizing facts.
                filters = expand_products(products)
                patterns = [f"%{operator}%" for operator in operators]
                await cur.execute(
                    "select c.id as chunk_id, s.url, c.anchor, c.heading_path, c.content, "
                    "s.tier, s.fetched_at, 1.0::float8 as score from tutor.docs_chunk c "
                    "join tutor.docs_source s on s.id=c.source_id where s.status='active' "
                    "and s.url=any(%s::text[]) and c.content like any(%s::text[]) "
                    "and (%s::text[] is null or s.product=any(%s::text[])) "
                    "order by (select count(*) from unnest(%s::text[]) as terms(term) "
                    "where c.content like term) desc, s.url, c.ord limit %s",
                    (["https://supabase.com/docs/guides/ai/vector-columns.md",
                      "https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes.md",
                      "https://supabase.com/docs/guides/database/extensions/pgvector.md"],
                     patterns, filters, filters, patterns, min(2, k - len(anchors))),
                )
                existing = {hit.chunk_id for hit in anchors}
                anchors.extend(Chunk(**row) for row in await cur.fetchall() if row["chunk_id"] not in existing)
                anchor_ids = {hit.chunk_id for hit in anchors}
                chunks = [hit for hit in chunks if hit.chunk_id not in anchor_ids]
        if hide_chrome:
            anchors = [hit for hit in anchors if not pure_manual_chrome(hit.url, hit.content)]
        remaining = max(0, k - len(anchors))
        if self.reranker and remaining:
            chunks = await self.reranker.rerank(query, chunks, remaining)
        return anchors + chunks[:remaining]

    async def _sdk_matches(
        self, query: str, embedding: list[float], k: int, products: Sequence[str] | None, scope: SdkScope
    ) -> list[Chunk]:
        """Scope both retrieval signals before ranking; keep evidence for each compared edition."""
        pools = []
        async with self.pool.connection() as conn:
            cur = conn.cursor(row_factory=dict_row)
            for edition in scope.editions or (None,):
                await cur.execute(SDK_SEARCH_SQL, (
                    url_pattern(scope, edition), expand_products(products), expand_products(products),
                    str(embedding), query, query, max(k, RERANK_POOL) if self.reranker else k,
                ))
                hits = [Chunk(**row) for row in await cur.fetchall()]
                if self.reranker and hits:
                    hits = await self.reranker.rerank(query, hits, k)
                pools.append(hits)
        return [hits[i] for i in range(k) for hits in pools if i < len(hits)][:k]


SDK_SEARCH_SQL = """
with scoped as materialized (
    select c.id, c.anchor, c.heading_path, c.content, c.content_hash, c.fts, c.embedding,
           s.url, s.tier, s.fetched_at
    from tutor.docs_source s join tutor.docs_chunk c on c.source_id=s.id
    where s.status='active' and s.url ~ %s and (%s::text[] is null or c.meta->>'product'=any(%s))
), dense as (
    select id, row_number() over(order by embedding operator(extensions.<=>) %s::extensions.vector, id) pos
    from scoped where embedding is not null order by pos limit 60
), lexical as (
    select id, row_number() over(order by ts_rank_cd(fts,websearch_to_tsquery('english', %s)) desc, id) pos
    from scoped where fts @@ websearch_to_tsquery('english', %s) order by pos limit 60
), scored as (
    select s.*, coalesce(1.0/(60+d.pos),0)+coalesce(1.0/(60+l.pos),0) score
    from scoped s left join dense d using(id) left join lexical l using(id)
    where d.pos is not null or l.pos is not null
), unique_passages as (
    select distinct on (url,content_hash) * from scored order by url,content_hash,score desc,id
)
select id as chunk_id,url,anchor,heading_path,content,tier,fetched_at,score::double precision
from unique_passages order by score desc,id limit %s
"""