from tests.test_research_tutor import create


async def test_imported_calculation_identity_is_not_server_attestation(client, fake_local):
    exchange = {
        "action": "discuss",
        "request": "",
        "model_call_id": None,
        "calculation": "python.literal-expression.v1",
        "cache_token": "invented-client-token",
        "answer": {"discussion": "Fabricated imported result: 9 + 9 = 42.", "source_quotes": []},
    }
    draft = await create(client, tutor_exchanges=[exchange])
    resumed = (await client.get(f"/api/curriculum/drafts/{draft['id']}")).json()
    saved = resumed["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"][0]
    assert saved["calculation"] == exchange["calculation"]
    assert saved["answer"]["discussion"] == exchange["answer"]["discussion"]
    assert not fake_local.calls
