from __future__ import annotations

import os
import re

import streamlit as st

from modules.ai_client import generate_grounded_research


def _gemini_key() -> str:
    return str(os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "") or "").strip()


def is_available() -> bool:
    return bool(_gemini_key())


def _instruction_text(instructions: list[dict] | None) -> str:
    if not instructions:
        return "없음"
    values = []
    for item in instructions:
        text = (item.get("instruction") or "").strip()
        if text:
            values.append(f"- {text}")
    return "\n".join(values) or "없음"


def _research_to_results(research: dict, synthesis_title: str, source_type: str) -> list[dict]:
    results: list[dict] = []
    text = (research.get("text") or "").strip()
    if text:
        results.append(
            {
                "title": synthesis_title,
                "url": "",
                "content": text,
                "snippet": text[:1200],
                "score": None,
                "source_type": source_type,
                "trust_level": "supported",
                "is_synthesis": True,
            }
        )

    for source in research.get("sources") or []:
        results.append(
            {
                "title": source.get("title") or "Google Search source",
                "url": source.get("url") or "",
                "content": source.get("content") or source.get("snippet") or "",
                "snippet": source.get("snippet") or source.get("content") or "",
                "score": None,
                "source_type": source.get("source_type") or "Google Search 근거",
                "trust_level": source.get("trust_level") or "supported",
                "is_synthesis": False,
            }
        )
    return results


def research_company_sources(
    company: str,
    instructions: list[dict] | None = None,
    recent_months: int = 18,
) -> dict:
    prompt = f"""
너는 한국 취업용 기업 리서치 담당자다. 지금부터 Google Search를 실제로 사용해 '{company}'를 조사하라.
사용자가 자료를 찾아서 주는 방식이 아니라, 네가 먼저 웹에서 근거를 찾아야 한다.

[리서치 목적]
최종 목표는 회사 소개 보고서가 아니라 지원자가 자소서에서 사용할 수 있는 정확한 기업 이해 근거를 만드는 것이다.

[반드시 검색할 것]
1. 회사 공식 홈페이지: 사업영역, 제품/서비스, 고객/시장, 기술/사업 구조
2. 공식 채용/인재 페이지가 있으면 채용 방향, 인재상, 직무 관련 설명
3. 상장/공시 기업이면 DART/KIND/IR/사업보고서 등 공식·공공 자료
4. 최근 {recent_months}개월의 전략, 투자, 수주, 신사업, 기술, 시장 변화, 경영 이슈
5. 회사가 현재 해결해야 할 사업·시장·운영상 과제
6. 자소서 지원동기/직무연결/입사후포부에 직접 활용할 수 있는 구체적 사실

[출처 우선순위]
공식 회사 자료 > 공시/정부/공공기관 > 공식 산업기관 > 신뢰도 높은 언론 > 기타 자료.
가능하면 공식 자료와 최근 자료를 교차 확인하라.

[금지]
- 근거 없는 회사 칭찬
- 확인되지 않은 숫자나 계획 단정
- 다른 동명의 회사 정보 혼입
- 검색되지 않은 내용을 아는 척 채우기

[사용자 추가 지시]
{_instruction_text(instructions)}

[출력]
한국어로 아래 순서로 사실 중심 리서치 메모를 작성하라.
- 회사 식별 확인
- 주요 사업/제품/서비스
- 최근 변화 및 핵심 이슈
- 시장/경쟁/정책 환경
- 현재 과제
- 채용/직무와 연결할 만한 포인트
- 아직 확인되지 않은 부분
각 핵심 사실에는 어떤 출처 유형에서 확인했는지 문장 안에서 드러내라.
"""
    research = generate_grounded_research(prompt)
    return {
        **research,
        "results": _research_to_results(
            research,
            f"{company} 자동 기업 리서치",
            "자동 기업 리서치",
        ),
    }


def research_job_sources(
    company: str,
    position: str,
    team: str = "",
    instructions: list[dict] | None = None,
) -> dict:
    team_text = team.strip() or "미지정"
    prompt = f"""
너는 한국 취업용 채용공고·직무 리서치 담당자다. Google Search를 실제로 사용해 아래 지원 직무를 조사하라.
사용자에게 채용공고를 찾아오라고 요구하지 말고, 먼저 네가 공개 웹에서 찾을 수 있는 최신 근거를 수집한다.

회사: {company}
지원직무: {position}
지원조직/팀: {team_text}

[반드시 검색할 것]
1. 현재 또는 가장 최근의 회사 공식 채용공고에서 '{position}' 관련 공고
2. 회사 공식 직무소개/조직소개/현직자 인터뷰
3. 공공기관이면 NCS 직무기술서, ALIO, 기관 공식 채용자료
4. 동일·유사 직무의 과거 공고: 반복되는 업무/역량과 새로 추가된 요구사항 구분
5. 지원조직/팀이 공개되어 있으면 실제 담당 사업·제품·프로세스
6. 직무의 실제 주요업무, 협업대상, 사용하는 데이터/도구, 중요 문제
7. 필수조건/우대사항/반복 키워드/채용담당자가 확인하려는 행동역량

[출처 우선순위]
현재 공식 채용공고 > 공식 직무기술서/채용페이지 > 공식 조직·사업 자료 > 공공기관 자료 > 신뢰 가능한 채용플랫폼/언론.

[냉정한 분석을 위한 주의]
- 최신 공고와 과거 공고를 섞지 말고 시점을 구분한다.
- 팀 업무가 확인되지 않으면 추정이라고 명시한다.
- KPI, 사용도구, 팀 역할을 근거 없이 확정하지 않는다.
- 단순 '소통/협업' 같은 단어는 실제 행동으로 풀 수 있는 근거를 찾는다.

[사용자 추가 지시]
{_instruction_text(instructions)}

[출력]
한국어 리서치 메모로 작성한다.
- 확인된 최신 채용공고/직무자료
- 핵심 업무
- 필수/우대조건
- 지원조직/팀의 실제 업무
- 반복적으로 요구되는 역량
- 최근 추가/변화한 요구사항
- 채용의도 해석에 사용할 근거
- 확인되지 않은 부분
"""
    research = generate_grounded_research(prompt)
    return {
        **research,
        "results": _research_to_results(
            research,
            f"{company} {position} 자동 채용직무 리서치",
            "자동 채용직무 리서치",
        ),
    }


def search_recruiting_sources(company: str, position: str, team: str = "", max_results: int = 8) -> list[dict]:
    """Manual evidence-tab search, now powered by Gemini Google Search grounding.

    Kept under the previous function name so the existing UI stays compatible.
    """
    if not is_available():
        raise RuntimeError("GEMINI_API_KEY가 없습니다. 자동 웹 검색에는 기존 Gemini API 키를 사용합니다.")
    research = research_job_sources(company, position, team)
    # Keep the synthesis plus the most useful cited sources.
    return (research.get("results") or [])[: max(1, int(max_results))]
