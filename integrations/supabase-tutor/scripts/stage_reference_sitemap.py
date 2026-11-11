#!/usr/bin/env python3
"""Inventory or stage canonical SDK and product documentation from the official Supabase sitemap."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

import httpx

from ingest_llms import Doc, UA, chunk_markdown, fetch, product_of

SITEMAP = "https://supabase.com/docs/sitemap.xml"
SDK = ("csharp", "dart", "javascript", "kotlin", "python", "swift")
PRODUCT = ("api", "server", "middleware", "tanstack_db")
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
METHOD = re.compile(r"[a-z0-9-]+")
VERSION = re.compile(r"v[0-9]+")


def classify(url: str) -> tuple[str, str] | None:
    parsed = urlsplit(url)
    if (parsed.scheme, parsed.netloc) != ("https", "supabase.com") or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/docs/reference/([^/]+)(?:/(.*?))?/?", parsed.path)
    if not match:
        return None
    family, tail = match.groups()
    remainder = (tail or "").split("/")
    if family in SDK:
        if len(remainder) == 1 and METHOD.fullmatch(remainder[0]) and not VERSION.fullmatch(remainder[0]):
            return family, "unversioned"
        if len(remainder) == 2 and VERSION.fullmatch(remainder[0]) and METHOD.fullmatch(remainder[1]):
            return family, remainder[0]
    if family in PRODUCT and len(remainder) == 1 and METHOD.fullmatch(remainder[0]):
        return family, "product"
    return family, "unsupported"


def inventory(raw: bytes) -> dict[str, tuple[str, str]]:
    root = ElementTree.fromstring(raw)
    if root.tag != NS + "urlset":
        raise ValueError("Expected an official sitemap urlset.")
    result = {}
    for loc in root.findall(f"{NS}url/{NS}loc"):
        url = (loc.text or "").strip().rstrip("/")
        group = classify(url)
        if group:
            result[url] = group
    if not result:
        raise ValueError("Sitemap has no recognized Supabase reference URLs.")
    return result


def choose(
    pages: dict[str, tuple[str, str]],
    family_filter: str | None,
    edition: str | None,
    limit: int | None,
    group_filter: str = "sdk",
) -> list[str]:
    seen: Counter[tuple[str, str]] = Counter()
    selected = []
    for url, group in sorted(pages.items()):
        family, version = group
        if version == "unsupported" or (version == "product") != (group_filter == "product"):
            continue
        if (family_filter and family != family_filter) or (edition and version != edition):
            continue
        if limit and seen[group] >= limit:
            continue
        seen[group] += 1
        selected.append(url)
    return selected


async def stage(client: httpx.AsyncClient, targets: list[str], directory: Path, manifest: bytes) -> int:
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "sitemap.xml").write_bytes(manifest)
    (directory / "requested.json").write_text(json.dumps(targets, indent=2) + "\n", encoding="utf-8")
    raw_dir = directory / "pages"
    raw_dir.mkdir()
    semaphore = asyncio.Semaphore(4)
    completed: dict[str, str] = {}
    failures = 0
    no_body = 0
    with (
        (directory / "sources.jsonl").open("x", encoding="utf-8") as records,
        (directory / "passages.jsonl").open("x", encoding="utf-8") as passages,
    ):
        for offset in range(0, len(targets), 8):
            batch = targets[offset : offset + 8]
            pages = await asyncio.gather(
                *(fetch(client, Doc(url, 1, product_of(url)), semaphore, raw_dir=raw_dir) for url in batch)
            )
            for url, doc in zip(batch, pages, strict=True):
                group = classify(url)
                assert group is not None
                row = {
                    "requested_url": url,
                    "family": group[0],
                    "group": "product" if group[1] == "product" else "sdk",
                    "edition": None if group[1] == "product" else group[1],
                }
                if doc.status == "failed" or classify(doc.url) != group:
                    row["status"] = doc.failure_reason or "failed"
                    if doc.failure_reason == "no_indexable_body":
                        no_body += 1
                    failures += 1
                elif doc.url in completed and completed[doc.url] != doc.hash:
                    row["status"] = "canonical_content_changed_during_stage"
                    failures += 1
                else:
                    chunks = chunk_markdown(doc.text, product_of(doc.url), urlsplit(doc.url).path)
                    if not chunks:
                        row["status"] = "no_passages"
                        failures += 1
                    else:
                        row.update(status="staged", canonical_url=doc.url, content_sha256=doc.hash)
                        if doc.url not in completed:
                            completed[doc.url] = doc.hash
                            for chunk in chunks:
                                passages.write(
                                    json.dumps(
                                        {
                                            "url": doc.url,
                                            "family": group[0],
                                            "group": row["group"],
                                            "edition": row["edition"],
                                            "ord": chunk.ord,
                                            "heading": chunk.heading_path,
                                            "content": chunk.content,
                                            "content_sha256": chunk.hash,
                                        },
                                        ensure_ascii=False,
                                    )
                                    + "\n"
                                )
                records.write(json.dumps(row, ensure_ascii=False) + "\n")
            records.flush()
            passages.flush()
    summary = {
        "chunk_format": "fenced-markdown-v2",
        "sitemap_url": SITEMAP,
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "selected": len(targets),
        "canonical_staged": len(completed),
        "failed": failures,
        "no_indexable_body": no_body,
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 1 if failures else 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage-dir",
        type=Path,
        help="New directory for normalized source pages, passage citations and a manifest. Omit for inventory only.",
    )
    parser.add_argument(
        "--group",
        choices=("sdk", "product"),
        default="sdk",
        help="Stage SDK methods or product articles as separate sets.",
    )
    parser.add_argument("--family", choices=SDK + PRODUCT)
    parser.add_argument("--edition", help="unversioned or an exact edition segment, e.g. v1")
    parser.add_argument("--per-edition", type=int, help="Maximum pages to stage per SDK and edition")
    args = parser.parse_args()
    if args.per_edition is not None and args.per_edition < 1:
        parser.error("--per-edition must be positive")
    if args.edition and args.edition != "unversioned" and not VERSION.fullmatch(args.edition):
        parser.error("--edition must be unversioned or an exact version segment")
    async with httpx.AsyncClient() as client:
        response = await client.get(SITEMAP, headers={"User-Agent": UA}, timeout=30)
        response.raise_for_status()
        pages = inventory(response.content)
        groups = Counter(pages.values())
        selected = choose(pages, args.family, args.edition, args.per_edition, args.group)
        print(
            json.dumps(
                {
                    "reference_routes": len(pages),
                    "by_family_and_edition": {
                        f"{family}/{edition}": n for (family, edition), n in sorted(groups.items())
                    },
                    "selected": len(selected),
                },
                sort_keys=True,
            )
        )
        if not selected:
            print("No pages matched the requested family group and edition.", file=sys.stderr)
            return 2
        if args.stage_dir:
            return await stage(client, selected, args.stage_dir, response.content)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
