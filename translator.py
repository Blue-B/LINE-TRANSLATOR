"""
번역 엔진: 로컬 Ollama(Yanolja Rosetta 4B) 호출 + 언어감지 + 톤/용어집 + 캐시.
중요: Rosetta는 instruction/source/translation 고유 포맷으로 학습됨.
      Ollama 기본 gemma 템플릿을 쓰면 환각/폭주 → raw 모드로 직접 프롬프트 구성.
"""
import os
import re
import logging
from functools import lru_cache

import requests

logger = logging.getLogger("translator")

# ── 설정 (환경변수로 덮어쓰기 가능) ───────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.getenv(
    "TRANSLATE_MODEL",
    "hf.co/mradermacher/YanoljaNEXT-Rosetta-4B-2511-GGUF:Q8_0",
)
NUM_THREAD = int(os.getenv("OLLAMA_NUM_THREAD", "4"))
REQUEST_TIMEOUT = int(os.getenv("TRANSLATE_TIMEOUT", "60"))

# 톤: 번역 말투 지정 (기본 정중한 존댓말). 비우면 미적용.
DEFAULT_TONE = os.getenv("TRANSLATE_TONE", "Polite and professional tone")

# 용어집: 특정 단어를 항상 같은 번역으로 고정. "원문=번역,원문=번역" 형식.
def _parse_glossary(raw: str) -> dict:
    g = {}
    for pair in raw.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                g[k] = v
    return g

GLOSSARY = _parse_glossary(os.getenv("TRANSLATE_GLOSSARY", ""))

LANG_NAME = {"ko": "Korean", "ja": "Japanese"}


def _is_degenerate(text: str) -> bool:
    """같은 문자/짧은 패턴 반복 등 깨진 출력 감지."""
    if not text:
        return True
    if re.search(r"(.)\1{5,}", text):
        return True
    if len(text) > 12 and len(set(text)) / len(text) < 0.25:
        return True
    return False


# ── 언어 감지 ────────────────────────────────────────────────
_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_KANA = re.compile(r"[぀-ゟ゠-ヿ]")
_KANJI = re.compile(r"[一-鿿]")
_MEANINGFUL = re.compile(r"[^\s\d\W]", re.UNICODE)


def detect_pair(text: str):
    """(source, target) 반환. 번역 불필요하면 None."""
    if not _MEANINGFUL.search(text):
        return None  # 숫자/기호/이모지만 → 스킵
    if _HANGUL.search(text):
        return ("ko", "ja")
    if _KANA.search(text):
        return ("ja", "ko")
    if _KANJI.search(text):
        return ("ja", "ko")  # 가나 없는 한자 단독 → 일본어로 간주
    return None  # 라틴/영어 전용 → 스킵


# ── 프롬프트 (Rosetta 고유 포맷, raw 모드용) ─────────────────
def _build_prompt(text: str, target_lang: str, tone: str | None, glossary: dict | None) -> str:
    ins = [f"Translate the user's text to {LANG_NAME[target_lang]}."]
    if tone:
        ins.append(f"Tone: {tone}")
    if glossary:
        ins.append("Glossary:")
        for src, dst in glossary.items():
            ins.append(f"- {src} -> {dst}")
    ins.append("Provide the final translation immediately without any other text.")
    return (
        "<start_of_turn>instruction\n" + "\n".join(ins) + "<end_of_turn>\n"
        "<start_of_turn>source\n" + text + "<end_of_turn>\n"
        "<start_of_turn>translation\n"
    )


# ── 번역 (캐시: 같은 문장 재번역 방지) ───────────────────────
@lru_cache(maxsize=2000)
def _translate_cached(text: str, source: str, target: str, tone: str, glossary_key: str) -> str:
    prompt = _build_prompt(text, target, tone or None, GLOSSARY or None)
    num_predict = max(24, min(256, len(text) * 4 + 24))  # 폭주 시간낭비 차단(동적)
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "raw": True,  # Ollama 템플릿 우회 → Rosetta 포맷 그대로 사용
        "stream": False,
        "options": {
            "temperature": 0,
            "num_thread": NUM_THREAD,
            "num_predict": num_predict,
            "repeat_penalty": 1.1,
            "num_ctx": 1024,
            "stop": ["<end_of_turn>"],
        },
    }
    logger.info("번역 요청 [%s->%s]: %s", source, target, text)
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    out = r.json().get("response", "").strip()
    if _is_degenerate(out):
        logger.warning("깨진 출력 감지, 스킵: %s", out[:40])
        return ""
    logger.info("번역 결과: %s", out)
    return out


def translate(text: str):
    """텍스트 번역. 번역 불필요/실패 시 None 또는 '' 반환(빈 값이면 응답 안 함)."""
    pair = detect_pair(text)
    if not pair:
        return None
    source, target = pair
    glossary_key = ",".join(f"{k}={v}" for k, v in sorted(GLOSSARY.items()))
    return _translate_cached(text.strip(), source, target, DEFAULT_TONE, glossary_key)
