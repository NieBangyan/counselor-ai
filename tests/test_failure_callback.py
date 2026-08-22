from unittest.mock import MagicMock, patch

from rq.job import Job

from src.queue.tasks import (
    handle_wechat_job_failure,
)


# ============================================================
# Helpers
# ============================================================


def make_test_job(
    redis_connection,
    retries_left: int,
) -> Job:
    """
    创建一个仅供 callback 测试使用的 Job。

    args[0] 模拟微信 open_id。
    """

    job = Job.create(
        func=lambda: None,
        args=(
            "fake-open-id",
            "test message",
        ),
        connection=redis_connection,
    )

    job.retries_left = retries_left

    return job


# ============================================================
# Test 1
# 中间 Retry 不发送失败通知
# ============================================================


def test_failure_callback_skips_notification_when_retry_remains(
    redis_connection,
):
    job = make_test_job(
        redis_connection,
        retries_left=2,
    )

    with patch(
        "src.queue.tasks.get_wechat_client"
    ) as mock_get_client:

        handle_wechat_job_failure(
            job,
            redis_connection,
            RuntimeError,
            RuntimeError(
                "Intentional failure."
            ),
            None,
        )

        # 还有 Retry，
        # 不应该获取微信 Client，
        # 更不应该发送消息。
        mock_get_client.assert_not_called()


# ============================================================
# Test 2
# 最终失败发送一次通知
# ============================================================


def test_failure_callback_sends_final_notification_once(
    redis_connection,
):
    job = make_test_job(
        redis_connection,
        retries_left=0,
    )

    notification_key = (
        f"wechat:failure_notified:{job.id}"
    )

    # 防止之前测试留下同名 key
    redis_connection.delete(
        notification_key
    )

    mock_client = MagicMock()

    with patch(
        "src.queue.tasks.get_wechat_client",
        return_value=mock_client,
    ):
        # ----------------------------------------------------
        # 第一次 callback
        # ----------------------------------------------------

        handle_wechat_job_failure(
            job,
            redis_connection,
            RuntimeError,
            RuntimeError(
                "Intentional failure."
            ),
            None,
        )

        # ----------------------------------------------------
        # 模拟极端情况下 callback 又被调用一次
        # ----------------------------------------------------

        handle_wechat_job_failure(
            job,
            redis_connection,
            RuntimeError,
            RuntimeError(
                "Intentional failure."
            ),
            None,
        )

    # --------------------------------------------------------
    # 微信只能发送一次
    # --------------------------------------------------------

    assert (
        mock_client
        .send_text_message
        .call_count
        == 1
    )

    # --------------------------------------------------------
    # 检查发送对象
    # --------------------------------------------------------

    mock_client.send_text_message.assert_called_once_with(
        open_id="fake-open-id",
        content=(
            "AI 辅导员暂时无法处理"
            "这个问题，请稍后重新发送。"
        ),
    )

    # --------------------------------------------------------
    # 幂等 key 应存在
    # --------------------------------------------------------

    assert (
        redis_connection.get(
            notification_key
        )
        == b"1"
    )

    # 清理
    redis_connection.delete(
        notification_key
    )