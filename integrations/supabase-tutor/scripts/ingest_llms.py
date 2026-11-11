#!/usr/bin/env python3
"""Ingest the official Supabase docs corpus from https://supabase.com/llms.txt.

Fetches the index, selects sources by profile, chunks Markdown by headings, embeds
(Ollama nomic-embed-text or OpenAI text-embedding-3-small @768d) and upserts into
tutor.docs_source / tutor.docs_chunk. Idempotent: unchanged documents (by content hash)
are skipped.

Usage:
  uv run python scripts/ingest_llms.py --dry-run
  python scripts/ingest_llms.py --only llms/cli.txt
  python scripts/ingest_llms.py --profile all --corpus-version 2

Env: SUPABASE_DB_URL (postgres superuser or service connection), EMBEDDINGS_PROVIDER
(ollama|openai), EMBEDDINGS_MODEL (optional), OLLAMA_URL, OPENAI_API_KEY.
Refreshes reuse the active corpus model. For a new local corpus, select qwen3-embedding:0.6b
or use the legacy nomic-embed-text default. To migrate, build a separate corpus with the chosen
model, verify document/query retrieval, then switch consumers to the verified corpus.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from db import admin_url
from reference_html import REFERENCE_URL, CanonicalMethod, reference_markdown

# Support execution both as a script and from an editable vendor installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.tutor.embedding_space import (
    OPENAI,
    RECORDED_SQL,
    checked_vectors,
    ollama_payload,
    resolve_model,
)

INDEX_DEFAULT = "https://supabase.com/llms.txt"
UA = "kaenguru-tutor-ingest/0.1 (+local dev)"
SUPPORT_SKIP = re.compile(r"/llms/(dart|swift|kotlin|csharp)\.txt$")
TARGET_TOKENS, MAX_TOKENS, OVERLAP_PARAS = 600, 900, 1
DIM = 768
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "corpus"  # gitignored raw copies


@dataclass
class Doc:
    url: str
    tier: int
    product: str
    text: str = ""
    hash: str = ""
    etag: str | None = None
    status: str = "active"
    chunks: list[Chunk] = field(default_factory=list)


@dataclass
class Chunk:
    ord: int
    heading_path: str
    anchor: str | None
    content: str
    meta: dict
    embedding: list[float] | None = None

    @property
    def hash(self) -> str:
        return hashlib.sha256(" ".join(self.content.split()).encode()).hexdigest()


# ----------------------------------------------------------------------------- index
def product_of(url: str) -> str:
    p = urlparse(url).path
    if REFERENCE_URL.fullmatch(url):
        return "platform" if p.startswith("/docs/reference/api/") else "api"
    if p.startswith("/llms/"):
        name = p.split("/")[-1].replace(".txt", "")
        return {"js": "api", "server": "api", "api": "platform", "python": "api",
                "dart": "api", "swift": "api", "kotlin": "api", "csharp": "api"}.get(name, name)
    if "/docs/guides/" in p:
        return p.split("/docs/guides/")[1].split("/")[0].replace(".md", "")
    if p.startswith("/pricing"):
        return "pricing"
    if p.startswith("/kb"):
        return "kb"
    if p == "/llms-full.txt":
        return "full"
    return "other"


def parse_index(text: str, base: str) -> list[tuple[str, int]]:
    """Return (url, tier) for every link in llms.txt, including llms-full.txt from the intro."""
    urls = re.findall(r"https?://[^\s)\]]+", text)
    seen, out = set(), []
    for u in urls:
        u = urljoin(base, u.rstrip(".,"))
        if u in seen or "mcp.supabase.com" in u or u.endswith("openapi.json"):
            continue
        seen.add(u)
        out.append((u, 1))
    return out


GUIDE_LINK = re.compile(r"https://supabase\.com/docs/guides/[A-Za-z0-9/_\-.]+")
KB_LINK = re.compile(r"https://supabase\.com/kb/[A-Za-z0-9/_\-.]+")


def canonical_md(url: str) -> str | None:
    """Docs/KB page URL → its Markdown twin (`.../page.md`); None for assets like `.png`."""
    path = urlparse(url).path.rstrip("/")
    last = path.rsplit("/", 1)[-1]
    if last.endswith(".md"):
        return f"https://supabase.com{path}"
    if "." in last:
        return None
    return f"https://supabase.com{path}.md"


def discover(docs: list[Doc]) -> list[str]:
    """Depth-1 expansion: guide pages linked from the seed docs, KB pages linked from the KB sitemap."""
    found: list[str] = []
    for d in docs:
        if d.status == "failed":
            continue
        seed_sdk = {
            "/llms/js.txt": "javascript", "/llms/python.txt": "python",
            "/llms/dart.txt": "dart", "/llms/swift.txt": "swift",
            "/llms/kotlin.txt": "kotlin", "/llms/csharp.txt": "csharp",
        }.get(urlparse(d.url).path)
        if seed_sdk and urlparse(d.url).netloc == "supabase.com":
            for link in re.findall(r"https://supabase\.com/docs/reference/[^\s<>\[\]()\x22\x27]+", d.text):
                method_url = link.split("#", 1)[0].rstrip("/.,")
                if (REFERENCE_URL.fullmatch(method_url) and
                        f"/reference/{seed_sdk}/" in method_url and method_url not in found):
                    found.append(method_url)
        links = GUIDE_LINK.findall(d.text)
        if urlparse(d.url).path.startswith("/kb/"):
            links += KB_LINK.findall(d.text)
        for link in links:
            url = canonical_md(link)
            if url and url not in found:
                found.append(url)
    # KB troubleshooting articles are mirrored under docs/guides/troubleshooting; the KB rendering
    # rewrites relative links to broken /kb/... URLs, so the docs copy is the one to cite.
    docs_ts = {u.rsplit("/", 1)[-1] for u in found if "/docs/guides/troubleshooting/" in u}
    return [u for u in found if not ("/kb/troubleshooting/" in u and u.rsplit("/", 1)[-1] in docs_ts)]


def split_pages(text: str) -> list[str]:
    """Split llms-full.txt on `---` lines that are followed by a page title (`# ...`).

    Fence tracking is not reliable across 7 MB of mixed Markdown, so a separator is recognised by
    what follows it; a `---` inside YAML or a table is not followed by an H1.
    """
    lines = text.splitlines()
    pages: list[str] = []
    cur: list[str] = []
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            nxt = next((x for x in lines[i + 1 : i + 6] if x.strip()), "")
            if nxt.startswith("# "):
                pages.append("\n".join(cur))
                cur = []
                continue
        cur.append(ln)
    pages.append("\n".join(cur))
    return [p for p in pages if p.strip()]


def page_title(text: str) -> str | None:
    m = re.search(r"^# (.+)$", text, re.MULTILINE)
    return m.group(1).strip().lower() if m else None


def drop_duplicate_pages(full_text: str, titles: set[str]) -> tuple[str, int]:
    """Remove llms-full pages whose H1 matches a page ingested under its own URL (better citation)."""
    kept, dropped = [], 0
    for page in split_pages(full_text):
        if page_title(page) in titles:
            dropped += 1
        else:
            kept.append(page)
    return "\n\n".join(kept), dropped


def select(urls: list[tuple[str, int]], profile: str, only: str | None) -> list[tuple[str, int]]:
    sel = []
    for u, t in urls:
        if only and only not in u:
            continue
        if profile == "support" and SUPPORT_SKIP.search(u):
            continue
        sel.append((u, t))
    return sel


# ----------------------------------------------------------------------------- fetch
async def fetch(client: httpx.AsyncClient, doc: Doc, sem: asyncio.Semaphore, *, raw_dir: Path | None = None) -> Doc:
    async with sem:
        try:
            # Supabase serves its agent-friendly reference HTML to identifiable HTTP clients.
            agent = f"python-httpx/{httpx.__version__} {UA}" if REFERENCE_URL.fullmatch(doc.url) else UA
            r = await client.get(doc.url, headers={"User-Agent": agent}, timeout=30, follow_redirects=True)
            await asyncio.sleep(0.2)
            if r.status_code != 200 or not r.text.strip():
                doc.status = "failed"
                return doc
            if REFERENCE_URL.fullmatch(doc.url):
                final_url = str(r.url).rstrip("/")
                if (not REFERENCE_URL.fullmatch(final_url) or
                        final_url.rsplit("/", 1)[0] != doc.url.rstrip("/").rsplit("/", 1)[0]):
                    doc.status = "failed"
                    return doc
                try:
                    try:
                        doc.text = reference_markdown(r.text, doc.url)
                    except CanonicalMethod as alias:
                        target = str(alias)
                        r = await client.get(target, headers={"User-Agent": agent}, timeout=30)
                        r.raise_for_status()
                        if str(r.url).rstrip("/") != target:
                            raise ValueError("Canonical SDK reference redirected")
                        doc.text = reference_markdown(r.text, target)
                        doc.url = target
                except ValueError:
                    doc.status = "failed"
                    return doc
                content = doc.text.encode()
            else:
                doc.text = r.text
                content = r.content
            doc.etag = r.headers.get("etag")
            doc.hash = hashlib.sha256(content).hexdigest()
            directory = RAW_DIR if raw_dir is None else raw_dir
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{doc.hash}.md").write_bytes(content)
        except httpx.HTTPError:
            doc.status = "failed"
    return doc


# ----------------------------------------------------------------------------- chunk
def canonical_documents(docs: list[Doc]) -> list[Doc]:
    """Process each successful canonical URL once; keep failures for coverage reporting."""
    seen: set[str] = set()
    unique = []
    for doc in docs:
        if doc.status != "failed":
            if doc.url in seen:
                continue
            seen.add(doc.url)
        unique.append(doc)
    return unique


def slug(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-")


def approx_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def chunk_markdown(text: str, product: str, source_file: str) -> list[Chunk]:
    """Split on H1–H3, keep code fences/tables intact, pack sections to TARGET..MAX tokens."""
    lines = text.splitlines()
    sections: list[tuple[list[str], str]] = []  # (heading stack, body)
    stack: list[str] = []
    body: list[str] = []
    in_fence = False
    for ln in lines:
        if ln.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else re.match(r"^(#{1,3})\s+(.*)", ln)
        if m:
            if body and "".join(body).strip():
                sections.append((stack.copy(), "\n".join(body)))
            level = len(m.group(1))
            stack = stack[: level - 1] + [m.group(2).strip()]
            body = []
        else:
            body.append(ln)
    if body and "".join(body).strip():
        sections.append((stack.copy(), "\n".join(body)))

    # Rendered reference headings do not reliably define HTML fragment IDs.
    synthesize_anchors = not urlparse(source_file).path.startswith("/docs/reference/")
    chunks: list[Chunk] = []
    for hs, b in sections:
        paras = [p for p in re.split(r"\n{2,}", b) if p.strip()]
        cur: list[str] = []
        carry: list[str] = []

        def flush():
            nonlocal cur, carry
            if not cur:
                return
            content = "\n\n".join(carry + cur).strip()
            chunks.append(
                Chunk(
                    ord=len(chunks),
                    heading_path=" > ".join(hs),  # noqa: B023 - flush() runs inside the loop
                    anchor=slug(hs[-1]) if hs and synthesize_anchors else None,  # noqa: B023
                    content=content,
                    meta={
                        "product": product,
                        "source_file": source_file,
                        "has_code": "```" in content,
                    },
                )
            )
            carry = cur[-OVERLAP_PARAS:]
            cur = []

        for p in paras:
            if cur and approx_tokens("\n\n".join(cur + [p])) > MAX_TOKENS:
                flush()
            cur.append(p)
            if approx_tokens("\n\n".join(cur)) >= TARGET_TOKENS and not p.lstrip().startswith("```"):
                flush()
        flush()
    return chunks


# ----------------------------------------------------------------------------- embed
async def embed(texts: list[str], provider: str, client: httpx.AsyncClient, model: str) -> list[list[float]]:
    if provider == "ollama":
        url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/embed"
        r = await client.post(url, json=ollama_payload(texts, model, query=False), timeout=120)
        r.raise_for_status()
        return checked_vectors(r.json()["embeddings"], len(texts))
    if provider == "openai":
        r = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": "text-embedding-3-small", "input": texts, "dimensions": DIM},
            timeout=120,
        )
        r.raise_for_status()
        return checked_vectors([d["embedding"] for d in r.json()["data"]], len(texts))
    raise SystemExit(f"unknown EMBEDDINGS_PROVIDER {provider}")


# ----------------------------------------------------------------------------- db
def upsert(doc: Doc, model: str, corpus_version: int) -> int:
    import psycopg  # local import so --dry-run works without a DB driver

    with psycopg.connect(admin_url()) as conn, conn.transaction():
        with conn.cursor() as cur:
            # Serialize the space check with source writes, including initial concurrent refreshes.
            cur.execute("lock table tutor.docs_source in share row exclusive mode")
            cur.execute(RECORDED_SQL)
            provider = "openai" if model == OPENAI else "ollama"
            resolve_model(provider, model, (row[0] for row in cur.fetchall()))
            cur.execute(
                """
                insert into tutor.docs_source (url, tier, product, content_hash, etag, embedding_model, corpus_version, status, fetched_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, now())
                on conflict (url) do update set
                  content_hash = excluded.content_hash, etag = excluded.etag,
                  embedding_model = excluded.embedding_model, corpus_version = excluded.corpus_version,
                  status = excluded.status, fetched_at = now()
                returning id
                """,
                (doc.url, doc.tier, doc.product, doc.hash, doc.etag, model, corpus_version, doc.status),
            )
            row = cur.fetchone()
            assert row is not None
            sid = row[0]
            cur.execute("delete from tutor.docs_chunk where source_id = %s and ord >= %s", (sid, len(doc.chunks)))
            for c in doc.chunks:
                cur.execute(
                    """
                    insert into tutor.docs_chunk (source_id, ord, heading_path, anchor, content, content_hash, meta, embedding)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (source_id, ord) do update set
                      heading_path = excluded.heading_path, anchor = excluded.anchor, content = excluded.content,
                      content_hash = excluded.content_hash, meta = excluded.meta, embedding = excluded.embedding
                    """,
                    (sid, c.ord, c.heading_path, c.anchor, c.content, c.hash, json.dumps(c.meta), str(c.embedding)),
                )
        with conn.cursor() as cur:
            cur.execute("analyze tutor.docs_chunk")
    return len(doc.chunks)


def existing_hashes() -> dict[str, tuple[str, int, str | None]]:
    import psycopg

    with psycopg.connect(admin_url()) as conn, conn.cursor() as cur:
        cur.execute("select url, content_hash, corpus_version, embedding_model from tutor.docs_source where status = 'active'")
        return {u: (h, v, m) for u, h, v, m in cur.fetchall()}


def retire_missing(urls: list[str], index_url: str = INDEX_DEFAULT) -> int:
    """Retire absent sources only on this index's origin, preserving separate references."""
    if not urls:
        return 0  # An empty/failed index is not evidence that every document disappeared.
    origin = urlparse(index_url)
    if origin.scheme not in {"http", "https"} or not origin.hostname or origin.username or origin.password:
        raise ValueError("Reference index must have a credential-free HTTP origin")
    prefix = f"{origin.scheme}://{origin.netloc}/"
    import psycopg

    with psycopg.connect(admin_url()) as conn:
        cur = conn.execute(
            "update tutor.docs_source set status = 'retired' where status = 'active' "
            "and starts_with(url, %s) and url <> all(%s)", (prefix, urls)
        )
        return cur.rowcount


# ----------------------------------------------------------------------------- main
async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", default=INDEX_DEFAULT, help="llms.txt index URL")
    ap.add_argument("--profile", choices=["support", "all"], default="support",
                    help="support skips the dart/swift/kotlin/csharp references")
    ap.add_argument("--dry-run", action="store_true", help="fetch + chunk + print stats, no embeddings, no DB")
    ap.add_argument("--only", help="ingest only index entries whose URL contains this substring")
    ap.add_argument("--corpus-version", type=int, default=1, help="bump to force re-embedding everything")
    ap.add_argument("--limit", type=int, help="first N index entries (for tests)")
    ap.add_argument("--no-expand", action="store_true",
                    help="skip depth-1 expansion to linked guide pages and KB articles")
    ap.add_argument("--verbose", action="store_true", help="print one row per source, not only the summary")
    a = ap.parse_args()

    provider = os.environ.get("EMBEDDINGS_PROVIDER", "ollama")
    known = {} if a.dry_run else existing_hashes()
    model = resolve_model(provider, os.environ.get("EMBEDDINGS_MODEL"), (record[2] for record in known.values()))
    # A support profile deliberately omits SDK sources; absence is not removal.
    partial = bool(a.only or a.limit or a.no_expand or a.profile != "all")

    async with httpx.AsyncClient() as client:
        try:
            idx = await client.get(a.index, headers={"User-Agent": UA}, timeout=30)
            idx.raise_for_status()
        except httpx.HTTPError as e:
            print(f"cannot fetch index {a.index}: {e}", file=sys.stderr)
            return 2
        targets = select(parse_index(idx.text, a.index), a.profile, a.only)
        if a.limit:
            targets = targets[: a.limit]
        if not targets:
            print("Reference index or selection contains no document URLs; coverage could not be verified.", file=sys.stderr)
            return 2
        sem = asyncio.Semaphore(4)
        seeds = [Doc(url=u, tier=t, product=product_of(u)) for u, t in targets]
        seeds = list(await asyncio.gather(*(fetch(client, d, sem) for d in seeds)))

        expanded: list[Doc] = []
        if not a.no_expand:
            seed_urls = {d.url for d in seeds}
            extra = [u for u in discover(seeds) if u not in seed_urls]
            expanded = [Doc(url=u, tier=1, product=product_of(u)) for u in extra]
            expanded = list(await asyncio.gather(*(fetch(client, d, sem) for d in expanded)))

        docs = canonical_documents([d for d in seeds + expanded if d.product != "full"])
        full_docs = [d for d in seeds if d.product == "full"]
        # Pages fetched under their own URL are the canonical citation; drop their llms-full copies.
        titles = {t for d in docs if d.status != "failed" and (t := page_title(d.text))}
        for d in full_docs:
            if d.status != "failed":
                d.text, dropped = drop_duplicate_pages(d.text, titles)
                # What is kept depends on the other pages too, so "unchanged" must compare the kept text.
                d.hash = hashlib.sha256(d.text.encode()).hexdigest()
                print(f"llms-full.txt: dropped {dropped} pages already ingested under their own URL")

        rows: list[tuple[str, str, int, str]] = []
        seed_failed = expand_failed = 0
        for d in docs + full_docs:
            if d.status == "failed":
                if d in seeds:
                    seed_failed += 1
                else:
                    expand_failed += 1
                rows.append((d.url, "failed", 0, "-"))
                continue
            if known.get(d.url) == (d.hash, a.corpus_version, model):
                rows.append((d.url, "unchanged", 0, "no"))
                continue
            d.chunks = chunk_markdown(d.text, d.product, urlparse(d.url).path)
            if not a.dry_run and d.chunks:
                for i in range(0, len(d.chunks), 32):
                    batch = d.chunks[i : i + 32]
                    embs = await embed([f"{c.heading_path}\n{c.content}" for c in batch], provider, client, model)
                    for c, emb in zip(batch, embs, strict=True):
                        c.embedding = emb
                n = upsert(d, model, a.corpus_version)
            else:
                n = len(d.chunks)
            rows.append((d.url, d.status, n, "yes"))

    retired = 0
    if not a.dry_run and not partial and not seed_failed:
        retired = retire_missing([d.url for d in docs + full_docs], a.index)

    if a.verbose:
        w = max(len(r[0]) for r in rows)
        print(f"{'url':<{w}}  status     chunks  changed")
        for u, s, n, ch in rows:
            print(f"{u:<{w}}  {s:<9}  {n:>6}  {ch}")
    else:
        for u, s, _, _ in rows:
            if s == "failed":
                print(f"failed  {u}")
    by_status: dict[str, int] = {}
    for _, s, _, _ in rows:
        by_status[s] = by_status.get(s, 0) + 1
    print(f"\n{len(rows)} sources ({len(seeds)} from index, {len(expanded)} linked), "
          f"{sum(r[2] for r in rows)} chunks written, status {by_status}, "
          f"{seed_failed} index failures, {expand_failed} linked-page failures, {retired} retired"
          + ("; retirement skipped because seed discovery was incomplete" if seed_failed and not partial and not a.dry_run else "")
          + ("  (dry run)" if a.dry_run else ""))
    # Index entries are Tier 1 and must all succeed; a dead link inside the docs is only a warning.
    return 1 if seed_failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
