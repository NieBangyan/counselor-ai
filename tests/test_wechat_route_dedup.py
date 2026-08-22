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


def test_duplicate_wechat_message_only_enqueues_once():
    """
    验证微信 Router 的去重行为：

    第一次：
        claim_wechat_message() -> True
        正常 enqueue

    第二次：
        claim_wechat_message() -> False
        识别为重复消息
        不再 enqueue

    Redis SET NX 本身的行为由
    test_wechat_dedup.py 单独测试。
    """

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

    xml_body = build_wechat_xml(
        msg_id=msg_id,
        content="测试重复消息",
    )

    with (
        patch(
            "src.wechat.router."
            "verify_wechat_signature",
            return_value=True,
        ),
        patch(
            "src.wechat.router."
            "claim_wechat_message",
            side_effect=[
                True,
                False,
            ],
        ) as mock_claim,
        patch(
            "src.wechat.router."
            "enqueue_user_message"
        ) as mock_enqueue,
    ):
        # ====================================================
        # Mock RQ Job
        # ====================================================

        mock_job = (
            mock_enqueue.return_value
        )

        mock_job.id = (
            "fake-job-id"
        )

        # ====================================================
        # 第一次 POST
        # ====================================================

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

        # ====================================================
        # 第二次完全相同的 POST
        # ====================================================

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

        # ====================================================
        # Response
        # ====================================================

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

        # ====================================================
        # Dedup
        # ====================================================

        # 两次请求都应该进行去重检查。
        assert (
            mock_claim.call_count
            == 2
        )

        mock_claim.assert_any_call(
            msg_id
        )

        # ====================================================
        # Queue
        # ====================================================

        # 但只能真正入队一次。
        assert (
            mock_enqueue.call_count
            == 1
        )

        mock_enqueue.assert_called_once_with(
            open_id="test-open-id",
            content="测试重复消息",
        )