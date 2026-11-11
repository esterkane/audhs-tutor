#!/usr/bin/env python3
"""Ask the ingested corpus a question via tutor.hybrid_search (debugging aid for retrieval).

Uses the active corpus’s local embedding model and the tutor’s query formatting.

Usage:
  uv run python scripts/search.py "permission denied for table 42501"
  uv run python scripts/search.py -k 3 --product auth "jwt expiry"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx
import psycopg
from db import admin_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.tutor.embedding_space import RECORDED_SQL, checked_vectors, ollama_payload, resolve_model


def embed_query(text: str, conn: psycopg.Connection) -> list[float]:
    provider = os.environ.get("EMBEDDINGS_PROVIDER", "ollama")
    if provider != "ollama":
        raise SystemExit("only EMBEDDINGS_PROVIDER=ollama is wired up here")
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/embed"
    recorded = [row[0] for row in conn.execute(RECORDED_SQL).fetchall()]
    model = resolve_model(provider, os.environ.get("EMBEDDINGS_MODEL"), recorded)
    r = httpx.post(url, json=ollama_payload([text], model, query=True), timeout=60)
    r.raise_for_status()
    return checked_vectors(r.json()["embeddings"], 1)[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5, help="results to return")
    ap.add_argument("--product", action="append", help="restrict to meta.product (repeatable)")
    args = ap.parse_args()

    with psycopg.connect(admin_url()) as conn:
        emb = str(embed_query(args.query, conn))
        rows = conn.execute(
            "select score, url, anchor, heading_path, left(regexp_replace(content, '\\s+', ' ', 'g'), 160)"
            " from tutor.hybrid_search(%s, %s::extensions.vector, %s, %s)",
            (args.query, emb, args.k, args.product),
        ).fetchall()
    for score, url, anchor, path, snippet in rows:
        print(f"{score:.4f}  {url}{'#' + anchor if anchor else ''}\n        {path}\n        {snippet}\n")


if __name__ == "__main__":
    main()
