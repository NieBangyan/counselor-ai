from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker

from src.queue.connection import REDIS_URL


def main() -> None:
    connection = Redis.from_url(
        REDIS_URL
    )

    queues = [
        Queue(
            "wechat",
            connection=connection,
        )
    ]

    worker = SimpleWorker(
        queues,
        connection=connection,
    )

    worker.work(
        with_scheduler=True
    )


if __name__ == "__main__":
    main()