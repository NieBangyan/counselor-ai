from rq.job import Dependency
from rq.worker import SimpleWorker


# ============================================================
# Test Jobs
# ============================================================


def always_fail_job():
    """
    模拟前一条消息最终处理失败。
    """

    print(
        "[TEST DEPENDENCY] "
        "A1 executing -> fail"
    )

    raise RuntimeError(
        "Intentional dependency test failure."
    )


def following_job():
    """
    模拟同一用户的后一条消息。
    """

    print(
        "[TEST DEPENDENCY] "
        "A2 executing -> success"
    )

    return "A2 success"


# ============================================================
# Test
# ============================================================


def test_dependency_allows_previous_failure(
    test_queue,
    redis_connection,
):
    """
    验证：

    A1 FAILED
        ↓
    Dependency(
        allow_failure=True
    )
        ↓
    A2 仍然执行
        ↓
    A2 FINISHED
    """

    # --------------------------------------------------------
    # 1. A1
    # --------------------------------------------------------

    first_job = test_queue.enqueue(
        always_fail_job,
        job_timeout=30,
        failure_ttl=60,
    )

    # --------------------------------------------------------
    # 2. A2
    # --------------------------------------------------------

    dependency = Dependency(
        jobs=[
            first_job
        ],
        allow_failure=True,
    )

    second_job = test_queue.enqueue(
        following_job,
        depends_on=dependency,
        job_timeout=30,
        result_ttl=60,
        failure_ttl=60,
    )

    # A1 尚未执行，
    # 所以 A2 此时应该等待。
    second_job.refresh()

    assert second_job.is_deferred

    # --------------------------------------------------------
    # 3. Worker
    # --------------------------------------------------------

    worker = SimpleWorker(
        [
            test_queue
        ],
        connection=redis_connection,
    )

    worker.work(
        burst=True,
    )

    # --------------------------------------------------------
    # 4. Refresh
    # --------------------------------------------------------

    first_job.refresh()
    second_job.refresh()

    # --------------------------------------------------------
    # 5. Assertions
    # --------------------------------------------------------

    assert first_job.is_failed

    assert second_job.is_finished

    assert (
        second_job.return_value()
        == "A2 success"
    )