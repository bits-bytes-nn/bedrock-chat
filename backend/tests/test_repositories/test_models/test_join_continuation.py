from app.repositories.models.conversation import (
    ReasoningContentModel,
    TextContentModel,
    ToolUseContentModel,
    drop_partial_word,
    join_continuation,
)
import pytest


def text(body: str) -> TextContentModel:
    return TextContentModel(content_type="text", body=body)


REASONING = ReasoningContentModel(
    content_type="reasoning", text="thinking", signature="s", redacted_content=b""
)


def test_joins_the_text_at_the_cut():
    previous = [REASONING, text("The first")]
    assert join_continuation(previous, [text(" half")]) == [
        REASONING,
        text("The first half"),
    ]
    # The stored answer is not changed in place.
    assert previous[-1] == text("The first")


def test_drops_the_reasoning_of_the_continuation():
    # Models that always reason start the continuation with reasoning, which
    # would otherwise hide the text that follows it.
    assert join_continuation([text("The first")], [REASONING, text(" half")]) == [
        text("The first half")
    ]


def test_keeps_the_previous_answer_when_the_blocks_differ():
    tool_use = ToolUseContentModel.model_validate(
        {
            "content_type": "toolUse",
            "body": {"tool_use_id": "t", "name": "search", "input": {}},
        }
    )
    assert join_continuation([tool_use], [text("rest")]) == [tool_use, text("rest")]
    assert join_continuation([text("all")], [REASONING]) == [text("all")]


def test_keeps_one_space_between_words():
    # Models often start the continuation with the space, or without it.
    assert join_continuation([text("due to ")], [text(" similar")]) == [
        text("due to similar")
    ]
    assert join_continuation([text("due to ")], [text("similar")]) == [
        text("due to similar")
    ]
    # Indentation after a line break is kept.
    assert join_continuation([text("def f():\n")], [text("    return 1")]) == [
        text("def f():\n    return 1")
    ]


@pytest.mark.parametrize(
    ("body", "kept"),
    [
        ("ranging up to 800\u00b0", "ranging up to "),
        ("| 2 | He | Hel", "| 2 | He | "),
        ("ends with a space ", "ends with a space "),
        ("ends a line\n", "ends a line\n"),
        ("오늘은 날씨가 좋", "오늘은 날씨가 "),
        # No spaces between Japanese words: nothing is known to be cut.
        ("今日は良い天気ですね。外に出て", "今日は良い天気ですね。外に出て"),
        ("oneword", "oneword"),
    ],
)
def test_drops_the_word_the_limit_may_have_cut(body, kept):
    assert drop_partial_word([REASONING, text(body)]) == [REASONING, text(kept)]


def test_keeps_a_word_that_would_leave_no_text():
    assert drop_partial_word([REASONING, text("\n\nThe")]) == [
        REASONING,
        text("\n\nThe"),
    ]


def test_leaves_content_that_does_not_end_in_text():
    assert drop_partial_word([REASONING]) == [REASONING]
    assert drop_partial_word([]) == []
