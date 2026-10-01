"""Model artifacts (ADR-0010): Ollama library pulls, Hugging Face GGUF -> Modelfile ->
`ollama create`, mlx-community snapshots. Everything lands under MODELS_DIR and is size-tracked."""

import asyncio
import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from huggingface_hub import HfApi, hf_hub_download, snapshot_download

Progress = Callable[[str], None] | None


class DownloadError(Exception):
    pass


def slugify(*parts: str | None) -> str:
    raw = "-".join(p for p in parts if p)
    raw = raw.lower().replace("/", "-").replace(":", "-").replace("_", "-").replace(".gguf", "")
    raw = re.sub(r"[^a-z0-9.-]+", "-", raw)
    return re.sub(r"-{2,}", "-", raw).strip("-")


def modelfile_for(gguf_path: Path, *, num_ctx: int | None = None) -> str:
    """Ollama reads the chat template from GGUF metadata; only FROM (+ optional num_ctx) is needed."""
    lines = [f"FROM {gguf_path}"]
    if num_ctx:
        lines.append(f"PARAMETER num_ctx {num_ctx}")
    return "\n".join(lines) + "\n"


def dir_size_gb(path: Path) -> float:
    if path.is_file():
        return round(path.stat().st_size / 1e9, 3)
    total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0
    return round(total / 1e9, 3)


# ----------------------------------------------------------------- Hugging Face metadata
def hf_search(
    query: str, *, gguf: bool = False, mlx: bool = False, limit: int = 20
) -> list[dict[str, Any]]:
    api = HfApi()
    kwargs: dict[str, Any] = {"search": query, "sort": "downloads", "direction": -1, "limit": limit}
    if gguf:
        kwargs["filter"] = "gguf"
    if mlx:
        kwargs["author"] = "mlx-community"
    out = []
    for m in api.list_models(**kwargs):
        out.append(
            {
                "repo_id": m.id,
                "downloads": getattr(m, "downloads", None),
                "likes": getattr(m, "likes", None),
                "pipeline": getattr(m, "pipeline_tag", None),
                "tags": [t for t in (getattr(m, "tags", None) or []) if t.startswith("license:")],
            }
        )
    return out


def hf_info(repo_id: str, token: str | None = None) -> dict[str, Any]:
    """Licence, GGUF files (with sizes) and total size for a repo."""
    api = HfApi(token=token or None)
    info = api.model_info(repo_id, files_metadata=True)
    licence = None
    card = getattr(info, "card_data", None)
    if card is not None:
        licence = getattr(card, "license", None)
    if not licence:
        for t in info.tags or []:
            if t.startswith("license:"):
                licence = t.split(":", 1)[1]
    files: list[dict[str, Any]] = []
    for s in info.siblings or []:
        files.append({"filename": s.rfilename, "size_gb": round((s.size or 0) / 1e9, 3)})
    ggufs = [f for f in files if f["filename"].lower().endswith(".gguf")]
    return {
        "repo_id": repo_id,
        "licence": licence,
        "gguf_files": ggufs,
        "total_size_gb": round(sum(f["size_gb"] for f in files), 3),
    }


# ----------------------------------------------------------------- downloader
class Downloader:
    def __init__(self, ollama_host: str, models_dir: Path, hf_token: str = "") -> None:
        self.ollama_host = ollama_host.rstrip("/")
        self.models_dir = models_dir
        self.hf_token = hf_token or None

    async def ollama_pull(self, tag: str, progress: Progress = None) -> None:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self.ollama_host}/api/pull", json={"model": tag, "stream": True}
            ) as r:
                r.raise_for_status()
                last = ""
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    msg = json.loads(line)
                    if "error" in msg:
                        raise DownloadError(f"ollama pull {tag}: {msg['error']}")
                    status = msg.get("status", "")
                    if progress and status != last:
                        total, done = msg.get("total"), msg.get("completed")
                        pct = f" {done / total:.0%}" if total and done else ""
                        progress(f"{status}{pct}")
                        last = status

    async def ollama_installed(self) -> set[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.ollama_host}/api/tags")
            r.raise_for_status()
        return {m["name"] for m in r.json().get("models", [])}

    async def ollama_delete(self, tag: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.request(
                "DELETE", f"{self.ollama_host}/api/delete", json={"model": tag}
            )
            if r.status_code not in (200, 404):
                raise DownloadError(f"ollama delete {tag}: {r.text}")

    async def hf_gguf(
        self,
        repo_id: str,
        filename: str,
        ollama_name: str,
        *,
        num_ctx: int | None = None,
        progress: Progress = None,
    ) -> Path:
        target = self.models_dir / "gguf" / slugify(repo_id)
        target.mkdir(parents=True, exist_ok=True)
        if progress:
            progress(f"downloading {repo_id}/{filename}")
        path_str = await asyncio.to_thread(
            hf_hub_download, repo_id, filename, local_dir=str(target), token=self.hf_token
        )
        gguf_path = Path(path_str)
        modelfile = target / f"Modelfile.{slugify(filename)}"
        modelfile.write_text(modelfile_for(gguf_path, num_ctx=num_ctx))
        if progress:
            progress(f"ollama create {ollama_name}")
        await self._ollama_create(ollama_name, modelfile)
        return gguf_path

    async def _ollama_create(self, name: str, modelfile: Path) -> None:
        proc = await asyncio.create_subprocess_exec(
            "ollama",
            "create",
            name,
            "-f",
            str(modelfile),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            raise DownloadError(
                f"ollama create {name} failed: {out.decode(errors='replace')[-800:]}"
            )

    async def hf_mlx(self, repo_id: str, progress: Progress = None) -> Path:
        target = self.models_dir / "mlx" / slugify(repo_id)
        if progress:
            progress(f"snapshot {repo_id}")
        path_str = await asyncio.to_thread(
            snapshot_download, repo_id, local_dir=str(target), token=self.hf_token
        )
        return Path(path_str)

    async def hf_file(
        self, repo_id: str, filename: str, registry_id: str, progress: Progress = None
    ) -> Path:
        """One file from a Hugging Face repo into MODELS_DIR/onnx/<registry id>/ (Silero VAD)."""
        target = self.models_dir / "onnx" / registry_id
        target.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
        if progress:
            progress(f"download {repo_id}/{filename}")
        path_str = await asyncio.to_thread(
            hf_hub_download, repo_id, filename, local_dir=str(target), token=self.hf_token
        )
        # hf_hub_download replicates the repo layout (src/…/file.onnx); the app looks for the flat name
        flat = target / Path(filename).name
        if Path(path_str).resolve() != flat.resolve():  # noqa: ASYNC240
            await asyncio.to_thread(shutil.move, path_str, flat)
        return flat

    async def fastembed_cross_encoder(self, repo_id: str, progress: Progress = None) -> Path:
        """Download (and load once) a fastembed cross-encoder into MODELS_DIR/fastembed."""
        target = self.models_dir / "fastembed"
        target.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
        if progress:
            progress(f"fastembed cross-encoder {repo_id}")

        def _run() -> None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            TextCrossEncoder(model_name=repo_id, cache_dir=str(target))

        await asyncio.to_thread(_run)
        return target

    async def remove(self, *, runtime: str, tag: str | None, local_path: str | None) -> None:
        if runtime == "ollama" and tag:
            await self.ollama_delete(tag)
        if local_path:
            p = Path(local_path)
            root = p if p.is_dir() else p.parent  # noqa: ASYNC240
            if self.models_dir in root.parents or root == self.models_dir:
                shutil.rmtree(root, ignore_errors=True)
