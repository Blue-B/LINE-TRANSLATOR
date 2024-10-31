## LINE-TRANSLATOR
파이썬으로 개발한 라인 메신저 한-일 번역 봇입니다.
대화하고자 하는 상대와 봇을 추가하여 대화방을 개설하고 대화를 나누면 봇이 자동으로 번역된 텍스트를 응답합니다.
   


## 미리보기
![image](https://github.com/user-attachments/assets/9a4bb65a-5136-40bb-b511-fcbdd0cf599f)


봇과 대화상대 그리고 나, 세명의 대화상대가 한 방에 있고 '나'가 일본인, 한국인임을 가정해서 메세지를 보내면 이를 번역봇이 자동으로 번역해줍니다.
AI가 문맥을 고려하여 번역해주기 때문에 더 자연스러운 문장으로 읽을수 있습니다.
   

## 개발 정보
라인 봇 생성, api key발급 방법 기타 개발일지에 대한 내용은 블로그에서 확인할 수 있습니다.


블로그 : [Link](https://newstroyblog.tistory.com/574)



# 🚀 Skills
![](https://img.shields.io/badge/Line-00C300?style=for-the-badge&logo=line&logoColor=white)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)

   


## 필요 패키지 설치
``` pip install -r requirements.txt```

## API key
GPT, LINE-BOT-SDK에 필요한 API발급 방법은 개발정보를 올려둔 블로그 게시물에 상세히 기록해두었습니다.


.env 작성항목
- LINE_CHANNEL_SECRET(channel secret)
- LINE_CHANNEL_ACCESS_TOKEN(access token)
- OPENAI_API_KEY(openAI API Key)

   
## 실행 프로세스
1.app.py 파일을 실행하여 플라스크 서버를 활성화합니다.


2.ngrok 5000 서버를 실행하여 Forwarding 주소를 LINE-BOT 웹훅으로 연결합니다.


3.라인에서 대화상대와 봇을 초대하여 대화를 나눕니다.


4.대화를 나눌때 실시간으로 번역정보가 대화방에 나타나게됩니다.


   

### TAG
라인 메신저 한-일 번역 봇, LINE Messenger Korean - Japanese Translator Bot
