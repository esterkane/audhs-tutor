import math

import pytest

from app.kernel.vector_metrics import vector_metrics


def test_known_values_and_negative_inner_product_ordering():
    score = vector_metrics([1, 0], [2, 2])
    assert score.dot == 2 and score.negative_inner_product == -2
    assert score.l2 == pytest.approx(math.sqrt(5))
    assert score.cosine_similarity == pytest.approx(1 / math.sqrt(2))
    assert score.cosine_distance == pytest.approx(1 - 1 / math.sqrt(2))


def test_unequal_norms_can_reverse_inner_product_and_cosine_rankings():
    a, b = vector_metrics([1, 0], [2, 2]), vector_metrics([1, 0], [1, 0])
    assert a.negative_inner_product < b.negative_inner_product
    assert a.cosine_distance > b.cosine_distance
    assert a.l2 > b.l2


def test_equal_norms_are_not_necessary_for_agreeing_rankings():
    a, b = vector_metrics([1, 0], [2, 0]), vector_metrics([1, 0], [0, 1])
    assert a.negative_inner_product < b.negative_inner_product
    assert a.cosine_distance < b.cosine_distance


@pytest.mark.parametrize("query", [[1, 0], [0, 3], [-2, 1], [0.1, -0.2]])
def test_equal_nonzero_candidate_norms_give_same_three_rankings(query):
    candidates = [[5, 0], [3, 4], [-3, 4], [-5, 0], [0, -5]]
    scores = [vector_metrics(query, value) for value in candidates]
    for i, a in enumerate(scores):
        for b in scores[i + 1 :]:
            # Compare pairwise signs, including ties rather than arbitrary sort stability.
            differences = [
                a.negative_inner_product - b.negative_inner_product,
                a.cosine_distance - b.cosine_distance,
                a.l2 - b.l2,
            ]
            signs = [0 if abs(d) < 1e-12 else math.copysign(1, d) for d in differences]
            assert signs[0] == signs[1] == signs[2]


@pytest.mark.parametrize("query,candidate", [([0, 0], [1, 0]), ([1, 0], [0, 0]), ([0], [0])])
def test_zero_vector_has_no_cosine_score(query, candidate):
    score = vector_metrics(query, candidate)
    assert score.cosine_similarity is None and score.cosine_distance is None
    assert score.dot == 0


@pytest.mark.parametrize(
    "query,candidate",
    [
        ([], []),
        ([1], [1, 2]),
        ([True], [1]),
        ([float("nan")], [1]),
        ([float("inf")], [1]),
        ([1e101], [1]),
        ([1e-101], [1]),
        ([1] * 4097, [1] * 4097),
        ([10**1000], [1]),
    ],
)
def test_unsupported_inputs_fail_explicitly(query, candidate):
    with pytest.raises(ValueError):
        vector_metrics(query, candidate)


@pytest.mark.parametrize("scale", [1e-100, 1, 1e100])
def test_supported_extreme_ranges_stay_finite(scale):
    score = vector_metrics([scale, 0], [0, scale])
    assert math.isfinite(score.l2) and math.isfinite(score.dot)
    assert score.cosine_distance == 1


def test_negative_dot_product_is_not_mistaken_for_negative_distance():
    score = vector_metrics([1, 0], [-2, 0])
    assert score.dot == -2
    assert score.negative_inner_product == 2
    assert score.cosine_similarity == -1
    assert score.cosine_distance == 2
    assert score.l2 == 3
