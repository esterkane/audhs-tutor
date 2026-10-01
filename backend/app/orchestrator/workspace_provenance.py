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


def disclose(text: str) -> tuple[str, bool]:
    """Keep raw response intact; prepend a readable, listenable limitation if needed."""
    if not _REFERENCE.search(_CODE.sub("", text)):
        return text, False
    return WARNING + "\n\n" + text, True
