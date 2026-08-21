from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import dataclass
from typing import Any

import streamlit as st


DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_FALLBACKS = []
TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}


@dataclass
class AIServiceError(RuntimeError):
    message: str
    code: int | None = None
    model_attempts: list[dict] | None = None

    def __str__(self) -> str:
        return self.message


@st.cache_resource
def get_ai_client():
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY가 없습니다. Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요."
        )
    return genai.Client(api_key=str(api_key).strip())


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise ValueError("AI 응답이 비어 있습니다.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.S)
    if match:
        return json.loads(match.group(1))

    start_obj, end_obj = text.find("{"), text.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        return json.loads(text[start_obj : end_obj + 1])

    start_arr, end_arr = text.find("["), text.rfind("]")
    if start_arr >= 0 and end_arr > start_arr:
        return json.loads(text[start_arr : end_arr + 1])

    raise ValueError("AI 응답에서 JSON을 찾지 못했습니다.")


def get_model_name(model: str | None = None) -> str:
    if model:
        return model
    configured = os.getenv("GEMINI_MODEL") or st.secrets.get("GEMINI_MODEL", "")
    return str(configured).strip() or DEFAULT_MODEL


def get_fallback_models() -> list[str]:
    configured = os.getenv("GEMINI_FALLBACK_MODELS") or st.secrets.get("GEMINI_FALLBACK_MODELS", "")
    if configured:
        values = [x.strip() for x in str(configured).split(",") if x.strip()]
    else:
        values = list(DEFAULT_FALLBACKS)
    primary = get_model_name()
    return [x for x in values if x != primary]


def _error_code(exc: Exception) -> int | None:
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    text = str(exc)
    match = re.search(r"\b(408|429|500|502|503|504)\b", text)
    return int(match.group(1)) if match else None


def _friendly_error(exc: Exception, attempts: list[dict]) -> AIServiceError:
    code = _error_code(exc)
    if code == 503:
        msg = (
            "Gemini 서버가 일시적으로 혼잡합니다(503). 웹 검색 결과와 저장된 근거는 사라지지 않습니다. "
            "잠시 후 'AI 분석만 재시도'를 누르면 Tavily 검색 크레딧을 추가로 쓰지 않고 다시 분석합니다."
        )
    elif code == 429:
        msg = (
            "Gemini API 사용 한도에 도달했습니다(429). 저장된 웹 근거는 유지됩니다. "
            "API 한도가 복구된 뒤 AI 분석만 다시 실행해주세요."
        )
    elif code in {408, 500, 502, 504}:
        msg = "Gemini API의 일시적인 통신 오류가 발생했습니다. 저장된 근거는 유지되므로 AI 분석만 다시 시도해주세요."
    else:
        msg = f"Gemini 호출에 실패했습니다: {exc}"
    return AIServiceError(msg, code=code, model_attempts=attempts)


def _call_generate(prompt: str, *, model: str, json_mode: bool):
    from google.genai import types

    client = get_ai_client()
    # Gemini 3.6+에서는 temperature/top_p/top_k가 deprecated이므로 보내지 않는다.
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    return client.models.generate_content(model=model, contents=prompt, config=config)


def _generate_resilient(prompt: str, *, model: str | None = None, json_mode: bool = False):
    primary = get_model_name(model)
    models = [primary, *[m for m in get_fallback_models() if m != primary]]
    attempts: list[dict] = []
    last_exc: Exception | None = None

    # 일시적 429/503 등은 같은 모델에서 지수 백오프로 재시도한다.
    # fallback 모델은 Streamlit Secrets의 GEMINI_FALLBACK_MODELS에 사용자가 명시한 경우에만 사용한다.
    for model_index, model_name in enumerate(models):
        max_attempts = 3 if model_index == 0 else 1
        for attempt_no in range(1, max_attempts + 1):
            started = time.monotonic()
            try:
                response = _call_generate(prompt, model=model_name, json_mode=json_mode)
                elapsed = round(time.monotonic() - started, 2)
                attempts.append({
                    "model": model_name,
                    "attempt": attempt_no,
                    "status": "success",
                    "elapsed_sec": elapsed,
                })
                return response, {
                    "model": model_name,
                    "primary_model": primary,
                    "fallback_used": model_name != primary,
                    "attempts": attempts,
                }
            except Exception as exc:
                last_exc = exc
                code = _error_code(exc)
                elapsed = round(time.monotonic() - started, 2)
                attempts.append({
                    "model": model_name,
                    "attempt": attempt_no,
                    "status": "error",
                    "code": code,
                    "elapsed_sec": elapsed,
                    "message": str(exc)[:300],
                })
                if code not in TRANSIENT_CODES:
                    raise _friendly_error(exc, attempts) from exc
                if attempt_no < max_attempts:
                    delay = 2.0 * (2 ** (attempt_no - 1)) + random.uniform(0.3, 1.0)
                    time.sleep(delay)
                    continue
                # transient error: move to fallback model if one exists
                break

    assert last_exc is not None
    raise _friendly_error(last_exc, attempts) from last_exc


def generate_text(prompt: str, model: str | None = None, temperature: float | None = None) -> str:
    # temperature arg is kept only for backwards compatibility; it is intentionally ignored.
    response, _meta = _generate_resilient(prompt, model=model, json_mode=False)
    return (response.text or "").strip()


def generate_json(prompt: str, model: str | None = None, temperature: float | None = None) -> Any:
    # temperature arg is kept only for backwards compatibility; it is intentionally ignored.
    response, meta = _generate_resilient(prompt, model=model, json_mode=True)
    data = _extract_json(response.text or "")
    if isinstance(data, dict):
        data.setdefault("_ai_meta", meta)
    return data
