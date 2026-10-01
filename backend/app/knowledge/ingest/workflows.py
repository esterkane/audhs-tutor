"""Read n8n exports as untrusted source data, never as executable workflows."""

from typing import Any

from app.knowledge.ingest.normalize import redact_secrets, strip_invisible
from app.knowledge.ingest.types import Block

MAX_NODES = 1000
MAX_EDGES = 5000
MAX_OUTPUT_CHARS = 250_000


def workflow_blocks(obj: Any) -> list[Block] | None:
    """Return None for unrelated JSON; malformed recognizable workflows raise ValueError.

    Whitelist structural fields and teaching notes. Parameter values (including scripts,
    expressions, URLs and headers), credentials, pinned data and execution state stay on disk.
    """
    if not isinstance(obj, dict) or not isinstance(obj.get("nodes"), list):
        return None
    nodes = obj["nodes"]
    if "connections" not in obj or not any(
        isinstance(n, dict)
        and isinstance(n.get("type"), str)
        and n["type"].startswith(("n8n-nodes-base.", "@n8n/"))
        for n in nodes
    ):
        return None
    if not 0 < len(nodes) <= MAX_NODES:
        raise ValueError("n8n: too large (node limit)")

    def label(value: Any, limit: int = 500) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("n8n: invalid text field")
        if len(value) > limit:
            raise ValueError("n8n: too large (text field)")
        return redact_secrets(strip_invisible(value))

    blocks = [
        Block(
            text="n8n workflow structure. Parameter values, credentials and runtime data omitted.",
            heading="Workflow overview",
        )
    ]
    names: set[str] = set()
    size = 0

    def add(text: str, heading: str, *, prose: bool = False) -> None:
        nonlocal size
        size += len(text) + len(heading)
        if size > MAX_OUTPUT_CHARS:
            raise ValueError("n8n: too large (extracted text limit)")
        blocks.append(Block(text=text, heading=heading, kind="prose" if prose else "code"))

    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("n8n: invalid node")
        name = label(node.get("name"))
        typ = label(node.get("type"))
        raw_name = node["name"]
        if raw_name in names:
            raise ValueError("n8n: duplicate node name")
        names.add(raw_name)
        params = node.get("parameters", {})
        if not isinstance(params, dict) or len(params) > 200:
            raise ValueError("n8n: invalid parameter map")
        keys = ", ".join(label(k) for k in sorted(params))
        add(f"Node: {name}\nType: {typ}\nParameter names: {keys or '(none)'}", name)
        if node.get("notes") and (not isinstance(node["notes"], str) or node["notes"].strip()):
            add(label(node["notes"], 16_000), name + " — notes", prose=True)
        if (
            typ == "n8n-nodes-base.stickyNote"
            and params.get("content")
            and (not isinstance(params["content"], str) or params["content"].strip())
        ):
            add(label(params["content"], 16_000), name + " — teaching note", prose=True)

    connections = obj["connections"]
    if not isinstance(connections, dict) or len(connections) > MAX_NODES:
        raise ValueError("n8n: invalid connections")
    edges = 0
    slots = 0
    for source, channels in connections.items():
        if source not in names or not isinstance(channels, dict) or len(channels) > 100:
            raise ValueError("n8n: unknown source or invalid channels")
        for channel, outputs in channels.items():
            channel_label = label(channel)
            if not isinstance(outputs, list):
                raise ValueError("n8n: invalid output ports")
            slots += len(outputs)
            if slots > MAX_EDGES:
                raise ValueError("n8n: too large (output port limit)")
            for port, targets in enumerate(outputs):
                if not isinstance(targets, list):
                    raise ValueError("n8n: invalid targets")
                edges += len(targets)
                if edges > MAX_EDGES:
                    raise ValueError("n8n: too large (edge limit)")
                for target in targets:
                    if not isinstance(target, dict) or not isinstance(target.get("node"), str):
                        raise ValueError("n8n: invalid target")
                    if target["node"] not in names:
                        raise ValueError("n8n: unknown target node")
                    index = target.get("index")
                    if type(index) is not int or not 0 <= index <= MAX_EDGES:
                        raise ValueError("n8n: invalid input port")
                    edge_type = label(target.get("type"))
                    add(
                        f"{label(source)} [{channel_label}:{port}] -> "
                        f"{label(target['node'])} [{edge_type}:{index}]",
                        "Connection",
                    )
    return blocks
