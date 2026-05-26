# LINE 한↔일 번역 봇

라인(LINE) 대화방에 초대해두면, 한국어·일본어 메시지를 자동으로 감지해서 번역해주는 봇입니다.
한국인과 일본인이 한 방에서 얘기할 때, 봇이 중간에서 통역사처럼 번역문을 달아줍니다.

처음엔 OpenAI(GPT-4o-mini)로 번역했지만, **API 비용 없이 직접 굴리려고** 번역 엔진을 오픈소스 모델로 통째로 교체했습니다.
지금은 야놀자가 공개한 번역 특화 모델 **YanoljaNEXT-Rosetta-4B** 를 [Ollama](https://ollama.com)로 셀프 호스팅합니다.
→ 토큰 비용이 들지 않고, 번역 데이터도 외부로 나가지 않습니다.

![image](https://github.com/user-attachments/assets/9a4bb65a-5136-40bb-b511-fcbdd0cf599f)

---

## 어떻게 동작하나

```
LINE 메시지
   │
   ▼
Cloudflare 터널(HTTPS)  →  Flask 웹훅(/callback)
                               │  (즉시 200 응답)
                               ▼
                          백그라운드 스레드
                               │
                               ▼
                          Ollama  →  Yanolja Rosetta 4B  →  번역
                               │
                               ▼
                          LINE에 답장(reply)
```

메시지가 오면 웹훅은 **곧바로 200을 돌려주고**, 실제 번역은 백그라운드에서 처리합니다.
CPU로 모델을 돌리면 번역 한 건에 몇 초가 걸리는데, 그동안 웹훅을 붙잡고 있으면 LINE이 타임아웃으로 재전송을 하기 때문입니다.

---

## 왜 이렇게 만들었나

직접 골랐던 부분이라 이유를 남겨둡니다.

- **왜 자체 호스팅?** GPT API는 쓸 때마다 비용이 발생하고 번역문이 외부로 전송됩니다. 직접 호스팅하면 토큰 비용이 들지 않고, 데이터도 내 환경 안에서만 처리됩니다.
- **왜 이 모델?** 번역 전용으로 튜닝돼 한국어 품질이 좋고, 라이선스가 자유로워 부담 없이 쓸 수 있으며, 4B라 GPU 없이 CPU에서도 돌아갈 만큼 가볍습니다. (NLLB·Tower 계열은 라이선스 제약이 있어 제외)
- **왜 Q8 양자화?** 메모리는 충분했고 품질을 우선했습니다. 더 가볍게 가려면 Q4~Q6도 선택지입니다.
- **왜 비동기?** 위에 적은 대로, CPU 추론이 느려서 웹훅을 빨리 비워줘야 LINE 재전송을 피할 수 있습니다.

---

## 기능

- **언어 자동 감지** — 한글/가나/한자를 구분해서 KO→JA, JA→KO 방향을 알아서 정합니다. (영어·숫자만 있는 메시지는 번역하지 않고 넘어갑니다)
- **말투(톤) 지정** — 기본은 정중한 존댓말. 캐주얼 등으로 바꿀 수 있습니다.
- **용어집** — 브랜드명·제품명 같은 단어를 항상 같은 번역으로 고정합니다. (예: `라인 → LINE`)
- **캐시** — 같은 문장은 다시 모델을 부르지 않고 재사용합니다.
- **이상 출력 방어** — 모델이 가끔 같은 글자를 무한 반복하는 경우를 감지해 그 응답은 버립니다.

---

## 설치 & 실행

### 0. 사전 준비 — LINE 채널 자격증명 발급
> 자격증명은 이 저장소에 들어있지 않습니다. **직접 발급해서 `.env`에 넣어야** 합니다. (`.env`는 git에 올라가지 않습니다)

[LINE Developers Console](https://developers.line.biz/console/) 에서:
1. 로그인 → **Provider** 생성
2. **Messaging API** 채널 생성 (무료)
3. `LINE_CHANNEL_SECRET` ← *Basic settings* 탭에서 복사
4. `LINE_CHANNEL_ACCESS_TOKEN` ← *Messaging API* 탭에서 발급(Issue)
5. 같은 화면의 **Webhook URL** 에 아래 5단계에서 만든 HTTPS 주소(`.../callback`)를 등록하고, *Use webhook* 켜기 / 자동응답 끄기

### 1. 번역 모델 (Ollama)
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull hf.co/mradermacher/YanoljaNEXT-Rosetta-4B-2511-GGUF:Q8_0
```

### 2. 앱 설치
```bash
pip install -r requirements.txt
cp .env.example .env   # 위에서 발급받은 값 입력
```

`.env` 주요 항목:
```ini
LINE_CHANNEL_SECRET=발급받은_값
LINE_CHANNEL_ACCESS_TOKEN=발급받은_값
TRANSLATE_TONE=Polite and professional tone   # 말투 (선택)
TRANSLATE_GLOSSARY=라인=LINE,안내=ご案内                  # 용어집 (선택)
```

### 3. 실행
```bash
gunicorn -w 2 -b 127.0.0.1:5005 app:app
```
운영 환경이라면 `line-translator.service`로 systemd에 등록해 자동 재시작되게 하는 걸 권장합니다.

### 4. 웹훅 주소(HTTPS) 노출
LINE 웹훅은 HTTPS가 필수입니다. 도메인이 없다면 Cloudflare 터널로 바로 만들 수 있습니다.
```bash
cloudflared tunnel --url http://127.0.0.1:5005
# 출력되는 https://xxxx.trycloudflare.com/callback 를 LINE Webhook URL에 등록
```

---

## 트러블슈팅 메모 — Rosetta 프롬프트 포맷 (중요)

이 모델을 Ollama로 그냥 돌리면 **번역이 아니라 이상한 환각/무한반복**이 나옵니다.
원인은 프롬프트 포맷이었습니다. 보통 Gemma 계열은 `user / model` 턴을 쓰는데,
Rosetta는 아래처럼 **`instruction → source → translation`** 이라는 고유 포맷으로 학습돼 있습니다.

```
<start_of_turn>instruction
Translate the user's text to Japanese.
...
<end_of_turn>
<start_of_turn>source
(원문)
<end_of_turn>
<start_of_turn>translation
```

Ollama 기본 채팅 템플릿을 쓰면 이 포맷이 안 맞아서 모델이 헷갈립니다.
그래서 이 프로젝트는 `/api/chat` 대신 **`/api/generate` 의 `raw` 모드**로 위 포맷을 직접 만들어 보냅니다. (`translator.py` 참고)

---

## 구성 파일

| 파일 | 설명 |
|---|---|
| `app.py` | Flask 웹훅 서버 (비동기 처리) |
| `translator.py` | 번역 엔진 (언어감지 · 프롬프트 구성 · 톤/용어집 · 캐시) |
| `requirements.txt` | 파이썬 의존성 |
| `line-translator.service` | systemd 서비스 정의 |
| `.env.example` | 환경변수 템플릿 |

---

## 기술 스택
![](https://img.shields.io/badge/LINE-00C300?style=for-the-badge&logo=line&logoColor=white)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)

## 개발 기록
봇 생성·API 발급 등 자세한 과정은 블로그에 정리해 두었습니다 → [개발일지](https://newstroyblog.tistory.com/574)
