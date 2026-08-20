from src.wechat.client import WeChatClient


def main() -> None:
    client = WeChatClient()

    open_id = "okpWM24QlGOqJE51S3mJcp2k7WgA"

    client.send_text_message(
        open_id=open_id,
        content="AI 辅导员微信主动消息测试成功。",
    )

    print("消息发送完成。")


if __name__ == "__main__":
    main()