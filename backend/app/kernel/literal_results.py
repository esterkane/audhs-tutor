"""Bounded Python-3 literal arithmetic. Never eval/exec code or resolve user callables."""

import ast
import keyword
import math
import operator
import re
from dataclasses import dataclass
from typing import Any


class Unsupported(ValueError):
    pass


class OperationFailure(Exception):
    def __init__(self, name: str, detail: str) -> None:
        self.name = name
        self.detail = detail


@dataclass(frozen=True)
class LiteralResult:
    expression: str
    value: str
    error: bool = False
    detail: str = ""


def bounded(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        raise Unsupported()
    if type(value) in (int, float):
        if not math.isfinite(value) or abs(value) > 10**12:
            raise Unsupported()
    elif type(value) is str:
        if len(value) > 128:
            raise Unsupported()
    elif type(value) in (list, tuple):
        if len(value) > 128:
            raise Unsupported()
        for item in value:
            bounded(item, depth + 1)
    elif value is not None and type(value) is not bool:
        raise Unsupported()
    if len(repr(value)) > 500:
        raise Unsupported()
    return value


def calculate(node: ast.AST, names: dict[str, Any], *, literal: bool = False) -> Any:
    if isinstance(node, ast.Constant):
        return bounded(node.value)
    if isinstance(node, (ast.List, ast.Tuple)):
        items = [calculate(item, names, literal=literal) for item in node.elts]
        return bounded(tuple(items) if isinstance(node, ast.Tuple) else items)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = calculate(node.operand, names, literal=literal)
        if type(value) not in (int, float, bool):
            raise Unsupported()
        return bounded(-value if isinstance(node.op, ast.USub) else +value)
    if isinstance(node, ast.Name) and not literal and node.id in names:
        return names[node.id]
    if literal or not isinstance(node, ast.BinOp):
        raise Unsupported()
    operations = {
        ast.Add: ("+", operator.add),
        ast.Sub: ("-", operator.sub),
        ast.Mult: ("*", operator.mul),
        ast.Div: ("/", operator.truediv),
        ast.FloorDiv: ("//", operator.floordiv),
        ast.Mod: ("%", operator.mod),
    }
    operation = operations.get(type(node.op))
    if operation is None:
        raise Unsupported()
    left, right = calculate(node.left, names), calculate(node.right, names)
    if isinstance(node.op, ast.Mod) and (
        type(left) not in (int, float, bool) or type(right) not in (int, float, bool)
    ):
        raise Unsupported()  # String formatting has separate size and semantic requirements.
    if isinstance(node.op, ast.Mult):
        for sequence, count in ((left, right), (right, left)):
            if type(sequence) in (str, list, tuple) and type(count) in (int, bool):
                if abs(count) > 32 or len(sequence) * max(count, 0) > 128:
                    raise Unsupported()
    try:
        return bounded(operation[1](left, right))
    except (TypeError, ZeroDivisionError) as error:
        detail = f"{type(left).__name__} {operation[0]} {type(right).__name__}"
        raise OperationFailure(type(error).__name__, detail) from None


def literal_results(source: str, question: str) -> tuple[list[LiteralResult], bool] | None:
    """Only complete output questions with backtick-delimited expressions and literal bindings."""
    if len(source) > 1800 or len(question) > 700:
        return None
    match = re.fullmatch(
        r"What\s+(?:do|does)\s+(`[\s\S]+`)\s+(?:return|produce|evaluate\s+to)\?",
        question.strip(),
        re.IGNORECASE,
    )
    german = False
    if match is None:
        match = re.fullmatch(
            r"Was\s+(?:geben|gibt)\s+(`[\s\S]+`)\s+zur(?:ü|ue)ck\?",
            question.strip(),
            re.IGNORECASE,
        )
        german = True
    if match is None:
        return None
    expressions = re.findall(r"`([^`\r\n]{1,120})`", match[1])
    separators = re.sub(r"`[^`\r\n]{1,120}`", "", match[1])
    if not 1 <= len(expressions) <= 4 or re.sub(
        r"\b(?:and|und)\b|[,\s]", "", separators, flags=re.IGNORECASE
    ):
        return None
    code = source.strip()
    fence = re.fullmatch(r"```python[ \t]*\r?\n([\s\S]*?)```", code, re.IGNORECASE)
    header = re.fullmatch(r"Python[ \t]+3:[ \t]*(?:\r?\n([\s\S]*))?", code, re.IGNORECASE)
    if fence and (not fence[1] or fence[1].endswith("\n")):
        code = fence[1]
    elif header:
        code = header[1] or ""
    else:
        return None
    try:
        tree = ast.parse(code)
        if len(list(ast.walk(tree))) > 100 or len(tree.body) > 8:
            return None
        names: dict[str, Any] = {}
        for statement in tree.body:
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                return None
            target = statement.targets[0]
            if not isinstance(target, ast.Name) or not re.fullmatch(
                r"[a-zA-Z_]\w{0,19}", target.id
            ):
                return None
            if target.id in names or keyword.iskeyword(target.id) or target.id.startswith("__"):
                return None
            names[target.id] = calculate(statement.value, {}, literal=True)
        results = []
        for expression in expressions:
            parsed = ast.parse(expression.strip(" \t"), mode="eval")
            nodes = list(ast.walk(parsed))
            allowed = (
                ast.Expression,
                ast.Constant,
                ast.List,
                ast.Tuple,
                ast.UnaryOp,
                ast.UAdd,
                ast.USub,
                ast.BinOp,
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.FloorDiv,
                ast.Mod,
                ast.Name,
                ast.Load,
            )
            if len(nodes) > 80 or any(not isinstance(node, allowed) for node in nodes):
                return None
            # Validate the entire expression even if an earlier operand would raise.
            for node in nodes:
                if isinstance(node, ast.Name) and node.id not in names:
                    return None
                if isinstance(node, ast.Constant):
                    bounded(node.value)
            try:
                result = LiteralResult(expression, repr(calculate(parsed.body, names)))
            except OperationFailure as error:
                result = LiteralResult(expression, error.name, True, error.detail)
            results.append(result)
        return results, german
    except (Unsupported, SyntaxError, RecursionError, ValueError, OverflowError):
        return None
