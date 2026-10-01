"""Source files (course repos, exercise solutions) -> fenced code blocks split at top-level
definitions, each carrying the first definition name as its heading. Obvious credentials are
redacted; minified files and lockfiles are refused (no concept in them)."""

import re

from app.knowledge.ingest.normalize import redact_secrets
from app.knowledge.ingest.types import Block

LANG_BY_SUFFIX: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".m": "objectivec",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".ps1": "powershell",
    ".sql": "sql",
    ".r": "r",
    ".jl": "julia",
    ".lua": "lua",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".hs": "haskell",
    ".clj": "clojure",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".dockerfile": "dockerfile",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".tf": "hcl",
    ".vue": "vue",
    ".svelte": "svelte",
    ".css": "css",
    ".scss": "scss",
}
CODE_FILENAMES = {"dockerfile": "dockerfile", "makefile": "makefile", "justfile": "make"}
LOCKFILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "cargo.lock",
    "gemfile.lock",
    "composer.lock",
    "pipfile.lock",
}
MAX_FILE_CHARS = 200_000
MAX_UNIT_CHARS = 3000  # the chunker keeps code blocks up to 2 × MAX_CHARS whole
_DEF_START = re.compile(
    r"^(?:@|(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:pub(?:\([^)]*\))?\s+)?"
    r"(?:def|class|function|func|fn|struct|enum|impl|trait|interface|type|module|object|record"
    r"|public|private|protected|static|abstract|final|CREATE|create)\b)"
)
_NAME = re.compile(
    r"(?:def|class|function|func|fn|struct|enum|impl|trait|interface|type|module|object|record"
    r"|TABLE|table|VIEW|view|FUNCTION|PROCEDURE)\s+(?:IF NOT EXISTS\s+)?([A-Za-z_][\w.:]*)"
)


def language_for(name: str) -> str | None:
    lower = name.lower()
    if lower in LOCKFILES:
        return None
    if lower in CODE_FILENAMES:
        return CODE_FILENAMES[lower]
    dot = lower.rfind(".")
    return LANG_BY_SUFFIX.get(lower[dot:]) if dot >= 0 else None


def _units(text: str) -> list[str]:
    lines = text.split("\n")
    units: list[list[str]] = [[]]
    blank_run = 0
    for ln in lines:
        if not ln.strip():
            blank_run += 1
            units[-1].append(ln)
            continue
        starts_def = ln[:1] not in (" ", "\t") and _DEF_START.match(ln) is not None
        # a decorator/attribute line stays with the definition that follows it
        prev_is_decorator = any(
            s.strip().startswith(("@", "#[")) for s in units[-1][-1 - blank_run :] if s.strip()
        )
        if (starts_def and units[-1] and not prev_is_decorator and blank_run > 0) or blank_run >= 2:
            if any(s.strip() for s in units[-1]):
                units.append([])
        blank_run = 0
        units[-1].append(ln)
    out: list[str] = []
    for u in units:
        body = "\n".join(u).strip("\n")
        if not body.strip():
            continue
        while len(body) > MAX_UNIT_CHARS:  # hard split on a line boundary
            cut = body.rfind("\n", 0, MAX_UNIT_CHARS)
            cut = cut if cut > MAX_UNIT_CHARS // 2 else MAX_UNIT_CHARS
            out.append(body[:cut])
            body = body[cut:].strip("\n")
        if body:
            out.append(body)
    return out


def code_blocks(text: str, lang: str, *, filename: str = "") -> list[Block]:
    if len(text) > MAX_FILE_CHARS:
        raise ValueError(f"source file too large ({len(text)} chars)")
    if any(len(ln) > 2000 for ln in text.split("\n")):
        raise ValueError("minified or generated source (line > 2000 chars)")
    text = redact_secrets(text.replace("\r\n", "\n"))
    blocks: list[Block] = []
    packed: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal packed, size
        if not packed:
            return
        body = "\n\n".join(packed)
        m = _NAME.search(body)
        heading = m.group(1) if m else (filename or None)
        blocks.append(Block(text=f"```{lang}\n{body}\n```", kind="code", heading=heading))
        packed, size = [], 0

    for unit in _units(text):
        if packed and size + len(unit) > MAX_UNIT_CHARS:
            flush()
        packed.append(unit)
        size += len(unit) + 2
    flush()
    return blocks
