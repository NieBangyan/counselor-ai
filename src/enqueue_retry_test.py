from rq import Retry

from src.queue.connection import (
    wechat_queue,
)
from src.queue.retry_test import (
    retry_test_job,
)


def main() -> None:
    job = wechat_queue.enqueue(
        retry_test_job,
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
    )

    print(
        "[RETRY TEST ENQUEUED] "
        f"job={job.id}"
    )


if __name__ == "__main__":
    main()