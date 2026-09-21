"""P3 vocab-identity + vocab-import: card identity by language + direction + word + meaning,
schedules preserved on re-import, legacy refs adopted, CSV parsing variants, statuses, limits,
atomicity, routes."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.models import MemoryState, ReviewItem
from app.kernel import memory, practice, vocab_import
from app.kernel.vocab_import import parse_csv


async def _cards(db: AsyncSession, learner_id: str) -> list[ReviewItem]:
    stmt = select(ReviewItem).where(
        ReviewItem.learner_id == learner_id, ReviewItem.item_type == "vocab"
    )
    return list((await db.execute(stmt)).scalars())


async def test_identity_includes_meaning_and_direction(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    a, created_a = await practice.add_vocab(
        db, learner.id, lang="de", word="Bank", translation="bench"
    )
    b, created_b = await practice.add_vocab(
        db, learner.id, lang="de", word="Bank", translation="bank (money)"
    )
    assert created_a and created_b and a.id != b.id  # two meanings → two cards
    same, created = await practice.add_vocab(
        db, learner.id, lang="DE", word=" bank ", translation="Bench"
    )
    assert not created and same.id == a.id  # whitespace / case → the same card
    rev, created_r = await practice.add_vocab(
        db, learner.id, lang="de", word="bench", translation="Bank", direction="reverse"
    )
    assert created_r and rev.id not in (a.id, b.id) and rev.prompt_json["direction"] == "reverse"
    assert rev.prompt_json["q"] == "bench" and rev.prompt_json["a"] == "Bank"
    assert practice.vocab_ref("de", "forward", "Bank ", "bench") == "de:forward:bank:bench"
    with pytest.raises(ValueError):
        await practice.add_vocab(
            db, learner.id, lang="de", word="x", translation="y", direction="up"
        )


async def test_reimport_keeps_schedule_and_fills_only_missing_fields(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    item, _ = await practice.add_vocab(db, learner.id, lang="de", word="Haus", translation="house")
    later = datetime.now(UTC) + timedelta(days=1)
    await memory.review(db, learner.id, item.id, 3, now=later)
    ms_before = (
        await db.execute(select(MemoryState).where(MemoryState.review_item_id == item.id))
    ).scalar_one()
    stability, due = ms_before.stability, ms_before.due
    again, created = await practice.add_vocab(
        db,
        learner.id,
        lang="de",
        word="Haus",
        translation="house",
        example="Das Haus ist alt.",
        attribution={"source": "list.csv", "source_row": 3},
    )
    assert not created and again.id == item.id
    ms_after = (
        await db.execute(select(MemoryState).where(MemoryState.review_item_id == item.id))
    ).scalar_one()
    assert (ms_after.stability, ms_after.due) == (stability, due)  # schedule untouched
    assert (
        again.prompt_json["example"] == "Das Haus ist alt."
        and again.prompt_json["source"] == "list.csv"
    )
    third, _ = await practice.add_vocab(
        db, learner.id, lang="de", word="Haus", translation="house", example="Another example."
    )
    assert (
        third.prompt_json["example"] == "Das Haus ist alt."
    )  # an existing example is not overwritten


async def test_legacy_ref_is_adopted_not_duplicated(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    node = await practice.vocab_deck(db, "de")
    legacy, _ = await memory.ensure_item(
        db,
        learner.id,
        node.id,
        "vocab",
        {"ref": "de:baum", "type": "vocab", "q": "Baum", "a": "tree", "lang": "de"},
    )
    adopted, created = await practice.add_vocab(
        db, learner.id, lang="de", word="Baum", translation="tree"
    )
    assert not created and adopted.id == legacy.id
    assert adopted.prompt_json["ref"] == "de:forward:baum:tree"
    other, created2 = await practice.add_vocab(
        db, learner.id, lang="de", word="Baum", translation="beam"
    )
    assert created2 and other.id != legacy.id  # a different meaning is a new card


def test_parse_csv_variants_and_statuses() -> None:
    bom_semicolon = "﻿Wort;Bedeutung;Beispiel\nHaus;house;Das Haus\nBaum;tree\n;missing\nHaus ; House ;x\n".encode()
    pv = parse_csv(bom_semicolon)
    assert (
        pv.header
        and pv.delimiter == ";"
        and pv.columns == {"word": 0, "translation": 1, "example": 2}
    )
    statuses = [(r.word, r.status) for r in pv.rows]
    assert statuses == [
        ("Haus", "new"),
        ("Baum", "new"),
        ("", "invalid"),
        ("Haus", "duplicate_in_file"),
    ]
    assert pv.rows[2].problem == "word and translation are required"
    tab_no_header = b"front\tback\napple\tApfel\n"  # 'front/back' is a recognised header
    pv = parse_csv(tab_no_header)
    assert pv.header and pv.delimiter == "\t" and [r.word for r in pv.rows] == ["apple"]
    positional = '"dog, the",Hund\ncat,Katze,"Die Katze schläft"\n'.encode()
    pv = parse_csv(positional)
    assert not pv.header and [(r.word, r.translation, r.example) for r in pv.rows] == [
        ("dog, the", "Hund", None),
        ("cat", "Katze", "Die Katze schläft"),
    ]
    too_long = ("x" * 121 + ",y\n").encode()
    assert parse_csv(too_long).rows[0].status == "invalid"
    assert parse_csv(b"").errors == ["empty file"]
    assert "larger than" in parse_csv(b"a,b\n" * 600_000).errors[0]
    many = ("w,m\n" + "".join(f"w{i},m{i}\n" for i in range(2005))).encode()
    pv = parse_csv(many)
    assert len(pv.rows) == 2000 and "first 2000" in pv.errors[0]
    latin1 = "Stra\xdfe,street\n".encode("cp1252")
    assert parse_csv(latin1).rows[0].word == "Straße"


async def test_preview_marks_existing_and_import_is_idempotent_and_atomic(
    db: AsyncSession, learner: models.LearnerProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    learner_id = learner.id  # the rollback below expires ORM instances; keep the plain id
    await practice.add_vocab(db, learner_id, lang="de", word="Haus", translation="house")
    data = b"word,translation\nHaus,house\nBaum,tree\nBaum,tree\nKatze,\n"
    pv = await vocab_import.preview(db, learner_id, lang="de", data=data)
    assert pv.counts == {
        "new": 1,
        "exists": 1,
        "reverse_only": 0,
        "duplicate_in_file": 1,
        "invalid": 1,
    }
    rows = [{"word": r.word, "translation": r.translation, "example": r.example} for r in pv.rows]
    res = await vocab_import.import_rows(db, learner_id, lang="de", rows=rows, source="list.csv")
    assert (res.added, res.skipped_existing, res.invalid, res.reverse_added) == (1, 1, 1, 0)
    assert res.duplicate_in_file == 1
    cards = await _cards(db, learner_id)
    assert len(cards) == 2 and any(c.prompt_json.get("source") == "list.csv" for c in cards)
    # the same file again: nothing added, nothing touched
    res2 = await vocab_import.import_rows(db, learner_id, lang="de", rows=rows, source="list.csv")
    assert res2.added == 0 and res2.skipped_existing == 2 and len(await _cards(db, learner_id)) == 2
    # with reverse cards: existing forward cards are skipped, reverse ones created once
    res3 = await vocab_import.import_rows(db, learner_id, lang="de", rows=rows, reverse=True)
    assert res3.added == 0 and res3.reverse_added == 2 and len(await _cards(db, learner_id)) == 4
    pv2 = await vocab_import.preview(db, learner_id, lang="de", data=data, reverse=True)
    assert pv2.counts["exists"] == 2  # both directions exist now
    assert res3.reverse_skipped == 0 and res.duplicate_in_file == 1  # counted, not dropped silently
    # atomic: a failure mid-way leaves no half-imported deck
    calls = {"n": 0}
    real = practice.add_vocab

    async def flaky(*a, **kw):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("disk full")
        return await real(*a, **kw)

    monkeypatch.setattr(practice, "add_vocab", flaky)
    fresh = [{"word": f"n{i}", "translation": f"m{i}"} for i in range(3)]
    with pytest.raises(RuntimeError):
        await vocab_import.import_rows(db, learner_id, lang="fr", rows=fresh)
    langs = (
        await db.execute(
            select(ReviewItem.prompt_json).where(
                ReviewItem.learner_id == learner_id, ReviewItem.item_type == "vocab"
            )
        )
    ).scalars()
    assert not any(pj.get("lang") == "fr" for pj in langs)  # rolled back: no half-imported deck
    with pytest.raises(ValueError):
        await vocab_import.import_rows(
            db, learner_id, lang="de", rows=[{"word": "a", "translation": "b"}] * 2001
        )


async def test_import_routes(client: AsyncClient) -> None:
    csv_text = "Wort;Bedeutung\nHaus;house\nBaum;tree\n"
    r = await client.post(
        "/api/vocab/import/preview", json={"lang": "de", "csv_text": csv_text, "reverse": False}
    )
    assert r.status_code == 200, r.text
    pv = r.json()
    assert pv["header"] and pv["delimiter"] == ";" and pv["counts"]["new"] == 2
    rows = [
        {"word": x["word"], "translation": x["translation"], "example": x["example"]}
        for x in pv["rows"]
    ]
    r = await client.post(
        "/api/vocab/import",
        json={"lang": "de", "rows": rows, "reverse": True, "source": "words.csv"},
    )
    assert r.status_code == 201, r.text
    assert r.json() == {
        "lang": "de",
        "added": 2,
        "reverse_added": 2,
        "reverse_skipped": 0,
        "skipped_existing": 0,
        "duplicate_in_file": 0,
        "invalid": 0,
    }
    decks = (await client.get("/api/vocab")).json()
    assert decks["decks"][0]["cards"] == 4
    r = await client.post("/api/vocab/import", json={"lang": "de", "rows": rows, "reverse": False})
    assert r.json()["added"] == 0 and r.json()["skipped_existing"] == 2
    r = await client.post("/api/vocab/import/preview", json={"lang": "de", "csv_text": ""})
    assert r.status_code == 200 and r.json()["errors"] == ["empty file"]


def test_parse_csv_quoting_order_unicode_and_lang_header() -> None:
    quoted = b'"Wort";"Bedeutung"\n"Bank, die";bench\n'  # quoted cells with commas inside
    pv = parse_csv(quoted)
    assert pv.delimiter == ";" and pv.header and pv.rows[0].word == "Bank, die"
    reordered = b"Bedeutung;Wort\nhouse;Haus\n"
    pv = parse_csv(reordered)
    assert pv.columns == {"translation": 0, "word": 1} and pv.rows[0].word == "Haus"
    pipes = b"cat|Katze|Die Katze\n"
    pv = parse_csv(pipes)
    assert pv.delimiter == "|" and pv.rows[0].example == "Die Katze"
    codes = b"de,en\nHaus,house\n"
    pv = parse_csv(codes, lang="en")
    assert pv.rows[0].word == "house" and pv.rows[0].translation == "Haus"  # deck language = word
    pv = parse_csv(codes, lang="de")
    assert pv.rows[0].word == "Haus"
    example_only = b",,just an example\n"
    assert parse_csv(example_only).rows[0].status == "invalid"
    # identity: NFC == NFD, but Maße ≠ Masse (lower(), not casefold())
    assert practice.norm_text("caf\u00e9") == practice.norm_text("cafe\u0301")
    assert practice.norm_text("Maße") != practice.norm_text("Masse")
    assert practice.vocab_ref("de", "forward", "a:b", "c") != practice.vocab_ref(
        "de", "forward", "a", "b:c"
    )


async def test_preview_never_creates_a_deck_and_reverse_only_status(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    from app.db.models import SkillNode

    pv = await vocab_import.preview(db, learner.id, lang="xx", data=b"a,b\n")
    assert pv.counts["new"] == 1
    node = (
        await db.execute(select(SkillNode).where(SkillNode.slug == practice.deck_slug("xx")))
    ).scalar_one_or_none()
    assert node is None  # nothing saved by a preview
    await practice.add_vocab(db, learner.id, lang="de", word="Haus", translation="house")
    pv = await vocab_import.preview(db, learner.id, lang="de", data=b"Haus,house\n", reverse=True)
    assert pv.rows[0].status == "reverse_only"  # honest: only the reverse card is new
    res = await vocab_import.import_rows(
        db, learner.id, lang="de", rows=[{"word": "Haus", "translation": "house"}], reverse=True
    )
    assert (res.added, res.skipped_existing, res.reverse_added) == (0, 1, 1)


def test_identity_migration_rewrites_legacy_refs(tmp_path: Path) -> None:
    """The data step runs on a disposable DB with a pre-P3 card: ref rewritten, ids and FSRS rows
    untouched; downgrade restores the legacy ref."""
    import json
    import sqlite3

    from alembic import command
    from app.db.migrate import alembic_config

    db_file = tmp_path / "legacy.db"
    url = f"sqlite:///{db_file}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "5798bbccbea6")  # the revision before the identity change
    conn = sqlite3.connect(db_file)
    conn.execute(
        "INSERT INTO skill_node (id, domain, slug, title, description, success_criteria_json, "
        "assessment_requirements_json, example_applications_json, created_at) "
        "VALUES ('N1', 'language', 'lang-de', 'German vocabulary', '', '[]', '{}', '[]', 't')"
    )
    prompt = {"ref": "de:baum", "type": "vocab", "q": "Baum", "a": "tree", "lang": "de"}
    conn.execute(
        "INSERT INTO review_item (id, learner_id, skill_id, object_id, item_type, prompt_json, "
        "active, created_at) VALUES ('I1', 'L1', 'N1', NULL, 'vocab', ?, 1, 't')",
        (json.dumps(prompt),),
    )
    conn.execute(
        "INSERT INTO memory_state (id, learner_id, review_item_id, fsrs_card_json, state, due) "
        "VALUES ('M1', 'L1', 'I1', '{}', 'new', 't')"
    )
    conn.commit()
    ms_before = conn.execute("SELECT * FROM memory_state").fetchall()
    conn.close()
    command.upgrade(cfg, "ffb15bdebad6")
    conn = sqlite3.connect(db_file)
    (raw,) = conn.execute("SELECT prompt_json FROM review_item WHERE id='I1'").fetchone()
    assert json.loads(raw)["ref"] == "de:forward:baum:tree"
    assert json.loads(raw)["direction"] == "forward"
    assert conn.execute("SELECT * FROM memory_state").fetchall() == ms_before
    conn.close()
    command.downgrade(cfg, "5798bbccbea6")
    conn = sqlite3.connect(db_file)
    (raw,) = conn.execute("SELECT prompt_json FROM review_item WHERE id='I1'").fetchone()
    assert json.loads(raw)["ref"] == "de:baum"
    conn.close()
