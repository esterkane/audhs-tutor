import copy

import pytest

from app.integrations.supabase_project import project_module
from app.integrations.supabase_transport import (
    _NATIVE_OUTPUT,
    _NATIVE_TEXT,
    _STRUCTURED_OUTPUT,
    _STRUCTURED_TEXT,
    structured_project_policy,
)
from tests.test_supabase_local_bridge import setup_bridge


@pytest.mark.parametrize("persona", [False, True])
def test_actual_prompt_changes_only_transport_instructions(persona):
    project_module()
    from backend.tutor.prompt import static_prefix

    original = static_prefix(persona, "Learner")
    changed = structured_project_policy(original)
    assert changed != original
    assert _NATIVE_OUTPUT not in changed
    assert _NATIVE_TEXT not in changed
    assert changed.replace(_STRUCTURED_OUTPUT, _NATIVE_OUTPUT).replace(
        _STRUCTURED_TEXT, _NATIVE_TEXT
    ) == original
    assert structured_project_policy(changed) == changed


@pytest.mark.parametrize("policy", ["Unrelated policy", _NATIVE_OUTPUT, _NATIVE_TEXT])
def test_incomplete_or_unknown_contract_is_untouched(policy):
    assert structured_project_policy(policy) == policy


def test_ambiguous_repeated_contract_is_untouched():
    project_module()
    from backend.tutor.prompt import static_prefix

    original = static_prefix(False, "Learner") * 2
    assert structured_project_policy(original) == original


async def test_adapter_changes_policy_only_and_preserves_full_history(monkeypatch):
    project_module()
    from backend.tutor.prompt import static_prefix

    client, complete, _, _ = setup_bridge(monkeypatch)
    policy = static_prefix(True, "Learner")
    history = [{"role": "user", "content": policy},
               {"role": "assistant", "content": "Earlier answer\n```json tutor_turn\n{}\n```"}]
    original = copy.deepcopy(history)
    async with client.messages.stream(
        system=[{"text": policy}], messages=history, tools=[], max_tokens=16000
    ):
        pass
    messages = complete.call_args.args[1]
    assert _NATIVE_OUTPUT not in messages[0].content
    assert messages[1].content == policy
    assert messages[2].content == history[1]["content"]
    assert history == original
    assert complete.call_args.kwargs["max_tokens"] == 16000
