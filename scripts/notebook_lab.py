"""Start the optional local notebook environment; never executes imported cells."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = [
    "jupyterlab==4.6.4",
    "ipykernel==7.4.0",
    "numpy==2.5.3",
    "pandas==3.0.6",
    "matplotlib==3.11.2",
    "scikit-learn==1.9.1",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install pinned notebook tools in a separate environment",
    )
    parser.add_argument("--directory", type=Path, default=ROOT / "data/notebooks")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    env = ROOT / "data/notebook-env"
    python = env / "bin/python"
    if args.install:
        if not python.exists():
            subprocess.run(["uv", "venv", "--python", "3.12", str(env)], check=True)
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), *PACKAGES], check=True
        )
    if not python.exists():
        parser.error("Run python3 scripts/notebook_lab.py --install once first.")
    folder = args.directory.expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    # Remove inherited model credentials from kernel environment. Jupyter keeps normal token auth.
    servers = subprocess.run(
        [str(python), "-m", "jupyter", "server", "list", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in servers.stdout.splitlines():
        try:
            server = json.loads(line)
        except ValueError:
            continue
        if server.get("port") == 8890:
            print(
                "A notebook lab is already running on port 8890. Reuse its authenticated browser tab, or stop it with Ctrl-C in its terminal before launching another."
            )
            return 0
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if not any(x in k.upper() for x in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))
    }
    command = [
        str(python),
        "-m",
        "jupyterlab",
        "--ServerApp.ip=127.0.0.1",
        "--ServerApp.port=8890",
        "--ServerApp.port_retries=0",
        f"--ServerApp.root_dir={folder}",
    ]
    if args.no_browser:
        command.append("--no-browser")
    print(
        "Local notebook lab: open the authenticated URL printed by Jupyter. Run cells only after reading them.",
        flush=True,
    )
    return subprocess.call(command, env=clean_env)


if __name__ == "__main__":
    sys.exit(main())
