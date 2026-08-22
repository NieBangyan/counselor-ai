from rq import Callback, Retry

from src.queue.connection import (
    wechat_queue,
)
from src.queue.failure_callback_test import (
    failing_wechat_like_job,
)
from src.queue.tasks import (
    handle_wechat_job_failure,
)


def main() -> None:
    job = wechat_queue.enqueue(
        failing_wechat_like_job,
        "fake-open-id",
        "callback test",
        job_timeout=60,
        failure_ttl=86400,
        retry=Retry(
            max=3,
            interval=[
                5,
                15,
                30,
            ],
        ),
        on_failure=Callback(
            handle_wechat_job_failure,
            timeout=15,
        ),
    )

    print(
        "[CALLBACK TEST ENQUEUED] "
        f"job={job.id}"
    )


if __name__ == "__main__":
    main()