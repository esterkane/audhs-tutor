"""Offline safeguards; no credentials or paid requests."""

import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts/eval_ask_hosted.py"
    spec = importlib.util.spec_from_file_location("ask_hosted_trial", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_frozen_contract_and_changed_schema(tmp_path, monkeypatch):
    m = module()
    campaign = m.load_campaign()
    assert len(campaign["cases"]) == 5
    assert m.reservation() * 5 < m.CEILING
    path = tmp_path / "changed.json"
    path.write_bytes(m.SOURCE.read_bytes() + b" ")
    with pytest.raises(ValueError, match="changed"):
        m.load_campaign(path)
    monkeypatch.setattr(m.AnswerReviewProposal, "model_json_schema", lambda: {})
    with pytest.raises(ValueError, match="schema changed"):
        m.load_campaign()


def test_pending_restart_unknown_case_and_no_resend(tmp_path):
    m = module()
    campaign = m.load_campaign()
    path = tmp_path / "journal.db"
    first = m.Journal(path, campaign)
    assert first.reserve("generate-explicit")
    first.db.close()
    second = m.Journal(path, campaign)
    with pytest.raises(ValueError, match="Uncertain"):
        second.reserve("generate-explicit")
    second.settle("generate-explicit", {"accounting_valid": True, "cost_usd": "0.001"})
    assert not second.reserve("generate-explicit")
    with pytest.raises(ValueError, match="Unknown"):
        second.reserve("sixth")
    second.db.close()


@pytest.mark.parametrize("cost", [None, "NaN", "Infinity", "-1", "99"])
def test_uncertain_or_excess_billing_halts(tmp_path, cost):
    m = module()
    j = m.Journal(tmp_path / "journal.db", m.load_campaign())
    j.reserve("generate-explicit")
    j.settle("generate-explicit", {"accounting_valid": True, "cost_usd": cost})
    assert j.report()["results"][0]["state"] == "halted"
    with pytest.raises(ValueError, match="Uncertain"):
        j.reserve("generate-guided")
    j.db.close()


def test_parallel_reservation_only_one_can_send(tmp_path):
    m = module()
    campaign = m.load_campaign()
    path = tmp_path / "journal.db"
    m.Journal(path, campaign).db.close()

    def reserve(_):
        j = m.Journal(path, campaign)
        try:
            return j.reserve("generate-explicit")
        except ValueError:
            return False
        finally:
            j.db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(reserve, range(2))) == 1


def test_all_five_consumed_and_changed_journal_identity(tmp_path):
    m = module()
    campaign = m.load_campaign()
    j = m.Journal(tmp_path / "journal.db", campaign)
    for case in campaign["cases"]:
        assert j.reserve(case["id"])
        j.settle(case["id"], {"accounting_valid": True, "cost_usd": "0.001"})
    for case in campaign["cases"]:
        assert not j.reserve(case["id"])
    j.db.execute("UPDATE campaign SET identity='other'")
    j.db.commit()
    j.db.close()
    with pytest.raises(ValueError, match="different campaign"):
        m.Journal(tmp_path / "journal.db", campaign)


def test_review_valid_quotes_do_not_claim_semantic_pass():
    m = module()
    case = m.load_campaign()["cases"][3]
    source = json.loads(
        case["messages"][2]["content"]
        .removeprefix("<source_passages>\n")
        .removesuffix("\n</source_passages>")
    )
    text = {
        "claims": [
            {
                "claim_quote": case["answer"],
                "verdict": "supported",
                "explanation": "The source states this rule.",
                "evidence": [{"passage_id": next(iter(source)), "quote": case["answer"]}],
            }
        ]
    }
    result = {"text": json.dumps(text), "status": "completed", "first_visible_seconds": 1}
    m.check_review(case, result)
    assert result["schema_and_quote_binding"] == "passed_not_semantic_verification"
    assert result["target_claim_coverage"] == "requires_human_review"
    assert "first_visible_seconds" not in result
    text["claims"][0]["evidence"][0]["quote"] = "invented quotation"
    result["text"] = json.dumps(text)
    m.check_review(case, result)
    assert result["status"] == "invalid_review"


async def test_missing_approval_cannot_start(monkeypatch):
    m = module()
    monkeypatch.setattr(m, "load_campaign", lambda: pytest.fail("Must reject before loading"))
    with pytest.raises(ValueError, match="approval"):
        await m.run("unapproved")


async def test_frozen_requests_only_once_and_redacted_key(tmp_path, monkeypatch, capsys):
    import httpx

    m = module()
    campaign = m.load_campaign()
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setattr(m, "JOURNAL", tmp_path / "journal.db")
    calls = []
    catalog = {
        "data": {
            "id": m.MODEL,
            "endpoints": [
                {
                    "tag": "deepinfra/bf16",
                    "status": 0,
                    "context_length": 131072,
                    "max_completion_tokens": 16384,
                    "supported_parameters": ["temperature", "max_tokens", "response_format"],
                    "pricing": {"prompt": "0.0000003", "completion": "0.0000012", "request": "0"},
                }
            ],
        }
    }

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalog)
        body = json.loads(request.content)
        calls.append(body)
        chunk = {
            "model": m.MODEL,
            "provider": "DeepInfra",
            "choices": [{"delta": {"content": "Synthetic answer"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 1000, "cost": "0.002"},
        }
        return httpx.Response(200, text="data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n")

    original = httpx.AsyncClient
    monkeypatch.setattr(
        m.httpx,
        "AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler)),
    )
    await m.run(m.DIGEST)
    await m.run(m.DIGEST)
    assert calls == [case["request_body"] for case in campaign["cases"]]
    assert "synthetic-key" not in capsys.readouterr().out
    journal = m.Journal(m.JOURNAL, campaign)
    assert all(row["state"] == "settled" for row in journal.report()["results"])
    assert journal.report()["results"][2]["result"]["status"] == "invalid_review"
    journal.db.close()
