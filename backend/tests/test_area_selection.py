from sqlalchemy import select

from app.db import models
from app.kernel import areas
from app.knowledge.ingest.service import ingest_path


def test_topic_tokens_do_not_match_unrelated_longer_words():
    assert not areas.passage_matches("Title\nCharacterTextSplitter splits text.", ["character"])
    assert not areas.passage_matches("Title\nBusiness canvas describes customers.", ["canva"])
    assert areas.passage_matches(
        "Title\nCharacters and prompts shape the scene.", ["character", "prompt"]
    )
    assert areas.passage_matches("Title\nStatistical evaluation of deployment.", ["statisti"])
    assert areas.passage_matches("Title\nEvaluating a model.", ["evaluat"])


async def test_selection_accepts_css_but_ignores_reports_and_intro(db, tmp_path):
    root = tmp_path / "CSS transitions"
    root.mkdir()
    (root / "CSS style.css").write_text(
        "button { background-color: blue; transition-duration: 3000ms; }\n"
        "button:hover { background-color: green; }"
    )
    (root / "CSS report.txt").write_text(
        "Report created: today\nProject name: CSS transitions.aep\n"
        "Source files collected: All\nCollected comps: Main\n"
        "Rendering plug-ins: Classic 3D\n" + "CSS animation project assets and files " * 15
    )
    (root / "CSS intro.md").write_text(
        "# CSS transitions\nWelcome to this course. You will learn CSS transitions. "
        "This course will teach you how to make beautiful effects. Get ready to learn "
        "all about the lessons and the topics that we will cover."
    )
    await ingest_path(db, root, course="CSS examples")
    area = models.KnowledgeArea(slug="css-test", title="CSS", terms_json=["css"])
    chosen, _ = await areas.excerpts(db, area)
    assert len(chosen) == 1
    assert "transition-duration: 3000ms" in chosen[0]["text"]
    doc = (
        await db.execute(
            select(models.Document).where(models.Document.id == chosen[0]["document_id"])
        )
    ).scalar_one()
    assert "style" in doc.title


def test_existing_technical_topic_plurals_keep_membership():
    for term, plural in [
        ("database", "Databases"),
        ("tensor", "Tensors"),
        ("gradient", "Gradients"),
    ]:
        assert areas.passage_matches("Title\n" + plural + " are discussed here.", [term])
        assert (
            areas.match(models.Document(title=plural, source_type="text"), [term])
            == "title/section"
        )
