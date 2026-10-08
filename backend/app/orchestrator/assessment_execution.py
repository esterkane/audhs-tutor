"""Conservative, per-submission boundaries for releasing an unstarted claim."""

from dataclasses import dataclass

from app.orchestrator.assessment_guard import AssessmentGuard


@dataclass
class AssessmentExecution:
    guard: AssessmentGuard | None = None
    prepared_continuation: bool = False
    gateway_entered: bool = False
    learning_commit_started: bool = False
    result_persistence_started: bool = False

    @property
    def can_release(self) -> bool:
        return (
            not self.gateway_entered
            and not self.learning_commit_started
            and not self.result_persistence_started
        )
