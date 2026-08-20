import time


def test_job(
    number: int,
) -> dict:
    print(
        f"[TEST START] job={number}"
    )

    time.sleep(5)

    print(
        f"[TEST DONE] job={number}"
    )

    return {
        "job": number,
        "success": True,
    }