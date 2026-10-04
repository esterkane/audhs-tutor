"""Non-destructive disclosure for source-like markers in source-free workspace replies."""

import re

# Deliberately conservative: leave all original code/prose intact. This is not a Markdown
# validator or a truth checker. Ambiguous standalone numeric lists may also be flagged.
_CODE = re.compile(r"```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`+[^`\n]*`+")
_REFERENCE = re.compile(r"(?<![\w\]\\])\[\d+(?:\s*[,–-]\s*\d+)*\](?!\s*\()")
WARNING = (
    "Source note: this reply contains possible citation markers, but no supporting course "
    "sources were retrieved. Treat those markers as unverified, not as evidence. "
    "The explanation itself has not been independently verified."
)


def disclose(text: str, *, source_count: int = 0, grounded: bool = False) -> tuple[str, bool]:
    """Keep raw response intact; prepend a readable, listenable limitation if needed."""
    markers = _REFERENCE.findall(_CODE.sub("", text))
    if grounded or source_count:
        # Grounded prompts use single [n] references. Composite numeric brackets are
        # ambiguous (often vector/list literals), not proof of an invalid citation.
        markers = [marker for marker in markers if re.fullmatch(r"\[\d+\]", marker)]
    if not markers:
        return text, False
    if source_count and all(
        re.fullmatch(r"\[\d+\]", marker) and 1 <= int(marker[1:-1]) <= source_count
        for marker in markers
    ):
        return text, False
    warning = (
        (
            "Source note: this reply contains unsupported citation markers. Only the numbered "
            "reference passages supplied below are available; citation presence does not verify a claim."
        )
        if source_count
        else WARNING
    )
    return warning + "\n\n" + text, True
