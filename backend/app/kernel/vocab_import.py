"""CSV vocabulary import (P3, ported from lernapp-updates @ c2bf79f `services/vocab_import.py` +
`services/vocab.parse_csv`, re-implemented on the tutor's FSRS review items).

Deterministic and bounded: the learner sees a preview (detected columns, one status per row),
edits or removes rows, chooses language and direction, and only then confirms. Cards are
identified by language + direction + normalised word + normalised meaning (`practice.vocab_ref`),
so re-importing the same file adds nothing and never touches an existing schedule. Nothing here
invents definitions: only explicit word/meaning pairs are accepted (PDF glossary layouts are out of
scope until a PDF text-layout dependency is approved — export the glossary as CSV)."""

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SkillNode
from app.kernel import practice

MAX_BYTES = 2_000_000
MAX_ROWS = 2000
MAX_WORD = 120
MAX_MEANING = 200
MAX_EXAMPLE = 300
HEADER_ALIASES: dict[str, str] = {
    # word
    "word": "word", "wort": "word", "term": "word", "front": "word", "vocab": "word",
    "vokabel": "word", "expression": "word", "phrase": "word", "source": "word",
    # meaning
    "meaning": "translation", "translation": "translation", "bedeutung": "translation",
    "übersetzung": "translation", "uebersetzung": "translation", "definition": "translation",
    "back": "translation", "answer": "translation", "target": "translation",
    # example
    "example": "example", "beispiel": "example", "sentence": "example", "context": "example",
    "note": "example", "notes": "example",
}  # fmt: skip
RowStatus = Literal["new", "exists", "reverse_only", "duplicate_in_file", "invalid"]


@dataclass
class PreviewRow:
    row: int  # 1-based line in the file (after the header)
    word: str
    translation: str
    example: str | None
    status: RowStatus
    problem: str | None = None


@dataclass
class Preview:
    rows: list[PreviewRow]
    columns: dict[str, int]  # detected column → index
    delimiter: str
    header: bool
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _decode(data: bytes) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _sniff_delimiter(text: str) -> str:
    """The delimiter that gives the most consistent ≥ 2-column shape over the first lines (a quoted
    `"Wort, das";Bedeutung` must not flip to `,`); falls back to the most frequent character."""
    sample = "\n".join(text.split("\n")[:20])
    best, best_score = ",", -1.0
    for d in (",", ";", "\t", "|"):
        widths = [len(r) for r in csv.reader(io.StringIO(sample), delimiter=d) if r]
        if not widths or max(widths) < 2:
            continue
        common = max(set(widths), key=widths.count)
        score = widths.count(common) / len(widths) + (0.01 if common >= 2 else 0)
        if common >= 2 and score > best_score:
            best, best_score = d, score
    if best_score < 0:
        first = next((ln for ln in text.split("\n") if ln.strip()), "")
        counts = {d: first.count(d) for d in (",", ";", "\t", "|")}
        best = max(counts, key=lambda d: counts[d])
    return best


def _detect_columns(cells: list[str], lang: str | None = None) -> tuple[dict[str, int], bool]:
    """Header row → column map; without a recognised header the first two columns are
    word / translation and the third the example. A header of language codes (`de,en`) maps the
    deck's language to `word` and the other code to `translation`."""
    lowered = [c.strip().lower().strip("﻿") for c in cells]
    aliases = dict(HEADER_ALIASES)
    codes = [c for c in lowered if re.fullmatch(r"[a-z]{2,3}", c)]
    if lang and lang.lower() in codes:
        aliases[lang.lower()] = "word"
        for other in codes:
            if other != lang.lower():
                aliases.setdefault(other, "translation")
    mapped = {aliases[c]: i for i, c in enumerate(lowered) if c in aliases}
    if "word" in mapped and "translation" in mapped:
        return mapped, True
    return {"word": 0, "translation": 1, "example": 2}, False  # a 3rd column, when present


def _validate(word: str, translation: str, example: str | None) -> str | None:
    if not word or not translation:
        return "word and translation are required"
    if len(word) > MAX_WORD:
        return f"word longer than {MAX_WORD} characters"
    if len(translation) > MAX_MEANING:
        return f"translation longer than {MAX_MEANING} characters"
    if example is not None and len(example) > MAX_EXAMPLE:
        return f"example longer than {MAX_EXAMPLE} characters"
    return None


def _cell(cells: list[str], columns: dict[str, int], name: str) -> str:
    idx = columns.get(name)
    return cells[idx] if idx is not None and idx < len(cells) else ""


def parse_csv(data: bytes, *, lang: str | None = None) -> Preview:
    """Rows with statuses `new` / `duplicate_in_file` / `invalid`; `exists` is decided against the
    learner's cards in `preview()`. Never raises for content problems — they are reported."""
    if len(data) > MAX_BYTES:
        return Preview(
            rows=[],
            columns={},
            delimiter=",",
            header=False,
            errors=[f"file larger than {MAX_BYTES // 1_000_000} MB"],
        )
    text = _decode(data)
    delimiter = _sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    raw_rows = [row for row in reader]
    if not raw_rows:
        return Preview(
            rows=[], columns={}, delimiter=delimiter, header=False, errors=["empty file"]
        )
    columns, header = _detect_columns(raw_rows[0], lang)
    body = raw_rows[1:] if header else raw_rows
    errors: list[str] = []
    if len(body) > MAX_ROWS:
        errors.append(
            f"the file has {len(body)} rows; only the first {MAX_ROWS} are shown — split the file "
            f"after row {MAX_ROWS} and import the rest separately"
        )
        body = body[:MAX_ROWS]
    out: list[PreviewRow] = []
    seen: set[str] = set()
    for i, cells in enumerate(body, 1):
        cells = [c.strip() for c in cells]
        if not any(cells):
            continue

        word, translation = _cell(cells, columns, "word"), _cell(cells, columns, "translation")
        example = _cell(cells, columns, "example") or None
        problem = _validate(word, translation, example)
        if problem:
            out.append(PreviewRow(i, word, translation, example, "invalid", problem))
            continue
        key = f"{practice.norm_text(word)}|{practice.norm_text(translation)}"
        if key in seen:
            out.append(PreviewRow(i, word, translation, example, "duplicate_in_file"))
            continue
        seen.add(key)
        out.append(PreviewRow(i, word, translation, example, "new"))
    return Preview(rows=out, columns=columns, delimiter=delimiter, header=header, errors=errors)


async def existing_refs(db: AsyncSession, learner_id: str, lang: str) -> set[str]:
    """Refs of the learner's active cards in this deck. Never creates the deck (a preview saves
    nothing)."""
    node = (
        await db.execute(select(SkillNode).where(SkillNode.slug == practice.deck_slug(lang)))
    ).scalar_one_or_none()
    if node is None:
        return set()
    idx = await practice.deck_index(db, learner_id, node.id)
    return set(idx.by_ref)


async def preview(
    db: AsyncSession, learner_id: str, *, lang: str, data: bytes, reverse: bool = False
) -> Preview:
    """Parse + mark rows whose card (forward, and reverse when requested) already exists."""
    pv = parse_csv(data, lang=lang)
    have = await existing_refs(db, learner_id, lang)
    for r in pv.rows:
        if r.status != "new":
            continue
        fwd = practice.vocab_ref(lang, "forward", r.word, r.translation)
        rev = practice.vocab_ref(lang, "reverse", r.translation, r.word)
        if fwd in have:
            if not reverse or rev in have:
                r.status = "exists"
            else:
                r.status = "reverse_only"  # forward card exists; only the reverse card is new
    pv.counts = _counts(pv.rows)
    return pv


def _counts(rows: list[PreviewRow]) -> dict[str, int]:
    counts = {"new": 0, "exists": 0, "reverse_only": 0, "duplicate_in_file": 0, "invalid": 0}
    for r in rows:
        counts[r.status] += 1
    return counts


@dataclass
class ImportResult:
    added: int = 0
    skipped_existing: int = 0
    invalid: int = 0
    duplicate_in_file: int = 0
    reverse_added: int = 0
    reverse_skipped: int = 0
    lang: str = ""


async def import_rows(
    db: AsyncSession,
    learner_id: str,
    *,
    lang: str,
    rows: list[dict[str, Any]],
    reverse: bool = False,
    source: str | None = None,
) -> ImportResult:
    """Confirmed import. Idempotent by identity (existing cards and their schedules are never
    touched); one transaction: any failure leaves no half-imported cards (the deck *node* of a new
    language is the one row that may survive a rollback — it holds no cards)."""
    if len(rows) > MAX_ROWS:
        raise ValueError(f"at most {MAX_ROWS} rows per import")
    lang = lang.strip().lower()
    res = ImportResult(lang=lang)
    seen: set[str] = set()
    try:
        node = await practice.vocab_deck(db, lang, commit=False)
        index = await practice.deck_index(db, learner_id, node.id)  # one scan per import
        for n, raw in enumerate(rows, 1):
            word = " ".join(str(raw.get("word", "")).split())
            translation = " ".join(str(raw.get("translation", "")).split())
            example = raw.get("example")
            example = " ".join(str(example).split()) if example else None
            if _validate(word, translation, example):
                res.invalid += 1
                continue
            key = f"{practice.norm_text(word)}|{practice.norm_text(translation)}"
            if key in seen:
                res.duplicate_in_file += 1
                continue
            seen.add(key)
            attribution = {"source": source, "source_row": n} if source else None
            _, created = await practice.add_vocab(
                db,
                learner_id,
                lang=lang,
                word=word,
                translation=translation,
                example=example,
                attribution=attribution,
                commit=False,
                index=index,
            )
            if created:
                res.added += 1
            else:
                res.skipped_existing += 1
            if reverse:
                _, created_r = await practice.add_vocab(
                    db,
                    learner_id,
                    lang=lang,
                    word=translation,
                    translation=word,
                    example=example,
                    direction="reverse",
                    attribution=attribution,
                    commit=False,
                    index=index,
                )
                if created_r:
                    res.reverse_added += 1
                else:
                    res.reverse_skipped += 1
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return res
