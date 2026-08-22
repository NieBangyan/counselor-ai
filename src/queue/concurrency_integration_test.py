import time

from src.queue.connection import (
    redis_connection,
)


TEST_TTL = 600


def concurrency_integration_job(
    user_id: str,
    message_id: str,
    delay: float = 3.0,
):
    """
    多 Worker 并发集成测试任务。

    把真实开始/结束时间写入 Redis，
    用于验证不同 Worker 是否发生时间重叠。
    """

    started_at = time.time()

    start_key = (
        f"test:concurrency:"
        f"{user_id}:{message_id}:start"
    )

    end_key = (
        f"test:concurrency:"
        f"{user_id}:{message_id}:end"
    )

    redis_connection.set(
        start_key,
        str(started_at),
        ex=TEST_TTL,
    )

    print(
        "[INTEGRATION START] "
        f"user={user_id} "
        f"message={message_id} "
        f"time={started_at:.3f}"
    )

    time.sleep(delay)

    finished_at = time.time()

    redis_connection.set(
        end_key,
        str(finished_at),
        ex=TEST_TTL,
    )

    print(
        "[INTEGRATION DONE] "
        f"user={user_id} "
        f"message={message_id} "
        f"time={finished_at:.3f}"
    )

    return {
        "user_id": user_id,
        "message_id": message_id,
        "started_at": started_at,
        "finished_at": finished_at,
    }