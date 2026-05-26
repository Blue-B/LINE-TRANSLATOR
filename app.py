import os
import logging
import threading

from flask import Flask, request, abort
from dotenv import load_dotenv

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.configuration import Configuration
from linebot.v3.messaging.api_client import ApiClient
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

import translator

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(channel_secret=LINE_CHANNEL_SECRET)


def _reply(reply_token: str, text: str):
    """별도 ApiClient로 응답 (스레드 안전)."""
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


def _worker(reply_token: str, user_input: str):
    """백그라운드 번역 → 응답. reply_token은 ~1분 유효하므로 6~9초 번역 OK."""
    try:
        translated = translator.translate(user_input)
        if translated:
            _reply(reply_token, translated)
    except Exception as e:
        app.logger.error("번역 처리 오류: %s", e)
        try:
            _reply(reply_token, "번역 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        except Exception:
            pass


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. LINE_CHANNEL_SECRET을 확인하세요.")
        abort(400)
    return "OK"


@app.route("/health")
def health():
    return "ok", 200


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_input = event.message.text
    # 웹훅은 즉시 반환하고, 무거운 번역은 백그라운드로 (LINE 재전송/타임아웃 방지)
    threading.Thread(
        target=_worker, args=(event.reply_token, user_input), daemon=True
    ).start()


if __name__ == "__main__":
    # 운영은 gunicorn 사용. debug=False.
    app.run(host="127.0.0.1", port=5005)
