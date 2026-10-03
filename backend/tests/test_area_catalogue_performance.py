"""Catalogue aggregation preserves metadata membership and yields during worker work."""

import asyncio
import threading
from types import SimpleNamespace

from app.db.models import CurriculumDraft, Document, KnowledgeArea, LearnerProfile
from app.kernel import areas


def test_grouped_counts_equal_document_membership_with_boundaries_and_overlaps():
    terms = tuple((slug, tuple(values)) for slug, _, values in areas.DEFAULTS) + (
        ("literal", (" C++ ", "", "Straße", "a.b")),
        ("empty", (" ",)),
    )
    docs = (
        ("Python and tensors", None, None, "Vectors"),
        ("Python and tensors", None, None, "Vectors"),
        ("pythonic agent_id ragtime", None, None, None),
        ("deployment and statistics", "C++", "STRASSE", ""),
        ("a.b but not axb", None, None, "Workflow"),
        ("unrelated", "SQL", "prompts", "DATABASES"),
    )
    counts, courses, related, assigned = areas._catalogue_counts(terms, docs)
    memberships = {
        identifier: {
            index
            for index, values in enumerate(docs)
            if areas.match(
                SimpleNamespace(
                    **dict(zip(("title", "section", "lecture", "course"), values, strict=True))
                ),
                list(values_terms),
            )
        }
        for identifier, values_terms in terms
    }
    assert counts == {identifier: len(members) for identifier, members in memberships.items()}
    assert counts["python"] == 2
    assert counts["literal"] == 2
    assert counts["empty"] == 0
    assert assigned == len(set().union(*memberships.values()))
    for identifier, members in memberships.items():
        assert courses[identifier] == sorted({docs[i][3] for i in members if docs[i][3]})
        assert related[identifier] == {
            other
            for other, values in memberships.items()
            if other != identifier and values & members
        }
    assert areas._catalogue_counts((), docs) == ({}, {}, {}, 0)


async def test_catalogue_offloads_plain_snapshots_and_scopes_drafts(db, learner, monkeypatch):
    area = KnowledgeArea(id="python-area", slug="python", title="Python", terms_json=["python"])
    other = LearnerProfile(id="other-owner", display_name="other")
    db.add_all([area, other, Document(title="python", source_type="manual", course="Course")])
    await db.flush()
    for identifier, owner, status in (
        ("owned", learner.id, "draft"),
        ("rejected", learner.id, "rejected"),
        ("foreign", other.id, "draft"),
    ):
        db.add(
            CurriculumDraft(
                id=identifier, learner_id=owner, area_id=area.id, title="Draft", status=status
            )
        )
    await db.commit()
    main_thread = threading.get_ident()
    started = threading.Event()
    released = threading.Event()
    original = areas._catalogue_counts

    def worker(area_terms, documents):
        assert threading.get_ident() != main_thread
        assert isinstance(area_terms, tuple) and isinstance(documents, tuple)
        assert all(isinstance(row, tuple) for row in documents)
        assert all(value is None or isinstance(value, str) for row in documents for value in row)
        started.set()
        assert released.wait(2), "event loop did not run while worker was waiting"
        return original(area_terms, documents)

    monkeypatch.setattr(areas, "_catalogue_counts", worker)
    task = asyncio.create_task(areas.catalogue(db, learner.id))
    for _ in range(200):
        if started.is_set():
            break
        await asyncio.sleep(0.005)
    assert started.is_set()
    released.set()
    result = await asyncio.wait_for(task, 2)
    assert result["total_documents"] == 1
    assert result["unassigned_documents"] == 0
    assert result["areas"][0]["documents"] == 1
    assert result["areas"][0]["draft_ids"] == ["owned"]
