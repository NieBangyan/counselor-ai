import pytest

from redis import Redis
from rq import Queue

from src.queue.connection import (
    REDIS_URL,
)


TEST_QUEUE_NAME = "wechat-test"


@pytest.fixture
def redis_connection():
    """
    测试使用的 Redis connection。

    当前仍连接本机 Redis，
    但所有测试 Job 使用独立 Queue。
    """

    connection = Redis.from_url(
        REDIS_URL
    )

    assert connection.ping()

    return connection


@pytest.fixture
def test_queue(
    redis_connection,
):
    """
    独立的 RQ 测试队列。

    不使用生产队列：
        wechat

    使用：
        wechat-test
    """

    queue = Queue(
        TEST_QUEUE_NAME,
        connection=redis_connection,
    )

    # 测试开始前清理遗留 Job
    queue.empty()

    yield queue

    # 测试结束后再次清理
    queue.empty()