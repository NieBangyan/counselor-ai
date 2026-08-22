from rq import Retry
from rq.job import Dependency

from src.queue.connection import (
    wechat_queue,
)
from src.queue.dependency_test import (
    failing_job,
    success_job,
)


def main() -> None:
    # ========================================================
    # A1
    # 故意失败，并自动重试
    # ========================================================

    first_job = wechat_queue.enqueue(
        failing_job,
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
        "[DEPENDENCY TEST] "
        f"A1={first_job.id}"
    )

    # ========================================================
    # A2
    # 依赖 A1，但允许 A1 最终失败
    # ========================================================

    dependency = Dependency(
        jobs=[
            first_job
        ],
        allow_failure=True,
    )

    second_job = wechat_queue.enqueue(
        success_job,
        depends_on=dependency,
        job_timeout=60,
        result_ttl=500,
        failure_ttl=86400,
    )

    print(
        "[DEPENDENCY TEST] "
        f"A2={second_job.id}"
    )

    print(
        "[DEPENDENCY TEST] "
        "A2 should run after A1 finishes "
        "or finally fails."
    )


if __name__ == "__main__":
    main()