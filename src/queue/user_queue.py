from rq import (
    Callback,
    Retry,
)
from rq.job import (
    Dependency,
    Job,
)

from src.queue.connection import (
    redis_connection,
    wechat_queue,
)
from src.queue.tasks import (
    handle_wechat_job_failure,
    process_wechat_message,
)


# ============================================================
# Configuration
# ============================================================

USER_JOB_TTL = 86400

USER_LOCK_TIMEOUT = 10
USER_LOCK_BLOCKING_TIMEOUT = 5

JOB_TIMEOUT = 180
JOB_RESULT_TTL = 500
JOB_FAILURE_TTL = 86400

JOB_RETRY_INTERVALS = [
    5,
    15,
    30,
]


# ============================================================
# User Queue
# ============================================================


def enqueue_user_message(
    open_id: str,
    content: str,
):
    """
    微信用户消息入队。

    同一用户：
        严格按照消息顺序执行。

    不同用户：
        可以由不同 Worker 并发执行。

    任务失败：
        自动 Retry。

    前一个任务最终失败：
        后一个任务仍允许继续。

    最终失败：
        failure callback 给用户发送一次兜底提示。
    """

    user_key = (
        f"wechat:last_job:{open_id}"
    )

    lock_key = (
        f"wechat:user_lock:{open_id}"
    )

    # ========================================================
    # 1. 同一用户入队锁
    # ========================================================

    lock = redis_connection.lock(
        lock_key,
        timeout=USER_LOCK_TIMEOUT,
        blocking_timeout=(
            USER_LOCK_BLOCKING_TIMEOUT
        ),
    )

    acquired = lock.acquire(
        blocking=True
    )

    if not acquired:
        raise RuntimeError(
            "无法获取用户消息队列锁。"
        )

    try:
        # ====================================================
        # 2. 查找这个用户上一个 Job
        # ====================================================

        previous_job_id = (
            redis_connection.get(
                user_key
            )
        )

        previous_job = None

        if previous_job_id:
            try:
                if isinstance(
                    previous_job_id,
                    bytes,
                ):
                    previous_job_id = (
                        previous_job_id.decode(
                            "utf-8"
                        )
                    )

                previous_job = Job.fetch(
                    previous_job_id,
                    connection=(
                        redis_connection
                    ),
                )

                # 已经结束的 Job
                # 不需要再作为 dependency。
                if (
                    previous_job.is_finished
                    or previous_job.is_failed
                    or previous_job.is_canceled
                    or previous_job.is_stopped
                ):
                    previous_job = None

            except Exception as exc:
                print(
                    "[USER QUEUE] "
                    "previous job unavailable: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                previous_job = None

        # ====================================================
        # 3. 基础入队参数
        # ====================================================

        enqueue_kwargs = {
            "job_timeout": JOB_TIMEOUT,
            "result_ttl": JOB_RESULT_TTL,
            "failure_ttl": JOB_FAILURE_TTL,

            "retry": Retry(
                max=3,
                interval=(
                    JOB_RETRY_INTERVALS
                ),
            ),

            "on_failure": Callback(
                handle_wechat_job_failure,
                timeout=15,
            ),
        }

        # ====================================================
        # 4. 同用户 dependency
        # ====================================================

        if previous_job is not None:
            dependency = Dependency(
                jobs=[
                    previous_job
                ],
                allow_failure=True,
            )

            enqueue_kwargs[
                "depends_on"
            ] = dependency

            print(
                "[USER QUEUE] "
                f"user={open_id} "
                f"depends_on={previous_job.id}"
            )

        # ====================================================
        # 5. 入队
        # ====================================================

        job = wechat_queue.enqueue(
            process_wechat_message,
            open_id,
            content,
            **enqueue_kwargs,
        )

        # ====================================================
        # 6. 更新当前用户最后一个 Job
        # ====================================================

        redis_connection.set(
            user_key,
            job.id,
            ex=USER_JOB_TTL,
        )

        print(
            "[USER QUEUE] "
            f"user={open_id} "
            f"new_job={job.id}"
        )

        return job

    finally:
        # ====================================================
        # 7. Redis Lock release
        # ====================================================

        try:
            lock.release()

        except Exception as exc:
            print(
                "[USER QUEUE] "
                "lock release warning: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )