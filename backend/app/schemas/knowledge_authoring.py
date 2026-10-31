"""Learner-authored knowledge, with optional uploaded source lineage."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Domain
from app.schemas.curriculum import DraftOut


class PersonalMemory(BaseModel):
    id: str
    draft_id: str
    version: int
    title: str
    kind: str
    text: str


class MemorySearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class MemorySearchOut(BaseModel):
    memories: list[PersonalMemory]


class ResearchTutorAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    discussion: str = Field(default="", max_length=2000)
    needs_check: str = Field(default="", max_length=1000)
    source_quotes: list[str] = Field(default_factory=list, max_length=3)
    next_question: str = Field(default="", max_length=500)
    section: str = Field(default="", max_length=2000)


def _operand_scoped_explanation(value: str) -> str:
    # Narrow checks for observed false causal claims, not a general factual classifier.
    # Fresh internal responses only; historical public answers remain readable unchanged.
    motive_claims = re.sub(
        r"\b(?:not|never) (?:calculated|used|intended|done) to "
        r"(?:maintain symmetry|balance the distribution)",
        "",
        value,
        flags=re.IGNORECASE,
    )
    if "median" in value.casefold() and re.search(
        r"(?<!not )\b(?:to maintain symmetry|to balance (?:the distribution|opposing halves)|"
        r"by balancing (?:the distribution|opposing halves)|"
        r"because (?:it |this |averaging )?(?:maintains symmetry|balances the distribution))\b",
        motive_claims,
        re.IGNORECASE,
    ):
        raise ValueError(
            "Do not claim that computing a median makes data symmetric or balances its "
            "distribution. Explain the middle ranks: for even-sized sorted data the usual "
            "sample median averages the two central observations; for odd-sized data it "
            "uses the single middle observation. Retain all requested calculations and "
            "source references. State each rule once, without an invented purpose or recap."
        )
    patterns = (
        r"because mixed[- ]type operations are (?:not (?:automatically handled|allowed|supported)|invalid)",
        r"because (?:the )?['\"`]?\+['\"`]? operator "
        r"(?:is not defined for|cannot handle) (?:mixed|different)(?: data)? types",
        r"because Python does not support concatenating different data types",
    )
    if (
        ("repeat" in value.lower() or "repetition" in value.lower())
        and "string" in value.lower()
        and re.search(r"negative values raise (?:a )?ValueError", value, re.IGNORECASE)
    ):
        raise ValueError(
            "Python string repetition by a negative integer returns the empty string; "
            "it does not raise ValueError. Remove the invented restriction and explain "
            "only the requested example and supported conditions."
        )
    if re.search(r"original object unless (?:explicitly )?reassigned", value, re.IGNORECASE):
        raise ValueError(
            "Python strings are immutable. Reassignment binds a name to a value; "
            "it does not mutate the original string object. Describe the supplied "
            "expression results and whether the variable was reassigned."
        )
    if re.search(
        r"requires the left operand to be a string and the right operand to be an integer",
        value,
        re.IGNORECASE,
    ):
        raise ValueError(
            "Python supports both str * int and int * str for string repetition. "
            "Explain the supplied operand order without claiming the reversed order is invalid."
        )
    if re.search(
        r"negative (?:integer|count|multiplier)[^.!?]{0,70}(?<!not )(?<!n't )(?<!never )raises? (?:a )?ValueError",
        value,
        re.IGNORECASE,
    ) or re.search(r"(?<!not )because negative repetition is not supported", value, re.IGNORECASE):
        raise ValueError(
            "Python sequence repetition by a non-positive integer is supported and "
            "produces an empty sequence, not ValueError. Keep every requested result "
            "and the unchanged original; do not invent a conflicting implementation."
        )
    if re.search(
        r"(?:operation|string repetition|sequence repetition) requires a non-negative integer[.;]",
        value,
        re.IGNORECASE,
    ):
        raise ValueError(
            "Built-in Python sequence repetition accepts non-positive integer counts, "
            "returning an empty sequence. Explain the supplied operation without "
            "inventing a non-negative-count requirement."
        )
    unsupported = (
        r"(?:you|your (?:mistake|claim|error)|the (?:learner|original claim))[^.!?]{0,60}"
        r"(?:likely|probably|must have)[^.!?]{0,35}(?:confus|assum|misunderst)",
        r"negative[^.!?;,]{0,100}(?<!not )(?<!n't )(?<!never )truncates?",
        r"list concatenation with negative counts",
    )
    if any(re.search(pattern, value, re.IGNORECASE) for pattern in unsupported):
        raise ValueError(
            "Correct only the stated claim using the supplied code and results. "
            "The origin of a learner's mistake is unknown. Python sequence repetition "
            "with a non-positive count produces zero copies and an empty sequence, "
            "leaving the original unchanged. Explain this operation without invented "
            "truncation or unrelated comparisons."
        )
    if any(re.search(pattern, value, re.IGNORECASE) for pattern in patterns):
        raise ValueError(
            "Explain the specific operator and operand requirement. String concatenation "
            "requires another string, so str + int needs explicit str conversion. "
            "Numeric int + float addition is supported. Correct the causal explanation "
            "and retain the requested code, result and source references."
        )
    return value


class ResearchDiscussion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_sentence: str = Field(
        min_length=1,
        max_length=1200,
        description=(
            "A brief complete answer covering each requested point. "
            "Finish all sentences and examples; no recap or repeated conclusion."
        ),
    )
    source_indices: list[Annotated[int, Field(ge=1, le=4)]] = Field(min_length=1, max_length=3)

    _check_operands = field_validator("answer_sentence")(_operand_scoped_explanation)


class ResearchSectionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section: str = Field(min_length=1, max_length=2000)
    source_indices: list[Annotated[int, Field(ge=1, le=4)]] = Field(min_length=1, max_length=3)

    _check_operands = field_validator("section")(_operand_scoped_explanation)


def is_unmeasured_observation(source: str) -> bool:
    """Only the observed complete neutral-note templates, not arbitrary research text."""
    return bool(
        re.fullmatch(
            r"(?:(?:A note|The note) reports slower requests after deployment but provides no "
            r"measurements(?:, comparison)? or investigation results\.?|"
            r"The monitoring note records slower requests after deployment\. It contains no "
            r"latency measurements, controlled comparison or root cause analysis\.?)",
            " ".join(source.split()),
            re.IGNORECASE,
        )
    )


def _neutral_note_claims(value: str) -> str:
    # Ignore only quoted wording explicitly rejected by the surrounding sentence.
    # Keep the returned prose intact and inspect every other assertion normally.
    assertions = list(value)
    for opening, closing in [('"', '"'), ("“", "”"), ("'", "'"), ("‘", "’")]:
        pattern = (
            r"\b(?:the (?:phrase|statement|wording)|describing (?:this|the note) as)\s+"
            + re.escape(opening)
            + r"(?P<quote>(?:(?!"
            + re.escape(closing)
            + r")[^\n]){1,500})"
            + re.escape(closing)
            + r"\s+(?:is (?:wrong|unsupported|misleading|not supported|not established)"
            r"|overstates|misrepresents)\b"
        )
        for match in re.finditer(pattern, value, re.IGNORECASE):
            start, end = match.span("quote")
            assertions[start:end] = " " * (end - start)
    inspected = "".join(assertions)
    if re.search(
        r"(?<!not )(?<!n't )(?<!never )\b(?:only (?:a )?|shows? (?:a )?|establishes? (?:a )?)correlation\b",
        inspected,
        re.IGNORECASE,
    ) or re.search(
        r"\b(?:the )?(?:note|source|passage) (?:incorrectly claims|falsely asserts)\b|"
        r"\b(?:note|source|passage)[’']s claim of definite causation\b",
        inspected,
        re.IGNORECASE,
    ):
        raise ValueError(
            "This selected source only reports slower requests after deployment and explicitly "
            "provides no measurements/comparison/investigation results. Report temporal order, "
            "not an established statistical correlation or causal effect. The definite-cause "
            "and never-measured claims belong to the learner, not this neutral source. "
            "Correct both claims directly: cause is not established here; missing results "
            "here do not establish that measurements or investigation never occurred. "
            "Use a direct correction such as: the note reports event order, not established "
            "cause; measurements missing here do not prove they were never taken. "
            "Do not claim measurements must exist elsewhere. Keep the limitation once, "
            "without a recap or invented source assertion."
        )
    if re.search(
        r"(?:^|[.!?]\s+)(?:the )?(?:claim|assertion) that no measurements were ever taken "
        r"is (?:corroborated|confirmed|supported|proven)\b",
        inspected,
        re.IGNORECASE,
    ):
        raise ValueError(
            "The source does not corroborate that measurements were never taken. "
            "It says measurements/results are not provided here. Keep that distinction: "
            "the learner's never-measured claim is not established, and measurements "
            "may or may not exist elsewhere. Do not infer their presence or absence. "
            "Return the corrected causal and missing-evidence conclusions once each."
        )
    return value


class NeutralObservationDiscussion(ResearchDiscussion):
    _check_note = field_validator("answer_sentence")(_neutral_note_claims)


class NeutralObservationSection(ResearchSectionDraft):
    _check_note = field_validator("section")(_neutral_note_claims)


class ResearchRepetitionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule: str = Field(
        min_length=1,
        max_length=300,
        description=(
            "One brief accurate rule explaining the supplied verified literal-string results. "
            "No example calculations, recap or guess about the learner."
        ),
    )
    source_indices: list[Annotated[int, Field(ge=1, le=4)]] = Field(min_length=1, max_length=3)

    _check_operands = field_validator("rule")(_operand_scoped_explanation)


class ResearchTutorExchange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["discuss", "draft"]
    request: str = Field(max_length=2000)
    answer: ResearchTutorAnswer
    model_call_id: str | None = Field(max_length=128)
    calculation: (
        Literal[
            "python.string-repetition.v1", "python.literal-expression.v1", "vector.dot-cosine.v1"
        ]
        | None
    ) = Field(default=None, exclude_if=lambda value: value is None)
    reference: Literal["python.string-identity.v1"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    memories: list[PersonalMemory] = Field(default_factory=list, max_length=3)
    cache_token: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def generation_identity(self) -> "ResearchTutorExchange":
        if (
            sum(
                value is not None
                for value in (self.model_call_id, self.calculation, self.reference)
            )
            != 1
        ):
            raise ValueError("Exactly one model, calculation or reference identity is required")
        return self


class ResearchQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    prompt: str = Field(min_length=1, max_length=2000)
    source_quote: str | None = Field(default=None, max_length=2000)
    findings: str = Field(default="", max_length=8000)
    evidence: str = Field(default="", max_length=8000)
    unresolved: str = Field(default="", max_length=4000)
    section: str = Field(default="", max_length=4000)
    memory_ids: list[Annotated[str, Field(pattern="^[a-f0-9]{64}$")]] = Field(
        default_factory=list, max_length=3
    )
    tutor_request: str = Field(default="", max_length=2000)
    tutor_basis: str = Field(default="", max_length=32000)
    tutor_exchanges: list[ResearchTutorExchange] = Field(default_factory=list, max_length=12)


class KnowledgeResearch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # A durable snapshot, independent of assessment tokens and API process lifetime.
    passage: str = Field(min_length=1, max_length=6000)
    topic: str = Field(min_length=1, max_length=300)
    questions: list[ResearchQuestion] = Field(min_length=1, max_length=12)
    current: int = Field(default=0, ge=0, le=11)

    @model_validator(mode="after")
    def valid_position(self) -> "KnowledgeResearch":
        if self.current >= len(self.questions):
            raise ValueError("Research position must refer to an existing question")
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError("Research question ids must be distinct")
        if any(
            q.source_quote is not None
            and (not q.source_quote.strip() or q.source_quote not in self.passage)
            for q in self.questions
        ):
            raise ValueError("Question source quotations must match the saved passage exactly")
        return self


class KnowledgeMaterialInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus_topic: (
        Literal["elasticsearch", "vector-search", "supabase", "postgresql", "qdrant", "kubernetes"]
        | None
    ) = None
    title: str = Field(min_length=1, max_length=300)
    workflow_step: Literal["source", "research", "write", "review"] = "source"
    domain: Domain = Domain.AI_ML
    notes: str = Field(min_length=1, max_length=120000)
    research: KnowledgeResearch | None = None
    upload_id: str | None = Field(default=None, max_length=128)
    objective: str = Field(default="", max_length=1000)
    explanation: str = Field(default="", max_length=4000)
    worked_example: str = Field(default="", max_length=4000)
    question: str = Field(default="", max_length=4000)
    criteria: list[str] = Field(default_factory=list, max_length=12)


class KnowledgeMaterialUpdate(KnowledgeMaterialInput):
    expected_version: int = Field(ge=1)


class KnowledgeUploadOut(BaseModel):
    document_id: str
    filename: str
    text: str
    sha256: str
    characters: int


class KnowledgeSuggestIn(BaseModel):
    expected_version: int = Field(ge=1)


class ResearchTutorIn(KnowledgeSuggestIn):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1, max_length=80)
    action: Literal["discuss", "draft"]
    refresh: bool = False


class ResearchTutorOut(DraftOut):
    reused: bool = False


class SourceResearchQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    source_quote: str = Field(min_length=1, max_length=2000)


class SourceResearchQuestions(BaseModel):
    questions: list[SourceResearchQuestion] = Field(min_length=3, max_length=3)


class KnowledgeLessonSuggestion(BaseModel):
    objective: str = Field(min_length=1, max_length=1000)
    explanation: str = Field(min_length=1, max_length=4000)
    worked_example: str = Field(min_length=1, max_length=4000)
    question: str = Field(min_length=1, max_length=4000)
    criteria: list[str] = Field(min_length=1, max_length=4)


class KnowledgeReadingOut(BaseModel):
    draft_id: str
    title: str
    objective: str
    explanation: str
    worked_example: str
    question: str
    notes: str
    sources: list[str]
    learning_object_version: int
