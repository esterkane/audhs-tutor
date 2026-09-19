#!/usr/bin/env python3
"""Model registry CLI (ADR-0010). Skeleton: the contract Stage 0 implements.

  models.py list
  models.py search-hf <query> [--gguf|--mlx]
  models.py add <source> <repo_id> [--file F | --tag T] [--role chat|code|embed|rerank|stt|tts|judge]
  models.py pull <id>            # ollama pull | hf snapshot (+ Modelfile → ollama create) | mlx snapshot
  models.py bench <id>           # tok/s, first-token latency, 5-case tutoring eval → benchmark_json
  models.py assign <task> <id>   # writes learner_preference routing.<task>; refuses unbenchmarked models
  models.py rm <id>              # deletes artifact under $MODELS_DIR and marks row removed
Sources: ollama_library | huggingface_gguf | huggingface_mlx | hosted
"""

import argparse
import sys


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("search-hf")
    s.add_argument("query")
    s.add_argument("--gguf", action="store_true")
    s.add_argument("--mlx", action="store_true")
    a = sub.add_parser("add")
    a.add_argument("source")
    a.add_argument("repo_id")
    a.add_argument("--file")
    a.add_argument("--tag")
    a.add_argument("--role", default="chat")
    for name in ("pull", "bench", "rm"):
        sub.add_parser(name).add_argument("id")
    g = sub.add_parser("assign")
    g.add_argument("task")
    g.add_argument("id")
    args = p.parse_args()
    print(
        f"not implemented yet: {args.cmd} — implement in backend/app/models_ai/registry.py and call it from here",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
