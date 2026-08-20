import hashlib
import os

from dotenv import load_dotenv

from src.wechat.router import (
    verify_wechat_signature,
)


load_dotenv()


def main() -> None:
    token = os.getenv("WECHAT_TOKEN")

    if not token:
        raise RuntimeError(
            "WECHAT_TOKEN 未配置。"
        )

    timestamp = "1234567890"
    nonce = "abcdef"

    values = [
        token,
        timestamp,
        nonce,
    ]

    values.sort()

    signature = hashlib.sha1(
        "".join(values).encode("utf-8")
    ).hexdigest()

    valid = verify_wechat_signature(
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )

    print(
        f"WeChat signature valid: {valid}"
    )


if __name__ == "__main__":
    main()