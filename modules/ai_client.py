from __future__ import annotations

import json
import os
import re
from typing import Any

import streamlit as st


DEFAULT_MODEL = "gemini-3.6-flash"


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


def generate_text(prompt: str, model: str | None = None, temperature: float = 0.35) -> str:
    from google.genai import types

    client = get_ai_client()
    response = client.models.generate_content(
        model=get_model_name(model),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
        ),
    )
    return (response.text or "").strip()


def generate_json(prompt: str, model: str | None = None, temperature: float = 0.2) -> Any:
    from google.genai import types

    client = get_ai_client()
    response = client.models.generate_content(
        model=get_model_name(model),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    return _extract_json(response.text or "")
