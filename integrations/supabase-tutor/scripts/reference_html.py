"""Convert canonical SDK reference HTML into heading-aware text for the Markdown chunker."""

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

REFERENCE_URL = re.compile(
    r"https://supabase\.com/docs/reference/(?:(?:javascript|python|dart|swift|kotlin|csharp)/(?:v[0-9]+/)?|(?:api|server|middleware|tanstack_db)/)[a-z0-9-]+/?"
)


CONFIG_GUIDES = {
    "https://supabase.com/docs/guides/local-development/cli/config": ("Supabase CLI config", "project_id"),
    "https://supabase.com/docs/guides/self-hosting/auth/config": ("Auth Self-hosting Config", "GOTRUE_SITE_URL"),
}


class _Page(HTMLParser):
    ignored = frozenset({"nav", "script", "style", "footer", "header", "aside", "template"})
    blocks = frozenset({"p", "ul", "ol", "section", "article", "div", "li", "tr"})

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.canonical = ""
        self.config_guide = url in CONFIG_GUIDES
        self.article_depth = 0
        self.line_number_depth = 0
        self.skip = 0
        self.started = False
        self.headings = 0
        self.parts: list[str] = []
        self.code: list[str] | None = None
        self.language = ""
        self.link = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "canonical" in (a.get("rel") or "").split():
            self.canonical = urljoin(self.url, a.get("href") or "")
        if self.config_guide:
            if tag == "article" and (self.article_depth or a.get("id") == "sb-docs-guide-main-article"):
                self.article_depth += 1
            if not self.article_depth:
                return
        if self.config_guide and tag == "span" and (
            self.line_number_depth or (self.code is not None and "linenumber" in (a.get("class") or "").split())
        ):
            self.line_number_depth += 1
        if self.line_number_depth:
            return
        if tag in self.ignored and not (self.config_guide and tag == "header"):
            self.skip += 1
        if self.skip:
            return
        if tag == "h1":
            self.started = True
            self.headings += 1
        if not self.started:
            return
        if tag == "pre":
            self.code = []
            self.language = ""
        elif self.code is not None:
            if tag == "code":
                m = re.fullmatch(r"language-([A-Za-z0-9_+-]+)", a.get("class") or "")
                self.language = m.group(1) if m else ""
            elif tag == "br":
                self.code.append("\n")
        elif re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in self.blocks:
            self.parts.append("\n\n")
            if tag == "li":
                self.parts.append("- ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "a":
            dest = urljoin(self.url, a.get("href") or "")
            self.link = dest if urlsplit(dest).scheme in {"http", "https"} else ""
            if self.link:
                self.parts.append("[")
        elif tag == "code":
            self.parts.append("`")

    def handle_endtag(self, tag):
        if self.line_number_depth:
            if tag == "span":
                self.line_number_depth -= 1
            return
        if self.config_guide:
            if not self.article_depth:
                return
            if tag == "article":
                self.article_depth -= 1
        if self.skip:
            if tag in self.ignored:
                self.skip -= 1
            return
        if not self.started:
            return
        if tag == "pre" and self.code is not None:
            body = "".join(self.code)
            fence = "`" * max(3, 1 + max(map(len, re.findall(r"`+", body)), default=0))
            self.parts.extend(
                ["\n\n", fence, self.language, "\n", body, "" if body.endswith("\n") else "\n", fence, "\n\n"]
            )
            self.code = None
        elif self.code is not None:
            return
        elif tag == "a" and self.link:
            self.parts.append("](" + self.link + ")")
            self.link = ""
        elif tag == "code":
            self.parts.append("`")
        elif tag in self.blocks or re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_data(self, data):
        if self.started and not self.skip and not self.line_number_depth and (not self.config_guide or self.article_depth):
            if self.code is not None:
                self.code.append(data)
            else:
                self.parts.append(re.sub(r"\s+", " ", data))


class CanonicalMethod(ValueError):
    """An official method alias claims another canonical URL within the same SDK."""


class NoReferenceBody(ValueError):
    """The canonical page contains only a title, with no indexable article text."""


def reference_markdown(html: str, url: str) -> str:
    """Require the requested official reference URL and one non-empty article."""
    if not REFERENCE_URL.fullmatch(url):
        raise ValueError("Expected an official reference article URL")
    page = _Page(url)
    page.feed(html)
    page.close()
    text = "".join(page.parts).strip()
    canonical = page.canonical.rstrip("/")
    if canonical != url.rstrip("/"):
        if (
            REFERENCE_URL.fullmatch(canonical)
            and canonical.rsplit("/", 1)[0] == url.rstrip("/").rsplit("/", 1)[0]
        ):
            raise CanonicalMethod(canonical)
        raise ValueError("Reference points outside the requested SDK")
    if page.headings == 1 and page.code is None and re.fullmatch(r"# [^\n]+",text):
        raise NoReferenceBody("Canonical reference has no indexable body")
    if page.headings != 1 or page.code is not None or not re.search(r"^# [^\n]+\n\s*\S", text):
        raise ValueError("Incomplete or mismatched SDK reference page")
    version = re.fullmatch(r"/docs/reference/([^/]+)/(v[0-9]+)/[^/]+/?", urlsplit(url).path)
    if version:
        heading, rest = text.split("\n", 1)
        text = f"{heading} [{version[1]} SDK {version[2]}]\n{rest}"
    return text + "\n"

def config_guide_markdown(html: str, url: str) -> str:
    """Read the official configuration article when its Markdown twin is unavailable."""
    title, setting = CONFIG_GUIDES[url]
    page = _Page(url)
    page.feed(html)
    page.close()
    text = "".join(page.parts).strip()
    # The upstream H1 wraps its title in a paragraph.
    text = re.sub(r"^#\s+", "# ", text)
    if (page.canonical != url or page.headings != 1 or page.article_depth or page.code is not None
            or not text.startswith(f"# {title}\n") or not re.search(rf"\b{setting}\b", text)):
        raise ValueError("Incomplete or mismatched configuration guide")
    return text + "\n"
