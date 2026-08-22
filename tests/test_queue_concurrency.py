import time

from rq.worker import SimpleWorker


# ============================================================
# Test Job
# ============================================================


def concurrency_test_job(
    user_id: str,
    message_id: str,
    delay: float,
):
    """
    模拟一个需要一定处理时间的 AI Job。
    """

    started_at = time.time()

    print(
        "[CONCURRENCY TEST START] "
        f"user={user_id} "
        f"message={message_id}"
    )

    time.sleep(delay)

    finished_at = time.time()

    print(
        "[CONCURRENCY TEST DONE] "
        f"user={user_id} "
        f"message={message_id}"
    )

    return {
        "user_id": user_id,
        "message_id": message_id,
        "started_at": started_at,
        "finished_at": finished_at,
    }


# ============================================================
# Basic queue test
# ============================================================


def test_multiple_users_jobs_complete(
    test_queue,
    redis_connection,
):
    """
    验证多个不同用户的 Job
    都能够被正常处理。

    注意：
    SimpleWorker 本身是单 Worker，
    这个测试暂时不证明真正的并行执行。

    真正多 Worker 并行，
    后面单独做集成测试。
    """

    jobs = []

    for user_id in [
        "user-a",
        "user-b",
        "user-c",
    ]:
        job = test_queue.enqueue(
            concurrency_test_job,
            user_id,
            "message-1",
            0.05,
            job_timeout=30,
        )

        jobs.append(job)

    worker = SimpleWorker(
        [test_queue],
        connection=redis_connection,
    )

    worker.work(
        burst=True,
    )

    for job in jobs:
        job.refresh()

        assert job.is_finished

        result = job.return_value()

        assert result[
            "user_id"
        ] in {
            "user-a",
            "user-b",
            "user-c",
        }

        assert (
            result["message_id"]
            == "message-1"
        )