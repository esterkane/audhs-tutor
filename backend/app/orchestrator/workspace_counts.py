"""Read-only, explicitly supplied count observations; never a fairness assessment."""

import json

from app.kernel.group_counts import compare_groups
from app.schemas.playground import PlaygroundRequest

SCOPE = (
    "Computed from user-entered counts, not verified dataset results. Assumes nonoverlapping "
    "groups, the same counting unit and unchanged membership, with rows removed rather than added. "
    "Representation is within the entered groups only. Counts do not establish causes, "
    "model accuracy, fairness or a grade. Undefined means a zero denominator."
)


def count_summary(body: PlaygroundRequest) -> str:
    if body.group_counts is None or body.intent == "hint":
        return ""
    result = compare_groups(body.group_counts)
    lines = [f"Total: {result.before_total} before → {result.after_total} after"]
    for row in result.groups:
        # JSON quoting escapes line breaks and keeps labels literal in the code block.
        lines.extend(
            [
                f"Group {json.dumps(row.label, ensure_ascii=False)}: "
                f"{row.before} before → {row.after} after; {row.removed} removed",
                f"  Retained: {row.retention if row.retention is not None else 'undefined'}",
                "  Representation: "
                f"{row.representation_before if row.representation_before is not None else 'undefined'}"
                " → "
                f"{row.representation_after if row.representation_after is not None else 'undefined'}",
            ]
        )
    # Indented code keeps user-controlled labels literal in the rendered calculation.
    # The model caller must still escape this whole summary as untrusted data.
    return (
        "Local group-count calculation (exact fractions, not a grade):\n\n"
        + "\n".join("    " + line for line in lines)
        + "\n\n"
        + SCOPE
    )
