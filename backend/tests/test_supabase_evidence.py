import copy
import json

import pytest

from app.integrations.supabase_evidence import retry_report, stored_experiments
from app.kernel.evidence_answers import UnsupportedPlan


def observation(workers=2, minimum=1, first="a"):
    runs = []
    decision = workers > minimum
    victim = "b" if first == "a" else "a"
    for level, strategy in [
        ("read committed", "none"),
        ("repeatable read", "none"),
        ("serializable", "none"),
        ("serializable", "full"),
        ("serializable", "update_only"),
    ]:
        tx = {
            actor: {
                "read": {"count": workers},
                "decision": decision,
                "updated": int(decision),
                "committed": True,
                "error": None,
            }
            for actor in ["a", "b"]
        }
        retry = None
        if level == "serializable" and decision:
            tx[victim]["committed"] = False
            tx[victim]["error"] = {"sqlstate": "40001", "stage": "commit"}
        final = workers - sum(t["updated"] for t in tx.values() if t["committed"])
        if strategy != "none" and decision:
            count = workers - 1 if strategy == "full" else workers
            retry = {
                "transaction": victim,
                "read": {"count": count} if strategy == "full" else None,
                "decision": count > minimum,
                "updated": int(count > minimum),
                "committed": True,
                "error": None,
            }
            final -= retry["updated"]
        runs.append(
            {
                "level": level,
                "retry_strategy": strategy,
                "transactions": tx,
                "retry": retry,
                "final_active": final,
                "minimum_satisfied": final >= minimum,
            }
        )
    return {
        "database": "lab",
        "schema_removed": True,
        "server_version": "17.11",
        "input": {"workers": workers, "minimum_active": minimum, "first_commit": first},
        "runs": runs,
    }


def recorded(value, identity="call-1"):
    return [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "compare_isolation_lab",
                    "id": identity,
                    "input": copy.deepcopy(value["input"]),
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": identity,
                    "is_error": False,
                    "content": json.dumps(value),
                }
            ],
        },
    ]


@pytest.mark.parametrize("language", ["en", "de"])
def test_saved_retry_comparison_copies_correct_decisions_counts_and_commit_order(language):
    history = recorded(observation()) + recorded(observation(minimum=0, first="b"), "call-2")
    before = copy.deepcopy(history)
    sources = stored_experiments(history)
    assert len(sources) == 2
    report = retry_report(sources, [s.source.id for s in sources], language=language)
    assert "1 > 1 = false" in report and "1 > 0 = true" in report
    assert "2 > 1 = true" in report and "2 > 0 = true" in report
    assert "A" in report and "B" in report
    assert (
        "do not deactivate own row" if language == "en" else "eigene Zeile nicht deaktivieren"
    ) in report
    assert (
        "no new read; reused original count 2"
        if language == "en"
        else "nicht neu gelesen; ursprüngliche Anzahl 2"
    ) in report
    assert all(s.source.id in report for s in sources)
    assert history == before


def test_no_retry_is_not_falsely_reported_as_a_missing_or_reused_fresh_count():
    source = stored_experiments(recorded(observation(minimum=2)))
    report = retry_report(source, [source[0].source.id], language="en")
    assert report.count("not performed") == 2
    assert "newly read count" not in report and "reused original count" not in report
    assert report.count("2 active rows afterwards") == 2


@pytest.mark.parametrize("workers,minimum", [(3, 1), (3, 2), (20, 19), (2, 0)])
def test_unseen_parameters_are_derived_from_recorded_predicates(workers, minimum):
    source = stored_experiments(recorded(observation(workers, minimum, "b")))
    report = retry_report(source, [source[0].source.id], language="en")
    expected = str(workers - 1) + " > " + str(minimum) + " = " + str(workers - 1 > minimum).lower()
    assert expected in report
    assert "original count " + str(workers) in report


@pytest.mark.parametrize(
    "change",
    [
        lambda h: h[0]["content"][0].update(name="search_docs"),
        lambda h: h[0]["content"][0]["input"].update(workers=3),
        lambda h: h[1]["content"][0].update(is_error=True),
        lambda h: h[1]["content"][0].update(tool_use_id="another"),
    ],
)
def test_only_matching_successful_owned_tool_records_are_sources(change):
    history = recorded(observation())
    change(history)
    assert stored_experiments(history) == ()


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v.update(schema_removed=False),
        lambda v: v["runs"][3]["retry"].update(decision=True),
        lambda v: v["runs"][4].update(final_active=1),
        lambda v: v["runs"][4]["retry"].update(read={"count": 1}),
        lambda v: v["runs"][3].pop("retry"),
        lambda v: v["runs"][3]["retry"].pop("read"),
    ],
)
def test_inconsistent_observations_cannot_be_rewritten_as_verified_answers(change):
    value = observation()
    change(value)
    assert stored_experiments(recorded(value)) == ()


def test_unknown_duplicate_or_other_session_selections_fail_closed():
    history = recorded(observation())
    sources = stored_experiments(history)
    identity = sources[0].source.id
    for selected in [["unknown"], [identity, identity], []]:
        with pytest.raises(UnsupportedPlan):
            retry_report(sources, selected, language="en")
    with pytest.raises(UnsupportedPlan):
        retry_report((), [identity], language="en")
    assert stored_experiments(history + history) == ()


def test_boolean_input_aliases_and_duplicate_result_replays_are_not_verified_sources():
    history = recorded(observation(minimum=0))
    history[0]["content"][0]["input"]["minimum_active"] = False
    assert stored_experiments(history) == ()
    history = recorded(observation())
    assert stored_experiments(history + [copy.deepcopy(history[-1])]) == ()


def test_initial_and_fresh_retry_counts_must_match_the_fixed_trial_schedule():
    value = observation()
    for tx in value["runs"][3]["transactions"].values():
        tx["read"]["count"] = 1
        tx["decision"] = False
    assert stored_experiments(recorded(value)) == ()
    value = observation()
    retry = value["runs"][3]["retry"]
    retry.update(read={"count": 2}, decision=True, updated=1)
    value["runs"][3].update(final_active=0, minimum_satisfied=False)
    assert stored_experiments(recorded(value)) == ()


def test_a_result_before_its_tool_call_is_not_authoritative_evidence():
    history = recorded(observation())
    assert stored_experiments(list(reversed(history))) == ()
