"""Conservative course-logistics checks, not a general semantic quality classifier."""

import re

_COURSE = r"(?:course|curriculum|syllabus|lecture|lesson|module|part\s+\d+)"
_LOGISTICS = re.compile(
    rf"\b{_COURSE}\s+(?:roadmap|syllabus|outline|goals?|objectives?|overview|duration|price|budget)\b"
    rf"|(?:^|\bwhat\s+(?:does|will)\s+)(?:this|the|our|your)\s+{_COURSE}\s+(?:will\s+)?(?:cover|covers|teach|teaches|promise|promises)\b"
    rf"|\b(?:focus|scope|roadmap|syllabus|overview|objectives?|duration|cost|price|budget)\b"
    rf"[^.!?;\n]{{0,90}}\b(?:of|for)\s+(?:(?:the|this|our|your|entire|whole)\s+){{0,3}}{_COURSE}\b",
    re.I,
)
_ORIENTATION = re.compile(
    r"^\s*welcome(?:\s*$|\s*(?:&|to\b|!))|\b(?:course|curriculum)\s+(?:overview|roadmap|introduction)\b"
    r"|what\s+(?:you|we)(?:['’ʼ]ll|\s+will)\s+(?:learn|build)",
    re.I,
)


def course_metadata(text: str) -> bool:
    """Narrow grammatical patterns; technical module scope/cost/learning are allowed."""
    recommendation_trivia = (
        re.search(r"\b(?:course|lecture|instructor)\b", text, re.I)
        and re.search(r"\brecommend(?:ed|s|ation)?\b", text, re.I)
        and re.search(r"\b(?:students?|beginners?|course)\b", text, re.I)
    )
    return bool(_LOGISTICS.search(text) or recommendation_trivia)


def orientation_title(text: str) -> bool:
    return bool(_ORIENTATION.search(text))


def unsuitable_question(text: str) -> bool:
    return course_metadata(text) or orientation_title(text)
