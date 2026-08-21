from __future__ import annotations

import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
import streamlit as st

from modules.repository import (
    bump_research_cache_use,
    get_research_cache,
    log_research_usage,
    save_research_cache,
)

TAVILY_ENDPOINT = "https://api.tavily.com/search"
COMPANY_CACHE_DAYS = 30
JOB_CACHE_DAYS = 7


def _api_key() -> str:
    return str(os.getenv("TAVILY_API_KEY") or st.secrets.get("TAVILY_API_KEY", "") or "").strip()


def is_available() -> bool:
    return bool(_api_key())


def _norm(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _cache_key(research_type: str, company: str, position: str = "", team: str = "", extra: str = "") -> str:
    raw = json.dumps({
        "type": research_type,
        "company": _norm(company),
        "position": _norm(position),
        "team": _norm(team),
        "extra": _norm(extra),
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _fresh_cache(cache_key: str) -> dict | None:
    row = get_research_cache(cache_key)
    if not row:
        return None
    expires = _parse_dt(row.get("expires_at"))
    if not expires or expires <= datetime.now(timezone.utc):
        return None
    return row


def _guess_source_type(url: str, title: str) -> tuple[str, str]:
    host = (urlparse(url).netloc or "").lower()
    text = f"{host} {title}".lower()
    if any(x in host for x in ["dart.fss.or.kr", "kind.krx.co.kr", "alio.go.kr", "go.kr"]):
        return "공시/공공기관 자료", "official"
    if any(x in text for x in ["채용", "careers", "career", "recruit"]):
        return "채용 관련 웹자료", "supported"
    if any(x in host for x in ["jobkorea.co.kr", "saramin.co.kr", "wanted.co.kr", "linkedin.com"]):
        return "채용 플랫폼", "supported"
    return "웹 리서치 근거", "supported"


def _search(query: str, max_results: int = 8) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError(
            "TAVILY_API_KEY가 없습니다. Tavily에서 무료 API 키를 발급한 뒤 Streamlit Secrets에 등록해주세요."
        )
    payload = {
        "query": query,
        "search_depth": "basic",  # 1 credit: default cost-saving mode
        "max_results": max(1, min(int(max_results), 10)),
        "include_answer": False,
        "include_raw_content": True,
        "include_images": False,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    response = None
    last_error = None
    for attempt in range(2):
        try:
            response = requests.post(TAVILY_ENDPOINT, json=payload, headers=headers, timeout=45)
            if response.status_code == 401:
                raise RuntimeError("Tavily API 키 인증에 실패했습니다. Streamlit Secrets의 TAVILY_API_KEY를 확인해주세요.")
            if response.status_code == 429:
                raise RuntimeError("Tavily 검색 한도를 초과했습니다. 저장된 캐시 자료는 계속 사용할 수 있습니다.")
            if response.status_code >= 500 and attempt == 0:
                time.sleep(1.2 + random.uniform(0.2, 0.8))
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1.2 + random.uniform(0.2, 0.8))
                continue
            break
    raise RuntimeError(f"Tavily 검색 서버에 일시적인 오류가 발생했습니다. 저장된 캐시가 있으면 계속 사용할 수 있습니다. ({last_error})")


def _normalize(data: dict) -> list[dict]:
    results, seen = [], set()
    for item in data.get("results", []) or []:
        url = (item.get("url") or "").strip()
        title = (item.get("title") or "웹 검색 자료").strip()
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)
        source_type, trust = _guess_source_type(url, title)
        content = (item.get("raw_content") or item.get("content") or "").strip()
        results.append({
            "title": title,
            "url": url,
            "content": content,
            "snippet": (item.get("content") or content)[:1400],
            "score": item.get("score"),
            "source_type": source_type,
            "trust_level": trust,
            "is_synthesis": False,
        })
    return results


def _run_cached_research(*, research_type: str, company: str, position: str, team: str,
                         query: str, ttl_days: int, user_id: str = "", project_id: str = "",
                         force_refresh: bool = False, extra_key: str = "") -> dict:
    key = _cache_key(research_type, company, position, team, extra_key)
    if not force_refresh:
        cached = _fresh_cache(key)
        if cached:
            bump_research_cache_use(key)
            if user_id and project_id:
                log_research_usage(user_id, project_id, research_type, key, "cache", 0)
            return {
                "results": cached.get("results") or [],
                "queries": [cached.get("query_text") or query],
                "text": "",
                "cache_hit": True,
                "searched_at": cached.get("searched_at"),
                "expires_at": cached.get("expires_at"),
                "credits_estimate": 0,
            }

    data = _search(query, max_results=8)
    results = _normalize(data)
    expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()
    save_research_cache(key, research_type, company, position, team, query, results, expires)
    if user_id and project_id:
        log_research_usage(user_id, project_id, research_type, key, "tavily", 1)
    return {
        "results": results,
        "queries": [query],
        "text": "",
        "cache_hit": False,
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires,
        "credits_estimate": 1,
    }


def research_company_sources(company: str, instructions: list[dict] | None = None, recent_months: int = 18,
                             user_id: str = "", project_id: str = "", force_refresh: bool = False) -> dict:
    # User prompt instructions affect analysis, not the raw web-search cache key/query. This prevents needless cache fragmentation.
    query = (
        f'"{company}" 공식 홈페이지 사업 제품 서비스 전략 최근 {recent_months}개월 '
        f'공시 IR 채용 회사소개 주요 이슈'
    )
    return _run_cached_research(
        research_type="company", company=company, position="", team="", query=query,
        ttl_days=COMPANY_CACHE_DAYS, user_id=user_id, project_id=project_id,
        force_refresh=force_refresh, extra_key=str(recent_months),
    )


def research_job_sources(company: str, position: str, team: str = "", instructions: list[dict] | None = None,
                         user_id: str = "", project_id: str = "", force_refresh: bool = False) -> dict:
    team_text = team.strip()
    query = (
        f'"{company}" "{position}" {team_text} 최신 채용공고 공식 직무소개 직무기술서 '
        f'NCS 현직자 인터뷰 주요업무 필수 우대 지원조직 과거 채용'
    )
    return _run_cached_research(
        research_type="job", company=company, position=position, team=team, query=query,
        ttl_days=JOB_CACHE_DAYS, user_id=user_id, project_id=project_id, force_refresh=force_refresh,
    )


def search_recruiting_sources(company: str, position: str, team: str = "", max_results: int = 8) -> list[dict]:
    research = research_job_sources(company, position, team)
    return (research.get("results") or [])[: max(1, int(max_results))]
