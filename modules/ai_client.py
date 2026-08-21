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


def _support_segments_by_chunk(response) -> dict[int, list[str]]:
    """Map grounding chunk index -> response text segments supported by that source."""
    result: dict[int, list[str]] = {}
    try:
        candidate = response.candidates[0]
        metadata = candidate.grounding_metadata
        supports = metadata.grounding_supports or []
        for support in supports:
            segment = getattr(support, "segment", None)
            segment_text = (getattr(segment, "text", "") or "").strip()
            if not segment_text:
                continue
            indices = getattr(support, "grounding_chunk_indices", None) or []
            for idx in indices:
                result.setdefault(int(idx), [])
                if segment_text not in result[int(idx)]:
                    result[int(idx)].append(segment_text)
    except Exception:
        return {}
    return result


def generate_grounded_research(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.15,
) -> dict:
    """Run Gemini with Google Search grounding and return research text + citations.

    This uses the same GEMINI_API_KEY as the rest of the app. No Tavily key is required.
    """
    from google.genai import types

    client = get_ai_client()
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    response = client.models.generate_content(
        model=get_model_name(model),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            tools=[grounding_tool],
        ),
    )

    text = (response.text or "").strip()
    sources: list[dict] = []
    queries: list[str] = []
    search_entry_html = ""
    segment_map = _support_segments_by_chunk(response)

    try:
        candidate = response.candidates[0]
        metadata = candidate.grounding_metadata
        queries = list(getattr(metadata, "web_search_queries", None) or [])
        entry = getattr(metadata, "search_entry_point", None)
        search_entry_html = (getattr(entry, "rendered_content", "") or "").strip()
        chunks = getattr(metadata, "grounding_chunks", None) or []
        seen = set()
        for idx, chunk in enumerate(chunks):
            web = getattr(chunk, "web", None)
            if not web:
                continue
            url = (getattr(web, "uri", "") or "").strip()
            title = (getattr(web, "title", "") or "").strip() or "Google Search source"
            key = (url, title)
            if key in seen:
                continue
            seen.add(key)
            segments = segment_map.get(idx, [])
            sources.append(
                {
                    "title": title,
                    "url": url,
                    "content": "\n\n".join(segments).strip(),
                    "snippet": " ".join(segments)[:1200].strip(),
                    "source_type": "Google Search 근거",
                    "trust_level": "supported",
                }
            )
    except Exception:
        # The grounded synthesis itself remains useful even if metadata is absent.
        pass

    return {
        "text": text,
        "sources": sources,
        "queries": queries,
        "search_entry_html": search_entry_html,
    }
