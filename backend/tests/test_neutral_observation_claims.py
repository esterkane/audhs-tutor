import pytest
from pydantic import ValidationError

from app.schemas.knowledge_authoring import (
    NeutralObservationDiscussion,
    NeutralObservationSection,
    ResearchDiscussion,
    ResearchTutorAnswer,
    is_unmeasured_observation,
)

SOURCE = (
    "A note reports slower requests after deployment but provides no "
    "measurements, comparison or investigation results."
)


@pytest.mark.parametrize(
    "kind,key",
    [(NeutralObservationDiscussion, "answer_sentence"), (NeutralObservationSection, "section")],
)
@pytest.mark.parametrize(
    "claim",
    [
        "The note establishes only a correlation, not causation.",
        "The passage shows a correlation between deployment and slower requests.",
        "The note incorrectly claims deployment definitely caused it.",
        "The note's claim of definite causation is unsupported.",
        "The source falsely asserts no measurements were ever taken.",
        "The assertion that no measurements were ever taken is corroborated by the source.",
    ],
)
def test_fresh_neutral_note_claims_require_temporal_order_not_invented_attribution(
    kind, key, claim
):
    with pytest.raises(ValidationError, match="temporal order|does not corroborate"):
        kind.model_validate({key: claim, "source_indices": [1]})


@pytest.mark.parametrize(
    "claim",
    [
        "Only event order is reported; cause is not established, and measurements may exist elsewhere.",
        "This does not show a correlation or establish cause.",
        "No correlation or cause is established here.",
    ],
)
def test_valid_corrections_are_preserved(claim):
    assert (
        NeutralObservationDiscussion(answer_sentence=claim, source_indices=[1]).answer_sentence
        == claim
    )


def test_only_complete_observed_source_templates_are_selected():
    assert is_unmeasured_observation(SOURCE)
    assert is_unmeasured_observation(SOURCE.replace(", comparison", ""))
    assert not is_unmeasured_observation(
        SOURCE + " A measured correlation of 0.8 is reported elsewhere in this passage."
    )
    assert not is_unmeasured_observation("The worksheet falsely asserts the median is 9.")
    assert not is_unmeasured_observation("These observations show a measured correlation.")
    # Other contexts and historical prose can retain justified source criticism.
    text = "The source falsely asserts the median is 9."
    assert ResearchDiscussion(answer_sentence=text, source_indices=[1]).answer_sentence == text
    assert ResearchTutorAnswer(discussion="Only a correlation is established.").discussion


@pytest.mark.parametrize(
    "kind,key",
    [(NeutralObservationDiscussion, "answer_sentence"), (NeutralObservationSection, "section")],
)
@pytest.mark.parametrize(
    "text",
    [
        'The phrase "only a correlation" is unsupported; only event order is reported.',
        'The statement "the note incorrectly claims causation" is wrong; the note reports event order.',
        "Describing this as ‘only a correlation’ overstates the source; only event order is reported.",
        "The wording 'the source falsely asserts no measurements' is misleading; the note makes no such assertion.",
    ],
)
def test_quoted_claim_rejections_are_not_mistaken_for_assertions(kind, key, text):
    assert kind.model_validate({key: text, "source_indices": [1]}).model_dump()[key] == text


@pytest.mark.parametrize(
    "text",
    [
        'The note shows "only a correlation".',
        'The phrase "only a correlation" is unsupported. The note incorrectly claims causation.',
    ],
)
def test_quotes_do_not_exempt_assertions_or_other_unquoted_false_claims(text):
    with pytest.raises(ValidationError):
        NeutralObservationDiscussion(answer_sentence=text, source_indices=[1])
