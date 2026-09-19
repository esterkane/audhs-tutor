#!/usr/bin/env python3
"""Model registry CLI (ADR-0010).

  models.py seed                       # register routing_profiles.yaml defaults; detect installed
  models.py list
  models.py search-hf <query> [--gguf|--mlx] [--limit N]
  models.py info <repo_id>             # licence, GGUF files + sizes
  models.py add <source> <repo_id> [--file F | --tag T] [--role R] [--id ID] [--price-in X --price-out Y]
  models.py pull <id>                  # ollama pull | hf gguf (+ Modelfile -> ollama create) | mlx snapshot
  models.py bench <id>                 # tok/s, first-token ms, 5-case tutoring hard checks -> benchmark_json
  models.py assign <task> <id> [--learner L]   # learner_preference routing.<task>; refuses unbenchmarked
  models.py rm <id>                    # delete artifact + ollama model, mark removed
Sources: ollama_library | huggingface_gguf | huggingface_mlx | hosted
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.models import LearnerProfile  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.models_ai import registry  # noqa: E402
from app.models_ai.bench import bench_model, summarize  # noqa: E402
from app.models_ai.downloader import Downloader, hf_info, hf_search, slugify  # noqa: E402
from app.models_ai.factory import build_providers, installed_ollama_tags  # noqa: E402
from app.models_ai.provider import TaskClass  # noqa: E402

RUNTIME_FOR_SOURCE = {
    "ollama_library": "ollama",
    "huggingface_gguf": "ollama",
    "huggingface_mlx": "mlx",
    "hosted": "hosted",
}


def say(msg: str) -> None:
    print(msg, flush=True)


async def owner_learner(db: AsyncSession) -> LearnerProfile:
    row = (
        (await db.execute(select(LearnerProfile).order_by(LearnerProfile.created_at)))
        .scalars()
        .first()
    )
    if row is None:
        row = LearnerProfile(display_name="owner")
        db.add(row)
        await db.commit()
    return row


async def cmd_seed(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    installed = await installed_ollama_tags(s.ollama_host)
    if s.anthropic_api_key:
        installed.add("hosted")
    rows = await registry.seed_defaults(db, installed_ollama_tags=installed)
    # refresh readiness of already-known ollama rows
    for r in rows:
        if r.runtime == "ollama" and r.status in ("available", "ready"):
            tag = r.id if r.source == "huggingface_gguf" else (r.file_or_tag or r.repo_id)
            r.status = (
                "ready" if (tag in installed or f"{tag}:latest" in installed) else "available"
            )
        if r.runtime == "hosted" and r.status in ("available", "ready"):
            r.status = "ready" if s.anthropic_api_key else "available"
    await db.commit()
    return await cmd_list(db, s, a)


async def cmd_list(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    rows = await registry.list_models(db)
    say(f"{'id':24} {'status':11} {'runtime':7} {'role':6} {'size_gb':>7}  benchmark")
    for r in rows:
        size = f"{r.size_gb:.1f}" if r.size_gb else "-"
        say(
            f"{r.id:24} {r.status:11} {r.runtime:7} {r.role:6} {size:>7}  {summarize(r.benchmark_json)}"
        )
    return 0


async def cmd_search(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    for m in hf_search(a.query, gguf=a.gguf, mlx=a.mlx, limit=a.limit):
        lic = ",".join(t.split(":", 1)[1] for t in m["tags"]) or "-"
        say(
            f"{m['repo_id']:60} dl={m['downloads'] or 0:<8} likes={m['likes'] or 0:<5} licence={lic}"
        )
    say("next: models.py info <repo_id>  →  models.py add huggingface_gguf <repo_id> --file <F>")
    return 0


async def cmd_info(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    say(json.dumps(hf_info(a.repo_id, s.hf_token), indent=2))
    return 0


async def cmd_add(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    if a.source not in RUNTIME_FOR_SOURCE:
        say(f"unknown source {a.source}; one of {sorted(RUNTIME_FOR_SOURCE)}")
        return 2
    if a.source == "huggingface_gguf" and not a.file:
        say("huggingface_gguf needs --file <name.gguf>  (see: models.py info <repo_id>)")
        return 2
    if a.source == "hosted" and not a.tag:
        say("hosted needs --tag <model id>, e.g. --tag claude-sonnet-5")
        return 2
    file_or_tag = a.file or a.tag or (a.repo_id if a.source == "ollama_library" else None)
    rid = a.id or slugify(a.repo_id.split("/")[-1], a.file or a.tag)
    licence, size_gb = None, None
    if a.source.startswith("huggingface"):
        try:
            info = hf_info(a.repo_id, s.hf_token)
            licence = info["licence"]
            match = [f for f in info["gguf_files"] if f["filename"] == a.file]
            size_gb = match[0]["size_gb"] if match else (info["total_size_gb"] or None)
        except Exception as e:  # network optional at add time
            say(f"note: could not fetch HF metadata ({e})")
    row = await registry.upsert(
        db,
        {
            "id": rid,
            "display_name": a.display_name or rid,
            "source": a.source,
            "repo_id": a.repo_id,
            "file_or_tag": file_or_tag,
            "runtime": RUNTIME_FOR_SOURCE[a.source],
            "role": a.role,
            "quant": a.quant,
            "licence": licence,
            "size_gb": size_gb,
            "context_len": a.context_len,
            "status": "ready" if (a.source == "hosted" and s.anthropic_api_key) else "available",
            "price_in_per_mtok": a.price_in,
            "price_out_per_mtok": a.price_out,
        },
    )
    say(
        f"added {row.id} ({row.source}, {row.runtime}, licence={row.licence}) → models.py pull {row.id}"
    )
    return 0


async def cmd_pull(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    row = await registry.get_row(db, a.id)
    dl = Downloader(s.ollama_host, s.models_dir_resolved, s.hf_token)
    await registry.set_status(db, row.id, "downloading")
    try:
        if row.source == "ollama_library":
            tag = row.file_or_tag or row.repo_id
            await dl.ollama_pull(tag, say)
            await registry.set_status(db, row.id, "ready")
        elif row.source == "huggingface_gguf":
            assert row.file_or_tag
            path = await dl.hf_gguf(
                row.repo_id, row.file_or_tag, row.id, num_ctx=row.context_len, progress=say
            )
            await registry.set_status(
                db, row.id, "ready", local_path=str(path), size_gb=path.stat().st_size / 1e9
            )
        elif row.source == "huggingface_mlx":
            path = await dl.hf_mlx(row.repo_id, say)
            from app.models_ai.downloader import dir_size_gb

            await registry.set_status(
                db, row.id, "ready", local_path=str(path), size_gb=dir_size_gb(path)
            )
        elif row.source == "hosted":
            if not s.anthropic_api_key:
                say("hosted model: set ANTHROPIC_API_KEY in .env, then re-run")
                await registry.set_status(db, row.id, "available")
                return 1
            await registry.set_status(db, row.id, "ready")
    except Exception as e:
        await registry.set_status(db, row.id, "failed")
        say(f"pull failed: {e}")
        return 1
    say(f"{row.id} ready → models.py bench {row.id}")
    return 0


async def cmd_bench(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    row = await registry.get_row(db, a.id)
    if row.status != "ready":
        say(f"{row.id} is {row.status}; pull it first")
        return 1
    spec = registry.spec_from_row(row)
    provider = build_providers(s).get(spec.provider)
    if provider is None:
        say(f"no provider for runtime {row.runtime} (hosted needs ANTHROPIC_API_KEY)")
        return 1
    say(f"benchmarking {row.id} …")
    bench = await bench_model(provider, spec)
    await registry.set_status(db, row.id, "ready", benchmark_json=bench)
    say(json.dumps(bench, indent=2))
    say(f"{row.id}: {summarize(bench)} → models.py assign <task> {row.id}")
    return 0


async def cmd_assign(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    try:
        task = TaskClass(a.task)
    except ValueError:
        say(f"unknown task {a.task}; one of {[t.value for t in TaskClass]}")
        return 2
    learner_id = a.learner or (await owner_learner(db)).id
    try:
        await registry.assign(db, learner_id, task, a.id)
    except ValueError as e:
        say(str(e))
        return 1
    say(f"routing.{task} = {a.id} for learner {learner_id}")
    return 0


async def cmd_rm(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    row = await registry.get_row(db, a.id)
    dl = Downloader(s.ollama_host, s.models_dir_resolved, s.hf_token)
    tag = row.id if row.source == "huggingface_gguf" else row.file_or_tag
    await dl.remove(runtime=row.runtime, tag=tag, local_path=row.local_path)
    await registry.set_status(db, row.id, "removed", local_path=None, benchmark_json=None)
    say(f"removed {row.id}")
    return 0


COMMANDS = {
    "seed": cmd_seed,
    "list": cmd_list,
    "search-hf": cmd_search,
    "info": cmd_info,
    "add": cmd_add,
    "pull": cmd_pull,
    "bench": cmd_bench,
    "assign": cmd_assign,
    "rm": cmd_rm,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    sub.add_parser("list")
    sp = sub.add_parser("search-hf")
    sp.add_argument("query")
    sp.add_argument("--gguf", action="store_true")
    sp.add_argument("--mlx", action="store_true")
    sp.add_argument("--limit", type=int, default=20)
    sub.add_parser("info").add_argument("repo_id")
    ad = sub.add_parser("add")
    ad.add_argument("source")
    ad.add_argument("repo_id")
    ad.add_argument("--file")
    ad.add_argument("--tag")
    ad.add_argument("--role", default="chat")
    ad.add_argument("--id")
    ad.add_argument("--display-name")
    ad.add_argument("--quant")
    ad.add_argument("--context-len", type=int)
    ad.add_argument("--price-in", type=float, default=0.0)
    ad.add_argument("--price-out", type=float, default=0.0)
    for name in ("pull", "bench", "rm"):
        sub.add_parser(name).add_argument("id")
    g = sub.add_parser("assign")
    g.add_argument("task")
    g.add_argument("id")
    g.add_argument("--learner")
    return p


async def run(args: argparse.Namespace, settings: Settings | None = None) -> int:
    s = settings or get_settings()
    upgrade_to_head(s.sync_database_url)
    engine = make_engine(s.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            handler: Any = COMMANDS[args.cmd]
            result: int = await handler(db, s, args)
            return result
    finally:
        await engine.dispose()


def main() -> int:
    return asyncio.run(run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
