from rq.job import Dependency

from src.queue.connection import (
    wechat_queue,
)
from src.queue.concurrency_integration_test import (
    concurrency_integration_job,
)


def enqueue_job(
    user_id: str,
    message_id: str,
    previous_job=None,
):
    kwargs = {
        "job_timeout": 30,
        "result_ttl": 600,
        "failure_ttl": 600,
    }

    if previous_job is not None:
        kwargs["depends_on"] = Dependency(
            jobs=[previous_job],
            allow_failure=True,
        )

    return wechat_queue.enqueue(
        concurrency_integration_job,
        user_id,
        message_id,
        3.0,
        **kwargs,
    )


def main():
    # User A
    a1 = enqueue_job(
        "A",
        "A1",
    )

    a2 = enqueue_job(
        "A",
        "A2",
        a1,
    )

    a3 = enqueue_job(
        "A",
        "A3",
        a2,
    )

    # User B
    b1 = enqueue_job(
        "B",
        "B1",
    )

    b2 = enqueue_job(
        "B",
        "B2",
        b1,
    )

    # User C
    c1 = enqueue_job(
        "C",
        "C1",
    )

    print(
        "[INTEGRATION TEST ENQUEUED]"
    )

    print(
        f"A1={a1.id}"
    )
    print(
        f"A2={a2.id}"
    )
    print(
        f"A3={a3.id}"
    )

    print(
        f"B1={b1.id}"
    )
    print(
        f"B2={b2.id}"
    )

    print(
        f"C1={c1.id}"
    )


if __name__ == "__main__":
    main()