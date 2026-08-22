from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.wechat.router import router


def build_wechat_xml(
    msg_id: str,
    content: str,
) -> str:
    return f"""
<xml>
    <ToUserName><![CDATA[test-account]]></ToUserName>
    <FromUserName><![CDATA[test-open-id]]></FromUserName>
    <CreateTime>1234567890</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[{content}]]></Content>
    <MsgId>{msg_id}</MsgId>
</xml>
""".strip()


def test_duplicate_wechat_message_only_enqueues_once(
    redis_connection,
):
    app = FastAPI()

    app.include_router(
        router
    )

    client = TestClient(
        app
    )

    msg_id = (
        "pytest-route-dedup-001"
    )

    dedup_key = (
        f"wechat:message:{msg_id}"
    )

    redis_connection.delete(
        dedup_key
    )

    xml_body = build_wechat_xml(
        msg_id=msg_id,
        content="测试重复消息",
    )

    try:
        with (
            patch(
                "src.wechat.router."
                "verify_wechat_signature",
                return_value=True,
            ),
            patch(
                "src.wechat.router."
                "enqueue_user_message"
            ) as mock_enqueue,
        ):
            # 模拟 enqueue 返回一个有 id 的 Job
            mock_job = (
                mock_enqueue.return_value
            )

            mock_job.id = (
                "fake-job-id"
            )

            # ---------------------------------------------
            # 第一次 POST
            # ---------------------------------------------

            response_1 = client.post(
                "/wechat",
                params={
                    "signature": "test",
                    "timestamp": "123",
                    "nonce": "456",
                },
                content=xml_body,
                headers={
                    "Content-Type":
                        "application/xml",
                },
            )

            # ---------------------------------------------
            # 第二次完全相同的 POST
            # ---------------------------------------------

            response_2 = client.post(
                "/wechat",
                params={
                    "signature": "test",
                    "timestamp": "123",
                    "nonce": "456",
                },
                content=xml_body,
                headers={
                    "Content-Type":
                        "application/xml",
                },
            )

            # ---------------------------------------------
            # Response
            # ---------------------------------------------

            assert (
                response_1.status_code
                == 200
            )

            assert (
                response_2.status_code
                == 200
            )

            assert (
                response_1.text
                == "success"
            )

            assert (
                response_2.text
                == "success"
            )

            # ---------------------------------------------
            # 最关键：
            # 同一个 MsgId 只能入队一次
            # ---------------------------------------------

            assert (
                mock_enqueue.call_count
                == 1
            )

            mock_enqueue.assert_called_once_with(
                open_id="test-open-id",
                content="测试重复消息",
            )

    finally:
        redis_connection.delete(
            dedup_key
        )