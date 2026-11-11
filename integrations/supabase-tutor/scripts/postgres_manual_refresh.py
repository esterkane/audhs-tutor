"""Check a bounded, rotating sample of installed PostgreSQL 17 manual articles."""

from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import httpx
import psycopg

from db import admin_url
from postgres_manual_article import ManualArticle

ORIGIN = "https://www.postgresql.org/docs/17/"
HEX = re.compile(r"[a-f0-9]{64}")
PAGE = re.compile(r"[a-z0-9][a-z0-9.-]*\.html")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def check(
    client: httpx.AsyncClient, url: str, accepted: str, raw_dir: Path, state: Path
) -> dict[str, str]:
    if not url.startswith(ORIGIN) or not PAGE.fullmatch(url[len(ORIGIN) :]) or not HEX.fullmatch(accepted):
        return {"status": "invalid_identity"}
    archived = raw_dir / (accepted + ".html")
    if not archived.is_file():
        return {"status": "missing_baseline"}
    old = archived.read_bytes()
    if digest(old) != accepted:
        return {"status": "invalid_baseline"}
    try:
        before = ManualArticle.parse(url, old)
    except ValueError:
        return {"status": "invalid_baseline"}
    try:
        response = await client.get(url, follow_redirects=False, timeout=30)
        response.raise_for_status()
        if response.status_code != 200:
            return {"status": "unreachable"}
    except httpx.HTTPError:
        return {"status": "unreachable"}
    new = response.content
    raw_hash = digest(new)
    try:
        after = ManualArticle.parse(url, new)
    except ValueError:
        return {"status": "invalid_article", "observed": raw_hash}
    status = (
        "unchanged"
        if raw_hash == accepted
        else "site_only"
        if before.fingerprint == after.fingerprint
        else "article_changed"
    )
    if status == "article_changed":
        path = state / "candidates" / (raw_hash + ".html")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(new)
    return {
        "status": status,
        "observed": raw_hash,
        "old_article": before.fingerprint,
        "new_article": after.fingerprint,
    }


async def audit(
    client: httpx.AsyncClient, rows: dict[str, str], raw_dir: Path, state: Path, limit: int
) -> Counter:
    if not rows or not 1 <= limit <= 100:
        raise ValueError("Expected active PostgreSQL 17 sources and limit 1 through 100")
    state.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(state / "checks.sqlite") as history:
        history.execute("CREATE TABLE IF NOT EXISTS checks(url TEXT,accepted TEXT,checked TEXT,result TEXT)")
        history.execute("CREATE INDEX IF NOT EXISTS checks_by_source ON checks(url, accepted, checked)")
        latest = {
            (url, accepted): date
            for url, accepted, date in history.execute(
                "select url,accepted,max(checked) from checks group by url,accepted"
            )
        }
        selected = sorted(rows, key=lambda url: (latest.get((url, rows[url]), ""), url))[:limit]
        counts: Counter[str] = Counter()
        for start in range(0, len(selected), 4):
            batch = selected[start : start + 4]
            results = await asyncio.gather(*(check(client, url, rows[url], raw_dir, state) for url in batch))
            stamp = datetime.now(UTC).isoformat()
            with history:
                for url, result in zip(batch, results, strict=True):
                    counts[result["status"]] += 1
                    history.execute(
                        "insert into checks values(?,?,?,?)", (url, rows[url], stamp, json.dumps(result))
                    )
    return counts


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-dir",
        required=True,
        type=Path,
        help="Archived official HTML named by installed content SHA-256",
    )
    parser.add_argument(
        "--state-dir", required=True, type=Path, help="Local review ledger and candidate directory"
    )
    parser.add_argument("--limit", default=48, type=int)
    args = parser.parse_args()
    with psycopg.connect(admin_url()) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        rows: dict[str, str] = dict(
            conn.execute(
                "select url,content_hash from tutor.docs_source where status='active' and starts_with(url,%s)",
                (ORIGIN,),
            ).fetchall()
        )
    async with httpx.AsyncClient(headers={"User-Agent": "AuDHS-reference-freshness/1.0"}) as client:
        counts = await audit(client, rows, args.baseline_dir, args.state_dir, args.limit)
    print(json.dumps({"enrolled": len(rows), "checked": sum(counts.values()), "outcomes": counts}))
    return int(bool(set(counts) - {"unchanged", "site_only", "article_changed"}))


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
