"""Exercise an uploaded notebook against loopback Qdrant from the sandbox browser.

Run in a disposable checkout with frontend dependencies, backend/.venv and
data/notebook-env prepared. Playwright uses its normal sandbox ports and database.
"""

import json
import os
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4


def main() -> None:
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    collection = "audhs_jupyter_" + uuid4().hex
    url = "http://127.0.0.1:6333/collections/" + collection

    def call(method: str, suffix: str = "", body: dict | None = None) -> None:
        request = Request(
            url + suffix,
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            if json.load(response)["status"] != "ok":
                raise RuntimeError("Qdrant fixture request failed")

    call("PUT", body={"vectors": {"size": 2, "distance": "Dot"}})
    try:
        call(
            "PUT",
            "/points?wait=true",
            {"points": [{"id": 1, "vector": [1, 0]}, {"id": 2, "vector": [0, 1]}]},
        )
        subprocess.run(
            [
                "node",
                "node_modules/@playwright/test/cli.js",
                "test",
                "--config=playwright.focus.config.ts",
                "project-notebook-reading",
            ],
            cwd=frontend,
            env={
                **os.environ,
                "AUDHS_TEST_JUPYTER": "1",
                "AUDHS_NOTEBOOK_QDRANT_COLLECTION": collection,
            },
            check=True,
        )
    finally:
        call("DELETE")


if __name__ == "__main__":
    main()
