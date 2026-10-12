"""Fake transport and durable accounting; never calls a hosted model."""

import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts/eval_hosted_glimmer.py"
    spec = importlib.util.spec_from_file_location("hosted_trial", path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_pending_request_survives_restart_and_blocks_resend(tmp_path):
    m = module()
    path = tmp_path / "journal.db"
    journal = m.Journal(path)
    assert journal.reserve("one")
    journal.db.close()
    restored = m.Journal(path)
    with pytest.raises(ValueError, match="Uncertain"):
        restored.reserve("one")
    with pytest.raises(ValueError, match="Uncertain"):
        restored.reserve("two")
    restored.settle("one", {"accounting_valid": False, "cost_usd": None})
    assert restored.report()["results"][0]["state"] == "halted"
    restored.db.close()


def test_settled_cases_are_not_repeated_and_campaign_is_eight_total(tmp_path):
    m = module()
    path = tmp_path / "journal.db"
    for number in range(8):
        journal = m.Journal(path)
        assert journal.reserve(str(number))
        journal.settle(str(number), {"cost_usd": "0.001", "accounting_valid": True})
        assert not journal.reserve(str(number))
        journal.db.close()
    journal = m.Journal(path)
    assert journal.report()["accounted_with_fee_usd"] == "0.008440"
    with pytest.raises(ValueError, match="exhausted"):
        journal.reserve("extra")
    journal.db.close()


def test_competing_process_connections_reserve_only_once(tmp_path):
    m = module()
    path = tmp_path / "journal.db"
    m.Journal(path).db.close()

    def attempt(name):
        journal = m.Journal(path)
        try:
            return journal.reserve(name)
        except ValueError:
            return False
        finally:
            journal.db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, ["first", "second"])) == [False, True]


def events(m, *, cost="0.0001", provider="DeepInfra", finish="stop", done=True):
    chunks = [
        {
            "model": m.MODEL,
            "provider": provider,
            "choices": [{"delta": {"reasoning": "not visible"}, "finish_reason": None}],
        },
        {"choices": [{"delta": {"content": "Answer"}, "finish_reason": None}]},
        {
            "choices": [{"delta": {}, "finish_reason": finish}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 30,
                "cost": cost,
                "completion_tokens_details": {"reasoning_tokens": 10},
            },
        },
    ]
    return (
        ": heartbeat\n\n"
        + "".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
        + ("data: [DONE]\n\n" if done else "")
    )


async def test_stream_uses_visible_text_and_preserves_accounting():
    m = module()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text=events(m)))
    ) as client:
        result = await m.stream_reply(client, {"model": m.MODEL})
    assert result["text"] == "Answer"
    assert result["first_visible_seconds"] is not None
    assert result["status"] == "completed"
    assert result["reasoning_tokens"] == 10
    assert result["tokens_out"] == 30  # reasoning is a subset, not added again
    assert result["cost_usd"] == "0.0001"


@pytest.mark.parametrize(
    "options",
    [
        {"done": False},
        {"cost": None},
        {"cost": "-1"},
        {"cost": "NaN"},
        {"provider": "Together"},
        {"finish": "error"},
    ],
)
async def test_ambiguous_stream_is_rejected(options):
    m = module()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text=events(m, **options)))
    ) as client:
        with pytest.raises((ValueError, ArithmeticError)):
            await m.stream_reply(client, {})


def test_catalog_price_drift_is_rejected():
    m = module()
    payload = {
        "data": {
            "id": m.MODEL,
            "endpoints": [
                {
                    "tag": m.PROVIDER,
                    "status": 0,
                    "context_length": m.CONTEXT_LIMIT,
                    "max_completion_tokens": 16384,
                    "supported_parameters": ["max_tokens", "temperature"],
                    "pricing": {"prompt": "0.0000003", "completion": "0.0000012"},
                }
            ],
        }
    }
    m.validate_catalog(payload)
    payload["data"]["endpoints"][0]["pricing"]["prompt"] = "0.0000004"
    with pytest.raises(ValueError, match="contract changed"):
        m.validate_catalog(payload)


def test_catalog_request_surcharge_is_rejected():
    m = module()
    payload = {
        "data": {
            "id": m.MODEL,
            "endpoints": [
                {
                    "tag": m.PROVIDER,
                    "status": 0,
                    "context_length": m.CONTEXT_LIMIT,
                    "max_completion_tokens": 16384,
                    "supported_parameters": ["max_tokens", "temperature"],
                    "pricing": {"prompt": "0.0000003", "completion": "0.0000012", "request": "2"},
                }
            ],
        }
    }
    with pytest.raises(ValueError, match="contract changed"):
        m.validate_catalog(payload)


async def test_full_fake_campaign_never_repeats_calls(tmp_path, monkeypatch, capsys):
    m = module()
    monkeypatch.setattr(m, "JOURNAL", tmp_path / "campaign.db")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    calls = []
    catalog = {
        "data": {
            "id": m.MODEL,
            "endpoints": [
                {
                    "tag": m.PROVIDER,
                    "status": 0,
                    "context_length": m.CONTEXT_LIMIT,
                    "max_completion_tokens": 16384,
                    "supported_parameters": ["max_tokens", "temperature"],
                    "pricing": {"prompt": "0.0000003", "completion": "0.0000012", "request": "0"},
                }
            ],
        }
    }

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalog)
        body = json.loads(request.content)
        assert body["provider"]["max_price"] == {"prompt": 0.3, "completion": 1.2, "request": 0}
        assert body["provider"]["only"] == ["deepinfra/bf16"]
        assert body["provider"]["allow_fallbacks"] is False
        assert body["max_tokens"] == 900
        calls.append(body)
        return httpx.Response(200, text=events(m))

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        m.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(**kwargs, transport=httpx.MockTransport(handler)),
    )
    await m.run()
    await m.run()
    assert len(calls) == 8
    expected = m.load_requests(m.SOURCE)
    assert [c["messages"] for c in calls] == [r["body"]["messages"] for r in expected]
    assert "synthetic-key" not in capsys.readouterr().out


async def test_empty_length_reply_does_not_count_as_visible_answer():
    m = module()
    payload = events(m, finish="length").replace('"content": "Answer"', '"content": ""')
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text=payload))
    ) as client:
        result = await m.stream_reply(client, {})
    assert result["first_visible_seconds"] is None
    assert result["status"] == "incomplete"


async def test_inconsistent_reasoning_is_flagged_not_double_billed():
    m = module()
    payload = events(m).replace('"reasoning_tokens": 10', '"reasoning_tokens": 40')
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text=payload))
    ) as client:
        result = await m.stream_reply(client, {})
    assert result["usage_detail_warning"] == "inconsistent_reasoning_breakdown"
    assert result["cost_usd"] == "0.0001"
    assert result["tokens_out"] == 30
