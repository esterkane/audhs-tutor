"""Bounded literal arithmetic identities; never code execution or learning evidence."""

import ast
import re
from dataclasses import dataclass
from fractions import Fraction

VERSION = "literal-arithmetic.v1"
MAX_CHECKS = 6
# Mask code without changing offsets. Arithmetic inside code is outside this contract.
_CODE = re.compile(r"```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`+[^`\n]*`+")
_ISLAND = re.compile(r"[0-9.()+*/%=−×÷^,\- \t]+")
_NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)")
_PERCENT = re.compile(r"(\d+(?:\.\d*)?|\.\d+)\s*%")


@dataclass(frozen=True)
class EqualityCheck:
    expression: str
    left: str
    right: str
    holds: bool


def _evaluate(expression: str) -> Fraction:
    if len(expression) > 128:
        raise ValueError("Expression too long")
    expression = expression.translate(str.maketrans("−×÷", "-*/"))
    if any(len(number.group().replace(".", "")) > 12 for number in _NUMBER.finditer(expression)):
        raise ValueError("Literal too long")
    expression = _PERCENT.sub(r"(\1/100)", expression).strip()
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > 48:
        raise ValueError("Expression too complex")

    def visit(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            literal = ast.get_source_segment(expression, node)
            if literal is None or _NUMBER.fullmatch(literal) is None:
                raise ValueError("Unsupported literal")
            return Fraction(literal)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
        raise ValueError("Unsupported syntax")

    return visit(tree.body)


def check_equalities(answer: str) -> list[EqualityCheck]:
    """Check only complete numeric islands. No natural-language claim or grade inference.

    Exact rational equality: approximate notation, units, names, powers, code and chained
    equalities are unsupported. Invalid or zero-divisor expressions remain unverified.
    """
    if len(answer) > 8000:
        return []
    masked = _CODE.sub(lambda match: "\x00" * len(match.group()), answer)
    results: list[EqualityCheck] = []
    for match in _ISLAND.finditer(masked):
        raw = match.group()
        expression = raw.strip()
        terminated = expression.endswith((".", ","))
        if terminated:
            expression = expression[:-1].rstrip()
        if expression.count("=") != 1 or len(expression) > 256:
            continue
        before = masked[match.start() - 1 : match.start()] if match.start() else ""
        after = masked[match.end() : match.end() + 1]
        # Admit known prose boundaries rather than blacklist individual operators. A root,
        # ratio, bitwise operator or masked code operand must not become a numeric suffix.
        # A word may be a named operator (for example cosh), not prose. Abstain unless
        # this starts a line or is explicitly quoted/separated; do not guess from a word list.
        if before and before not in "\n\r;\"'“‘":
            continue
        paired_quote = {'"': '"', "'": "'", "“": "”", "‘": "’"}.get(before)
        if paired_quote and (
            after != paired_quote
            or (before in "\"'" and masked[: match.start()].count(before) % 2 != 1)
        ):
            continue
        if after:
            paired_quote = {'"': '"', "'": "'", "“": "”", "‘": "’"}.get(before)
            prose_after_sentence = terminated and raw[-1].isspace() and after.isalpha()
            terminal_question = after == "?" and not masked[match.end() + 1 :].strip()
            if not (
                after in "\n\r;"
                or after == paired_quote
                or prose_after_sentence
                or terminal_question
            ):
                continue
        left_text, right_text = expression.split("=")
        try:
            left, right = _evaluate(left_text), _evaluate(right_text)
        except (ValueError, SyntaxError, ZeroDivisionError, RecursionError):
            continue
        results.append(EqualityCheck(expression, str(left), str(right), left == right))
        if len(results) == MAX_CHECKS:
            break
    return results
