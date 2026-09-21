"""LaTeX sources (lecture notes, papers) -> blocks. Sectioning commands become headings, verbatim
and listing environments become code blocks, formatting commands are unwrapped, references and
labels are dropped; math is kept as written (the tutor can read TeX)."""

import re

from app.knowledge.ingest.types import Block

_COMMENT = re.compile(r"(?<!\\)%.*$", re.M)
_CODE_ENV = re.compile(
    r"\\begin\{(verbatim|lstlisting|minted|Verbatim|python|pycode)\}(\[[^\]]*\])?(\{[^}]*\})?"
    r"(.*?)\\end\{\1\}",
    re.S,
)
_SECTION = re.compile(
    r"\\(part|chapter|section|subsection|subsubsection|paragraph)\*?(?:\[[^\]]*\])?\{((?:[^{}]|\{[^{}]*\})*)\}"
)
_TITLE = re.compile(r"\\title\{((?:[^{}]|\{[^{}]*\})*)\}")
_UNWRAP = re.compile(
    r"\\(?:textbf|textit|emph|texttt|textsc|underline|textrm|textsf|mathrm|text|mbox|url|href\{[^}]*\}"
    r"|caption|footnote|item\[[^\]]*\]|section\*?|subsection\*?|paragraph)\{"
)
_DROP_WITH_ARG = re.compile(
    r"\\(?:label|ref|eqref|cref|autoref|pageref|cite[tp]?\*?|citep|citet|nocite|index|vspace\*?|hspace\*?"
    r"|includegraphics|input|include|usepackage|documentclass|bibliography|bibliographystyle"
    r"|newcommand|renewcommand|setlength|hyphenation|graphicspath|author|date|thanks|maketitle)"
    r"(?:\[[^\]]*\])*(?:\{[^{}]*\})*"
)
_DROP_ENVS = re.compile(
    r"\\(?:begin|end)\{(?:document|abstract|center|figure\*?|table\*?|itemize|enumerate|description|quote|quotation|frame|columns?|block)\}(?:\[[^\]]*\])?(?:\{[^}]*\})?"
)
_BARE = re.compile(
    r"\\(?:noindent|centering|newpage|clearpage|maketitle|tableofcontents|hline|toprule|midrule|bottomrule|small|large|Large|normalsize|ldots|dots|par|linebreak|newline|bigskip|medskip|smallskip)\b"
)
_PLACEHOLDER = "\x00CODE%d\x00"
_MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$|\\\[.*?\\\]|\\\(.*?\\\)", re.S)


def _unwrap(text: str) -> str:
    """Replace `\\cmd{arg}` by `arg` for formatting commands, handling one level of nesting."""
    prev = None
    while prev != text:
        prev = text
        text = _UNWRAP.sub("{", text)
        text = re.sub(r"\{([^{}]*)\}", r"\1", text) if "{" in text else text
    return text


def latex_blocks(raw: str) -> tuple[str | None, list[Block]]:
    text = _COMMENT.sub("", raw.replace("\r\n", "\n"))
    if "\\begin{document}" in text:
        pre, text = text.split("\\begin{document}", 1)
        tm = _TITLE.search(pre)
    else:
        tm = _TITLE.search(text)
    title = _unwrap(tm.group(1)).strip() if tm else None
    codes: list[tuple[str, str]] = []

    def stash(m: re.Match[str]) -> str:
        codes.append((m.group(1).lower(), m.group(4).strip("\n")))
        return "\n\n" + _PLACEHOLDER % (len(codes) - 1) + "\n\n"

    text = _CODE_ENV.sub(stash, text)
    text = _SECTION.sub(lambda m: f"\n\n\x00H {_unwrap(m.group(2)).strip()}\x00\n\n", text)
    text = _DROP_WITH_ARG.sub("", text)
    text = _DROP_ENVS.sub("\n", text)
    text = text.replace("\\item", "\n• ")
    text = _BARE.sub(" ", text)
    text = text.replace("\\\\", "\n").replace("~", " ")
    maths: list[str] = []

    def keep_math(m: re.Match[str]) -> str:
        maths.append(m.group(0))
        return f"\x00M{len(maths) - 1}\x00"

    text = _MATH.sub(keep_math, text)
    text = _unwrap(text)
    text = re.sub(r"\x00M(\d+)\x00", lambda m: maths[int(m.group(1))], text)
    text = re.sub(r"[ \t]+", " ", text)
    blocks: list[Block] = []
    heading: str | None = None
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if para.startswith("\x00H ") and para.endswith("\x00"):
            heading = para[3:-1].strip() or heading
            continue
        m = re.fullmatch(r"\x00CODE(\d+)\x00", para)
        if m:
            lang, body = codes[int(m.group(1))]
            fence = {"verbatim": "text", "lstlisting": "text", "minted": "text"}.get(lang, lang)
            blocks.append(Block(text=f"```{fence}\n{body}\n```", kind="code", heading=heading))
            continue
        blocks.append(Block(text=para.replace("\x00", ""), kind="prose", heading=heading))
    return title, blocks
