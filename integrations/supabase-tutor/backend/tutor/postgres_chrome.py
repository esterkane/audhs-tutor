"""Recognize complete site-navigation passages from the PostgreSQL manual import."""

import re

PG17_PAGE = re.compile(r"https://www\.postgresql\.org/docs/17/[a-z0-9][a-z0-9.-]*\.html")
CORRECTION = (
    "If you see anything in the documentation that is not correct, does not match your "
    "experience with the particular feature or requires further clarification, please use "
    "this form to report a documentation issue."
)
NUMBER = r"\d+(?:\.\d+)?"
VERSION_LIST = rf"{NUMBER}(?: / {NUMBER})*"
HEADER = re.compile(
    r"[A-Z][a-z]+ \d{1,2}, \d{4}: PostgreSQL [^\n]{1,100} Released!\n\n"
    r"Documentation → PostgreSQL 17\n\n"
    rf"Supported Versions: Current \({NUMBER}\)(?: / {NUMBER})+\n\n"
    rf"Development Versions: (?:{VERSION_LIST} / )?devel\n\n"
    rf"(?:Unsupported versions: {VERSION_LIST}\n\n)?"
    r"\| [^|\n]{1,180} \|\n"
    r"\| Prev \| Up \| [^|\n]{1,180} \| Home \| Next \|"
)
NAV_QUERY = re.compile(
    r"\b(?:supported versions|unsupported versions|development versions|versions? (?:of (?:the )?)?(?:the )?(?:postgresql )?documentation|"
    r"documentation (?:page )?navigation|documentation versions?|documentation (?:correction|issue|feedback|navigation)|"
    r"(?:report|correct).{0,40}(?:documentation|manual)|(?:documentation|manual).{0,40}(?:navigation links|correction form)|"
    r"unterstützte(?:n)? (?:postgresql[- ])?versionen|dokumentations(?:fehler|navigation)|"
    r"(?:fehler|korrektur).{0,35}(?:handbuch|dokumentation)|(?:handbuch|dokumentation).{0,35}(?:fehler melden|navigation))\b",
    re.IGNORECASE,
)


def pure_manual_chrome(url: str, content: str) -> bool:
    if not PG17_PAGE.fullmatch(url):
        return False
    text = content.strip()
    return text == CORRECTION or bool(HEADER.fullmatch(text))
