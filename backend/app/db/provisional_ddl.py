"""Immutable advisory records; deletion remains available to learner wipe."""

PROVISIONAL_GUARDS = {
    "provisional_feedback_no_update": (
        "CREATE TRIGGER provisional_feedback_no_update BEFORE UPDATE ON provisional_feedback "
        "BEGIN SELECT RAISE(ABORT, 'provisional feedback is immutable'); END"
    ),
    "provisional_feedback_owned_insert": (
        "CREATE TRIGGER provisional_feedback_owned_insert BEFORE INSERT ON provisional_feedback "
        "WHEN NOT EXISTS (SELECT 1 FROM workspace_request w JOIN session s ON s.id=w.session_id "
        "WHERE w.id=NEW.claim_id AND w.learner_id=NEW.learner_id "
        "AND s.learner_id=NEW.learner_id AND s.id=NEW.session_id) "
        "OR (NEW.revision_of_feedback_id IS NOT NULL AND NOT EXISTS "
        "(SELECT 1 FROM provisional_feedback p WHERE p.id=NEW.revision_of_feedback_id "
        "AND p.learner_id=NEW.learner_id AND p.assessment_id=NEW.assessment_id "
        "AND p.content_fingerprint=NEW.content_fingerprint)) "
        "BEGIN SELECT RAISE(ABORT, 'provisional feedback ownership mismatch'); END"
    ),
}

INVALID_PROVISIONAL_OWNERSHIP = (
    "SELECT 1 FROM provisional_feedback f WHERE NOT EXISTS "
    "(SELECT 1 FROM workspace_request w JOIN session s ON s.id=w.session_id "
    "WHERE w.id=f.claim_id AND w.learner_id=f.learner_id "
    "AND s.learner_id=f.learner_id AND s.id=f.session_id) "
    "OR (f.revision_of_feedback_id IS NOT NULL AND NOT EXISTS "
    "(SELECT 1 FROM provisional_feedback p WHERE p.id=f.revision_of_feedback_id "
    "AND p.learner_id=f.learner_id AND p.assessment_id=f.assessment_id "
    "AND p.content_fingerprint=f.content_fingerprint)) LIMIT 1"
)
