from rq import get_current_job


def failing_job() -> None:
    """
    故意失败的前置任务。
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
        "[DEPENDENCY TEST FAIL] "
        f"job={job_id} "
        f"retries_left={retries_left}"
    )

    raise RuntimeError(
        "Intentional dependency failure."
    )


def success_job() -> str:
    """
    前置任务最终失败后，
    这个任务应该仍然能够执行。
    """

    job = get_current_job()

    job_id = (
        job.id
        if job is not None
        else "unknown"
    )

    print(
        "[DEPENDENCY TEST SUCCESS] "
        f"job={job_id}"
    )

    return "dependency test passed"