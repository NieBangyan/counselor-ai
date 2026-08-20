from src.queue.connection import (
    wechat_queue,
)
from src.test_queue_concurrency import (
    test_job,
)


def main() -> None:
    jobs = []

    for number in range(1, 11):
        job = wechat_queue.enqueue(
            test_job,
            number,
            job_timeout=30,
        )

        jobs.append(job)

        print(
            f"[ENQUEUE] "
            f"job={number} "
            f"id={job.id}"
        )

    print()
    print(
        f"已成功加入 {len(jobs)} 个任务。"
    )


if __name__ == "__main__":
    main()