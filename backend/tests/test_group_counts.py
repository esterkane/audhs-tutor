from fractions import Fraction

import pytest
from pydantic import ValidationError

from app.kernel.group_counts import GroupCountInput, compare_groups


def comparison(rows: list[dict[str, object]]):
    return compare_groups(GroupCountInput.model_validate({"groups": rows}))


def test_retention_is_distinct_from_representation_and_labels_follow_rows():
    rows = [
        {"label": " North ", "before": 100, "after": 90},
        {"label": "South", "before": 50, "after": 30},
    ]
    result = comparison(rows)
    north, south = result.groups
    assert (result.before_total, result.after_total) == (150, 120)
    assert (north.label, north.removed, south.removed) == ("North", 10, 20)
    assert (north.retention, south.retention) == (Fraction(9, 10), Fraction(3, 5))
    assert (south.representation_before, south.representation_after) == (
        Fraction(1, 3),
        Fraction(1, 4),
    )
    assert comparison(list(reversed(rows))).groups == tuple(reversed(result.groups))


def test_zero_group_and_all_removed_have_explicit_undefined_denominators():
    result = comparison(
        [
            {"label": "Empty", "before": 0, "after": 0},
            {"label": "Removed", "before": 3, "after": 0},
        ]
    )
    empty, removed = result.groups
    assert empty.retention is None
    assert empty.representation_before == 0
    assert removed.retention == 0
    assert all(row.representation_after is None for row in result.groups)
    zeros = comparison(
        [
            {"label": "X", "before": 0, "after": 0},
            {"label": "Y", "before": 0, "after": 0},
        ]
    )
    assert all(row.representation_before is None for row in zeros.groups)


def test_maximum_groups_and_counts_keep_exact_unchanged_shares():
    result = comparison([{"label": str(i), "before": 10**9, "after": 10**9} for i in range(8)])
    assert result.before_total == result.after_total == 8 * 10**9
    assert all(row.retention == 1 and row.removed == 0 for row in result.groups)
    assert all(row.representation_after == Fraction(1, 8) for row in result.groups)


@pytest.mark.parametrize("value", [True, False, "2", 2.0, 1.5, -1, 10**9 + 1, None])
@pytest.mark.parametrize("field", ["before", "after"])
def test_counts_reject_coercion_and_out_of_bounds(field, value):
    rows = [{"label": "A", "before": 2, "after": 1}, {"label": "B", "before": 2, "after": 1}]
    rows[0][field] = value
    with pytest.raises(ValidationError):
        comparison(rows)


@pytest.mark.parametrize(
    "patch",
    [
        {"label": " B "},
        {"label": " "},
        {"label": "x" * 81},
        {"label": 1},
        {"after": 3},
        {"verified": True},
    ],
)
def test_invalid_labels_membership_and_untrusted_extra_claims(patch):
    with pytest.raises(ValidationError):
        comparison(
            [
                {"label": "A", "before": 2, "after": 1, **patch},
                {"label": "B", "before": 2, "after": 1},
            ]
        )


@pytest.mark.parametrize("size", [0, 1, 9])
def test_group_count_bounds(size):
    with pytest.raises(ValidationError):
        comparison([{"label": str(i), "before": 1, "after": 1} for i in range(size)])


def test_snapshot_does_not_follow_mutations_of_input():
    rows = [{"label": "A", "before": 2, "after": 1}, {"label": "B", "before": 2, "after": 1}]
    supplied = GroupCountInput.model_validate({"groups": rows})
    rows[0]["after"] = 0
    assert compare_groups(supplied).groups[0].after == 1
    with pytest.raises(ValidationError):
        supplied.groups[0].after = 0
