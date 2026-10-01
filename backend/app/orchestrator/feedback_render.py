"""Readable, saved and spoken rendering of formative feedback, never a grade."""

import html
import re

from app.schemas.feedback import QuotedFeedback


def literal(text: str) -> str:
    """Prevent supplied quotations from introducing active Markdown or HTML."""
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~\-])", r"\\\1", html.escape(text))


def render_feedback(feedback: QuotedFeedback) -> str:
    labels = {
        "supported": "Supported by the supplied work",
        "needs_revision": "Needs revision",
        "needs_more_information": "More information needed",
    }
    parts = ["Model feedback on your submitted answer — not a verified grade."]
    for point in feedback.points:
        quote = "\n".join("> " + literal(line) for line in point.learner_quote.splitlines())
        parts.append(f"You wrote:\n\n{quote}\n\n**{labels[point.finding]}:** {point.explanation}")
    parts.append("**Next step:** " + feedback.next_step)
    if feedback.followup_question:
        parts.append("**Question to explore:** " + feedback.followup_question)
    return "\n\n".join(parts)
