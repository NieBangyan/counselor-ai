from rq.job import Job

from src.queue.connection import (
    redis_connection,
    wechat_queue,
)
from src.queue.tasks import (
    process_wechat_message,
)


USER_JOB_TTL = 86400

USER_LOCK_TIMEOUT = 10
USER_LOCK_BLOCKING_TIMEOUT = 5


def enqueue_user_message(
    open_id: str,
    content: str,
):
    """
    微信用户消息入队。

    同一用户：
        按消息进入顺序建立 RQ dependency，
        保证串行处理。

    不同用户：
        使用不同 Redis Lock，
        可以并发入队、并发执行。
    """

    user_key = (
        f"wechat:last_job:{open_id}"
    )

    lock_key = (
        f"wechat:user_lock:{open_id}"
    )

    # ========================================================
    # 同一用户入队过程加 Redis 分布式锁
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
        # 1. 找这个用户上一个任务
        # ====================================================

        previous_job_id = (
            redis_connection.get(
                user_key
            )
        )

        previous_job = None

        if previous_job_id:
            try:
                previous_job = Job.fetch(
                    previous_job_id.decode(
                        "utf-8"
                    ),
                    connection=(
                        redis_connection
                    ),
                )

                # 已经彻底结束的任务
                # 不需要继续依赖。
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
        # 2. 构造新任务
        # ====================================================

        enqueue_kwargs = {
            "job_timeout": 180,
            "result_ttl": 500,
            "failure_ttl": 86400,
        }

        if previous_job is not None:
            enqueue_kwargs[
                "depends_on"
            ] = previous_job

            print(
                "[USER QUEUE] "
                f"user={open_id} "
                f"depends_on={previous_job.id}"
            )

        # ====================================================
        # 3. 入队
        # ====================================================

        job = wechat_queue.enqueue(
            process_wechat_message,
            open_id,
            content,
            **enqueue_kwargs,
        )

        # ====================================================
        # 4. 原子区间内更新当前用户最后一个任务
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
        try:
            lock.release()
        except Exception:
            pass