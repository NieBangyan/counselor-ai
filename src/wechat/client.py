import json
import os
import time

import requests
from dotenv import load_dotenv


load_dotenv()


TOKEN_ERROR_CODES = {
    40001,  # invalid credential
    40014,  # invalid access_token
    42001,  # access_token expired
}


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
        self._expires_at: float = 0.0

    # ========================================================
    # Access Token
    # ========================================================

    def clear_access_token(
        self,
    ) -> None:
        """
        清除本地 access_token 缓存。
        """

        self._access_token = None
        self._expires_at = 0.0

    def get_access_token(
        self,
        force_refresh: bool = False,
    ) -> str:
        """
        获取微信 access_token。

        默认优先使用本地缓存。

        force_refresh=True 时：
            忽略缓存并重新向微信请求。
        """

        if (
            not force_refresh
            and self._access_token
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

        access_token = data.get(
            "access_token"
        )

        if not access_token:
            raise RuntimeError(
                "获取微信 access_token 失败："
                f"{data}"
            )

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

        print(
            "[WECHAT TOKEN] refreshed"
        )

        return access_token

    # ========================================================
    # Send Helpers
    # ========================================================

    def _send_text_request(
        self,
        open_id: str,
        content: str,
        access_token: str,
    ) -> dict:
        """
        实际执行一次微信客服消息请求。
        """

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

        return response.json()

    # ========================================================
    # Public API
    # ========================================================

    def send_text_message(
        self,
        open_id: str,
        content: str,
    ) -> None:
        """
        通过微信客服消息接口发送文本消息。

        如果微信提示 access_token 无效或过期：
            1. 清除本地 token；
            2. 强制获取新 token；
            3. 立即重试一次。

        第二次仍失败时才抛异常，
        交给外层 RQ Retry。
        """

        # ----------------------------------------------------
        # 第一次发送
        # ----------------------------------------------------

        access_token = (
            self.get_access_token()
        )

        data = self._send_text_request(
            open_id=open_id,
            content=content,
            access_token=access_token,
        )

        errcode = int(
            data.get(
                "errcode",
                0,
            )
        )

        if errcode == 0:
            print(
                f"[WECHAT SEND] "
                f"{open_id} -> success"
            )

            return

        # ----------------------------------------------------
        # Token 失效：刷新并重试一次
        # ----------------------------------------------------

        if errcode in TOKEN_ERROR_CODES:
            print(
                "[WECHAT TOKEN INVALID] "
                f"errcode={errcode}, "
                "refreshing token..."
            )

            self.clear_access_token()

            access_token = (
                self.get_access_token(
                    force_refresh=True
                )
            )

            retry_data = (
                self._send_text_request(
                    open_id=open_id,
                    content=content,
                    access_token=access_token,
                )
            )

            retry_errcode = int(
                retry_data.get(
                    "errcode",
                    0,
                )
            )

            if retry_errcode == 0:
                print(
                    f"[WECHAT SEND] "
                    f"{open_id} "
                    "-> success after token refresh"
                )

                return

            raise RuntimeError(
                "发送微信客服消息失败："
                f"{retry_data}"
            )

        # ----------------------------------------------------
        # 其他微信错误
        # ----------------------------------------------------

        raise RuntimeError(
            "发送微信客服消息失败："
            f"{data}"
        )