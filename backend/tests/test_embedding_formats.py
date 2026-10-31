import json

import httpx
import pytest

from app.core.config import Settings
from app.db.models import ModelRegistry
from app.kernel.learner import get_or_create_owner
from app.knowledge.reindex import embed_spec, embedding_collection
from app.models_ai import registry
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import EmbeddingFormat, ModelSpec, ProviderError, TaskClass


def qwen_spec():
    return registry.spec_from_row(
        ModelRegistry(
            id="qwen3-embedding-0.6b",
            display_name="Embedding fixture",
            source="ollama_library",
            repo_id="qwen3-embedding",
            file_or_tag="qwen3-embedding:0.6b",
            runtime="ollama",
            role="embed",
            context_len=32768,
        )
    )


def test_registry_supplies_dimension_and_model_specific_query_format():
    spec = qwen_spec()
    assert spec.embedding is not None and spec.embedding.dimensions == 768
    assert spec.embedding_inputs(["Original source\nSELECT 1;"]) == ["Original source\nSELECT 1;"]
    query = spec.embedding_inputs(["Was bedeutet SQLSTATE 42501?"], query=True)[0]
    assert query.startswith("Instruct: ") and "\nQuery: Was bedeutet SQLSTATE 42501?" in query


def test_legacy_inputs_and_existing_collection_are_unchanged():
    spec = ModelSpec(registry_id="legacy", provider="ollama", model="legacy")
    assert spec.embedding_inputs(["Original"]) == ["Original"]
    assert spec.embedding_inputs(["Question"], query=True) == ["Question"]
    assert spec.embedding_inputs(
        ["Question"], query=True, legacy_query_prefix="search_query: "
    ) == ["search_query: Question"]
    assert embedding_collection(spec) == "corpus_v1"


def test_new_vector_space_never_reuses_an_incompatible_collection():
    spec = qwen_spec()
    alternate = spec.model_copy(update={"embedding": EmbeddingFormat(dimensions=1024)})
    changed_prompt = spec.model_copy(
        update={"embedding": EmbeddingFormat(dimensions=768, query_prefix="Different: ")}
    )
    assert (
        len(
            {
                embedding_collection(spec),
                embedding_collection(alternate),
                embedding_collection(changed_prompt),
                embedding_collection(spec, 2),
                "corpus_v1",
            }
        )
        == 5
    )


@pytest.mark.parametrize(
    "size,expected_context", [(10, 2048), (3000, 4096), (6000, 8192), (40000, 32768)]
)
async def test_native_embedding_contract_keeps_input_and_sets_explicit_bounds(
    monkeypatch, size, expected_context
):
    posts = []
    original = httpx.AsyncClient
    text = "x" * size

    def handle(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        posts.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[0.0] * 768]})

    monkeypatch.setattr(
        "app.models_ai.ollama.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    result = await OllamaProvider("http://127.0.0.1:11434").embed(qwen_spec(), [text])
    assert len(result[0]) == 768
    assert posts == [
        {
            "model": "qwen3-embedding:0.6b",
            "input": [text],
            "truncate": False,
            "dimensions": 768,
            "options": {"num_ctx": expected_context},
        }
    ]


async def test_embedding_context_rejection_does_not_silently_clip_or_retry(monkeypatch):
    posts = []
    original = httpx.AsyncClient
    text = "Full input including its important ending."

    def handle(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        posts.append(json.loads(request.content))
        return httpx.Response(400, json={"error": "the input length exceeds the context length"})

    monkeypatch.setattr(
        "app.models_ai.ollama.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    with pytest.raises(ProviderError):
        await OllamaProvider("http://127.0.0.1:11434").embed(qwen_spec(), [text])
    assert len(posts) == 1 and posts[0]["input"] == [text] and posts[0]["truncate"] is False


async def test_corpus_respects_the_owners_explicit_embedding_assignment(db):
    await registry.seed_defaults(
        db, installed_ollama_tags={"nomic-embed-text", "qwen3-embedding:0.6b"}
    )
    owner = await get_or_create_owner(db)
    row = await registry.get_row(db, "qwen3-embedding-0.6b")
    row.benchmark_json = {"fixture": "offline embedding assignment contract"}
    await db.commit()
    await registry.assign(db, owner.id, TaskClass.EMBED, row.id)
    assert (await embed_spec(db, Settings())).registry_id == row.id


@pytest.mark.parametrize("vectors", [None, [], [[]], [[1.0]], [[True] * 768], [["bad"] * 768]])
async def test_invalid_embedding_vectors_never_enter_the_index(monkeypatch, vectors):
    original = httpx.AsyncClient

    def handle(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        return httpx.Response(200, json={"embeddings": vectors})

    monkeypatch.setattr(
        "app.models_ai.ollama.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    with pytest.raises(ProviderError):
        await OllamaProvider("http://127.0.0.1:11434").embed(qwen_spec(), ["A complete input"])


@pytest.mark.parametrize("floor", [2047, -1, 131073, True])
def test_invalid_embedding_context_floor_is_rejected(floor):
    with pytest.raises(ValueError):
        OllamaProvider("http://127.0.0.1:11434", embedding_context_floor=floor)


async def test_bulk_context_floor_only_increases_capacity_and_keeps_full_inputs(monkeypatch):
    posts = []
    original = httpx.AsyncClient

    def handle(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        posts.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[0.0] * 768]})

    monkeypatch.setattr(
        "app.models_ai.ollama.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    provider = OllamaProvider("http://127.0.0.1:11434", embedding_context_floor=8192)
    for text, expected in [("Short", 8192), ("x" * 10000, 16384), ("x" * 40000, 32768)]:
        await provider.embed(qwen_spec(), [text])
        assert posts[-1]["options"]["num_ctx"] == expected
        assert posts[-1]["input"] == [text] and posts[-1]["truncate"] is False
