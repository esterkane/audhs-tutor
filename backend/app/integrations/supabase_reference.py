"""Extractive SQLSTATE identity answers; broader explanations stay with the tutor."""

import json
import re
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4


@dataclass(frozen=True)
class ReferenceAnswer:
    turn: Any
    messages: list[dict[str, Any]]
    model: str
    summary: str


def identity_request(text: str, state: Any) -> tuple[str, ...]:
    if (
        state.mode != "neutral"
        or state.delivery != "explicit"
        or state.active_lab is not None
        or state.incident is not None
        or len(text) > 240
    ):
        return ()
    subject = text.strip().rstrip("?").strip()
    question = re.fullmatch(
        r"(?:what (?:does|do) (.+?) mean|was bedeut(?:et|en) (.+?)|"
        r"what (?:is|are) (?:the )?condition names? for (.+?))",
        subject,
        re.IGNORECASE,
    )
    if question:
        subject = next(value for value in question.groups() if value is not None)
    code = r"[\"'`]?[0-9A-Z]{5}[\"'`]?"
    if not re.fullmatch(
        r"(?:SQLSTATE(?: codes?)?\s*[:=]?\s*)?"
        + code
        + r"(?:\s*(?:,|/|and|or|und|oder)\s*"
        + code
        + r"){0,3}",
        subject,
        re.IGNORECASE,
    ):
        return ()
    from backend.tutor.retrieval import sqlstate_codes

    return cast(tuple[str, ...], sqlstate_codes(subject.replace("`", "")))


def active_releases(text: str, state: Any, history: list[dict[str, Any]] | None) -> list[str]:
    from backend.tutor.postgres_versions import requested_releases

    def releases(content: str) -> list[str]:
        return requested_releases(content) or re.findall(
            r"\bversion\s+(\d+(?:\.\d+)*)\b", content, re.IGNORECASE
        )

    current = releases(text)
    if current:
        return current
    for message in reversed(history or []):
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            prior = releases(message["content"])
            if prior:
                return prior
    return releases(getattr(state, "objective", None) or "")


def supports_manual(
    version: str, text: str, state: Any, history: list[dict[str, Any]] | None
) -> bool:
    return all(release == version for release in active_releases(text, state, history))


def lab_scope_note(
    measured: str, text: str, state: Any, history: list[dict[str, Any]] | None
) -> str:
    from backend.tutor.postgres_versions import major

    number = re.match(r"\d+(?:\.\d+)*", measured)
    observed = number[0] if number else ""
    missing = [
        v for v in active_releases(text, state, history) if v != observed and v != major(observed)
    ]
    if not missing:
        return ""
    versions = ", ".join("PostgreSQL " + version for version in missing)
    if state.language == "de":
        return f"Diese Ergebnisse wurden auf PostgreSQL {measured} gemessen. Für {versions} fehlt ein eigener Lauf."
    return f"These results were measured on PostgreSQL {measured}. A separate run is needed for {versions}."


def config_default_request(text: str) -> str | None:
    key = r"(`?)([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)\1"
    request = re.fullmatch(
        r"(?i:what(?: is|'s) the default(?: value)? (?:of|for)|"
        r"was ist der standardwert (?:von|für)) "
        + key
        + r" (?i:in (?:supabase/)?config\.toml|in (?:the |der )?supabase cli)\??",
        text.strip(),
    )
    return request[2] if request else None


async def config_default_answer(
    text: str, key: str, state: Any, ctx: Any
) -> ReferenceAnswer | None:
    from backend.tutor.tools import TurnBudget, dispatch

    args = {"query": key + " config.toml default", "k": 8, "products": ["local-development"]}
    result = await dispatch("search_docs", args, ctx, TurnBudget())
    if result.is_error:
        return None
    url = "https://supabase.com/docs/guides/local-development/cli/config"
    matches: list[tuple[str, dict[str, Any]]] = []
    for hit in json.loads(result.content).get("results", []):
        if hit.get("url") not in {url, f"{url}#{key}"} or hit.get("tier") != 1:
            continue
        rows = [
            line.strip().strip("|").strip() for line in hit["content"].splitlines() if line.strip()
        ]
        if not rows or [field.strip() for field in rows[0].split("|")] != [
            "Name",
            "Default",
            "Required",
        ]:
            continue
        fields = rows[1:]
        if fields and re.fullmatch(r"[- :|]+", fields[0]):
            fields = fields[1:]
        if fields:
            cells = [field.strip() for field in fields[0].split("|")]
            if len(cells) == 3 and cells[0] == key and cells[2] in {"true", "false"}:
                matches.append((cells[1], hit))
    if len({value for value, _ in matches}) != 1:
        return None
    value, source = matches[0]
    # Only literal numeric and boolean defaults are unambiguous without the surrounding prose.
    if not re.fullmatch(r"true|false|-?[0-9]+(?:\.[0-9]+)?", value):
        return None
    label = (
        "Die Supabase-CLI-Referenz nennt"
        if state.language == "de"
        else "The Supabase CLI reference lists"
    )
    description = (
        f"{label} `{value}` als Standardwert für `{key}`."
        if state.language == "de"
        else f"{label} `{value}` as the default for `{key}`."
    )
    return build_reference_answer(
        text,
        state,
        args,
        result,
        description + " [1]",
        description.replace("`", ""),
        [
            {
                "n": 1,
                "url": source["url"],
                "title": source["title"],
                "tier": 1,
                "fetched_at": source.get("fetched_at"),
            }
        ],
        "reference:supabase-config-default.v1",
        "Supabase CLI configuration reference.",
    )


async def reference_answer(
    text: str, state: Any, ctx: Any, history: list[dict[str, Any]] | None = None
) -> ReferenceAnswer | None:
    codes = identity_request(text, state)
    if ctx is None:
        return None
    if not codes:
        if (
            state.mode == "neutral"
            and state.delivery == "explicit"
            and not state.active_lab
            and not state.incident
            and not history
            and not getattr(state, "objective", None)
        ):
            key = config_default_request(text)
            if key:
                return await config_default_answer(text, key, state, ctx)
        return None
    from backend.tutor.tools import TurnBudget, dispatch

    args = {"query": text, "k": 12, "products": ["database"]}
    result = await dispatch("search_docs", args, ctx, TurnBudget())
    if result.is_error:
        return None
    payload = json.loads(result.content)
    rows: dict[str, list[tuple[str, str, dict[str, Any]]]] = {code: [] for code in codes}
    for hit in payload.get("results", []):
        source = re.fullmatch(
            r"https://www\.postgresql\.org/docs/([0-9]+)/errcodes-appendix\.html(?:#[^\s]*)?",
            hit.get("url", ""),
        )
        if source is None:
            continue
        for line in hit.get("content", "").splitlines():
            row = re.fullmatch(r"\|\s*([0-9A-Z]{5})\s*\|\s*([a-z][a-z0-9_]*)\s*\|", line)
            if row is not None and row[1] in rows:
                rows[row[1]].append((source[1], row[2], hit))
    if any(len({(version, name) for version, name, _ in hits}) != 1 for hits in rows.values()):
        return None
    versions = {hits[0][0] for hits in rows.values()}
    if len(versions) != 1:
        return None
    version = next(iter(versions))
    if not supports_manual(version, text, state, history):
        return None
    urls: dict[str, int] = {}
    citations = []
    lines = []
    speech = []
    for code, hits in rows.items():
        _, condition, hit = hits[0]
        url = hit["url"]
        if url not in urls:
            urls[url] = len(urls) + 1
            citations.append(
                {
                    "n": urls[url],
                    "url": url,
                    "title": hit.get("title", "SQLSTATE"),
                    "tier": hit["tier"],
                    "fetched_at": hit.get("fetched_at"),
                }
            )
        lines.append(f"| `{code}` | `{condition}` | [{urls[url]}] |")
        speech.append(f"{code}: {condition}")
    german = state.language == "de"
    label = "Indizierter SQLSTATE-Katalog" if german else "Indexed SQLSTATE catalogue"
    header = "SQLSTATE | Fehlername | Quelle" if german else "SQLSTATE | Condition name | Source"
    markers = " ".join(f"[{n}]" for n in urls.values())
    body = f"{label}: PostgreSQL {version}. {markers}\n\n| {header} |\n| --- | --- | --- |\n"
    body += "\n".join(lines)
    return build_reference_answer(
        text,
        state,
        args,
        result,
        body,
        "; ".join(speech),
        citations,
        "reference:postgres-sqlstate.v1",
        "Versioned PostgreSQL SQLSTATE reference.",
    )


def build_reference_answer(
    text: str,
    state: Any,
    args: dict[str, Any],
    result: Any,
    body: str,
    speech: str,
    citations: list[dict[str, Any]],
    model: str,
    summary: str,
) -> ReferenceAnswer:
    from app.integrations.supabase_project import project_module

    turn = project_module().TutorTurn(
        mode=state.mode,
        language=state.language,
        persona_on=state.persona_on,
        text=body,
        speech=speech,
        citations=citations,
    )
    tool_id = "reference-" + str(uuid4())
    return ReferenceAnswer(
        turn,
        [
            {"role": "user", "content": text},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": tool_id, "name": "search_docs", "input": args}
                ],
            },
            {"role": "user", "content": [result.to_block(tool_id)]},
            {"role": "assistant", "content": body},
        ],
        model,
        summary,
    )
