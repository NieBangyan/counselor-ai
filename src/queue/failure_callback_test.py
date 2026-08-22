from rq import get_current_job


def failing_wechat_like_job(
    open_id: str,
    content: str,
) -> None:
    job = get_current_job()

    print(
        "[FAILURE CALLBACK TEST] "
        f"job={job.id if job else 'unknown'} "
        f"user={open_id} "
        f"content={content} "
        f"retries_left={getattr(job, 'retries_left', None)}"
    )

    raise RuntimeError(
        "Intentional callback test failure."
    )