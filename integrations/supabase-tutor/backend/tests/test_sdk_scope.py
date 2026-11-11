"""Explicit caller cues, comparison coverage and retained-history boundaries."""

import json

import pytest

from backend.tests.test_guard import codes, turn
from backend.tests.test_tools import FakeRetriever, ctx
from backend.tutor import tools
from backend.tutor.guard import GuardContext
from backend.tutor.sdk_scope import SdkScope, learner_sdk_scope


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("In JavaScript SDK v1, compare PostgreSQL v1 vs v3 extensions.", None),
        ("Compare current JavaScript SDK with v1.", SdkScope("javascript", ("unversioned", "v1"))),
        (
            "Wie unterscheidet sich der aktuelle JavaScript-Client von Version 1?",
            SdkScope("javascript", ("unversioned", "v1")),
        ),
        ("Compare JavaScript SDK v1 vs v2", SdkScope("javascript", ("v1", "v2"))),
        ("Compare Python and Swift SDKs", None),
        ("My Python process reports a database failure", None),
        ("Show the JavaScript client", SdkScope("javascript", ())),
        ("What changed in the JavaScript SDK v8?", SdkScope("javascript", ("v8",))),
    ],
)
def test_caller_binding(question, expected):
    assert learner_sdk_scope(question) == expected


class Spy(FakeRetriever):
    async def search(self, query, k=8, products=None, **options):
        self.calls.append(options)
        return []


async def test_untrusted_planner_filters_do_not_create_scope_and_missing_editions_are_not_substituted():
    spy = Spy()
    tool = ctx(retriever=spy, learner_text="Which rows are visible?")
    args = tools.SearchDocsInput(query="Python SDK v1 documentation", sdk="python", edition="v1")
    await tools._search_docs(args, tool, tools.TurnBudget())
    assert spy.calls == [{}]
    tool.learner_text = "Compare current Swift SDK with v1."
    result = await tools._search_docs(args, tool, tools.TurnBudget())
    assert spy.calls[-1] == {"sdk_scope": SdkScope("swift", ("unversioned", "v1"))}
    assert json.loads(result.content)["scope_note"]["sdk_reference"]["missing_from_results"] == [
        "unversioned",
        "v1",
    ]
    tool.learner_text = "What changed in Swift SDK v8?"
    result = await tools._search_docs(args, tool, tools.TurnBudget())
    assert spy.calls[-1] == {"sdk_scope": SdkScope("swift", ("v8",))}
    assert json.loads(result.content)["results"] == []


def test_prior_conversation_url_cannot_satisfy_another_edition():
    link = "https://supabase.com/docs/reference/dart/v1/insert#examples"
    t = turn(
        text="This is documented [1]. What now?",
        citations=[{"n": 1, "url": link, "title": "Reference", "tier": 1}],
    )
    context = GuardContext(sources={link: 1}, learner_text="How do I insert using the current Dart SDK?")
    assert codes(t, context)["SDK_REFERENCE_SCOPE_MISMATCH"] == "block"


@pytest.mark.parametrize(
    ("expected", "question"),
    [
        [
            "csharp/v0/range",
            "With version 0 of the Supabase C# client, how do I request just the second page of ten records?",
        ],
        [
            "csharp/range",
            "In the current C# library I need ten rows starting at row 10. How do I paginate the database result?",
        ],
        ["dart/v1/insert", "In the version 1 Flutter Dart client, which call creates a new database row?"],
        ["dart/insert", "In the current Dart SDK, how can I add a record to the table?"],
        ["javascript/v1/auth-signout", "JavaScript client v1: how do I end the currently logged-in session?"],
        [
            "javascript/auth-exchangecodeforsession",
            "I got a PKCE authorization code in my JS callback. How do I turn it into a session with the current SDK?",
        ],
        [
            "python/select",
            "In the current Python client what call retrieves a few named columns from a table?",
        ],
        [
            "python/update",
            "With the current Python client how do I change the values on records that match my filter?",
        ],
        ["swift/v1/delete", "Which operation removes matching rows from a table in Swift SDK version 1?"],
        ["swift/order", "In the current Swift API how do I sort rows by a column in descending order?"],
        [
            "kotlin/v2/auth-exchangecodeforsession",
            "Using Kotlin SDK v2 how do I complete a PKCE sign-in given the authorization code?",
        ],
        [
            "kotlin/auth-signout",
            "With the current Kotlin client, how do I log out of the current Supabase session?",
        ],
    ],
)
def test_frozen_caller_queries(expected, question):
    parts = expected.split("/")
    assert learner_sdk_scope(question) == SdkScope(
        parts[0], (parts[1] if len(parts) == 3 else "unversioned",)
    )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("How do I recover a session in Supabase C# v0?", SdkScope("csharp", ("v0",))),
        ("I am not using the Python SDK. What SQL should I run?", None),
        ("Did JavaScript SDK v2.1 change this?", SdkScope("javascript", ("v2.1",))),
    ],
)
def test_release_and_negation_cues(query, expected):
    assert learner_sdk_scope(query) == expected
