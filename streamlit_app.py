from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from modules.ai_client import generate_json
from modules.document_parser import extract_text
from modules.prompts import (
    allocation_prompt,
    candidate_structure_prompt,
    company_analysis_prompt,
    essay_writer_prompt,
    experience_structure_prompt,
    job_analysis_prompt,
    question_analysis_prompt,
    review_prompt,
)
from modules.repetition import local_repetition_report
from modules.repository import (
    add_experience,
    add_instruction,
    add_question,
    add_source,
    authenticate_user,
    create_project,
    deactivate_instruction,
    delete_question,
    delete_source,
    get_allocation,
    get_analysis,
    get_candidate_profile,
    get_project,
    instruction_context,
    list_drafts,
    list_experiences,
    list_instructions,
    list_projects,
    list_questions,
    list_sources,
    prior_used_materials,
    register_user,
    save_allocation,
    save_analysis_section,
    save_candidate_profile,
    save_draft,
    update_project,
    update_question,
    update_source,
)
from modules.recruiting_search import (
    is_available as recruiting_search_available,
    research_company_sources,
    research_job_sources,
    search_recruiting_sources,
)
from modules.web_ingest import fetch_url_text


APP_TITLE = "Career Essay AI"
APP_SUBTITLE = "기업을 이해하고 · 채용직무를 해석하고 · 내 경험으로 자소서를 완성합니다"
VERSION = "v0.2.2"

st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="wide")


# =========================================================
# Styling
# =========================================================
st.markdown(
    """
    <style>
      .block-container {max-width: 1380px; padding-top: 1.25rem; padding-bottom: 4rem;}
      .hero {padding: 22px 24px; border:1px solid #e5e7eb; border-radius:18px; background:#ffffff; margin-bottom:14px;}
      .hero-title {font-size:30px; font-weight:800; letter-spacing:-0.7px; color:#111827;}
      .hero-sub {font-size:14px; color:#64748b; margin-top:4px;}
      .stage-card {border:1px solid #e5e7eb; border-radius:16px; padding:18px; background:#fff; min-height:128px;}
      .stage-number {font-size:12px; font-weight:700; color:#64748b;}
      .stage-title {font-size:19px; font-weight:800; color:#111827; margin-top:4px;}
      .stage-desc {font-size:13px; color:#64748b; margin-top:6px; line-height:1.45;}
      .result-box {border:1px solid #e5e7eb; border-radius:14px; padding:16px; background:#fff;}
      .muted {font-size:13px; color:#64748b;}
      .mini-label {font-size:12px; font-weight:700; color:#475569; margin-bottom:3px;}
      .gate-pass {padding:8px 10px; border-radius:10px; background:#ecfdf5; color:#065f46; font-weight:700;}
      .gate-partial {padding:8px 10px; border-radius:10px; background:#fffbeb; color:#92400e; font-weight:700;}
      .gate-gap {padding:8px 10px; border-radius:10px; background:#fef2f2; color:#991b1b; font-weight:700;}
      div[data-testid="stMetric"] {border:1px solid #e5e7eb; border-radius:14px; padding:12px; background:#fff;}
      .stTabs [data-baseweb="tab-list"] {gap:8px;}
      .stTabs [data-baseweb="tab"] {height:44px; border-radius:10px; padding-left:16px; padding-right:16px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Helpers
# =========================================================
def rerun():
    st.rerun()


def pretty(data):
    st.json(data or {}, expanded=False)


def exp_view(row: dict) -> dict:
    s = row.get("structured") or {}
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "fact_status": row.get("fact_status"),
        **s,
    }


def find_exp(experiences: list[dict], exp_id: str | None) -> dict:
    for row in experiences:
        if str(row.get("id")) == str(exp_id):
            return exp_view(row)
    return {}


def get_alloc_for_question(allocation: dict, question_id: str) -> dict:
    for item in (allocation or {}).get("allocations", []):
        if str(item.get("question_id")) == str(question_id):
            return item
    return {}


def require_project():
    user = st.session_state.get("user")
    project_id = st.session_state.get("project_id")
    if not user or not project_id:
        st.info("왼쪽에서 지원 프로젝트를 먼저 선택하거나 새로 만들어주세요.")
        st.stop()
    project = get_project(user["id"], project_id)
    if not project:
        st.warning("지원 프로젝트를 불러오지 못했습니다.")
        st.stop()
    return project




def save_auto_research_results(user_id: str, project_id: str, results: list[dict]) -> int:
    """Persist grounded research without creating duplicates on every re-analysis."""
    existing = list_sources(user_id, project_id)
    existing_map = {
        ((row.get("url") or "").strip(), (row.get("title") or "").strip()): row
        for row in existing
    }
    saved = 0
    for item in results or []:
        title = (item.get("title") or item.get("source_type") or "자동 웹 리서치").strip()
        url = (item.get("url") or "").strip()
        key = (url, title)
        content = (item.get("content") or item.get("snippet") or "").strip()
        if not content and not url:
            continue
        source_type = item.get("source_type") or "Google Search 근거"
        trust = item.get("trust_level") or "supported"
        existing_row = existing_map.get(key)
        if existing_row:
            # Refresh the synthesis/snippet on re-analysis so the DB does not stay stale.
            if content and content != (existing_row.get("content") or ""):
                update_source(
                    user_id, project_id, existing_row["id"],
                    source_type=source_type, title=title, content=content, url=url, trust_level=trust,
                )
            continue
        row = add_source(user_id, project_id, source_type, title, content, url, trust)
        existing_map[key] = row or {"title": title, "url": url, "content": content}
        saved += 1
    return saved

def stage_status(project_id: str) -> dict:
    analysis = get_analysis(USER_ID, project_id)
    qs = list_questions(USER_ID, project_id)
    alloc = get_allocation(USER_ID, project_id)
    drafts = list_drafts(USER_ID, project_id)
    return {
        "company": bool(analysis.get("company")),
        "job": bool(analysis.get("job")),
        "questions": bool(qs),
        "question_analysis": bool(qs) and all(bool(q.get("analysis")) for q in qs),
        "allocation": bool(alloc),
        "drafts": bool(drafts),
    }


def render_stage_cards(project: dict):
    status = stage_status(project["id"])
    cols = st.columns(3, gap="medium")
    cards = [
        ("01", "기업분석", "회사의 사업·최근 변화·과제를 자소서용 근거로 정리", status["company"]),
        ("02", "채용직무분석", "공고·직무기술서·지원조직 자료에서 실제 업무와 채용의도를 해석", status["job"]),
        ("03", "자소서 완성", "문항 분석 → 하고 싶은 말 → 경험 매칭 → 소재 배분 → 작성·검토", status["drafts"]),
    ]
    for col, (num, title, desc, ok) in zip(cols, cards):
        badge = "✅ 완료" if ok else "⬜ 진행 전"
        col.markdown(
            f'<div class="stage-card"><div class="stage-number">STEP {num} · {badge}</div>'
            f'<div class="stage-title">{title}</div><div class="stage-desc">{desc}</div></div>',
            unsafe_allow_html=True,
        )


def render_analysis_summary(title: str, data: dict, fields: list[tuple[str, str]]):
    st.markdown(f"#### {title}")
    if not data:
        st.info("아직 분석 결과가 없습니다.")
        return
    for label, key in fields:
        value = data.get(key)
        if not value:
            continue
        with st.expander(label, expanded=label in {"핵심 요약", "핵심 업무", "채용 핵심"}):
            if isinstance(value, str):
                st.write(value)
            else:
                pretty(value)


def gate_badge(status: str):
    status = (status or "gap").lower()
    cls = {"pass": "gate-pass", "partial": "gate-partial", "gap": "gate-gap"}.get(status, "gate-gap")
    label = {"pass": "PASS · 문항 필수조건 충족", "partial": "PARTIAL · 보완하면 작성 가능", "gap": "GAP · 추가 사실 필요"}.get(status, status)
    st.markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)


# =========================================================
# Session
# =========================================================
for key, default in {
    "user": None,
    "project_id": None,
    "candidate_preview": None,
    "experience_preview": None,
    "recruit_search_results": [],
    "generated_drafts": {},
    "generated_reviews": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# =========================================================
# Login
# =========================================================
if not st.session_state.user:
    st.markdown(
        f'<div class="hero"><div class="hero-title">📝 {APP_TITLE}</div>'
        f'<div class="hero-sub">{APP_SUBTITLE} · {VERSION}</div></div>',
        unsafe_allow_html=True,
    )
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("로그인")
        with st.form("login"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인", type="primary", use_container_width=True):
                try:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        rerun()
                    st.error("아이디 또는 비밀번호가 맞지 않습니다.")
                except Exception as e:
                    st.error(f"로그인 오류: {e}")
    with right:
        st.subheader("처음 사용")
        st.caption("계정을 만들면 이력·경험·기업분석·자소서가 사용자별로 분리 저장됩니다.")
        with st.form("register"):
            new_id = st.text_input("새 아이디")
            display_name = st.text_input("표시 이름")
            new_pw = st.text_input("새 비밀번호", type="password", placeholder="8자 이상")
            if st.form_submit_button("개인 저장소 만들기", use_container_width=True):
                try:
                    u = register_user(new_id, new_pw, display_name)
                    st.session_state.user = {
                        "id": u["id"],
                        "username": u["username"],
                        "display_name": u.get("display_name") or u["username"],
                    }
                    rerun()
                except Exception as e:
                    st.error(str(e))
    st.stop()


USER = st.session_state.user
USER_ID = USER["id"]


# =========================================================
# Sidebar: project + always-on prompt instruction
# =========================================================
with st.sidebar:
    st.markdown(f"### 👤 {USER.get('display_name') or USER.get('username')}")
    st.caption("개인 저장소")
    if st.button("로그아웃", use_container_width=True):
        st.session_state.user = None
        st.session_state.project_id = None
        rerun()

    st.divider()
    st.markdown("### 지원 프로젝트")
    projects = list_projects(USER_ID)
    if projects:
        options = {
            f"{p['company']} · {p['position']}" + (f" · {p.get('team')}" if p.get("team") else ""): p["id"]
            for p in projects
        }
        labels = list(options.keys())
        if st.session_state.project_id not in options.values():
            st.session_state.project_id = options[labels[0]]
        current_label = next(k for k, v in options.items() if v == st.session_state.project_id)
        selected = st.selectbox("프로젝트 선택", labels, index=labels.index(current_label), label_visibility="collapsed")
        st.session_state.project_id = options[selected]
    else:
        st.info("첫 지원 프로젝트를 만들어주세요.")

    with st.expander("➕ 새 지원 프로젝트", expanded=not bool(projects)):
        with st.form("new_project", clear_on_submit=True):
            company = st.text_input("기업명")
            position = st.text_input("지원 직무")
            team = st.text_input("사업부/팀/지원 조직", placeholder="모르면 비워도 됩니다")
            deadline = st.date_input("지원 마감일", value=None)
            if st.form_submit_button("프로젝트 만들기", type="primary", use_container_width=True):
                if not company.strip() or not position.strip():
                    st.error("기업명과 지원 직무를 입력해주세요.")
                else:
                    p = create_project(USER_ID, company, position, team, deadline.isoformat() if deadline else "")
                    st.session_state.project_id = p["id"]
                    rerun()

    if st.session_state.project_id:
        st.divider()
        st.markdown("### 💬 AI에게 계속 지시하기")
        st.caption("어느 화면에 있든 저장한 지시는 해당 단계 프롬프트에 누적 반영됩니다.")
        scope_label = st.selectbox(
            "적용 범위",
            ["전체 프로젝트", "기업분석", "채용직무분석", "자소서"],
            key="sidebar_instruction_scope",
        )
        scope_map = {"전체 프로젝트": "global", "기업분석": "company", "채용직무분석": "job", "자소서": "essay"}
        instruction = st.text_area(
            "추가 지시",
            height=92,
            placeholder="예: 최근 1년 이슈 중심으로 봐줘 / 문장을 담백하게 써줘",
            key="sidebar_instruction_text",
        )
        if st.button("지시 저장", use_container_width=True):
            try:
                add_instruction(USER_ID, st.session_state.project_id, scope_map[scope_label], instruction)
                st.success("지시를 저장했습니다.")
                rerun()
            except Exception as e:
                st.error(str(e))


# =========================================================
# Header + nav
# =========================================================
st.markdown(
    f'<div class="hero"><div class="hero-title">📝 {APP_TITLE}</div>'
    f'<div class="hero-sub">{APP_SUBTITLE} · {VERSION}</div></div>',
    unsafe_allow_html=True,
)

if st.session_state.project_id:
    current_project = require_project()
    render_stage_cards(current_project)
    st.write("")

main_tab, profile_tab, evidence_tab, storage_tab, settings_tab = st.tabs([
    "🎯 메인 워크플로우",
    "👤 내 정보",
    "🧾 분석 근거",
    "📚 저장소",
    "⚙️ 프로젝트 설정",
])


# =========================================================
# MAIN WORKFLOW: 3 visible stages only
# =========================================================
with main_tab:
    project = require_project()
    analysis_bundle = get_analysis(USER_ID, project["id"])
    company_data = analysis_bundle.get("company") or {}
    job_data = analysis_bundle.get("job") or {}
    sources = list_sources(USER_ID, project["id"])

    company_stage, job_stage, essay_stage = st.tabs([
        "1️⃣ 기업분석",
        "2️⃣ 채용직무분석",
        "3️⃣ 자소서 완성",
    ])

    # ---------------- STEP 1 ----------------
    with company_stage:
        st.subheader(f"{project['company']} 기업분석")
        st.caption("회사 소개를 길게 만드는 단계가 아닙니다. 자소서에서 실제로 써야 할 사업·변화·과제만 근거 중심으로 추립니다.")
        c1, c2, c3 = st.columns(3)
        c1.metric("저장된 근거", f"{len(sources)}개")
        c2.metric("공식 근거", f"{sum(1 for s in sources if s.get('trust_level') == 'official')}개")
        c3.metric("분석 상태", "완료" if company_data else "진행 전")

        st.info("기업명만으로 시작할 수 있습니다. **실행 버튼을 누르면 AI가 Google Search로 공식 홈페이지·공시·최근 이슈를 먼저 찾고, 그 근거를 저장한 뒤 기업분석을 진행합니다.**")
        if st.button("웹 리서치 + 기업분석 실행 / 다시 분석", type="primary", use_container_width=True):
            try:
                ins = instruction_context(USER_ID, project["id"], "company")
                with st.spinner("웹에서 공식자료·공시·최근 사업 이슈를 찾고 있습니다..."):
                    web_research = research_company_sources(project["company"], ins)
                    saved_count = save_auto_research_results(USER_ID, project["id"], web_research.get("results") or [])
                    sources = list_sources(USER_ID, project["id"])
                if not sources:
                    raise RuntimeError("웹 검색에서 분석에 사용할 근거를 확보하지 못했습니다. 회사명이 정확한지 확인해주세요.")
                with st.spinner("수집한 근거를 바탕으로 자소서용 기업분석을 만들고 있습니다..."):
                    result = generate_json(company_analysis_prompt(project["company"], sources, ins))
                result["web_research_queries"] = web_research.get("queries") or []
                result["auto_sources_added"] = saved_count
                save_analysis_section(USER_ID, project["id"], "company", result)
                st.success(f"기업분석을 저장했습니다. 자동 웹 근거 {saved_count}개를 새로 저장했습니다.")
                rerun()
            except Exception as e:
                st.error(f"기업분석 실패: {e}")

        render_analysis_summary(
            "기업분석 결과",
            company_data,
            [
                ("핵심 요약", "business_summary"),
                ("주요 사업", "key_businesses"),
                ("최근 변화", "recent_changes"),
                ("현재 과제", "current_challenges"),
                ("자소서 활용 포인트", "essay_specific_points"),
                ("과장하면 안 되는 부분", "do_not_overclaim"),
                ("추가로 필요한 자료", "data_gaps"),
            ],
        )

    # ---------------- STEP 2 ----------------
    with job_stage:
        st.subheader(f"{project['position']} 채용직무분석")
        st.caption("채용공고를 단어만 추출하지 않고 실제 업무·행동역량·지원조직·숨은 채용의도로 해석합니다.")
        if not company_data:
            st.warning("1단계 기업분석을 먼저 완료하는 것을 권장합니다. 직무분석 자체는 자동 웹 검색으로 실행할 수 있습니다.")
        st.info("AI가 **현재/최근 채용공고, 공식 직무소개, 지원조직 자료, 유사·과거 공고**를 먼저 검색한 뒤 실제 업무와 채용의도를 분석합니다.")

        if st.button("채용자료 자동검색 + 채용직무분석 실행 / 다시 분석", type="primary", use_container_width=True):
            try:
                ins = instruction_context(USER_ID, project["id"], "job")
                with st.spinner("최신 채용공고·직무기술서·지원조직 자료를 웹에서 찾고 있습니다..."):
                    web_research = research_job_sources(
                        project["company"], project["position"], project.get("team") or "", ins
                    )
                    saved_count = save_auto_research_results(USER_ID, project["id"], web_research.get("results") or [])
                    sources = list_sources(USER_ID, project["id"])
                if not sources:
                    raise RuntimeError("웹 검색에서 채용·직무 근거를 확보하지 못했습니다. 기업명/직무명을 확인해주세요.")
                with st.spinner("수집한 채용 근거에서 실제 업무·필수조건·지원조직·채용의도를 분석하고 있습니다..."):
                    result = generate_json(job_analysis_prompt(
                        project["company"], project["position"], project.get("team") or "", sources, company_data, ins
                    ))
                result["web_research_queries"] = web_research.get("queries") or []
                result["auto_sources_added"] = saved_count
                save_analysis_section(USER_ID, project["id"], "job", result)
                st.success(f"채용직무분석을 저장했습니다. 자동 웹 근거 {saved_count}개를 새로 저장했습니다.")
                rerun()
            except Exception as e:
                st.error(f"채용직무분석 실패: {e}")

        render_analysis_summary(
            "채용직무분석 결과",
            job_data,
            [
                ("채용 핵심", "posting_summary"),
                ("핵심 업무", "core_tasks"),
                ("필수·우대조건", "required_qualifications"),
                ("행동역량", "behavior_competencies"),
                ("숨은 채용의도", "hidden_hiring_intents"),
                ("지원조직/팀", "team"),
                ("역량 가중치", "competency_weights"),
                ("기업 변화 → 직무 영향", "company_to_job_link"),
                ("지원자에게 필요한 증거", "candidate_evidence_needed"),
                ("추가로 필요한 자료", "data_gaps"),
            ],
        )

    # ---------------- STEP 3 ----------------
    with essay_stage:
        st.subheader("자소서 완성")
        st.caption("문항을 먼저 냉정하게 분석하고, 사용자가 하고 싶은 말을 중심에 둔 뒤 경험을 배정합니다. 글부터 쓰지 않습니다.")

        questions = list_questions(USER_ID, project["id"])
        experiences = list_experiences(USER_ID)
        profile = get_candidate_profile(USER_ID)
        allocation = get_allocation(USER_ID, project["id"])

        sub1, sub2, sub3, sub4 = st.tabs([
            "① 문항 입력·분석",
            "② 소재 배분",
            "③ 작성",
            "④ 검토·최종",
        ])

        # 3-1 question input and analysis
        with sub1:
            left, right = st.columns([0.9, 1.1], gap="large")
            with left:
                st.markdown("#### 기업 자소서 문항 추가")
                st.caption("'내가 하고 싶은 말'은 선택 소재가 아니라, 이번 문항에서 반드시 전달하고 싶은 사용자 의도입니다.")
                with st.form("add_question_form", clear_on_submit=True):
                    q_text = st.text_area("자소서 문항", height=130, placeholder="기업의 실제 문항을 그대로 붙여넣으세요.")
                    q_limit = st.number_input("글자수 제한", min_value=0, max_value=5000, step=50, value=0)
                    q_message = st.text_area(
                        "내가 하고 싶은 말 (선택)",
                        height=115,
                        placeholder="예: 현재 데이터분석을 배우고 있고 AI 업무지원 프로그램을 직접 만들고 있다는 점을 꼭 보여주고 싶다.",
                    )
                    q_instruction = st.text_area(
                        "이 문항에만 적용할 추가 지시 (선택)",
                        height=80,
                        placeholder="예: 대학원 이야기는 쓰지 말아줘 / 현장 경험을 앞에 배치해줘",
                    )
                    if st.form_submit_button("문항 저장", type="primary", use_container_width=True):
                        if not q_text.strip():
                            st.error("자소서 문항을 입력해주세요.")
                        else:
                            add_question(USER_ID, project["id"], q_text, q_limit, q_message, q_instruction)
                            st.success("문항을 저장했습니다.")
                            rerun()

            with right:
                st.markdown(f"#### 저장된 문항 {len(questions)}개")
                if not questions:
                    st.info("기업의 자소서 문항을 추가하면 여기서 바로 분석할 수 있습니다.")
                for idx, q in enumerate(questions, start=1):
                    with st.expander(f"{idx}. {q['question_text'][:70]}", expanded=not bool(q.get("analysis"))):
                        st.write(q["question_text"])
                        if q.get("char_limit"):
                            st.caption(f"글자수 제한: {q['char_limit']}자")
                        if q.get("user_message"):
                            st.markdown("**내가 하고 싶은 말**")
                            st.info(q["user_message"])
                        if q.get("custom_instruction"):
                            st.caption(f"이 문항 추가 지시: {q['custom_instruction']}")

                        c_analyze, c_delete = st.columns([0.8, 0.2])
                        if c_analyze.button("문항 냉정 분석", key=f"qa_{q['id']}", use_container_width=True):
                            try:
                                ins = instruction_context(USER_ID, project["id"], "essay", q["id"])
                                if q.get("custom_instruction"):
                                    ins = [*ins, {"scope": "question", "instruction": q["custom_instruction"]}]
                                with st.spinner("채용담당자가 무엇을 보려는 문항인지 분해하고 있습니다..."):
                                    qa = generate_json(question_analysis_prompt(q, company_data, job_data, q.get("user_message") or "", ins))
                                update_question(USER_ID, project["id"], q["id"], analysis=qa)
                                st.success("문항 분석을 저장했습니다.")
                                rerun()
                            except Exception as e:
                                st.error(f"문항 분석 실패: {e}")
                        if c_delete.button("삭제", key=f"qd_{q['id']}", use_container_width=True):
                            delete_question(USER_ID, project["id"], q["id"])
                            rerun()

                        if q.get("analysis"):
                            qa = q["analysis"]
                            st.markdown("**한 줄 의도**")
                            st.write(qa.get("one_line_intent") or "-")
                            a, b = st.columns(2)
                            with a:
                                st.markdown("**반드시 답해야 할 것**")
                                for item in qa.get("must_answer_elements", []):
                                    st.write("-", item)
                                st.markdown("**하드 조건**")
                                for item in qa.get("hard_requirements", []):
                                    st.write("-", item)
                            with b:
                                st.markdown("**감점 위험**")
                                for item in qa.get("deduction_risks", []):
                                    st.write("-", item)
                                if qa.get("lookalike_but_wrong"):
                                    st.markdown("**비슷해 보여도 부적합한 경험**")
                                    for item in qa.get("lookalike_but_wrong", []):
                                        st.write("-", item)
                            if qa.get("user_message_core"):
                                st.markdown("**내가 하고 싶은 말 반영 전략**")
                                st.write(qa.get("user_message_integration") or qa.get("user_message_core"))
                                for ask in qa.get("user_message_evidence_questions", []):
                                    st.warning(ask)

        # 3-2 allocation
        with sub2:
            st.markdown("#### 전체 문항 소재 선배분")
            st.caption("문항마다 따로 쓰지 않습니다. 전체 문항을 함께 보고 Requirement Gate를 통과한 경험만 배정하며 의미상 중복을 사전에 막습니다.")
            analyzed_questions = [q for q in questions if q.get("analysis")]
            ready = bool(questions) and len(analyzed_questions) == len(questions) and bool(experiences)
            if not experiences:
                st.info("내 정보 탭에서 경험 DB를 먼저 추가해주세요.")
            if questions and len(analyzed_questions) != len(questions):
                st.warning("모든 문항을 먼저 '문항 냉정 분석'해야 소재 배분을 실행할 수 있습니다.")
            if st.button("전체 문항 소재 자동 배분", type="primary", use_container_width=True, disabled=not ready):
                try:
                    ins = instruction_context(USER_ID, project["id"], "essay")
                    payload_qs = [
                        {
                            "id": q["id"],
                            "question_text": q["question_text"],
                            "char_limit": q.get("char_limit") or 0,
                            "user_message": q.get("user_message") or "",
                            "analysis": q.get("analysis") or {},
                        }
                        for q in questions
                    ]
                    payload_exp = [exp_view(e) for e in experiences]
                    with st.spinner("필수조건 Gate → 경험 매칭 → 전체 문항 중복 차단 순서로 배분하고 있습니다..."):
                        alloc = generate_json(allocation_prompt(payload_qs, payload_exp, company_data, job_data, ins))
                    save_allocation(USER_ID, project["id"], alloc)
                    st.success("소재 배분을 저장했습니다.")
                    rerun()
                except Exception as e:
                    st.error(f"소재 배분 실패: {e}")

            allocation = get_allocation(USER_ID, project["id"])
            if allocation:
                for q in questions:
                    item = get_alloc_for_question(allocation, q["id"])
                    if not item:
                        continue
                    with st.expander(q["question_text"][:80], expanded=True):
                        gate = item.get("requirement_gate") or {}
                        gate_badge(gate.get("status") or "gap")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**선택 경험**")
                            selected_exp = find_exp(experiences, item.get("primary_experience_id"))
                            st.write(selected_exp.get("title") or "선택 경험 없음")
                            st.caption(item.get("reason") or "")
                            if item.get("user_message_anchor"):
                                st.markdown("**내가 하고 싶은 말의 중심축**")
                                st.info(item["user_message_anchor"])
                        with c2:
                            if gate.get("missing"):
                                st.markdown("**부족한 필수요소**")
                                for x in gate.get("missing", []):
                                    st.write("-", x)
                            if gate.get("gap_questions"):
                                st.markdown("**추가로 확인할 사실**")
                                for x in gate.get("gap_questions", []):
                                    st.warning(x)
                        if item.get("do_not_repeat"):
                            st.markdown("**다른 문항에서 반복 금지**")
                            st.write(" · ".join(map(str, item["do_not_repeat"])))

        # 3-3 writing
        with sub3:
            if not questions:
                st.info("먼저 자소서 문항을 추가해주세요.")
            elif not allocation:
                st.info("먼저 전체 문항 소재 배분을 실행해주세요.")
            else:
                labels = {f"{i+1}. {q['question_text'][:65]}": q for i, q in enumerate(questions)}
                selected_label = st.selectbox("작성할 문항", list(labels.keys()), key="write_q_select")
                q = labels[selected_label]
                qa = q.get("analysis") or {}
                alloc = get_alloc_for_question(allocation, q["id"])
                selected_exp = find_exp(experiences, alloc.get("primary_experience_id"))
                gate = alloc.get("requirement_gate") or {}

                top_left, top_right = st.columns([0.65, 0.35], gap="large")
                with top_left:
                    st.markdown("#### 이번 문항 작성 설계")
                    gate_badge(gate.get("status") or "gap")
                    st.write("**문항 의도:**", qa.get("one_line_intent") or "-")
                    st.write("**배정 경험:**", selected_exp.get("title") or "없음")
                    if q.get("user_message"):
                        st.markdown("**내가 하고 싶은 말**")
                        st.info(q["user_message"])
                    if alloc.get("recommended_structure"):
                        st.write("**권장 구조:**", " → ".join(map(str, alloc.get("recommended_structure") or [])))
                with top_right:
                    st.markdown("#### 작성 전 확인")
                    for x in gate.get("gap_questions", []):
                        st.warning(x)
                    if alloc.get("do_not_repeat"):
                        st.caption("반복 금지 소재")
                        for x in alloc.get("do_not_repeat", []):
                            st.write("-", x)

                can_write = (gate.get("status") or "gap") != "gap"
                if not can_write:
                    st.error("현재 경험 DB만으로는 문항의 필수조건을 충족하지 못합니다. 위 추가 질문에 해당하는 사실을 '내 정보' 또는 '내가 하고 싶은 말'에 보완한 뒤 다시 문항분석·소재배분을 실행해주세요.")

                if st.button("소제목 포함 자소서 초안 생성", type="primary", use_container_width=True, disabled=not can_write):
                    try:
                        ins = instruction_context(USER_ID, project["id"], "essay", q["id"])
                        if q.get("custom_instruction"):
                            ins = [*ins, {"scope": "question", "instruction": q["custom_instruction"]}]
                        prior = prior_used_materials(USER_ID, project["id"], q["id"])
                        with st.spinner("문항 의도·사용자 메시지·경험·기업/직무 근거를 연결해 작성하고 있습니다..."):
                            draft = generate_json(essay_writer_prompt(
                                q, qa, alloc, selected_exp, company_data, job_data,
                                profile.get("structured") or {}, prior,
                                q.get("user_message") or "", profile.get("style_sample") or "", ins,
                            ))
                        st.session_state.generated_drafts[str(q["id"])] = draft
                    except Exception as e:
                        st.error(f"초안 생성 실패: {e}")

                draft = st.session_state.generated_drafts.get(str(q["id"]))
                if draft:
                    if draft.get("status") == "needs_information":
                        st.warning("추가 사실 확인이 필요합니다.")
                        for x in draft.get("needs_confirmation", []):
                            st.write("-", x)
                    else:
                        st.markdown(f"### [{draft.get('title') or '소제목'}]")
                        edited = st.text_area("초안", value=draft.get("essay") or "", height=420, key=f"draft_edit_{q['id']}")
                        c1, c2 = st.columns(2)
                        c1.metric("현재 글자수", len(edited))
                        c2.metric("제한", f"{q.get('char_limit')}자" if q.get("char_limit") else "없음")
                        local = local_repetition_report(edited, [m for p in prior_used_materials(USER_ID, project["id"], q["id"]) for m in p.get("used_materials", [])])
                        if local.get("ai_tone_hits") or local.get("reused_facts"):
                            with st.expander("로컬 문체·중복 빠른 점검"):
                                pretty(local)
                        if st.button("초안 저장", use_container_width=True, key=f"save_draft_{q['id']}"):
                            save_draft(
                                USER_ID, project["id"], q["id"], "draft", edited,
                                draft.get("used_materials") or [], title=draft.get("title") or "",
                            )
                            st.success("초안을 저장했습니다.")

        # 3-4 review
        with sub4:
            if not questions:
                st.info("자소서 문항이 없습니다.")
            else:
                labels = {f"{i+1}. {q['question_text'][:65]}": q for i, q in enumerate(questions)}
                selected_label = st.selectbox("검토할 문항", list(labels.keys()), key="review_q_select")
                q = labels[selected_label]
                drafts = list_drafts(USER_ID, project["id"], q["id"])
                if not drafts:
                    st.info("먼저 해당 문항의 초안을 저장해주세요.")
                else:
                    draft_labels = {
                        f"{d.get('draft_type')} · {(d.get('created_at') or '')[:16]} · {(d.get('title') or '소제목 없음')}": d
                        for d in drafts
                    }
                    selected_d = st.selectbox("저장본", list(draft_labels.keys()))
                    d = draft_labels[selected_d]
                    source_essay = st.text_area("검토할 내용", value=d.get("content") or "", height=330)
                    alloc = get_alloc_for_question(allocation, q["id"])
                    selected_exp = find_exp(experiences, alloc.get("primary_experience_id"))
                    qa = q.get("analysis") or {}
                    if st.button("채용담당자 관점 종합 검토", type="primary", use_container_width=True):
                        try:
                            ins = instruction_context(USER_ID, project["id"], "essay", q["id"])
                            prior = prior_used_materials(USER_ID, project["id"], q["id"])
                            with st.spinner("문항 충족 → 사실 → 중복 → 기업/직무 적합성 → AI 말투 순으로 검토하고 있습니다..."):
                                review = generate_json(review_prompt(
                                    source_essay, q, qa, alloc, selected_exp, company_data, job_data,
                                    profile.get("structured") or {}, prior, q.get("user_message") or "", ins,
                                ))
                            st.session_state.generated_reviews[str(q["id"])] = review
                        except Exception as e:
                            st.error(f"검토 실패: {e}")

                    review = st.session_state.generated_reviews.get(str(q["id"]))
                    if review:
                        scores = review.get("scores") or {}
                        if scores:
                            st.markdown("#### 채용담당자 관점 점수")
                            df = pd.DataFrame([{"항목": k, "점수": v} for k, v in scores.items()])
                            st.dataframe(df, hide_index=True, use_container_width=True)
                        issue_cols = st.columns(3)
                        issue_map = [
                            ("치명적 문제", "fatal_issues"),
                            ("사실/문항 문제", "fact_issues"),
                            ("중복·AI 말투", "repetition_issues"),
                        ]
                        for col, (label, key) in zip(issue_cols, issue_map):
                            with col:
                                st.markdown(f"**{label}**")
                                vals = review.get(key) or []
                                if not vals:
                                    st.caption("특이사항 없음")
                                for x in vals:
                                    st.write("-", x)
                        st.markdown("#### 최종 수정본")
                        final_title = st.text_input("소제목", value=review.get("revised_title") or d.get("title") or "")
                        final_essay = st.text_area("최종본", value=review.get("revised_essay") or source_essay, height=430)
                        if st.button("최종본 저장", type="primary", use_container_width=True):
                            save_draft(
                                USER_ID, project["id"], q["id"], "final", final_essay,
                                d.get("used_materials") or [], review=review, title=final_title,
                            )
                            st.success("최종본을 저장했습니다.")


# =========================================================
# PROFILE / EXPERIENCE TAB
# =========================================================
with profile_tab:
    st.subheader("내 정보")
    st.caption("메인 화면을 복잡하게 만들지 않기 위해 이력서·경험 DB·문체는 여기서 관리합니다. 모든 지원 프로젝트에서 재사용됩니다.")
    ptab, etab = st.tabs(["이력서·프로필", "경험 DB"])

    with ptab:
        profile = get_candidate_profile(USER_ID)
        left, right = st.columns(2, gap="large")
        with left:
            uploaded = st.file_uploader("이력서/경력기술서", type=["pdf", "docx", "txt", "md"])
            raw_resume = st.text_area("또는 원문 붙여넣기", value=(profile.get("raw_text") or "") if not uploaded else "", height=260)
            style_sample = st.text_area(
                "내 문체 샘플 (선택)", value=profile.get("style_sample") or "", height=120,
                placeholder="내가 직접 쓴 자연스러운 문장을 넣으면 최종 말투에 참고합니다.",
            )
            if st.button("AI로 이력 구조화", type="primary", use_container_width=True):
                try:
                    text = extract_text(uploaded) if uploaded else raw_resume.strip()
                    if not text:
                        st.warning("파일을 올리거나 원문을 입력해주세요.")
                    else:
                        project_id = st.session_state.project_id
                        ins = instruction_context(USER_ID, project_id, "profile") if project_id else []
                        with st.spinner("이력과 경험을 사실 단위로 구조화하고 있습니다..."):
                            data = generate_json(candidate_structure_prompt(text, ins))
                        st.session_state.candidate_preview = {"raw": text, "data": data, "style_sample": style_sample}
                except Exception as e:
                    st.error(f"구조화 실패: {e}")
        with right:
            st.markdown("#### 구조화 결과")
            preview = st.session_state.candidate_preview
            if preview:
                pretty(preview["data"])
                if st.button("개인 DB에 저장", use_container_width=True):
                    save_candidate_profile(USER_ID, preview["raw"], preview["data"], preview.get("style_sample") or "")
                    existing_titles = {e.get("title") for e in list_experiences(USER_ID)}
                    for exp in preview["data"].get("experiences", []):
                        if exp.get("title") and exp.get("title") not in existing_titles:
                            add_experience(USER_ID, "이력서에서 자동 추출", exp)
                    st.session_state.candidate_preview = None
                    st.success("프로필과 경험을 저장했습니다.")
                    rerun()
            elif profile:
                pretty(profile.get("structured") or {})
            else:
                st.info("저장된 프로필이 없습니다.")

    with etab:
        left, right = st.columns([0.85, 1.15], gap="large")
        with left:
            raw_exp = st.text_area(
                "경험을 편하게 적어주세요", height=250,
                placeholder="정해진 양식 없이 기억나는 대로 적으세요. AI가 문제·판단·행동·결과로 구조화합니다.",
            )
            if st.button("경험 구조화", type="primary", use_container_width=True):
                if not raw_exp.strip():
                    st.warning("경험을 입력해주세요.")
                else:
                    try:
                        project_id = st.session_state.project_id
                        ins = instruction_context(USER_ID, project_id, "profile") if project_id else []
                        with st.spinner("내 행동과 팀 행동을 분리하고 부족한 근거를 찾고 있습니다..."):
                            data = generate_json(experience_structure_prompt(raw_exp, ins))
                        st.session_state.experience_preview = {"raw": raw_exp, "data": data}
                    except Exception as e:
                        st.error(f"경험 구조화 실패: {e}")
            if st.session_state.experience_preview:
                pretty(st.session_state.experience_preview["data"])
                if st.button("경험 DB에 저장", use_container_width=True):
                    p = st.session_state.experience_preview
                    add_experience(USER_ID, p["raw"], p["data"])
                    st.session_state.experience_preview = None
                    st.success("경험을 저장했습니다.")
                    rerun()
        with right:
            experiences = list_experiences(USER_ID)
            st.markdown(f"#### 저장된 경험 {len(experiences)}개")
            if not experiences:
                st.info("아직 저장된 경험이 없습니다.")
            for exp in experiences:
                s = exp.get("structured") or {}
                with st.expander(exp.get("title") or "경험"):
                    c1, c2, c3 = st.columns(3)
                    c1.caption(f"사실상태: {exp.get('fact_status') or '-'}")
                    c2.caption(f"역할: {s.get('my_role') or s.get('role') or '-'}")
                    c3.caption(f"결과: {s.get('result') or '-'}")
                    if s.get("missing_questions"):
                        st.markdown("**추가하면 가치가 큰 정보**")
                        for x in s.get("missing_questions", []):
                            st.write("-", x)
                    pretty(s)


# =========================================================
# EVIDENCE / ANALYSIS RECORD TAB
# =========================================================
with evidence_tab:
    project = require_project()
    st.subheader("분석 근거·중간 판단")
    st.caption("메인 워크플로우에는 결과만 보여주고, AI가 사용한 자료·분석결과·사용자 지시 이력은 여기서 투명하게 확인합니다.")
    sources_sub, analysis_sub, instruction_sub = st.tabs(["채용·기업 자료", "분석 상세", "AI 지시 이력"])

    with sources_sub:
        st.markdown("#### 자료 추가")
        search_col, url_col, text_col = st.tabs(["자동 검색", "URL 가져오기", "본문 직접 저장"])
        with search_col:
            if recruiting_search_available():
                st.caption("별도 검색 API가 필요하지 않습니다. 기존 GEMINI_API_KEY의 Google Search grounding을 사용합니다.")
                if st.button("Google Search로 관련 채용자료 찾기", type="primary", use_container_width=True):
                    try:
                        ins = instruction_context(USER_ID, project["id"], "job")
                        with st.spinner("기업·직무·지원조직 관련 공개 웹 자료를 검색하고 있습니다..."):
                            st.session_state.recruit_search_results = search_recruiting_sources(
                                project.get("company") or "", project.get("position") or "", project.get("team") or ""
                            )
                    except Exception as e:
                        st.error(f"검색 실패: {e}")
                for idx, item in enumerate(st.session_state.recruit_search_results):
                    with st.expander(f"{idx+1}. {item.get('title') or '검색결과'}"):
                        st.caption(item.get("url") or "Google Search 기반 종합 리서치")
                        st.write((item.get("snippet") or "")[:1000])
                        default_type = item.get("source_type") or "Google Search 근거"
                        stype = st.selectbox(
                            "자료 유형",
                            [default_type, "공식 채용공고", "공식 직무기술서", "공식 회사자료", "공식 직무인터뷰", "과거 채용공고", "채용 플랫폼", "언론/산업자료", "기타"],
                            key=f"search_stype_{idx}",
                        )
                        if st.button("이 자료 저장", key=f"save_search_{idx}"):
                            trust = "official" if stype.startswith("공식") else (item.get("trust_level") or "supported")
                            add_source(USER_ID, project["id"], stype, item.get("title") or stype, item.get("content") or item.get("snippet") or "", item.get("url") or "", trust)
                            rerun()
            else:
                st.info("GEMINI_API_KEY가 설정되면 자동 Google Search를 사용할 수 있습니다.")

        with url_col:
            with st.form("url_source_form"):
                url = st.text_input("자료 URL")
                source_type = st.selectbox("자료 유형", ["공식 채용공고", "공식 직무기술서", "공식 회사자료", "공식 직무인터뷰", "과거 채용공고", "채용 플랫폼", "언론/산업자료", "기타"])
                if st.form_submit_button("URL 본문 가져와 저장", type="primary", use_container_width=True):
                    try:
                        page = fetch_url_text(url)
                        trust = "official" if source_type.startswith("공식") else "supported"
                        add_source(USER_ID, project["id"], source_type, page["title"], page["text"], page["url"], trust)
                        st.success("자료를 저장했습니다.")
                        rerun()
                    except Exception as e:
                        st.error(f"가져오기 실패: {e}")

        with text_col:
            with st.form("manual_source_form", clear_on_submit=True):
                source_type = st.selectbox("자료 유형", ["공식 채용공고", "공식 직무기술서", "공식 회사자료", "공식 직무인터뷰", "과거 채용공고", "채용 플랫폼", "언론/산업자료", "기타"], key="manual_stype")
                title = st.text_input("자료 제목")
                url = st.text_input("출처 URL (선택)", key="manual_url")
                content = st.text_area("본문", height=280, placeholder="채용공고나 직무기술서 내용을 그대로 붙여넣으세요.")
                trust = st.selectbox("신뢰도", ["official", "supported", "inferred"], index=0 if source_type.startswith("공식") else 1)
                if st.form_submit_button("본문 저장", type="primary", use_container_width=True):
                    if not content.strip():
                        st.error("본문을 입력해주세요.")
                    else:
                        add_source(USER_ID, project["id"], source_type, title or source_type, content, url, trust)
                        st.success("자료를 저장했습니다.")
                        rerun()

        st.markdown("#### 저장된 근거")
        sources = list_sources(USER_ID, project["id"])
        if not sources:
            st.info("저장된 근거가 없습니다.")
        for s in sources:
            with st.expander(f"[{s.get('trust_level')}] {s.get('source_type')} · {s.get('title')}"):
                st.caption(s.get("url") or "URL 없음")
                st.text((s.get("content") or "")[:3000])
                if st.button("이 자료 삭제", key=f"src_del_{s['id']}"):
                    delete_source(USER_ID, project["id"], s["id"])
                    rerun()

    with analysis_sub:
        bundle = get_analysis(USER_ID, project["id"])
        st.markdown("#### 기업분석 원본")
        pretty(bundle.get("company") or {})
        st.markdown("#### 채용직무분석 원본")
        pretty(bundle.get("job") or {})
        st.markdown("#### 문항 분석 원본")
        for q in list_questions(USER_ID, project["id"]):
            with st.expander(q["question_text"][:90]):
                pretty(q.get("analysis") or {})
        st.markdown("#### 소재 배분 원본")
        pretty(get_allocation(USER_ID, project["id"]))

    with instruction_sub:
        instructions = list_instructions(USER_ID, project["id"], active_only=False)
        if not instructions:
            st.info("저장된 사용자 지시가 없습니다. 왼쪽 사이드바에서 언제든 추가할 수 있습니다.")
        for item in reversed(instructions):
            cols = st.columns([0.16, 0.64, 0.2])
            cols[0].caption(item.get("scope") or "")
            cols[1].write(item.get("instruction") or "")
            if item.get("active"):
                if cols[2].button("사용 중지", key=f"disable_{item['id']}"):
                    deactivate_instruction(USER_ID, project["id"], item["id"])
                    rerun()
            else:
                cols[2].caption("중지됨")


# =========================================================
# STORAGE TAB
# =========================================================
with storage_tab:
    project = require_project()
    st.subheader("저장소")
    st.caption("완성본과 이전 버전을 프로젝트별로 보관합니다.")
    qs = list_questions(USER_ID, project["id"])
    if not qs:
        st.info("저장된 자소서 문항이 없습니다.")
    for idx, q in enumerate(qs, start=1):
        with st.expander(f"{idx}. {q['question_text'][:90]}"):
            ds = list_drafts(USER_ID, project["id"], q["id"])
            if not ds:
                st.caption("저장본 없음")
            for d in ds:
                st.markdown(f"**{d.get('draft_type','draft').upper()} · {d.get('title') or '소제목 없음'}**")
                st.caption(d.get("created_at") or "")
                st.text_area("내용", value=d.get("content") or "", height=220, key=f"stored_{d['id']}")
                if d.get("review"):
                    with st.expander("검토 기록"):
                        pretty(d.get("review"))


# =========================================================
# SETTINGS TAB
# =========================================================
with settings_tab:
    project = require_project()
    st.subheader("프로젝트 설정")
    st.caption("메인 워크플로우에서 자주 바꾸지 않는 정보만 여기 둡니다.")
    with st.form("project_settings"):
        company = st.text_input("기업명", value=project.get("company") or "")
        position = st.text_input("지원 직무", value=project.get("position") or "")
        team = st.text_input("사업부/팀/지원 조직", value=project.get("team") or "")
        status_values = ["준비중", "작성중", "검토중", "지원완료", "서류합격", "불합격"]
        current_status = project.get("status") if project.get("status") in status_values else "준비중"
        status = st.selectbox("지원 상태", status_values, index=status_values.index(current_status))
        notes = st.text_area("프로젝트 메모", value=project.get("notes") or "")
        if st.form_submit_button("프로젝트 정보 저장", type="primary"):
            update_project(USER_ID, project["id"], company=company, position=position, team=team, status=status, notes=notes)
            st.success("프로젝트 정보를 저장했습니다.")
            rerun()

    st.divider()
    st.markdown("#### 설계 원칙")
    st.write("- 메인 화면은 **기업분석 → 채용직무분석 → 자소서 완성** 3단계만 크게 보여줍니다.")
    st.write("- 이력서·경험 DB·근거·중간분석·지시 이력은 별도 탭에 둡니다.")
    st.write("- '내가 하고 싶은 말'은 버릴 소재가 아니라 사용자가 반드시 전달하려는 핵심 의도로 취급합니다.")
    st.write("- 문항 분석은 지원자에게 유리하게 해석하지 않고 필수조건과 감점요소를 냉정하게 분해합니다.")
    st.write("- 경험이 문항 하드조건을 충족하지 못하면 자소서를 억지로 쓰지 않고 추가 사실을 요청합니다.")
