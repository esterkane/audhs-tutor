"""Run an optional loopback-only Ollama instance without changing app configuration."""

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
from pathlib import Path

APP_BINARY = Path("/Applications/Ollama.app/Contents/Resources/ollama")


def environment(port: int, full_cache: bool) -> dict[str, str]:
    if not 1024 <= port <= 65535 or port == 11434:
        raise ValueError(
            "Use an unused port from 1024–65535 other than the normal Ollama port 11434."
        )
    return {
        "OLLAMA_HOST": f"127.0.0.1:{port}",
        "OLLAMA_NO_CLOUD": "1",
        "OLLAMA_MAX_LOADED_MODELS": "2",
        "OLLAMA_NUM_PARALLEL": "1",
        "LLAMA_ARG_SWA_FULL": "1" if full_cache else "0",
    }


def check_runner(binary: Path) -> None:
    runner = binary.resolve().with_name("llama-server")
    if not runner.is_file():
        raise ValueError(
            "Full-cache mode requires an installed sibling llama-server with --swa-full."
        )
    result = subprocess.run([str(runner), "--help"], capture_output=True, text=True, timeout=30)
    if result.returncode or "--swa-full" not in result.stdout + result.stderr:
        raise ValueError(
            "This installed runner does not advertise --swa-full; leave full-cache mode off."
        )


def serve(binary: Path, overrides: dict[str, str]) -> int:
    def stop_on_term(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    process = subprocess.Popen(
        [str(binary), "serve"], env={**os.environ, **overrides}, start_new_session=True
    )
    previous_term = signal.signal(signal.SIGTERM, stop_on_term)
    try:
        return process.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        # Only this launcher's process group; never the normal Ollama daemon.
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=11435)
    parser.add_argument("--ollama", type=Path, default=Path(shutil.which("ollama") or APP_BINARY))
    parser.add_argument(
        "--full-cache",
        action="store_true",
        help=(
            "Experimental: Gemma 12B at 32K used about 11 GiB extra cache. "
            "No guarantee of faster or complete answers."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and print the launch settings without starting a server.",
    )
    args = parser.parse_args()
    try:
        overrides = environment(args.port, args.full_cache)
        binary = args.ollama.expanduser().resolve()
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise ValueError("Ollama executable not found. Install it or supply --ollama PATH.")
        if args.full_cache:
            check_runner(binary)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.port))
        print(
            json.dumps(
                {"command": [str(binary), "serve"], "environment_overrides": overrides}, indent=2
            ),
            flush=True,
        )
        print(
            "Uses installed models. No model download, app switch or .env edit. Ctrl-C stops this server.",
            flush=True,
        )
        if args.full_cache:
            print(
                "EXPERIMENTAL: roughly 11 GiB extra cache for the tested Gemma 12B/32K setup. "
                "Keep memory pressure visible.",
                flush=True,
            )
        if args.check:
            return 0
        return serve(binary, overrides)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
