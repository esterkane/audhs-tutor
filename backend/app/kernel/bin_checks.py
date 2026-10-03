"""Conditional literal pandas.cut boundaries, not execution or data validation.

Only direct module-level expression/assignment calls with at most x and bins positional
arguments are inspected. The named pd/pandas binding is assumed, never verified/imported.
"""

import ast
import math
from dataclasses import dataclass
from typing import cast

VERSION = "literal-bin-boundaries.v1"


@dataclass(frozen=True)
class BinCheck:
    line: int
    right: bool
    include_lowest: bool
    edges: list[str]
    boundary_bins: list[int | None]
    labels: list[str] | None = None


def _number(node: ast.AST) -> int | float | None:
    sign = 1
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        sign = -1 if isinstance(node.op, ast.USub) else 1
        node = node.operand
    if not isinstance(node, ast.Constant) or type(node.value) not in (int, float):
        return None
    value = sign * cast(int | float, node.value)
    if abs(value) > 1e15 or not math.isfinite(value):
        return None
    return value


def _check(call: ast.Call) -> BinCheck | None:
    function = call.func
    if not (
        isinstance(function, ast.Attribute)
        and function.attr == "cut"
        and isinstance(function.value, ast.Name)
        and function.value.id in {"pd", "pandas"}
    ):
        return None
    if len(call.args) > 2 or any(isinstance(arg, ast.Starred) for arg in call.args):
        return None
    keys = [kw.arg for kw in call.keywords]
    if None in keys or len(set(keys)) != len(keys):
        return None
    kwargs = {kw.arg: kw.value for kw in call.keywords}
    if set(kwargs) - {
        "x",
        "bins",
        "right",
        "labels",
        "retbins",
        "precision",
        "include_lowest",
        "duplicates",
        "ordered",
    }:
        return None
    if call.args and "x" in kwargs or len(call.args) == 2 and "bins" in kwargs:
        return None
    if not call.args and "x" not in kwargs:
        return None
    bins = call.args[1] if len(call.args) == 2 else kwargs.get("bins")
    if not isinstance(bins, (ast.List, ast.Tuple)) or not 2 <= len(bins.elts) <= 16:
        return None
    values = [_number(node) for node in bins.elts]
    if any(value is None for value in values):
        return None
    edges = [value for value in values if value is not None]
    if any(left >= right for left, right in zip(edges, edges[1:], strict=False)):
        return None
    options = {"right": True, "include_lowest": False, "ordered": True, "retbins": False}
    for key in options:
        if key in kwargs:
            node = kwargs[key]
            if not isinstance(node, ast.Constant) or type(node.value) is not bool:
                return None
            options[key] = node.value
    if "precision" in kwargs:
        node = kwargs["precision"]
        if (
            not isinstance(node, ast.Constant)
            or type(node.value) is not int
            or not 0 <= node.value <= 15
        ):
            return None
    if "duplicates" in kwargs:
        node = kwargs["duplicates"]
        if not isinstance(node, ast.Constant) or node.value not in ("raise", "drop"):
            return None
    labels: list[str] | None = None
    if "labels" in kwargs:
        node = kwargs["labels"]
        if isinstance(node, ast.Constant) and (node.value is None or node.value is False):
            pass
        elif isinstance(node, (ast.List, ast.Tuple)) and len(node.elts) == len(edges) - 1:
            labels = [
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
            if (
                len(labels) != len(node.elts)
                or len(set(labels)) != len(labels)
                or any(len(label) > 200 for label in labels)
            ):
                return None
        else:
            return None
    if not options["ordered"]:
        labels_node = kwargs.get("labels")
        if labels_node is None or (
            isinstance(labels_node, ast.Constant) and labels_node.value is None
        ):
            return None
    right = options["right"]
    assignments = (
        [0 if options["include_lowest"] else None] + list(range(len(edges) - 1))
        if right
        else list(range(len(edges) - 1)) + [None]
    )
    return BinCheck(
        call.lineno,
        right,
        options["include_lowest"],
        [str(value) for value in edges],
        assignments,
        labels,
    )


def check_bins(code: str) -> list[BinCheck]:
    if len(code) > 16_000:
        return []
    try:
        tree = ast.parse(code)
        if sum(1 for _ in ast.walk(tree)) > 3000:
            return []
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []
    checks = []
    for statement in tree.body:
        if isinstance(statement, (ast.Expr, ast.Assign, ast.AnnAssign)) and isinstance(
            statement.value, ast.Call
        ):
            check = _check(statement.value)
            if check is not None:
                checks.append(check)
                if len(checks) == 3:
                    break
    return checks
