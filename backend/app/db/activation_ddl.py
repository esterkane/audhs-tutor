"""Private activation membership guards, separate from historical migration DDL."""

ACTIVATION_REVISION = "969f9ebbe38a"

ACTIVATION_TABLES = (
    "lesson_activation",
    "lesson_activation_skill",
    "lesson_activation_object",
    "lesson_activation_assessment",
    "lesson_activation_edge",
)
ACTIVATION_GUARDS: dict[str, str] = {}


def _guard(name: str, action: str, table: str, condition: str) -> None:
    ACTIVATION_GUARDS[name] = (
        f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {action} ON {table} "
        f"WHEN {condition} BEGIN SELECT RAISE(ABORT, 'invalid activation history'); END"
    )


for _table in ACTIVATION_TABLES:
    _guard(f"{_table}_no_update", "UPDATE", _table, "1")

_SKILL_VALID = (
    "EXISTS (SELECT 1 FROM skill_node s WHERE s.id=NEW.entity_id "
    "AND s.owner_learner_id=NEW.learner_id)"
)
_guard("activation_skill_owner", "INSERT", "lesson_activation_skill", f"NOT ({_SKILL_VALID})")

# Used after restore too: triggers do not validate preexisting rows.
INVALID_ACTIVATION: list[str] = [
    "SELECT 1 FROM lesson_activation_skill l LEFT JOIN skill_node s ON s.id=l.entity_id "
    "WHERE s.owner_learner_id IS NOT l.learner_id LIMIT 1"
]
for _kind, _table, _parent in (
    ("object", "learning_object", "skill_id"),
    ("assessment", "assessment", "skill_id"),
    ("edge", "skill_edge", "to_skill_id"),
):
    _link = f"lesson_activation_{_kind}"
    _owner = " AND e.owner_learner_id=NEW.learner_id" if _kind == "assessment" else ""
    _valid = (
        f"EXISTS (SELECT 1 FROM {_table} e JOIN lesson_activation_skill s "
        f"ON s.entity_id=e.{_parent} WHERE e.id=NEW.entity_id "
        f"AND s.activation_id=NEW.activation_id AND s.learner_id=NEW.learner_id{_owner})"
    )
    _guard(f"activation_{_kind}_member", "INSERT", _link, f"NOT ({_valid})")
    _guard(
        f"activation_{_kind}_reparent",
        f"UPDATE OF {_parent}",
        _table,
        f"EXISTS (SELECT 1 FROM {_link} l WHERE l.entity_id=OLD.id AND NOT EXISTS "
        f"(SELECT 1 FROM lesson_activation_skill s WHERE s.entity_id=NEW.{_parent} "
        "AND s.activation_id=l.activation_id AND s.learner_id=l.learner_id))",
    )
    _guard(
        f"activation_skill_delete_{_kind}",
        "DELETE",
        "lesson_activation_skill",
        f"EXISTS (SELECT 1 FROM {_link} l JOIN {_table} e ON e.id=l.entity_id "
        f"WHERE e.{_parent}=OLD.entity_id AND l.activation_id=OLD.activation_id)",
    )
    _owner_check = " OR e.owner_learner_id IS NOT l.learner_id" if _kind == "assessment" else ""
    INVALID_ACTIVATION.append(
        f"SELECT 1 FROM {_link} l LEFT JOIN {_table} e ON e.id=l.entity_id "
        f"WHERE NOT EXISTS (SELECT 1 FROM lesson_activation_skill s WHERE s.entity_id=e.{_parent} "
        f"AND s.activation_id=l.activation_id AND s.learner_id=l.learner_id){_owner_check} LIMIT 1"
    )
