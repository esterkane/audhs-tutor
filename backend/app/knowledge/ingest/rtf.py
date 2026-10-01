"""RTF -> plain text (stdlib only). Handles groups, destinations (`{\\*\\…}`, font/colour tables,
stylesheet, info, pictures are dropped), `\\par`/`\\line`/`\\tab`, `\\'hh` cp1252 bytes and `\\uN`
unicode escapes with their fallback characters."""

import re

from app.knowledge.ingest.structured_text import structured_blocks
from app.knowledge.ingest.types import Block

_TOKEN = re.compile(
    r"\\([a-z]{1,32})(-?\d{1,10})?[ ]?|\\'([0-9a-f]{2})|\\([^a-z])|([{}])|([^\\{}]+)",
    re.I,
)
_DESTINATIONS = {
    "aftncn",
    "aftnsep",
    "aftnsepc",
    "annotation",
    "atnauthor",
    "atndate",
    "atnicn",
    "atnid",
    "atnparent",
    "atnref",
    "atntime",
    "atrfend",
    "atrfstart",
    "author",
    "background",
    "bkmkend",
    "bkmkstart",
    "blipuid",
    "buptim",
    "category",
    "colorschememapping",
    "colortbl",
    "comment",
    "company",
    "creatim",
    "datafield",
    "datastore",
    "defchp",
    "defpap",
    "do",
    "doccomm",
    "docvar",
    "dptxbxtext",
    "ebcend",
    "ebcstart",
    "factoidname",
    "falt",
    "fchars",
    "ffdeftext",
    "ffentrymcr",
    "ffexitmcr",
    "ffformat",
    "ffhelptext",
    "ffl",
    "ffname",
    "ffstattext",
    "field",
    "file",
    "filetbl",
    "fldinst",
    "fldrslt_ignore",
    "fldtype",
    "fname",
    "fontemb",
    "fontfile",
    "fonttbl",
    "footer",
    "footerf",
    "footerl",
    "footerr",
    "footnote",
    "formfield",
    "ftncn",
    "ftnsep",
    "ftnsepc",
    "g",
    "generator",
    "gridtbl",
    "header",
    "headerf",
    "headerl",
    "headerr",
    "hl",
    "hlfr",
    "hlinkbase",
    "hlloc",
    "hlsrc",
    "hsv",
    "htmltag",
    "info",
    "keycode",
    "keywords",
    "latentstyles",
    "lchars",
    "levelnumbers",
    "leveltext",
    "lfolevel",
    "linkval",
    "list",
    "listlevel",
    "listname",
    "listoverride",
    "listoverridetable",
    "listpicture",
    "liststylename",
    "listtable",
    "listtext",
    "lsdlockedexcept",
    "macc",
    "maccPr",
    "mailmerge",
    "mmaddfieldname",
    "mmconnectstr",
    "mmdatasource",
    "mmheadersource",
    "mmmailsubject",
    "mmodso",
    "mmquery",
    "mvfmf",
    "mvfml",
    "mvtof",
    "mvtol",
    "nesttableprops",
    "nextfile",
    "nonesttables",
    "objalias",
    "objclass",
    "objdata",
    "object",
    "objname",
    "objsect",
    "objtime",
    "oldcprops",
    "oldpprops",
    "oldsprops",
    "oldtprops",
    "oleclsid",
    "operator",
    "panose",
    "password",
    "passwordhash",
    "pgp",
    "pgptbl",
    "picprop",
    "pict",
    "pn",
    "pnseclvl",
    "pntext",
    "pntxta",
    "pntxtb",
    "printim",
    "private",
    "propname",
    "protend",
    "protstart",
    "protusertbl",
    "pxe",
    "result",
    "revtbl",
    "revtim",
    "rsidtbl",
    "rxe",
    "shp",
    "shpgrp",
    "shpinst",
    "shppict",
    "shprslt",
    "shptxt",
    "sn",
    "sp",
    "staticval",
    "stylesheet",
    "subject",
    "sv",
    "svb",
    "tc",
    "template",
    "themedata",
    "title",
    "txe",
    "ud",
    "upr",
    "userprops",
    "wgrffmtfilter",
    "windowcaption",
    "writereservation",
    "writereservhash",
    "xe",
    "xform",
    "xmlattrname",
    "xmlattrvalue",
    "xmlclose",
    "xmlname",
    "xmlnstbl",
    "xmlopen",
}
_SPECIAL = {
    "par": "\n",
    "line": "\n",
    "sect": "\n\n",
    "page": "\n\n",
    "tab": "\t",
    "emdash": "\u2014",
    "endash": "\u2013",
    "emspace": " ",
    "enspace": " ",
    "qmspace": " ",
    "bullet": "\u2022",
    "lquote": "\u2018",
    "rquote": "\u2019",
    "ldblquote": "\u201c",
    "rdblquote": "\u201d",
    "row": "\n",
    "cell": " | ",
    "nestrow": "\n",
    "nestcell": " | ",
}


def rtf_to_text(raw: str) -> str:
    out: list[str] = []
    stack: list[tuple[int, bool]] = []
    ucskip, ignorable = 1, False
    curskip = 0
    for m in _TOKEN.finditer(raw):
        word, arg, hexbyte, char, brace, tchar = m.groups()
        if brace == "{":
            stack.append((ucskip, ignorable))
        elif brace == "}":
            if stack:
                ucskip, ignorable = stack.pop()
        elif char is not None:
            if char == "~":
                out.append("\u00a0") if not ignorable else None
            elif char in "{}\\":
                if not ignorable:
                    out.append(char)
            elif char == "*":
                ignorable = True
            elif char == "\n" or char == "\r":
                if not ignorable:
                    out.append("\n")
        elif word is not None:
            curskip = 0
            wl = word.lower()
            if wl in _DESTINATIONS:
                ignorable = True
            elif ignorable:
                pass
            elif wl in _SPECIAL:
                out.append(_SPECIAL[wl])
            elif wl == "uc":
                ucskip = int(arg or 1)
            elif wl == "u":
                c = int(arg or 0)
                out.append(chr(c + 0x10000 if c < 0 else c))
                curskip = ucskip
        elif hexbyte is not None:
            if curskip > 0:
                curskip -= 1
            elif not ignorable:
                out.append(bytes([int(hexbyte, 16)]).decode("cp1252", "replace"))
        elif tchar is not None:
            if curskip > 0:
                cut = min(curskip, len(tchar))
                tchar, curskip = tchar[cut:], curskip - cut
            if not ignorable and tchar:
                out.append(tchar.replace("\r", "").replace("\n", ""))
    text = "".join(out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def rtf_blocks(raw: str) -> list[Block]:
    return structured_blocks(rtf_to_text(raw))
