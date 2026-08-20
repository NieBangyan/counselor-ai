import os

from dotenv import load_dotenv
from redis import Redis
from rq import Queue


load_dotenv()


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)


redis_connection = Redis.from_url(
    REDIS_URL,
)


wechat_queue = Queue(
    name="wechat",
    connection=redis_connection,
    default_timeout=180,
)