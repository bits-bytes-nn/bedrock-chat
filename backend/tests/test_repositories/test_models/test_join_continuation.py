from app.repositories.models.conversation import (
    ReasoningContentModel,
    TextContentModel,
    ToolUseContentModel,
    join_continuation,
)


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
