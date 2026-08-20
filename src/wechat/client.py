import json
import os
import time

import requests
from dotenv import load_dotenv


load_dotenv()


class WeChatClient:
    def __init__(self) -> None:
        self.app_id = os.getenv(
            "WECHAT_APP_ID"
        )

        self.app_secret = os.getenv(
            "WECHAT_APP_SECRET"
        )

        if not self.app_id:
            raise RuntimeError(
                "没有找到 WECHAT_APP_ID，"
                "请检查 .env 文件。"
            )

        if not self.app_secret:
            raise RuntimeError(
                "没有找到 WECHAT_APP_SECRET，"
                "请检查 .env 文件。"
            )

        self._access_token: str | None = None
        self._expires_at: float = 0

    def get_access_token(
        self,
    ) -> str:
        if (
            self._access_token
            and time.time()
            < self._expires_at - 60
        ):
            return self._access_token

        url = (
            "https://api.weixin.qq.com/"
            "cgi-bin/token"
        )

        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }

        response = requests.get(
            url,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if "access_token" not in data:
            raise RuntimeError(
                "获取微信 access_token 失败："
                f"{data}"
            )

        access_token = data[
            "access_token"
        ]

        expires_in = int(
            data.get(
                "expires_in",
                7200,
            )
        )

        self._access_token = (
            access_token
        )

        self._expires_at = (
            time.time()
            + expires_in
        )

        return access_token

    def send_text_message(
        self,
        open_id: str,
        content: str,
    ) -> None:
        """
        通过微信客服消息接口发送文本消息。
        显式使用 UTF-8 JSON，避免中文被显示成 \\uXXXX。
        """

        access_token = (
            self.get_access_token()
        )

        url = (
            "https://api.weixin.qq.com/"
            "cgi-bin/message/custom/send"
        )

        params = {
            "access_token": access_token,
        }

        payload = {
            "touser": open_id,
            "msgtype": "text",
            "text": {
                "content": content,
            },
        }

        headers = {
            "Content-Type":
                "application/json; charset=utf-8",
        }

        json_data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        response = requests.post(
            url,
            params=params,
            data=json_data,
            headers=headers,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("errcode", 0) != 0:
            raise RuntimeError(
                "发送微信客服消息失败："
                f"{data}"
            )

        print(
            f"[WECHAT SEND] "
            f"{open_id} -> success"
        )