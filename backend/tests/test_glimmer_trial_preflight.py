"""Offline budget and synthetic-only boundaries; no provider access."""
import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts/glimmer_trial_preflight.py"
    spec = importlib.util.spec_from_file_location("glimmer_preflight", path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_frozen_requests_and_pinned_provider(tmp_path):
    m = module()
    root = Path(__file__).resolve().parents[2]
    source = root / "evals/results/teaching-glimmer-fixed-20261012.json"
    requests = m.load_requests(source)
    assert len(requests) == 8
    for item in requests:
        assert item["body"]["provider"] == {
            "only": ["deepinfra/bf16"], "allow_fallbacks": False, "require_parameters": True,
        }
    changed = tmp_path / "changed.json"
    changed.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(ValueError, match="frozen"):
        m.load_requests(changed)


def test_reservation_blocks_concurrent_or_over_budget_attempts():
    m = module()
    budget = m.CampaignBudget(m.reservation())
    assert budget.reserve() == m.reservation()
    with pytest.raises(ValueError, match="Unsettled"):
        budget.reserve()
    budget.settle(m.reservation() / m.FEE_MULTIPLIER)
    with pytest.raises(ValueError, match="Insufficient"):
        budget.reserve()
    assert m.reservation() * 8 < Decimal("1")


@pytest.mark.parametrize("cost", [None, Decimal("NaN"), Decimal("Infinity"), Decimal("-1")])
def test_unknown_or_invalid_billing_stops_campaign(cost):
    m = module()
    budget = m.CampaignBudget()
    reserved = budget.reserve()
    budget.settle(cost)
    assert budget.charged == reserved
    with pytest.raises(ValueError, match="halted"):
        budget.reserve()


def test_actual_charge_reconciles_with_fee_and_excess_halts():
    m = module()
    budget = m.CampaignBudget()
    budget.reserve()
    budget.settle(Decimal("0.001"))
    assert budget.charged == Decimal("0.001055")
    budget.reserve()
    budget.settle(Decimal("0.1"))
    assert budget.halted
    assert budget.charged == Decimal("0.106555")
    with pytest.raises(ValueError, match="No outstanding"):
        budget.settle(Decimal("0"))


@pytest.mark.parametrize("limit", ["0", "-1", "1.01", "NaN", "Infinity"])
def test_cannot_expand_approved_limit(limit):
    with pytest.raises(ValueError, match="Ceiling"):
        module().CampaignBudget(Decimal(limit))
