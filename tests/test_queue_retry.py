from rq import Retry
from rq.worker import SimpleWorker


_attempts = 0


def failing_then_success_job():
    """
    前两次执行失败，
    第三次成功。
    """

    global _attempts

    _attempts += 1

    print(
        "[TEST RETRY] "
        f"attempt={_attempts}"
    )

    if _attempts < 3:
        raise RuntimeError(
            "Intentional test failure."
        )

    return "success"


def test_queue_retry(
    test_queue,
    redis_connection,
):
    """
    验证 RQ Retry：

    第一次失败
        ↓
    Retry
        ↓
    第二次失败
        ↓
    Retry
        ↓
    第三次成功
        ↓
    FINISHED
    """

    global _attempts

    _attempts = 0

    job = test_queue.enqueue(
        failing_then_success_job,
        retry=Retry(
            max=2,
        ),
        job_timeout=30,
    )

    worker = SimpleWorker(
        [
            test_queue
        ],
        connection=redis_connection,
    )

    worker.work(
        burst=True,
    )

    job.refresh()

    assert job.is_finished

    assert job.return_value() == "success"

    assert _attempts == 3