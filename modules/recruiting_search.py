from __future__ import annotations

import os

import requests
import streamlit as st


TAVILY_ENDPOINT = "https://api.tavily.com/search"


def _api_key() -> str:
    return str(os.getenv("TAVILY_API_KEY") or st.secrets.get("TAVILY_API_KEY", "") or "").strip()


def is_available() -> bool:
    return bool(_api_key())


def search_recruiting_sources(company: str, position: str, team: str = "", max_results: int = 8) -> list[dict]:
    key = _api_key()
    if not key:
        raise RuntimeError("TAVILY_API_KEY가 없습니다. 자동 웹 검색은 선택 기능이며 URL/본문 직접 저장은 계속 사용할 수 있습니다.")

    team_part = f" {team}" if team else ""
    query = (
        f'"{company}" "{position}"{team_part} '
        f'(채용 OR 직무 OR 직무소개 OR 현직자 OR 인터뷰 OR careers OR job)'
    )
    payload = {
        "api_key": key,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": True,
    }
    response = requests.post(TAVILY_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title") or "채용 자료",
            "url": item.get("url") or "",
            "content": item.get("raw_content") or item.get("content") or "",
            "snippet": item.get("content") or "",
            "score": item.get("score"),
        })
    return results
