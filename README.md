## LINE-TRANSLATOR

파이썬으로 개발한 라인 메신저 **한↔일 자동 번역 봇**입니다.
대화방에 봇을 초대하면, 한국어/일본어 메시지를 자동 감지해 번역문을 응답합니다.

> **v2 업데이트**: 유료 OpenAI API → **자체 호스팅 무료 모델(Yanolja Rosetta 4B + Ollama)** 로 전환.
> 토큰 비용 0, 데이터 외부 미전송, 존댓말/용어집 등 비즈니스 기능 추가.

## 특징
- **무료 자체 호스팅**: `YanoljaNEXT-Rosetta-4B`(번역 특화, Gemma 라이선스)를 Ollama로 로컬 구동. API 비용 없음.
- **언어 자동 감지**: 한글/가나/한자 구분 → KO↔JA 방향 자동 결정.
- **비동기 처리**: 웹훅 즉시 응답 → 백그라운드 번역 → `reply_message`. LINE 타임아웃/재전송 방지.
- **차별화 기능**:
  - 톤 제어(비즈니스 존댓말/캐주얼)
  - 용어집(브랜드·제품명 고정 번역)
- **안정성**: 깨진 출력(반복/폭주) 자동 감지·스킵, LRU 캐시.

## 아키텍처
```
LINE  →  Cloudflare Tunnel(HTTPS)  →  Flask(/callback, 비동기)
                                          │
                                          ▼
                                  Ollama  →  Yanolja Rosetta 4B (로컬)
```

## 기술 스택
![](https://img.shields.io/badge/Line-00C300?style=for-the-badge&logo=line&logoColor=white)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)

## 구성 파일
| 파일 | 설명 |
|---|---|
| `app.py` | Flask 웹훅 서버 (비동기 처리) |
| `translator.py` | 번역 엔진 (언어감지 + Rosetta 포맷 + 톤/용어집 + 캐시) |
| `requirements.txt` | 파이썬 의존성 |
| `line-translator.service` | systemd 서비스 정의 |
| `.env.example` | 환경변수 템플릿 |

## 설치 & 실행

### 1. 모델 서버 (Ollama)
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull hf.co/mradermacher/YanoljaNEXT-Rosetta-4B-2511-GGUF:Q8_0
```

### 2. 앱
```bash
pip install -r requirements.txt
cp .env.example .env   # LINE 자격증명 입력
```

### 3. 환경변수(.env)
> ⚠️ **자격증명은 저장소에 포함되지 않습니다.** 각자 직접 발급해 `.env`에 넣으세요. (`.env`는 `.gitignore` 처리됨)

**LINE 자격증명 발급** — [LINE Developers Console](https://developers.line.biz/console/) 에서:
1. 로그인 → **Provider** 생성
2. **Messaging API** 채널 생성 (무료)
3. `LINE_CHANNEL_SECRET`: **Basic settings** 탭에서 복사
4. `LINE_CHANNEL_ACCESS_TOKEN`: **Messaging API** 탭 → *Channel access token* 발급
5. 같은 화면의 **Webhook URL** 에 5번에서 만든 HTTPS 주소(`.../callback`) 등록 + *Use webhook* ON, *자동응답* OFF

```ini
LINE_CHANNEL_SECRET=발급받은_값
LINE_CHANNEL_ACCESS_TOKEN=발급받은_값
TRANSLATE_TONE=Polite and professional business tone   # 선택
TRANSLATE_GLOSSARY=라인=LINE,결제=決済                     # 선택(용어집)
```

### 4. 구동
```bash
gunicorn -w 2 -b 127.0.0.1:5005 app:app
```
운영 시 `line-translator.service`로 systemd 등록 권장.

### 5. 웹훅(HTTPS) 노출
LINE 웹훅은 HTTPS 필수. 도메인 없이 빠르게:
```bash
cloudflared tunnel --url http://127.0.0.1:5005
# 출력된 https://xxx.trycloudflare.com/callback 를 LINE Webhook URL에 등록
```

## 중요: Rosetta 프롬프트 포맷
Yanolja Rosetta는 일반 gemma `user/model` 템플릿이 아니라
`instruction → source → translation` 고유 포맷으로 학습됨.
Ollama 기본 템플릿을 쓰면 환각/반복이 발생하므로,
`/api/generate` 의 `raw` 모드로 직접 프롬프트를 구성한다. (`translator.py` 참고)

## 개발 정보
라인 봇 생성·API 발급 등은 블로그 참고: [Link](https://newstroyblog.tistory.com/574)

### TAG
라인 메신저 한-일 번역 봇, LINE Messenger Korean-Japanese Translator Bot, Self-hosted LLM, Ollama, Yanolja Rosetta
