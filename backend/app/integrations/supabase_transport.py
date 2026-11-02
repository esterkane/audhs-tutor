"""Adapt only the pinned native tutor's wire format to our structured gateway."""

from functools import lru_cache

_NATIVE_OUTPUT = """Write your answer as Markdown first (this is streamed to the learner), then end with
one fenced block ```` ```json tutor_turn ```` containing the `TutorTurn` object defined in
the TutorTurn schema below. Leave `text` out of the JSON: the app fills it with the Markdown you
just wrote, so do not repeat the answer. Rules:"""
_STRUCTURED_OUTPUT = """Return the structured response required by the host gateway. Put the complete
learner-facing Markdown answer in `text` and the TutorTurn metadata in `state`.
The host renders the protocol footer; do not put that footer inside `text`.
All TutorTurn field rules below apply to the metadata in `state`. Rules:"""
_NATIVE_TEXT = "- `text` is not part of the JSON: the app sets it to the streamed Markdown."
_STRUCTURED_TEXT = (
    "- `text` belongs to the outer structured response and contains the complete Markdown answer. "
    "The remaining TutorTurn fields belong to `state`."
)


@lru_cache(maxsize=1)
def _contracts() -> tuple[str, str, str, str]:
    from app.integrations.supabase_project import PROJECT_ROOT

    runtime = (PROJECT_ROOT / "prompts/tutor_runtime.md").read_text(encoding="utf-8").strip()
    schema = (PROJECT_ROOT / "prompts/tutor_output_schema.md").read_text(encoding="utf-8").strip()
    if runtime.count(_NATIVE_OUTPUT) != 1 or schema.count(_NATIVE_TEXT) != 1:
        return runtime, runtime, schema, schema
    return (
        runtime,
        runtime.replace(_NATIVE_OUTPUT, _STRUCTURED_OUTPUT, 1),
        schema,
        schema.replace(_NATIVE_TEXT, _STRUCTURED_TEXT, 1),
    )


def structured_project_policy(policy: str) -> str:
    """Preserve unknown prompts; never transform conversation or retrieved content.

    Both complete pinned sections must occur exactly once. Only the two contradictory
    transport instructions change; field constraints and all other policy stay intact.
    """
    runtime, adapted_runtime, schema, adapted_schema = _contracts()
    if policy.count(runtime) != 1 or policy.count(schema) != 1:
        return policy
    return policy.replace(runtime, adapted_runtime, 1).replace(schema, adapted_schema, 1)
