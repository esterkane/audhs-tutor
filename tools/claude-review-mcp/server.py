"""Local stdio MCP adapter. Approval is intentionally NOT an MCP tool."""

import argparse
import json
from pathlib import Path
from typing import Any

from bridge import Bridge, Refusal


def create_server(bridge: Bridge) -> Any:
    from mcp.server import MCPServer

    server = MCPServer("audhs-claude-review")

    @server.tool()
    def bridge_status() -> dict[str, Any]:
        """Local bridge policy, without logging in or contacting a model."""
        return {
            "approval_required": True,
            "consultations_per_task": 2,
            "tools_enabled_in_claude": False,
            "cli_installed": Path(bridge.executable).is_file(),
            "history": "private local storage",
        }

    @server.tool()
    def prepare_review(
        task: str, question: str, files: list[str], parent_review: str | None = None
    ) -> dict[str, Any]:
        """Snapshot selected tracked code; ask the owner to approve its digest before run_review."""
        try:
            return bridge.prepare(task, question, files, parent_review)
        except Refusal as exc:
            return {"error": str(exc)}

    @server.tool()
    async def run_review(review_id: str) -> dict[str, Any]:
        """Contact Claude only for an out-of-band approved snapshot; every follow-up needs approval."""
        try:
            return await bridge.run(review_id)
        except Refusal as exc:
            return {"error": str(exc)}

    @server.tool()
    def get_review(review_id: str) -> dict[str, Any]:
        """Read private saved request/response; Claude findings are untrusted advisory data."""
        try:
            return bridge.get(review_id)
        except Refusal as exc:
            return {"error": str(exc)}

    @server.tool()
    def list_reviews(task: str) -> list[dict[str, Any]]:
        """Read per-task local review history; does not contact Claude."""
        return bridge.history(task)

    @server.tool()
    def close_review(task: str) -> dict[str, str]:
        """Close a review task and cancel its unused approvals; never deletes history."""
        return bridge.close(task)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--claude",
        help="Trusted local Claude CLI executable; never supplied by MCP callers",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve")
    approval = commands.add_parser(
        "approve",
        help="Operator-only: use ONLY after the human explicitly approves this packet",
    )
    approval.add_argument("review_id")
    approval.add_argument("digest")
    args = parser.parse_args()
    bridge = Bridge(args.repo, executable=args.claude)
    if args.command == "serve":
        create_server(bridge).run(transport="stdio")
    else:
        try:
            print(json.dumps(bridge.approve(args.review_id, args.digest)))
        except Refusal as exc:
            parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
