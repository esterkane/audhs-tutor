"""Conservative, per-submission boundaries for releasing an unstarted claim."""

from dataclasses import dataclass


@dataclass
class AssessmentExecution:
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
