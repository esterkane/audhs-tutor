#!/usr/bin/env python3
"""Verify staged Supabase references, prepare local Qwen vectors, or add new canonical URLs atomically."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import struct
from urllib.parse import urlsplit

import httpx
import psycopg
from db import admin_url
from ingest_llms import Chunk, Doc, chunk_markdown, embed, product_of
from stage_reference_sitemap import SITEMAP, classify, inventory

MODEL = "qwen3-embedding:0.6b"
HEX = re.compile(r"[a-f0-9]{64}")
VECTOR = struct.Struct("<768f")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_lines(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def read_stage(path: Path) -> tuple[dict[str, Doc], int]:
    manifest = (path / "sitemap.xml").read_bytes()
    summary = json.loads((path / "summary.json").read_text())
    requested = json.loads((path / "requested.json").read_text())
    allowed = inventory(manifest)
    if (
        summary.get("chunk_format") != "fenced-markdown-v2"
        or summary["sitemap_url"] != SITEMAP
        or summary["manifest_sha256"] != digest(manifest)
        or len(requested) != len(set(requested))
        or len(requested) != summary["selected"]
        or not set(requested) <= allowed.keys()
    ):
        raise ValueError("Invalid staged request manifest")
    documents: dict[str, Doc] = {}
    reported = []
    missing = 0
    for row in json_lines(path / "sources.jsonl"):
        url = row["requested_url"]
        reported.append(url)
        if row["status"] == "no_indexable_body":
            missing += 1
            continue
        canonical = row.get("canonical_url", "")
        group = classify(canonical)
        if row["status"] != "staged" or not group or group[1] == "unsupported" or group != allowed.get(url):
            raise ValueError("Unresolved source failure or mismatched canonical edition")
        if row["family"] != group[0] or row["edition"] != (None if group[1] == "product" else group[1]):
            raise ValueError("Staged family/edition mismatch")
        page_hash = row["content_sha256"]
        if not HEX.fullmatch(page_hash):
            raise ValueError("Invalid page digest")
        if canonical in documents:
            if documents[canonical].hash != page_hash:
                raise ValueError("Conflicting canonical page digests")
            continue
        raw = (path / "pages" / (page_hash + ".md")).read_bytes()
        if digest(raw) != page_hash:
            raise ValueError("Page bytes do not match staged digest")
        product = product_of(canonical)
        chunks = chunk_markdown(raw.decode(), product, urlsplit(canonical).path)
        if not chunks:
            raise ValueError("Expected normalized article passages")
        for c in chunks:
            # The parser knows the page identity. Its synthetic heading slug is not an HTML fragment.
            c.anchor = None
            c.meta.update(reference_family=group[0], reference_edition=row["edition"])
        documents[canonical] = Doc(canonical, 1, product, hash=page_hash, chunks=chunks)
    if (
        reported != requested
        or missing != summary["failed"]
        or missing != summary["no_indexable_body"]
        or len(documents) != summary["canonical_staged"]
    ):
        raise ValueError("Incomplete staged source inventory")
    checked: dict[str, int] = defaultdict(int)
    for row in json_lines(path / "passages.jsonl"):
        url = row["url"]
        document = documents[url]
        index = checked[url]
        if index >= len(document.chunks):
            raise ValueError("Unrecognized staged passage")
        c = document.chunks[index]
        if (
            row["ord"],
            row["content"],
            row["content_sha256"],
            row["heading"],
            row["edition"],
            row["family"],
        ) != (
            c.ord,
            c.content,
            c.hash,
            c.heading_path,
            c.meta["reference_edition"],
            c.meta["reference_family"],
        ):
            raise ValueError("Passage content or identity differs from the normalized page")
        checked[url] += 1
    if any(checked[d.url] != len(d.chunks) for d in documents.values()):
        raise ValueError("Missing staged passage")
    return documents, missing


def embedding_input(chunk: Chunk) -> str:
    return chunk.heading_path + "\n" + chunk.content


def vector_key(text: str) -> str:
    return digest((MODEL + "\x00768\x00raw-document\x00" + text).encode())


def stored_vector(cache: sqlite3.Connection, key: str) -> list[float] | None:
    row = cache.execute("SELECT data,sha256 FROM vectors WHERE key=?", (key,)).fetchone()
    if row is None:
        return None
    if len(row[0]) != VECTOR.size or digest(row[0]) != row[1]:
        raise ValueError("Corrupt cached embedding")
    return list(VECTOR.unpack(row[0]))


async def local_model_digest() -> str:
    base = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    url = urlsplit(base)
    if url.scheme not in {"http", "https"} or url.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
        "host.docker.internal",
    }:
        raise ValueError("Reference vector preparation requires a local Ollama endpoint")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(base + "/api/tags")
        response.raise_for_status()
    for item in response.json()["models"]:
        if item.get("name") == MODEL and HEX.fullmatch(item.get("digest", "")):
            return item["digest"]
    raise ValueError("The local Qwen model or its manifest digest is unavailable")


def verify_cache_identity(cache: sqlite3.Connection, expected: str, *, create: bool = False) -> None:
    if create:
        cache.execute("CREATE TABLE IF NOT EXISTS provenance(model TEXT PRIMARY KEY,digest TEXT NOT NULL)")
        if not cache.execute("SELECT 1 FROM provenance").fetchone():
            if cache.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vectors'"
            ).fetchone():
                raise ValueError("Cache has no recorded model digest; prepare a new cache")
            cache.execute("INSERT INTO provenance VALUES(?,?)", (MODEL, expected))
            cache.commit()
    if cache.execute("SELECT model,digest FROM provenance").fetchall() != [(MODEL, expected)]:
        raise ValueError("Prepared vectors and installed model have different manifest identities")


def verify_completed(cache: sqlite3.Connection, expected: str) -> None:
    verify_cache_identity(cache, expected)
    table = cache.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='completion'").fetchone()
    if not table or cache.execute("SELECT digest FROM completion").fetchall() != [(expected,)]:
        raise ValueError("Vector preparation has not completed; rerun --prepare-vectors")


async def prepare_verified(documents: dict[str, Doc], cache: sqlite3.Connection, expected: str) -> int:
    verify_cache_identity(cache, expected, create=True)
    if cache.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='vectors'").fetchone():
        verify_completed(cache, expected)
    with cache:
        cache.execute("CREATE TABLE IF NOT EXISTS completion(digest TEXT PRIMARY KEY)")
        cache.execute("DELETE FROM completion")
    try:
        count = await prepare(documents, cache)
        if await local_model_digest() != expected:
            raise ValueError("Ollama model changed during preparation")
    except BaseException:
        # Intermediate batches might have used another model. Discard their provenance.
        with cache:
            cache.execute("DELETE FROM provenance")
        raise
    with cache:
        cache.execute("INSERT INTO completion VALUES(?)", (expected,))
    return count


async def prepare(documents: dict[str, Doc], cache: sqlite3.Connection):
    cache.execute(
        "CREATE TABLE IF NOT EXISTS vectors(key TEXT PRIMARY KEY,data BLOB NOT NULL,sha256 TEXT NOT NULL)"
    )
    pending = {}
    for doc in documents.values():
        for c in doc.chunks:
            text = embedding_input(c)
            key = vector_key(text)
            if key not in pending and stored_vector(cache, key) is None:
                pending[key] = text
    items = list(pending.items())
    async with httpx.AsyncClient() as client:
        for i in range(0, len(items), 16):
            batch = items[i : i + 16]
            vectors = await embed([text for _, text in batch], "ollama", client, MODEL)
            with cache:
                for (key, _), vec in zip(batch, vectors, strict=True):
                    blob = VECTOR.pack(*vec)
                    cache.execute("INSERT OR IGNORE INTO vectors VALUES(?,?,?)", (key, blob, digest(blob)))
    return len(items)


def apply_or_verify(conn: psycopg.Connection, docs: dict[str, Doc], cache: sqlite3.Connection | None):
    with conn.transaction(), conn.cursor() as cur:
        if cache is None:
            cur.execute("SET TRANSACTION READ ONLY")
        else:
            # Serialize the comparison with all source/chunk writers. Existing rows are never updated.
            cur.execute("SET LOCAL lock_timeout='10s'")
            cur.execute("LOCK TABLE tutor.docs_source, tutor.docs_chunk IN SHARE ROW EXCLUSIVE MODE")
        cur.execute("SELECT DISTINCT embedding_model FROM tutor.docs_source WHERE status='active'")
        models = {row[0] for row in cur.fetchall()}
        if models and models != {MODEL}:
            raise ValueError("Active corpus embedding space is incompatible")
        cur.execute(
            "SELECT s.url,s.content_hash,s.embedding_model,s.status,s.product,s.id FROM tutor.docs_source s WHERE s.url=ANY(%s)",
            (list(docs),),
        )
        existing = {}
        for url, page_hash, model, status, product, source_id in cur.fetchall():
            if (page_hash, model, status, product) != (docs[url].hash, MODEL, "active", docs[url].product):
                raise ValueError(f"Existing canonical URL differs: {url}")
            existing[url] = source_id
        if existing:
            cur.execute(
                "SELECT s.url,c.ord,c.heading_path,c.content,c.content_hash,c.anchor,c.embedding IS NOT NULL,c.meta FROM tutor.docs_source s JOIN tutor.docs_chunk c ON c.source_id=s.id WHERE s.url=ANY(%s) ORDER BY s.url,c.ord",
                (list(existing),),
            )
            counts: dict[str, int] = defaultdict(int)
            for url, index, heading, content, body_hash, anchor, vector, meta in cur.fetchall():
                if index != counts[url] or index >= len(docs[url].chunks):
                    raise ValueError("Existing passage order differs")
                expected = docs[url].chunks[index]
                if (heading, content, body_hash, anchor, vector, meta) != (
                    expected.heading_path,
                    expected.content,
                    expected.hash,
                    None,
                    True,
                    expected.meta,
                ):
                    raise ValueError(f"Existing passage differs: {url}")
                counts[url] += 1
            if any(counts[url] != len(docs[url].chunks) for url in existing):
                raise ValueError("Existing passage inventory incomplete")
        additions = [doc for url, doc in docs.items() if url not in existing]
        if cache is not None:
            for doc in additions:
                cur.execute(
                    "INSERT INTO tutor.docs_source(url,tier,product,content_hash,embedding_model,corpus_version,status,fetched_at) VALUES(%s,1,%s,%s,%s,1,'active',now()) RETURNING id",
                    (doc.url, doc.product, doc.hash, MODEL),
                )
                inserted = cur.fetchone()
                assert inserted is not None
                source_id = inserted[0]
                rows = []
                for c in doc.chunks:
                    vec = stored_vector(cache, vector_key(embedding_input(c)))
                    if vec is None:
                        raise ValueError("Missing prepared vector; run --prepare-vectors first")
                    rows.append(
                        (source_id, c.ord, c.heading_path, c.content, c.hash, json.dumps(c.meta), str(vec))
                    )
                cur.executemany(
                    "INSERT INTO tutor.docs_chunk(source_id,ord,heading_path,content,content_hash,meta,embedding,anchor) VALUES(%s,%s,%s,%s,%s,%s,%s,NULL)",
                    rows,
                )
        return {
            "existing": len(existing),
            "new_sources": len(additions),
            "new_passages": sum(len(d.chunks) for d in additions),
        }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stages", type=Path, nargs="+")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--prepare-vectors", type=Path, metavar="CACHE")
    group.add_argument("--check-db", action="store_true", help="Read-only compatibility and collision check")
    group.add_argument(
        "--apply",
        type=Path,
        metavar="CACHE",
        help="Atomically insert only new references using the existing local vector cache",
    )
    args = parser.parse_args()
    documents: dict[str, Doc] = {}
    excluded = 0
    for path in args.stages:
        docs, missing = read_stage(path)
        if documents.keys() & docs.keys():
            raise ValueError("Duplicate canonical URL across selected stages")
        documents.update(docs)
        excluded += missing
    print(
        json.dumps(
            {
                "verified_sources": len(documents),
                "passages": sum(len(d.chunks) for d in documents.values()),
                "no_indexable_body": excluded,
            }
        ),
        flush=True,
    )
    expected = await local_model_digest() if args.prepare_vectors or args.apply else ""
    if args.prepare_vectors:
        with sqlite3.connect(args.prepare_vectors) as cache:
            prepared = await prepare_verified(documents, cache, expected)
            print(json.dumps({"model": MODEL, "model_digest": expected, "prepared_inputs": prepared}))
    if args.check_db or args.apply:
        with psycopg.connect(admin_url(), autocommit=True) as conn:
            if args.apply:
                with sqlite3.connect(args.apply.resolve().as_uri() + "?mode=ro", uri=True) as cache:
                    verify_completed(cache, expected)
                    result = apply_or_verify(conn, documents, cache)
            else:
                result = apply_or_verify(conn, documents, None)
        print(json.dumps({"model_digest": expected or None, **result}))


if __name__ == "__main__":
    asyncio.run(main())
