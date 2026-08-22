import time

from rq import get_current_job


def retry_test_job() -> None:
    """
    专门用于测试 RQ Retry。

    每次执行都会故意抛出异常。
    """

    job = get_current_job()

    job_id = (
        job.id
        if job is not None
        else "unknown"
    )

    retries_left = (
        getattr(
            job,
            "retries_left",
            None,
        )
        if job is not None
        else None
    )

    print(
        "[RETRY TEST] "
        f"time={time.strftime('%H:%M:%S')} "
        f"job={job_id} "
        f"retries_left={retries_left}"
    )

    raise RuntimeError(
        "Intentional retry test failure."
    )