"""Explicit presentation preferences, independent of course and teaching mode."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel import preferences
from app.models_ai.provider import Message
from app.orchestrator.prompts import _read


@dataclass(frozen=True)
class TutorPresentation:
    persona: str = "none"
    language: str = "unchanged"

    @property
    def suffix(self) -> str:
        if self.persona == "none" and self.language == "unchanged":
            return ""
        return f"+presentation.v1.{self.persona}.{self.language}"

    @property
    def instruction(self) -> str:
        if not self.suffix:
            return ""
        voice = (
            "Use the ordinary tutor voice; no character roleplay."
            if self.persona == "none"
            else _read(f"personas/{self.persona}.v1.md")
        )
        language = (
            "Keep the response language requested by the learner or task."
            if self.language == "unchanged"
            else _read(f"personas/language-{self.language}.v1.md")
        )
        return "\n\n" + _read("_base/persona.v1.md") + "\n" + voice + "\n" + language

    def apply(self, messages: list[Message]) -> list[Message]:
        if not self.instruction:
            return messages
        first, *rest = messages
        return [first.model_copy(update={"content": first.content + self.instruction}), *rest]


def from_preferences(values: dict[str, Any]) -> TutorPresentation:
    persona = values.get("tutor.persona", "none")
    language = values.get("tutor.response_language", "unchanged")
    return TutorPresentation(
        persona=persona
        if isinstance(persona, str) and persona in {"none", "kangaroo", "guide", "coach"}
        else "none",
        language=language
        if isinstance(language, str) and language in {"unchanged", "en", "de"}
        else "unchanged",
    )


async def load(db: AsyncSession, learner_id: str) -> TutorPresentation:
    return from_preferences(await preferences.get_all(db, learner_id))
