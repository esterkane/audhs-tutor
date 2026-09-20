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
from app.models_ai import manage, registry  # noqa: E402
from app.models_ai.bench import summarize  # noqa: E402
from app.models_ai.downloader import hf_info, hf_search  # noqa: E402
from app.models_ai.provider import TaskClass  # noqa: E402


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
    await manage.seed(db, s)
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
    try:
        row = await manage.add(
            db,
            s,
            source=a.source,
            repo_id=a.repo_id,
            file=a.file,
            tag=a.tag,
            registry_id=a.id,
            display_name=a.display_name,
            role=a.role,
            quant=a.quant,
            context_len=a.context_len,
            price_in=a.price_in,
            price_out=a.price_out,
        )
    except ValueError as e:
        say(str(e))
        return 2
    say(
        f"added {row.id} ({row.source}, {row.runtime}, licence={row.licence}) → models.py pull {row.id}"
    )
    return 0


async def cmd_pull(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    try:
        row = await manage.pull(db, s, a.id, say)
    except Exception as e:
        say(f"pull failed: {e}")
        return 1
    say(f"{row.id} ready → models.py bench {row.id}")
    return 0


async def cmd_bench(db: AsyncSession, s: Settings, a: argparse.Namespace) -> int:
    try:
        bench = await manage.bench(db, s, a.id, say)
    except ValueError as e:
        say(str(e))
        return 1
    say(json.dumps(bench, indent=2))
    if "ms_per_16_docs" in bench:
        say(f"{a.id}: rerank {bench['ms_per_16_docs']} ms / 16 docs → routes via TaskClass.rerank")
    else:
        say(f"{a.id}: {summarize(bench)} → models.py assign <task> {a.id}")
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
    await manage.remove(db, s, a.id)
    say(f"removed {a.id}")
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
