"""Compare PostgreSQL manual articles while keeping code, links and citation anchors exact."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import re


class ManualArticle(HTMLParser):
    def __init__(self, url: str):
        super().__init__()
        self.path = url.removeprefix("https://www.postgresql.org")
        if not re.fullmatch(r"/docs/17/[a-z0-9][a-z0-9.-]*\.html", self.path):
            raise ValueError("Expected a versioned PostgreSQL 17 manual URL")
        self.selected = False
        self.roots = 0
        self.depth = 0
        self.skip = 0
        self.exact = 0
        self.events: list[tuple[str, ...]] = []
        self.anchors: set[str] = set()
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if (
            tag == "a"
            and "docs-version-selected" in a.get("class", "").split()
            and a.get("href") == self.path
        ):
            self.selected = True
        if not self.depth:
            if tag == "div" and a.get("id") == "docContent":
                self.depth = 1
                self.roots += 1
            return
        if tag == "div":
            self.depth += 1
            if self.skip or set(a.get("class", "").split()) & {"navheader", "navfooter"}:
                self.skip += 1
                return
        if self.skip:
            return
        self.events.append(("+", tag))
        for key in ("id", "name", "href", "src", "alt", "rowspan", "colspan", "start", "type"):
            if key in a and a[key] is not None:
                self.events.append((key, a[key]))
                if key == "id" or (key == "name" and tag == "a"):
                    self.anchors.add(a[key])
        if tag in {"pre", "code", "samp", "kbd"}:
            self.exact += 1

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag == "div":
            self.depth -= 1
            if self.skip:
                self.skip -= 1
                return
        if self.depth and not self.skip:
            self.events.append(("-", tag))
            if tag in {"pre", "code", "samp", "kbd"}:
                self.exact -= 1

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.text.append(data)
            value = data if self.exact else re.sub(r"\s+", " ", data)
            self.events.append(("text", value))

    @classmethod
    def parse(cls, url: str, raw: bytes) -> ManualArticle:
        parsed = cls(url)
        parsed.feed(raw.decode("utf-8"))
        parsed.close()
        if (
            parsed.roots != 1
            or parsed.depth
            or parsed.exact
            or not parsed.selected
            or not "".join(parsed.text).strip()
        ):
            raise ValueError("Missing or mismatched PostgreSQL 17 article")
        return parsed

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(self.events, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
