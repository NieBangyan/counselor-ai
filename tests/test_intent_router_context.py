from unittest.mock import (
    MagicMock,
    patch,
)

from src.routing.intent_router import (
    IntentRouter,
)


def build_response(
    content: str,
):
    response = MagicMock()

    response.choices = [
        MagicMock()
    ]

    response.choices[
        0
    ].message.content = content

    return response


@patch(
    "src.routing.intent_router.OpenAI"
)
def test_context_router_counseling(
    mock_openai,
):
    client = (
        mock_openai
        .return_value
    )

    client.chat.completions.create.return_value = (
        build_response(
            "counseling"
        )
    )

    router = IntentRouter()

    history = [
        {
            "role": "user",
            "content": (
                "最近学习压力特别大"
            ),
            "intent": "counseling",
        },
        {
            "role": "assistant",
            "content": (
                "最近主要是哪方面"
                "压力比较大？"
            ),
            "intent": "counseling",
        },
    ]

    result = (
        router.classify_with_context(
            "主要是数学",
            history,
        )
    )

    assert result == "counseling"


@patch(
    "src.routing.intent_router.OpenAI"
)
def test_context_router_policy(
    mock_openai,
):
    client = (
        mock_openai
        .return_value
    )

    client.chat.completions.create.return_value = (
        build_response(
            "policy"
        )
    )

    router = IntentRouter()

    history = [
        {
            "role": "user",
            "content": (
                "奖学金怎么申请？"
            ),
            "intent": "policy",
        },
        {
            "role": "assistant",
            "content": (
                "申请要求包括……"
            ),
            "intent": "policy",
        },
    ]

    result = (
        router.classify_with_context(
            "那什么时候截止？",
            history,
        )
    )

    assert result == "policy"


@patch(
    "src.routing.intent_router.OpenAI"
)
def test_context_router_other(
    mock_openai,
):
    client = (
        mock_openai
        .return_value
    )

    client.chat.completions.create.return_value = (
        build_response(
            "other"
        )
    )

    router = IntentRouter()

    history = [
        {
            "role": "user",
            "content": (
                "最近学习压力很大"
            ),
            "intent": "counseling",
        }
    ]

    result = (
        router.classify_with_context(
            "你好",
            history,
        )
    )

    assert result == "other"