#!/usr/bin/env python3
"""Bounded synthetic Ask diagnostic. Local only; semantic review is human, not a score."""

import argparse
import asyncio
import hashlib
import json
import tempfile
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from eval_local_runtime import local_settings, pinned_gateway

from app.core.config import get_settings
from app.db import answers
from app.evals.harness import open_world
from app.orchestrator.ask import respond
from app.schemas.ask import AskQuestion


class CandidateGateway:
    def __init__(self, gateway, candidate):
        self.gateway = gateway
        self.router = gateway.router
        self.candidate = candidate
        self.packets = []
        self.generation_settings = []

    async def complete(self, task, messages, **kwargs):
        packet = list(messages)
        if self.candidate:
            packet[0] = packet[0].model_copy(
                update={"content": packet[0].content + "\n" + self.candidate}
            )
        self.packets.append([m.model_dump() for m in packet])
        self.generation_settings.append(
            {
                "max_tokens": kwargs.get("max_tokens"),
                "temperature": kwargs.get("temperature", 0.2),
                "seed": "not pinned",
            }
        )
        return await self.gateway.complete(task, packet, **kwargs)


def load_inputs(candidate_path: Path | None):
    fixture_path = (
        Path(__file__).resolve().parents[1] / "evals/cases/ask-coefficient-interpretation.json"
    )
    return fixture_path.read_bytes(), candidate_path.read_text() if candidate_path else ""


def model_manifest():
    settings = local_settings(get_settings())
    with urlopen(settings.ollama_host.rstrip("/") + "/api/tags", timeout=10) as response:
        models = json.load(response)["models"]
    return next(
        {"name": item["name"], "digest": item["digest"]}
        for item in models
        if item["name"] == "llama3.1:8b"
    )


async def run(output: Path, candidate_path: Path | None):
    local_settings(get_settings())
    raw, candidate = await asyncio.to_thread(load_inputs, candidate_path)
    cases = json.loads(raw)["cases"]
    report = {
        "synthetic": True,
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "model": "llama31-8b",
        "installed_model_before_run": await asyncio.to_thread(model_manifest),
        "candidate": candidate,
        "scope": "Ask responder with optional experimental system suffix; no production routing change",
        "results": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("x") as artifact,
        tempfile.TemporaryDirectory(prefix="ask-quality-") as directory,
    ):
        world = await open_world(str(Path(directory) / "eval.db"), with_repo=False)
        try:
            async with world.session_factory() as db:
                gateway = CandidateGateway(await pinned_gateway(world, db, "llama31-8b"), candidate)
                for case in cases:
                    parent = None
                    conversation = str(uuid4())
                    for index, prior in enumerate(case["history"]):
                        turn = conversation if index == 0 else str(uuid4())
                        saved = await answers.save_completed(
                            db,
                            learner_id=world.learner_id,
                            session_id=None,
                            turn_id=turn,
                            surface="ask",
                            request=AskQuestion(question=prior["question"]).model_dump(),
                            text=prior["answer"],
                            metadata={
                                "area_id": None,
                                "parent_answer_id": parent,
                                "conversation_id": conversation,
                            },
                        )
                        parent = saved.id
                    reply = await asyncio.wait_for(
                        respond(
                            db,
                            gateway,
                            world.learner_id,
                            AskQuestion(question=case["question"], parent_answer_id=parent),
                            str(uuid4()),
                        ),
                        180,
                    )
                    report["results"].append(
                        {
                            "id": case["id"],
                            "criteria": case["criteria"],
                            "reply": reply.model_dump(mode="json"),
                            "packet": gateway.packets[-1],
                            "generation_settings": gateway.generation_settings[-1],
                        }
                    )
                    artifact.seek(0)
                    json.dump(report, artifact, indent=2)
                    artifact.truncate()
                    artifact.flush()
        finally:
            await world.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    options = parser.parse_args()
    asyncio.run(run(options.out, options.candidate))
