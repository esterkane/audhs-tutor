"""Check already indexed official guides and command sections; keep changed bytes for review."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile

import httpx

from reference_section import SECTION_URL, SectionReference

GUIDE_URL = re.compile(r"https://supabase\.com/docs/guides/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_-]+\.md")
MANIFEST = Path(__file__).with_name("enrolled_reference_urls.txt")


def enrolled() -> set[str]:
    urls = MANIFEST.read_text().splitlines()
    if (
        not urls
        or len(urls) != len(set(urls))
        or any(not (GUIDE_URL.fullmatch(u) or SECTION_URL.fullmatch(u)) for u in urls)
    ):
        raise ValueError("Invalid enrolled documentation manifest")
    return set(urls)


async def stage_checks(client: httpx.AsyncClient, active: dict[str, str], directory: Path) -> Counter:
    directory.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-"), dir=directory))
    groups: dict[str, list[str]] = defaultdict(list)
    targets = enrolled()
    for url in sorted(targets & active.keys()):
        part = SECTION_URL.fullmatch(url)
        groups[part[1] if part else url].append(url)
    semaphore = asyncio.Semaphore(4)
    outcomes: dict[str, dict[str, str]] = {url: {"status": "not_indexed"} for url in targets - active.keys()}

    async def check(urls: list[str]) -> None:
        try:
            async with semaphore:
                response = await client.get(
                    urls[0],
                    headers={"User-Agent": "kaenguru-tutor-ingest/0.1 (+local dev)"},
                    timeout=30,
                    follow_redirects=False,
                )
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("Unexpected HTTP status")
            page = SectionReference(response.text) if SECTION_URL.fullmatch(urls[0]) else None
            for url in urls:
                try:
                    if page:
                        body = page.markdown(url).encode()
                    else:
                        body = response.content
                        text = body.decode("utf-8")
                        if (
                            "html" in response.headers.get("content-type", "").lower()
                            or not re.search(r"^#\s+\S", text, re.MULTILINE)
                            or text.lstrip().startswith("<")
                        ):
                            raise ValueError("Expected Markdown guide")
                    digest = hashlib.sha256(body).hexdigest()
                    status = "unchanged" if digest == active[url] else "changed"
                    if status == "changed":
                        (run / (digest + ".md")).write_bytes(body)
                    outcomes[url] = {"status": status, "accepted": active[url], "observed": digest}
                except ValueError:
                    outcomes[url] = {"status": "invalid"}
        except (httpx.HTTPError, ValueError):
            outcomes.update({url: {"status": "unreachable"} for url in urls})

    await asyncio.gather(*(check(urls) for urls in groups.values()))
    (run / "review.json").write_text(json.dumps(outcomes, sort_keys=True, indent=2))
    return Counter(result["status"] for result in outcomes.values())
