"""Closed enums shared by kernel, orchestrator and the event log (docs/EVENT-SCHEMA.md)."""

from enum import StrEnum


class Mode(StrEnum):
    NOVELTY = "novelty"
    STEADY = "steady"
    LOW_CAPACITY = "low_capacity"


class Domain(StrEnum):
    AI_ML = "ai_ml"
    PROGRAMMING = "programming"
    LANGUAGE = "language"
    GUITAR = "guitar"
    MOVEMENT = "movement"
    META = "meta"


class ActivityType(StrEnum):
    NEW_MATERIAL = "new_material"
    RETRIEVAL = "retrieval"
    INTERLEAVED_REVIEW = "interleaved_review"
    CHALLENGE = "challenge"
    DOMAIN_SWITCH = "domain_switch"
    MOVEMENT = "movement"
    RECAP = "recap"
    CHAT = "chat"


class RepresentationKind(StrEnum):
    ANALOGY = "analogy"
    DERIVATION = "derivation"
    CODE = "code"
    DIAGRAM = "diagram"
    WORKED_EXAMPLE = "worked_example"
    PROBLEM_FIRST = "problem_first"
    NARRATIVE = "narrative"


class Modality(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class Actor(StrEnum):
    LEARNER = "learner"
    SYSTEM = "system"
    TUTOR = "tutor"


class ObjectType(StrEnum):
    ITEM = "item"
    NODE = "node"
    TURN = "turn"
    BLOCK = "block"
    SESSION = "session"
    EXPLANATION = "explanation"
    ADAPTATION = "adaptation"
    NOTE = "note"
    EXPERIMENT = "experiment"
    MODEL = "model"
