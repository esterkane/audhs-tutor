"""Jupyter notebooks -> blocks. Markdown cells become prose (headings tracked), code cells become
code blocks that carry the last markdown heading; short text outputs are appended to their cell."""

import json
import re
from typing import Any

from app.knowledge.ingest.types import Block

_H = re.compile(r"^\s*#{1,3}\s+(.+?)\s*$", re.M)
MAX_OUTPUT_CHARS = 400


def _source(cell: dict[str, Any]) -> str:
    src = cell.get("source") or ""
    return "".join(src) if isinstance(src, list) else str(src)


def _outputs(cell: dict[str, Any]) -> str:
    parts: list[str] = []
    for out in cell.get("outputs") or []:
        if out.get("output_type") == "stream":
            parts.append("".join(out.get("text") or []))
        elif out.get("output_type") in ("execute_result", "display_data"):
            data = out.get("data") or {}
            txt = data.get("text/plain")
            if txt:
                parts.append("".join(txt) if isinstance(txt, list) else str(txt))
        elif out.get("output_type") == "error":
            parts.append(f"{out.get('ename')}: {out.get('evalue')}")
    text = "\n".join(p.strip() for p in parts if p.strip())
    return text[:MAX_OUTPUT_CHARS] + ("…" if len(text) > MAX_OUTPUT_CHARS else "")


def notebook_blocks(raw: str) -> list[Block]:
    nb = json.loads(raw)
    kernel = (nb.get("metadata") or {}).get("kernelspec") or {}
    lang = str(kernel.get("language") or "python")
    heading: str | None = None
    blocks: list[Block] = []
    for cell in nb.get("cells") or []:
        src = _source(cell).strip()
        if not src:
            continue
        if cell.get("cell_type") == "markdown":
            m = _H.match(src)
            if m:
                heading = m.group(1)
                src = src[m.end() :].strip()  # the heading is carried as metadata
                if not src:
                    continue  # a heading-only cell
            blocks.append(Block(text=src, kind="prose", heading=heading))
        elif cell.get("cell_type") == "code":
            if src.lstrip().startswith(("!", "%")) and "\n" not in src.strip():
                continue  # shell/magic one-liners (pip install …) carry no concept
            out = _outputs(cell)
            text = f"```{lang}\n{src}\n```" + (f"\nOutput:\n{out}" if out else "")
            blocks.append(Block(text=text, kind="code", heading=heading))
    return blocks
