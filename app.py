import os
import re
import logging
from functools import lru_cache

from flask import Flask, request, abort
from dotenv import load_dotenv

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.configuration import Configuration
from linebot.v3.messaging.api_client import ApiClient
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from linebot.v3.messaging.models import (
    TextMessage,
    ReplyMessageRequest
)
from openai import OpenAI

# 환경 변수 로드
load_dotenv()

# Flask 앱 초기화
app = Flask(__name__)

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 환경 변수에서 필요한 정보 가져오기
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 라인봇 API 및 핸들러 초기화
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration=configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(channel_secret=LINE_CHANNEL_SECRET)

# OpenAI API 키 설정
client = OpenAI(
    api_key = os.getenv('OPENAI_API_KEY'),
)


# 캐시 설정 (최대 1000개의 최근 번역 결과를 저장)
@lru_cache(maxsize=1000)
def translate_text(text):
    source_lang = detect_language(text)
    if source_lang == '한국어':
        target_lang = '일본어'
    else:
        target_lang = '한국어'

    app.logger.info(f"API가 호출되었습니다 원문 텍스트: {text}\n\n\n")  # API 호출 로그

    # OpenAI API 요청 생성
    messages = [
        {
            "role": "system",
            "content": f"당신은 {source_lang}를 {target_lang}로 번역하는 전문 번역가입니다."  

        },
        {
            "role": "user",
            "content": text
        }
    ]

    # OpenAI API 요청 생성
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    # 번역 결과 추출
    translated_text = response.choices[0].message.content
    app.logger.info(f"번역 결과: {translated_text}")  # 번역 결과 로그 추가
    return translated_text.strip()



def detect_language(text):
    # 한글이 포함되어 있는지 체크
    if re.search("[\uac00-\ud7a3]", text):
        return '한국어'
    else:
        return '일본어'

@app.route("/callback", methods=['POST'])
def callback():
    # 라인 웹훅
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your LINE_CHANNEL_SECRET.")
        abort(400)

    return 'OK'

# 메시지 이벤트 핸들러 추가
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_input = event.message.text
    user_id = event.source.user_id

    app.logger.info(f"Received message from {user_id}: {user_input}")


    if re.fullmatch(r'[a-zA-Z\s]+', user_input):  # 영어만 포함된 경우
        app.logger.info("Input is English only.")
        return

    # 번역 처리
    try:
        translated_text = translate_text(user_input)
        reply_message_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(text=translated_text)
            ]
        )
        line_bot_api.reply_message(reply_message_request)
    except Exception as e:
        app.logger.error(f"Error during translation: {e}")
        reply_message_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(text="번역 중 오류가 발생하였습니다. 나중에 다시 시도해주세요.")
            ]
        )
        line_bot_api.reply_message(reply_message_request)

if __name__ == "__main__":
    app.run(debug=True)
