"""Storage ownership guards shared by migrations, create_all and backup validation."""

CONTENT_GUARD_REVISION = "52443d30fac9"

# A shared prerequisite may support a private target, never the reverse.
INVALID_EDGE = (
    "SELECT 1 FROM skill_edge e JOIN skill_node s ON s.id=e.from_skill_id "
    "JOIN skill_node t ON t.id=e.to_skill_id "
    "WHERE s.owner_learner_id IS NOT NULL "
    "AND s.owner_learner_id IS NOT t.owner_learner_id LIMIT 1"
)
INVALID_ASSESSMENT = (
    "SELECT 1 FROM assessment a JOIN skill_node s ON s.id=a.skill_id "
    "WHERE s.owner_learner_id IS NOT NULL "
    "AND s.owner_learner_id IS NOT a.owner_learner_id LIMIT 1"
)

CONTENT_GUARDS = {
    "assessment_owner_immutable": (
        "CREATE TRIGGER assessment_owner_immutable BEFORE UPDATE OF owner_learner_id ON assessment "
        "WHEN OLD.owner_learner_id IS NOT NEW.owner_learner_id "
        "BEGIN SELECT RAISE(ABORT, 'assessment ownership is immutable'); END"
    ),
    "skill_owner_immutable": (
        "CREATE TRIGGER skill_owner_immutable BEFORE UPDATE OF owner_learner_id ON skill_node "
        "WHEN OLD.owner_learner_id IS NOT NEW.owner_learner_id "
        "BEGIN SELECT RAISE(ABORT, 'skill ownership is immutable'); END"
    ),
    "object_owner_immutable": (
        "CREATE TRIGGER object_owner_immutable BEFORE UPDATE OF skill_id ON learning_object "
        "WHEN (SELECT owner_learner_id FROM skill_node WHERE id=OLD.skill_id) IS NOT "
        "(SELECT owner_learner_id FROM skill_node WHERE id=NEW.skill_id) "
        "BEGIN SELECT RAISE(ABORT, 'object ownership is immutable'); END"
    ),
    "representation_owner_immutable": (
        "CREATE TRIGGER representation_owner_immutable BEFORE UPDATE OF object_id ON representation "
        "WHEN (SELECT s.owner_learner_id FROM learning_object o JOIN skill_node s "
        "ON s.id=o.skill_id WHERE o.id=OLD.object_id) IS NOT "
        "(SELECT s.owner_learner_id FROM learning_object o JOIN skill_node s "
        "ON s.id=o.skill_id WHERE o.id=NEW.object_id) "
        "BEGIN SELECT RAISE(ABORT, 'representation ownership is immutable'); END"
    ),
}
for _action in ("INSERT", "UPDATE"):
    _name = f"skill_edge_owner_{_action.lower()}"
    CONTENT_GUARDS[_name] = (
        f"CREATE TRIGGER {_name} BEFORE {_action} ON skill_edge "
        "WHEN EXISTS (SELECT 1 FROM skill_node s JOIN skill_node t "
        "ON t.id=NEW.to_skill_id WHERE s.id=NEW.from_skill_id "
        "AND s.owner_learner_id IS NOT NULL "
        "AND s.owner_learner_id IS NOT t.owner_learner_id) "
        "BEGIN SELECT RAISE(ABORT, 'invalid private skill edge'); END"
    )
    _name = f"assessment_skill_owner_{_action.lower()}"
    CONTENT_GUARDS[_name] = (
        f"CREATE TRIGGER {_name} BEFORE {_action} ON assessment "
        "WHEN EXISTS (SELECT 1 FROM skill_node s WHERE s.id=NEW.skill_id "
        "AND s.owner_learner_id IS NOT NULL AND s.owner_learner_id IS NOT NEW.owner_learner_id) "
        "BEGIN SELECT RAISE(ABORT, 'assessment ownership differs from private skill'); END"
    )
