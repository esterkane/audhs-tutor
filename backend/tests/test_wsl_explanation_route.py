from app.models_ai.provider import TaskClass
from app.models_ai.routing import Router


def test_wsl_explanation_uses_evaluated_local_candidate_without_reassigning_grading() -> None:
    router = Router("wsl")
    assert router.chain_for(TaskClass.EXPLAIN_SIMPLE)[0] == "qwen3-14b"
    assert router.chain_for(TaskClass.GRADE_SIMPLE)[0] == "gemma3-12b"
    assert router.chain_for(TaskClass.GEN_ITEMS)[0] == "gemma3-12b"
    assert router.chain_for(TaskClass.ANSWER_FEEDBACK) == ["qwen3-14b"]
