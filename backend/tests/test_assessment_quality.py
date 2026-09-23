from app.kernel import curriculum
from app.kernel.assessment_quality import unsuitable_question


def test_orientation_and_logistics_are_not_competency_questions() -> None:
    for text in [
        "What is the primary focus of Part 1 of the course?",
        "What is the estimated API cost for the entire course?",
        "According to the course materials, which hardware option is recommended "
        "for most students starting with Part 1?",
        "According to the lecture, which hardware option is recommended for most students?",
        "Explain the course roadmap and what you will learn.",
        "Explain 'Welcome & What You’ll Build' in your own words.",
    ]:
        assert unsuitable_question(text)


def test_subject_matter_is_not_rejected_just_for_its_vocabulary() -> None:
    for text in [
        "How does the learning rate affect gradient descent?",
        "Explain how the learning rate in this lecture affects convergence.",
        "Compare module-level scope with local scope in Python.",
        "Predict the welcome message printed by this function.",
        "Choose a hosting option for a continuously running agent and justify the tradeoff.",
        "What does container isolation restrict, and what does it not guarantee?",
        "Explain the attention mechanism using the lecture example.",
        "Explain training in your own words, as the lecture teaches it: what it is for and how it works.",
        "Estimate request cost from token counts and a supplied price table.",
    ]:
        assert not unsuitable_question(text)


def test_source_cut_questions_skip_course_promises() -> None:
    chunks = [
        {
            "id": "welcome",
            "text": "Heading\nThis course covers local agent architecture and a roadmap of upcoming lessons.",
        }
    ]
    assert curriculum._cloze_candidates("Local agent architecture", chunks) == []


async def test_course_logistics_cannot_publish_even_when_hand_edited(db, learner) -> None:
    payload = {
        "skills": [
            {
                "slug": "agent",
                "title": "Agent",
                "prerequisites": [],
                "success_criteria": ["Explain the course roadmap."],
            }
        ],
        "learning_objects": [
            {"skill": "agent", "concept": "Agent", "goal": "Use an agent", "sources": []}
        ],
        "assessments": [
            {
                "skill": "agent",
                "kind": "mcq",
                "item": {
                    "question": "What is the primary focus of Part 1 of the course?",
                    "options": ["a", "b"],
                    "answer": 0,
                },
            }
        ],
    }
    problems = await curriculum.validate_payload(db, payload)
    assert any(p.level == "error" and "orientation or logistics" in p.message for p in problems)
    assert any(p.level == "error" and "success criteria describe" in p.message for p in problems)


async def test_model_metadata_is_omitted_but_substantive_concepts_survive(monkeypatch) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.orchestrator import drafting

    mat = curriculum.SectionMaterial(
        course="Agents",
        section="Orientation",
        lectures=[
            {
                "lecture": "Welcome & What You’ll Build",
                "title": "Welcome",
                "document_id": "doc",
                "chunks": [
                    {
                        "id": "substance",
                        "text": "Header\nAn agent uses tools to read files and save reports in a workspace.",
                    }
                ],
            }
        ],
    )
    slug = curriculum.lecture_slugs(mat)[0]
    monkeypatch.setattr(curriculum, "section_material", AsyncMock(return_value=mat))
    suggestion = drafting.LessonSuggestion(
        slug=slug,
        goal="Use file tools.",
        concept="File workflows",
        success_criteria=["Explain the course roadmap.", "Distinguish tools from reasoning."],
        explain_back_prompt="How would an agent turn workspace files into a saved report?",
        explain_source_chunk_id="substance",
        source_chunk_id="invented",
        mcq_question="What is the primary focus of the course?",
        mcq_options=["a", "b", "c", "d"],
        mcq_answer=0,
    )
    gateway = SimpleNamespace(
        complete=AsyncMock(
            return_value=SimpleNamespace(
                model_call_id="call",
                result=SimpleNamespace(parsed=drafting.DraftSuggestions(lessons=[suggestion])),
            )
        )
    )
    payload, _, _ = await drafting.draft_with_model(
        None, gateway, "owner", course=mat.course, section=mat.section
    )
    assert payload["skills"][0]["title"] == "File workflows"
    assert payload["skills"][0]["success_criteria"] == ["Distinguish tools from reasoning."]
    assert payload["learning_objects"][0]["success_criteria"] == [
        "Distinguish tools from reasoning."
    ]
    assert len(payload["assessments"]) == 1
    assert payload["assessments"][0]["source_chunk_id"] == "substance"
    assert payload["assessments"][0]["item"]["prompt"].startswith("How would an agent")
    assert payload["quality_notes"]
    assert "[source substance]" in gateway.complete.call_args.args[1][1].content
    suggestion.assessable = False
    payload, _, _ = await drafting.draft_with_model(
        None, gateway, "owner", course=mat.course, section=mat.section
    )
    assert payload["assessments"] == []


async def test_required_dimensions_without_matching_questions_block_activation(db) -> None:
    payload = {
        "skills": [
            {
                "slug": "agent",
                "title": "Agent",
                "prerequisites": [],
                "assessment_requirements": {"dimensions": ["recall", "explanation"]},
            }
        ],
        "learning_objects": [
            {"skill": "agent", "concept": "Agent", "goal": "Use tools", "sources": []}
        ],
        "assessments": [
            {
                "skill": "agent",
                "kind": "mcq",
                "item": {
                    "question": "Which component reads a file?",
                    "options": ["Tool", "Model"],
                    "answer": 0,
                },
            }
        ],
    }
    problems = await curriculum.validate_payload(db, payload)
    assert any(p.level == "error" and "no explain_back item" in p.message for p in problems)
    payload["assessments"] = [
        {
            "skill": "agent",
            "kind": "explain_back",
            "item": {"prompt": "How do tools read workspace files?"},
            "rubric": [{"criterion": "Distinguishes reasoning and execution"}],
        }
    ]
    problems = await curriculum.validate_payload(db, payload)
    assert any(p.level == "error" and "no mcq or cloze item" in p.message for p in problems)
