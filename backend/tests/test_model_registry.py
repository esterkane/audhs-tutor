from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_ai import registry
from app.models_ai.bench import bench_model, hard_checks, sentences, summarize
from app.models_ai.downloader import dir_size_gb, modelfile_for, slugify
from app.models_ai.fake import FakeProvider
from app.models_ai.provider import ModelSpec


def test_slugify_and_modelfile(tmp_path: Path) -> None:
    assert slugify("Qwen/Qwen2.5-0.5B-Instruct-GGUF", "qwen2.5-0.5b-instruct-q4_k_m.gguf") == (
        "qwen-qwen2.5-0.5b-instruct-gguf-qwen2.5-0.5b-instruct-q4-k-m"
    )
    assert slugify("llama3.1:8b") == "llama3.1-8b"
    p = tmp_path / "m.gguf"
    p.write_bytes(b"0" * 5_000_000)
    assert modelfile_for(p, num_ctx=8192) == f"FROM {p}\nPARAMETER num_ctx 8192\n"
    assert dir_size_gb(tmp_path) == pytest.approx(0.005)


def test_hard_checks() -> None:
    good = (
        "Think about the step size. What happens to the update when it is larger than the valley? "
        "Try halving it."
    )
    bad = "Great question! Visual learners like you should feel this. " + "Sentence. " * 8
    assert all(hard_checks(good).values())
    c = hard_checks(bad)
    assert not c["brevity_le_6_sentences"] and not c["no_banned_language"]
    assert sentences("One. Two? Three!") == 3


async def test_bench_with_fake_provider_and_store(db: AsyncSession) -> None:
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    fake = FakeProvider(text="Consider the learning rate first. What do you expect if it doubles?")
    spec = ModelSpec(registry_id="llama31-8b", provider="fake", model="x")
    bench = await bench_model(fake, spec)
    assert bench["tutoring_hard_checks"]["passed"] == bench["tutoring_hard_checks"]["total"] == 15
    assert bench["stream_chunks"] > 0 and "tok_per_s" in bench and bench["first_token_ms"] >= 0
    row = await registry.set_status(db, "llama31-8b", "ready", benchmark_json=bench)
    assert row.benchmark_json is not None and "15/15" in summarize(row.benchmark_json)


def test_spec_for_hf_gguf_uses_registry_id_as_ollama_tag() -> None:
    from app.db.models import ModelRegistry

    row = ModelRegistry(
        id="qwen25-05b",
        display_name="q",
        source="huggingface_gguf",
        repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        file_or_tag="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        runtime="ollama",
        role="chat",
    )
    spec = registry.spec_from_row(row)
    assert spec.model == "qwen25-05b" and spec.provider == "ollama" and not spec.hosted


def test_cli_parser_covers_contract() -> None:
    import importlib.util
    import sys

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("models_cli", root / "scripts" / "models.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["models_cli"] = mod
    spec.loader.exec_module(mod)
    p = mod.build_parser()
    a = p.parse_args(
        ["add", "huggingface_gguf", "Qwen/Qwen2.5-0.5B-Instruct-GGUF", "--file", "f.gguf"]
    )
    assert a.cmd == "add" and a.role == "chat"
    assert p.parse_args(["assign", "chat", "llama31-8b"]).task == "chat"
    assert set(mod.COMMANDS) == {
        "seed",
        "list",
        "search-hf",
        "info",
        "add",
        "pull",
        "bench",
        "assign",
        "rm",
    }
