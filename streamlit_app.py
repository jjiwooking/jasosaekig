from __future__ import annotations

import json
import html

import streamlit as st

from modules.ai_client import AIServiceError, generate_json
from modules.document_parser import extract_text
from modules.prompts import (
    allocation_prompt,
    application_analysis_prompt,
    candidate_structure_prompt,
    essay_writer_prompt,
    experience_structure_prompt,
    fact_check_prompt,
    final_edit_prompt,
    question_analysis_prompt,
    recruiter_review_prompt,
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
    get_monthly_research_usage,
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
)
from modules.web_ingest import fetch_url_text

APP_TITLE = "Career Essay AI"
APP_SUBTITLE = "한 기업을 분석하고, 내 경험으로 바로 자소서를 완성합니다"
VERSION = "v0.4.0"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# Calm, workspace-first UI
# =========================================================
st.markdown(
    """
    <style>
      .block-container {max-width: 1180px; padding-top: 1.2rem; padding-bottom: 4rem;}
      h1,h2,h3 {letter-spacing:-0.035em;}
      .app-head {padding:4px 0 18px 0; border-bottom:1px solid #edf0f4; margin-bottom:18px;}
      .app-title {font-size:28px; font-weight:800; color:#111827;}
      .app-sub {font-size:14px; color:#64748b; margin-top:5px;}
      .project-line {display:flex; gap:10px; align-items:center; padding:12px 14px; border:1px solid #e5e7eb; border-radius:14px; background:#fff; margin-bottom:14px;}
      .project-company {font-weight:800; color:#111827;}
      .project-role {font-size:13px; color:#64748b;}
      .step-wrap {display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:8px 0 22px 0;}
      .step {padding:13px 16px; border:1px solid #e5e7eb; border-radius:14px; background:#f8fafc;}
      .step.active {border-color:#2563eb; background:#eff6ff;}
      .step.done {border-color:#bbf7d0; background:#f0fdf4;}
      .step-kicker {font-size:11px; font-weight:800; color:#64748b;}
      .step-title {font-size:17px; font-weight:800; color:#111827; margin-top:2px;}
      .section-card {border:1px solid #e5e7eb; border-radius:14px; padding:16px; background:#fff; height:100%;}
      .section-kicker {font-size:11px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:.04em;}
      .section-title {font-size:16px; font-weight:800; color:#111827; margin-top:4px; margin-bottom:7px;}
      .section-body {font-size:14px; color:#334155; line-height:1.6;}
      .soft {padding:12px 14px; border-radius:12px; background:#f8fafc; color:#475569; font-size:13px; line-height:1.55;}
      .good {padding:11px 13px; border-radius:12px; background:#f0fdf4; color:#166534; font-weight:700; font-size:13px;}
      .warn {padding:11px 13px; border-radius:12px; background:#fffbeb; color:#92400e; font-weight:700; font-size:13px;}
      .bad {padding:11px 13px; border-radius:12px; background:#fef2f2; color:#991b1b; font-weight:700; font-size:13px;}
      .question-card {padding:14px 15px; border:1px solid #e5e7eb; border-radius:13px; background:#fff; margin-bottom:8px;}
      .q-num {font-size:11px; font-weight:800; color:#2563eb;}
      .q-text {font-size:14px; color:#111827; line-height:1.5; margin-top:4px;}
      .q-meta {font-size:12px; color:#64748b; margin-top:5px;}
      div[data-testid="stMetric"] {border:0; background:#f8fafc; border-radius:12px; padding:10px 12px;}
      .stTabs [data-baseweb="tab-list"] {gap:18px; border-bottom:1px solid #e5e7eb;}
      .stTabs [data-baseweb="tab"] {height:48px; padding:0 2px; background:transparent;}
      .stTabs [aria-selected="true"] {font-weight:800;}
      div[data-testid="stForm"] {border:1px solid #e5e7eb; border-radius:14px; padding:14px;}
      .stButton > button {border-radius:11px; min-height:42px;}
      textarea, input {border-radius:10px !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# Helpers
# =========================================================
def rerun():
    st.rerun()


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _short_list(value, limit=4):
    items = _as_list(value)
    out = []
    for item in items[:limit]:
        if isinstance(item, dict):
            text = (
                item.get("point") or item.get("fact") or item.get("challenge") or item.get("task")
                or item.get("competency") or item.get("intent") or item.get("item") or item.get("requirement")
                or json.dumps(item, ensure_ascii=False)
            )
        else:
            text = str(item)
        if text:
            out.append(text)
    return out


def _bullets(value, limit=5):
    items = _short_list(value, limit)
    if not items:
        st.caption("확인된 내용이 없습니다.")
        return
    for item in items:
        st.write(f"• {item}")


def require_project():
    if not st.session_state.get("user") or not st.session_state.get("project_id"):
        st.info("왼쪽에서 지원서를 하나 선택하거나 새로 만들어주세요.")
        st.stop()
    project = get_project(st.session_state.user["id"], st.session_state.project_id)
    if not project:
        st.warning("지원서를 불러오지 못했습니다.")
        st.stop()
    return project


def exp_view(row: dict) -> dict:
    s = row.get("structured") or {}
    return {"id": row.get("id"), "title": row.get("title"), "fact_status": row.get("fact_status"), **s}


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


def save_auto_research_results(user_id: str, project_id: str, results: list[dict]) -> int:
    existing = list_sources(user_id, project_id)
    existing_map = {
        ((row.get("url") or "").strip(), (row.get("title") or "").strip()): row
        for row in existing
    }
    saved = 0
    for item in results or []:
        title = (item.get("title") or "웹 리서치 자료").strip()
        url = (item.get("url") or "").strip()
        content = (item.get("content") or item.get("snippet") or "").strip()
        if not content and not url:
            continue
        source_type = item.get("source_type") or "웹 리서치 근거"
        trust = item.get("trust_level") or "supported"
        key = (url, title)
        old = existing_map.get(key)
        if old:
            if content and content != (old.get("content") or ""):
                update_source(
                    user_id, project_id, old["id"], source_type=source_type,
                    title=title, content=content, url=url, trust_level=trust,
                )
            continue
        row = add_source(user_id, project_id, source_type, title, content, url, trust)
        existing_map[key] = row or {"url": url, "title": title}
        saved += 1
    return saved


def run_application_analysis(user_id: str, project: dict, sources: list[dict]) -> dict:
    instructions = instruction_context(user_id, project["id"], "analysis")
    result = generate_json(application_analysis_prompt(
        project["company"], project["position"], project.get("team") or "", sources, instructions
    ))
    company = result.get("company") or {}
    job = result.get("job") or {}
    # 채용분석 결과는 job 데이터에도 함께 넣어 기존 Writer 프롬프트와 호환한다.
    job["recruiting"] = result.get("recruiting") or {}
    save_analysis_section(user_id, project["id"], "company", company)
    save_analysis_section(user_id, project["id"], "job", job)
    save_analysis_section(user_id, project["id"], "application", result)
    return result


def render_ai_error(exc: Exception):
    if isinstance(exc, AIServiceError):
        st.error(str(exc))
        if exc.code in {429, 503}:
            st.info("웹에서 찾은 자료는 이미 저장돼 있습니다. 잠시 후 **AI 분석만 다시 시도**하면 검색 크레딧은 추가로 사용하지 않습니다.")
        with st.expander("오류 상세", expanded=False):
            st.json(exc.model_attempts or [])
    else:
        st.error(str(exc))


def sync_profile_experiences(user_id: str, structured: dict) -> int:
    existing = list_experiences(user_id)
    signatures = set()
    for row in existing:
        s = row.get("structured") or {}
        signatures.add((
            (row.get("title") or "").strip().lower(),
            (s.get("period") or "").strip().lower(),
            (s.get("organization") or "").strip().lower(),
        ))
    added = 0
    for exp in structured.get("experiences", []) or []:
        sig = (
            (exp.get("title") or "경험").strip().lower(),
            (exp.get("period") or "").strip().lower(),
            (exp.get("organization") or "").strip().lower(),
        )
        if sig in signatures:
            continue
        add_experience(user_id, json.dumps(exp, ensure_ascii=False), exp)
        signatures.add(sig)
        added += 1
    return added


def latest_final(user_id: str, project_id: str, question_id: str) -> dict | None:
    for row in list_drafts(user_id, project_id, question_id):
        if row.get("draft_type") == "final":
            return row
    return None


def analysis_ready(project_id: str) -> bool:
    return bool((get_analysis(USER_ID, project_id) or {}).get("application"))


def allocation_ready(project_id: str) -> bool:
    return bool(get_allocation(USER_ID, project_id))


def set_workspace_step(step: int):
    st.session_state.workspace_step = int(step)


def generate_complete_essay(project: dict, question: dict, allocation: dict, experiences: list[dict], profile: dict):
    qa = question.get("analysis") or {}
    alloc = get_alloc_for_question(allocation, question["id"])
    exp = find_exp(experiences, alloc.get("primary_experience_id"))
    company_data = (get_analysis(USER_ID, project["id"]) or {}).get("company") or {}
    job_data = (get_analysis(USER_ID, project["id"]) or {}).get("job") or {}
    prior = prior_used_materials(USER_ID, project["id"], question["id"])
    instructions = instruction_context(USER_ID, project["id"], "essay", question["id"])
    if question.get("custom_instruction"):
        instructions = [*instructions, {"scope": "question", "instruction": question["custom_instruction"]}]

    with st.status("자소서를 작성하고 검토하고 있습니다...", expanded=True) as status:
        st.write("1/4 실제 경험과 문항 의도로 초안을 작성합니다.")
        draft = generate_json(essay_writer_prompt(
            question, qa, alloc, exp, company_data, job_data,
            profile.get("structured") or {}, prior,
            question.get("user_message") or "", profile.get("style_sample") or "", instructions,
        ))
        if draft.get("status") == "needs_information":
            status.update(label="추가 사실이 필요합니다.", state="error")
            return {"needs_information": draft}

        save_draft(
            USER_ID, project["id"], question["id"], "draft", draft.get("essay") or "",
            draft.get("used_materials") or [], title=draft.get("title") or "",
        )

        st.write("2/4 채용담당자 관점에서 감점요인을 찾습니다.")
        recruiter = generate_json(recruiter_review_prompt(
            draft.get("essay") or "", question, qa, alloc, company_data, job_data,
            question.get("user_message") or "", instructions,
        ))

        st.write("3/4 숫자·기간·역할·성과를 원 데이터와 대조합니다.")
        fact = generate_json(fact_check_prompt(
            draft.get("essay") or "", question, exp, profile.get("structured") or {},
            company_data, job_data, prior,
        ))

        st.write("4/4 사실은 유지하고 문장과 흐름만 최종 편집합니다.")
        final = generate_json(final_edit_prompt(
            draft.get("essay") or "", question, qa, recruiter, fact,
            question.get("user_message") or "", profile.get("style_sample") or "", instructions,
        ))

        review_bundle = {"recruiter": recruiter, "fact": fact, "final": final}
        saved = save_draft(
            USER_ID, project["id"], question["id"], "final",
            final.get("final_essay") or draft.get("essay") or "",
            draft.get("used_materials") or [], review=review_bundle,
            title=final.get("title") or draft.get("title") or "",
        )
        status.update(label="자소서 최종본이 완성됐습니다.", state="complete", expanded=False)
        return {"saved": saved, "draft": draft, "review": review_bundle}


# =========================================================
# Session
# =========================================================
for key, default in {
    "user": None,
    "project_id": None,
    "workspace_step": 1,
    "analysis_ai_failed": False,
    "candidate_preview": None,
    "experience_preview": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# =========================================================
# Login
# =========================================================
if not st.session_state.user:
    st.markdown(
        f'<div class="app-head"><div class="app-title">📝 {APP_TITLE}</div>'
        f'<div class="app-sub">{APP_SUBTITLE} · {VERSION}</div></div>',
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
        st.caption("한 번 만든 이력·경험 DB는 여러 지원서에서 다시 사용할 수 있습니다.")
        with st.form("register"):
            new_id = st.text_input("새 아이디")
            display_name = st.text_input("표시 이름")
            new_pw = st.text_input("새 비밀번호", type="password", placeholder="8자 이상")
            if st.form_submit_button("개인 저장소 만들기", use_container_width=True):
                try:
                    u = register_user(new_id, new_pw, display_name)
                    st.session_state.user = {"id": u["id"], "username": u["username"], "display_name": u.get("display_name") or u["username"]}
                    rerun()
                except Exception as e:
                    st.error(str(e))
    st.stop()

USER = st.session_state.user
USER_ID = USER["id"]

# =========================================================
# Sidebar: only application selection + simple controls
# =========================================================
with st.sidebar:
    st.markdown(f"### {USER.get('display_name') or USER.get('username')}")
    st.caption("Career Essay AI")
    if st.button("로그아웃", use_container_width=True):
        st.session_state.user = None
        st.session_state.project_id = None
        rerun()

    st.divider()
    st.markdown("#### 지원서")
    projects = list_projects(USER_ID)
    if projects:
        options = {
            f"{p['company']} · {p['position']}": p["id"]
            for p in projects
        }
        labels = list(options.keys())
        if st.session_state.project_id not in options.values():
            st.session_state.project_id = options[labels[0]]
        current_label = next(k for k, v in options.items() if v == st.session_state.project_id)
        selected = st.selectbox("현재 지원서", labels, index=labels.index(current_label), label_visibility="collapsed")
        new_pid = options[selected]
        if new_pid != st.session_state.project_id:
            st.session_state.project_id = new_pid
            st.session_state.workspace_step = 2 if analysis_ready(new_pid) else 1
            rerun()
    else:
        st.info("첫 지원서를 만들어주세요.")

    with st.expander("＋ 새 지원서 만들기", expanded=not bool(projects)):
        with st.form("new_project", clear_on_submit=True):
            company = st.text_input("기업명")
            position = st.text_input("지원 직무")
            team = st.text_input("지원 조직/팀", placeholder="모르면 비워도 됩니다")
            if st.form_submit_button("만들기", type="primary", use_container_width=True):
                if not company.strip() or not position.strip():
                    st.error("기업명과 지원 직무를 입력해주세요.")
                else:
                    p = create_project(USER_ID, company, position, team, "")
                    st.session_state.project_id = p["id"]
                    st.session_state.workspace_step = 1
                    rerun()

    if st.session_state.project_id:
        project = get_project(USER_ID, st.session_state.project_id)
        with st.expander("지원 정보 수정"):
            with st.form("edit_project"):
                company_e = st.text_input("기업명", value=project.get("company") or "")
                position_e = st.text_input("지원 직무", value=project.get("position") or "")
                team_e = st.text_input("지원 조직/팀", value=project.get("team") or "")
                if st.form_submit_button("저장", use_container_width=True):
                    update_project(USER_ID, project["id"], company=company_e, position=position_e, team=team_e)
                    rerun()

        with st.expander("💬 AI에게 추가 지시"):
            st.caption("예: 최근 1년 자료 중심 / AI 프로그램 경험을 강조 / 문장을 담백하게")
            extra = st.text_area("지시사항", height=90, label_visibility="collapsed")
            if st.button("지시 저장", use_container_width=True):
                try:
                    add_instruction(USER_ID, project["id"], "global", extra)
                    st.success("저장했습니다.")
                    rerun()
                except Exception as e:
                    st.error(str(e))

# =========================================================
# Header + simple top-level navigation
# =========================================================
st.markdown(
    f'<div class="app-head"><div class="app-title">📝 {APP_TITLE}</div>'
    f'<div class="app-sub">{APP_SUBTITLE} · {VERSION}</div></div>',
    unsafe_allow_html=True,
)

main_tab, profile_tab, archive_tab = st.tabs(["지원서", "내 경험", "보관함"])

# =========================================================
# 1 workspace = 1 company/role application
# =========================================================
with main_tab:
    project = require_project()
    bundle = get_analysis(USER_ID, project["id"]) or {}
    app_analysis = bundle.get("application") or {}

    st.markdown(
        f'<div class="project-line"><div><div class="project-company">{html.escape(project["company"])}</div>'
        f'<div class="project-role">{html.escape(project["position"])}{html.escape(" · " + project.get("team") if project.get("team") else "")}</div></div></div>',
        unsafe_allow_html=True,
    )

    if app_analysis and st.session_state.workspace_step == 1 and not st.session_state.get("manual_step_choice"):
        st.session_state.workspace_step = 2

    # two-step visual + click targets
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("① 지원기업 분석" + ("  ✓" if app_analysis else ""), use_container_width=True,
                     type="primary" if st.session_state.workspace_step == 1 else "secondary"):
            st.session_state.workspace_step = 1
            st.session_state.manual_step_choice = True
            rerun()
    with c2:
        if st.button("② 자소서 작성", use_container_width=True,
                     type="primary" if st.session_state.workspace_step == 2 else "secondary",
                     disabled=not bool(app_analysis)):
            st.session_state.workspace_step = 2
            st.session_state.manual_step_choice = True
            rerun()

    # -----------------------------------------------------
    # STEP 1: integrated company + role + recruiting analysis
    # -----------------------------------------------------
    if st.session_state.workspace_step == 1:
        st.markdown("## 지원기업 분석")
        st.caption("기업분석·기업 내 직무분석·실제 채용분석을 따로 보지 않고, **이 지원서에 필요한 하나의 분석**으로 묶습니다.")

        with st.expander("채용공고를 직접 가지고 있다면 추가하기 (선택)", expanded=False):
            posting_text = st.text_area("채용공고 내용", height=160, placeholder="공고 원문을 붙여넣으면 자동 웹검색 결과와 함께 분석합니다.")
            posting_url = st.text_input("채용공고 URL (선택)")
            if st.button("채용공고 저장", use_container_width=True):
                if posting_text.strip() or posting_url.strip():
                    content = posting_text.strip()
                    if posting_url.strip() and not content:
                        try:
                            content = fetch_url_text(posting_url.strip())
                        except Exception as e:
                            st.warning(f"URL 본문을 읽지 못했습니다. 공고 내용을 직접 붙여넣어주세요. ({e})")
                    if content:
                        add_source(USER_ID, project["id"], "사용자 입력 채용공고", "채용공고 원문", content, posting_url, "supported")
                        st.success("채용공고를 저장했습니다.")
                        rerun()

        sources = list_sources(USER_ID, project["id"])
        has_sources = bool(sources)
        button_label = "지원기업 분석 시작" if not app_analysis else "최신 자료 확인 후 다시 분석"
        force_refresh = st.checkbox("웹 자료를 강제로 새로 검색", value=False, help="평소에는 체크하지 않아도 됩니다. 저장된 캐시를 우선 재사용합니다.")

        if st.button(button_label, type="primary", use_container_width=True):
            try:
                if not recruiting_search_available() and not has_sources:
                    raise RuntimeError("TAVILY_API_KEY가 없고 저장된 자료도 없습니다. Streamlit Secrets에 Tavily 키를 등록해주세요.")

                with st.status("지원기업 자료를 확인하고 있습니다...", expanded=True) as status:
                    if recruiting_search_available():
                        st.write("기업·최근 이슈 자료를 확인합니다.")
                        company_research = research_company_sources(
                            project["company"], user_id=USER_ID, project_id=project["id"], force_refresh=force_refresh
                        )
                        save_auto_research_results(USER_ID, project["id"], company_research.get("results") or [])

                        st.write("채용공고·직무·지원조직 자료를 확인합니다.")
                        job_research = research_job_sources(
                            project["company"], project["position"], project.get("team") or "",
                            user_id=USER_ID, project_id=project["id"], force_refresh=force_refresh,
                        )
                        save_auto_research_results(USER_ID, project["id"], job_research.get("results") or [])

                    sources = list_sources(USER_ID, project["id"])
                    st.write("기업·직무·채용정보를 하나의 지원 맥락으로 분석합니다.")
                    result = run_application_analysis(USER_ID, project, sources)
                    status.update(label="지원기업 분석이 완료됐습니다.", state="complete", expanded=False)
                    st.session_state.analysis_ai_failed = False
                    st.session_state.workspace_step = 2
                    st.session_state.manual_step_choice = False
                    rerun()
            except Exception as e:
                st.session_state.analysis_ai_failed = True
                render_ai_error(e)

        # Gemini 503/429 after research: retry analysis only, no Tavily call
        if st.session_state.analysis_ai_failed and list_sources(USER_ID, project["id"]):
            if st.button("AI 분석만 다시 시도 (웹검색 없음)", use_container_width=True):
                try:
                    with st.spinner("저장된 근거로 AI 분석만 다시 시도하고 있습니다..."):
                        run_application_analysis(USER_ID, project, list_sources(USER_ID, project["id"]))
                    st.session_state.analysis_ai_failed = False
                    st.session_state.workspace_step = 2
                    st.session_state.manual_step_choice = False
                    rerun()
                except Exception as e:
                    render_ai_error(e)

        if app_analysis:
            st.divider()
            st.markdown("### 분석 요약")
            company_data = app_analysis.get("company") or {}
            job_data = app_analysis.get("job") or {}
            recruiting = app_analysis.get("recruiting") or {}
            summary = app_analysis.get("application_summary") or {}

            cols = st.columns(3, gap="medium")
            with cols[0]:
                with st.container(border=True):
                    st.caption("COMPANY")
                    st.markdown("**기업 핵심**")
                    st.write(company_data.get("business_summary") or summary.get("one_line") or "-")
                    _bullets(company_data.get("recent_changes"), 3)
            with cols[1]:
                with st.container(border=True):
                    st.caption("ROLE")
                    st.markdown("**직무 핵심**")
                    st.write(job_data.get("posting_summary") or "-")
                    _bullets(job_data.get("core_tasks"), 3)
            with cols[2]:
                with st.container(border=True):
                    st.caption("HIRING")
                    st.markdown("**채용 핵심**")
                    _bullets(recruiting.get("must_show_in_essay") or summary.get("top_essay_messages"), 4)

            with st.expander("분석 근거와 주의사항 자세히 보기"):
                st.markdown("**자소서에 활용할 기업 사실**")
                _bullets(summary.get("top_company_facts") or company_data.get("essay_specific_points"), 8)
                st.markdown("**핵심 직무 요구**")
                _bullets(summary.get("top_job_requirements") or job_data.get("behavior_competencies"), 8)
                st.markdown("**과장하면 안 되는 부분**")
                _bullets((company_data.get("what_not_to_use") or []) + (job_data.get("what_not_to_claim") or []), 8)

            if st.button("이 분석으로 자소서 작성하기 →", type="primary", use_container_width=True):
                st.session_state.workspace_step = 2
                st.session_state.manual_step_choice = True
                rerun()

    # -----------------------------------------------------
    # STEP 2: essay workspace
    # -----------------------------------------------------
    else:
        if not app_analysis:
            st.warning("먼저 지원기업 분석을 완료해주세요.")
            if st.button("지원기업 분석으로 이동", use_container_width=True):
                set_workspace_step(1)
                rerun()
            st.stop()

        st.markdown("## 자소서 작성")
        st.caption("문항 전체를 먼저 분석하고 소재를 배분한 뒤, 문항별로 **내가 하고 싶은 말 + 실제 경험 + 기업·직무 근거**를 연결합니다.")

        summary = app_analysis.get("application_summary") or {}
        if summary.get("top_essay_messages"):
            with st.expander("이번 지원서에서 기억할 핵심", expanded=False):
                _bullets(summary.get("top_essay_messages"), 5)

        questions = list_questions(USER_ID, project["id"])
        profile = get_candidate_profile(USER_ID)
        experiences = list_experiences(USER_ID)
        allocation = get_allocation(USER_ID, project["id"])

        with st.expander("＋ 자소서 문항 추가", expanded=not bool(questions)):
            with st.form("add_question", clear_on_submit=True):
                qtext = st.text_area("자소서 문항", height=100)
                qcol1, qcol2 = st.columns([0.28, 0.72])
                char_limit = qcol1.number_input("글자수", min_value=0, max_value=5000, value=0, step=50)
                user_message = qcol2.text_area("내가 하고 싶은 말 (선택)", height=90, placeholder="예: 데이터분석을 배우고 AI 업무지원 프로그램을 직접 만든 경험을 꼭 살리고 싶다.")
                if st.form_submit_button("문항 추가", type="primary", use_container_width=True):
                    if not qtext.strip():
                        st.error("문항을 입력해주세요.")
                    else:
                        add_question(USER_ID, project["id"], qtext, int(char_limit), user_message, "")
                        rerun()

        if not questions:
            st.info("자소서 문항을 모두 추가해주세요. 문항 전체를 함께 본 뒤 중복되지 않게 소재를 배분합니다.")
            st.stop()

        # compact question list
        st.markdown("### 문항")
        for idx, q in enumerate(questions, start=1):
            final = latest_final(USER_ID, project["id"], q["id"])
            state = "최종본 완료" if final else ("분석 완료" if q.get("analysis") else "분석 전")
            st.markdown(
                f'<div class="question-card"><div class="q-num">Q{idx}</div><div class="q-text">{html.escape(q["question_text"])}</div>'
                f'<div class="q-meta">{q.get("char_limit") or "제한 없음"}{"자" if q.get("char_limit") else ""} · {state}</div></div>',
                unsafe_allow_html=True,
            )

        with st.expander("문항 수정/삭제", expanded=False):
            edit_labels = {f"Q{i+1}. {q['question_text'][:50]}": q for i, q in enumerate(questions)}
            edit_label = st.selectbox("수정할 문항", list(edit_labels.keys()), key="edit_question_select")
            eq = edit_labels[edit_label]
            e_text = st.text_area("문항", value=eq.get("question_text") or "", height=90, key=f"eqt_{eq['id']}")
            e_limit = st.number_input("글자수", min_value=0, max_value=5000, value=int(eq.get("char_limit") or 0), step=50, key=f"eql_{eq['id']}")
            e_msg = st.text_area("내가 하고 싶은 말", value=eq.get("user_message") or "", height=90, key=f"eqm_{eq['id']}")
            ec1, ec2 = st.columns(2)
            if ec1.button("수정 저장", use_container_width=True):
                update_question(USER_ID, project["id"], eq["id"], question_text=e_text, char_limit=int(e_limit), user_message=e_msg, analysis={})
                save_allocation(USER_ID, project["id"], {})
                rerun()
            if ec2.button("문항 삭제", use_container_width=True):
                delete_question(USER_ID, project["id"], eq["id"])
                save_allocation(USER_ID, project["id"], {})
                rerun()

        all_analyzed = all(bool(q.get("analysis")) for q in questions)
        if st.button("전체 문항 분석 + 소재 배분" if not allocation else "문항 분석·소재 배분 다시 하기",
                     type="primary", use_container_width=True):
            if not experiences:
                st.error("먼저 '내 경험'에서 이력서 또는 경험을 등록해주세요.")
            else:
                try:
                    company_data = app_analysis.get("company") or {}
                    job_data = app_analysis.get("job") or {}
                    with st.status("문항을 냉정하게 분석하고 소재를 배분하고 있습니다...", expanded=True) as status:
                        for idx, q in enumerate(questions, start=1):
                            st.write(f"Q{idx} 문항 의도와 필수조건 분석")
                            ins = instruction_context(USER_ID, project["id"], "essay", q["id"])
                            qa = generate_json(question_analysis_prompt(
                                q, company_data, job_data, q.get("user_message") or "", ins
                            ))
                            update_question(USER_ID, project["id"], q["id"], analysis=qa)
                        refreshed = list_questions(USER_ID, project["id"])
                        st.write("전체 문항을 함께 보고 경험·전공·자격·배경의 중복을 사전에 차단")
                        alloc = generate_json(allocation_prompt(
                            refreshed,
                            [exp_view(x) for x in experiences],
                            company_data, job_data,
                            instruction_context(USER_ID, project["id"], "essay"),
                        ))
                        save_allocation(USER_ID, project["id"], alloc)
                        status.update(label="문항 분석과 소재 배분이 완료됐습니다.", state="complete", expanded=False)
                    rerun()
                except Exception as e:
                    render_ai_error(e)

        questions = list_questions(USER_ID, project["id"])
        allocation = get_allocation(USER_ID, project["id"])
        if not allocation:
            st.info("위 버튼을 눌러 문항 분석과 소재 배분을 먼저 완료해주세요.")
            st.stop()

        st.divider()
        qlabels = {f"Q{i+1}. {q['question_text'][:58]}": q for i, q in enumerate(questions)}
        selected_label = st.selectbox("작성할 문항", list(qlabels.keys()), key="essay_question_select")
        q = qlabels[selected_label]
        qa = q.get("analysis") or {}
        alloc = get_alloc_for_question(allocation, q["id"])
        gate = alloc.get("requirement_gate") or {}
        selected_exp = find_exp(experiences, alloc.get("primary_experience_id"))

        # editable user intent stays visible
        current_msg = st.text_area(
            "내가 하고 싶은 말",
            value=q.get("user_message") or "",
            height=92,
            help="이 내용은 버리는 후보 소재가 아니라, 이번 문항에서 반드시 살려야 할 사용자 의도로 처리됩니다.",
            key=f"user_message_live_{q['id']}",
        )
        if current_msg != (q.get("user_message") or ""):
            if st.button("하고 싶은 말 저장", use_container_width=True, key=f"save_msg_{q['id']}"):
                update_question(USER_ID, project["id"], q["id"], user_message=current_msg, analysis={})
                save_allocation(USER_ID, project["id"], {})
                st.success("저장했습니다. 문항 분석·소재 배분을 다시 실행해주세요.")
                rerun()

        st.markdown("### AI가 잡은 작성 방향")
        cards = st.columns(4, gap="small")
        card_values = [
            ("채용자가 보는 것", qa.get("one_line_intent") or qa.get("recruiter_is_testing") or "-"),
            ("반드시 답할 것", " / ".join(_short_list(qa.get("must_answer_elements"), 3)) or "-"),
            ("추천 경험", selected_exp.get("title") or "추가 경험 필요"),
            ("확인 필요", " / ".join(_short_list(gate.get("missing"), 3)) or "없음"),
        ]
        for col, (label, value) in zip(cards, card_values):
            col.markdown(
                f'<div class="section-card"><div class="section-kicker">{html.escape(str(label))}</div><div class="section-body">{html.escape(str(value))}</div></div>',
                unsafe_allow_html=True,
            )

        gate_status = (gate.get("status") or "gap").lower()
        if gate_status == "pass":
            st.markdown('<div class="good">문항의 핵심 조건을 충족하는 소재가 확인됐습니다.</div>', unsafe_allow_html=True)
        elif gate_status == "partial":
            st.markdown('<div class="warn">작성은 가능하지만 일부 사실을 보완하면 더 강해집니다.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="bad">현재 자료만으로는 문항의 핵심 조건을 충족하지 못합니다.</div>', unsafe_allow_html=True)
            for item in gate.get("gap_questions", []) or []:
                st.warning(item)

        if st.button("이 문항 자소서 완성하기", type="primary", use_container_width=True, disabled=gate_status == "gap"):
            try:
                result = generate_complete_essay(project, q, allocation, experiences, profile)
                if result.get("needs_information"):
                    draft = result["needs_information"]
                    st.warning("추가 사실이 필요합니다.")
                    for x in draft.get("needs_confirmation", []) or []:
                        st.write("•", x)
                else:
                    rerun()
            except Exception as e:
                render_ai_error(e)

        final_row = latest_final(USER_ID, project["id"], q["id"])
        if final_row:
            st.divider()
            st.markdown("### 최종본")
            title = final_row.get("title") or "소제목"
            st.markdown(f"#### [{title}]")
            final_text = st.text_area("최종 자소서", value=final_row.get("content") or "", height=420, key=f"final_text_{q['id']}")
            cc1, cc2 = st.columns(2)
            cc1.metric("현재 글자수", len(final_text))
            cc2.metric("글자수 제한", q.get("char_limit") or "없음")

            lc = local_repetition_report(final_text, [m for p in prior_used_materials(USER_ID, project["id"], q["id"]) for m in p.get("used_materials", [])])
            if lc.get("ai_tone_hits") or lc.get("reused_facts"):
                with st.expander("빠른 중복·AI 말투 점검"):
                    st.json(lc)

            b1, b2 = st.columns(2)
            if b1.button("직접 수정한 내용 저장", use_container_width=True):
                save_draft(USER_ID, project["id"], q["id"], "final", final_text, final_row.get("used_materials") or [], title=title)
                st.success("수정본을 저장했습니다.")
            with b2:
                with st.popover("AI에게 수정 지시"):
                    rewrite = st.text_area("수정 방향", placeholder="예: 첫 문단을 더 담백하게 / 내 행동을 더 선명하게 / 이 문장은 빼줘", height=100, key=f"rewrite_{q['id']}")
                    if st.button("지시 저장 후 다시 작성", use_container_width=True, key=f"rewrite_btn_{q['id']}"):
                        update_question(USER_ID, project["id"], q["id"], custom_instruction=rewrite)
                        st.success("지시를 저장했습니다. 창을 닫고 '이 문항 자소서 완성하기'를 다시 눌러주세요.")

            with st.expander("AI 검토 결과 자세히 보기"):
                st.json(final_row.get("review") or {})

# =========================================================
# Personal vault
# =========================================================
with profile_tab:
    st.markdown("## 내 경험")
    st.caption("이력서와 경험은 한 번 저장하면 모든 지원서에서 재사용됩니다.")
    profile = get_candidate_profile(USER_ID)

    p1, p2 = st.columns([1.15, 0.85], gap="large")
    with p1:
        st.markdown("### 이력서·프로필")
        uploaded = st.file_uploader("이력서/경력기술서", type=["pdf", "docx", "txt", "md"])
        if st.button("이력서 분석·저장", type="primary", use_container_width=True, disabled=uploaded is None):
            try:
                raw = extract_text(uploaded)
                with st.spinner("이력과 경험을 구조화하고 있습니다..."):
                    structured = generate_json(candidate_structure_prompt(raw, []))
                save_candidate_profile(USER_ID, raw, structured, profile.get("style_sample") or "")
                added = sync_profile_experiences(USER_ID, structured)
                st.success(f"프로필을 저장했습니다. 경험 DB에 새 경험 {added}개를 반영했습니다.")
                rerun()
            except Exception as e:
                render_ai_error(e)

        if profile.get("structured"):
            with st.expander("저장된 프로필 보기"):
                st.json(profile.get("structured") or {})

        st.markdown("### 내 문체")
        style = st.text_area("내가 자연스럽다고 느끼는 문장 샘플", value=profile.get("style_sample") or "", height=120)
        if st.button("문체 저장", use_container_width=True):
            save_candidate_profile(USER_ID, profile.get("raw_text") or "", profile.get("structured") or {}, style)
            st.success("문체 샘플을 저장했습니다.")

    with p2:
        st.markdown("### 경험 추가")
        raw_exp = st.text_area("경험을 편하게 적어주세요", height=180, placeholder="상황, 문제, 내가 한 판단과 행동, 결과를 자유롭게 적으면 됩니다.")
        if st.button("경험 분석·저장", type="primary", use_container_width=True):
            if not raw_exp.strip():
                st.error("경험을 입력해주세요.")
            else:
                try:
                    with st.spinner("경험에서 문제·판단·행동·결과를 구조화하고 있습니다..."):
                        s = generate_json(experience_structure_prompt(raw_exp, []))
                    add_experience(USER_ID, raw_exp, s)
                    st.success("경험 DB에 저장했습니다.")
                    rerun()
                except Exception as e:
                    render_ai_error(e)

        experiences = list_experiences(USER_ID)
        st.markdown(f"### 저장된 경험 {len(experiences)}개")
        for exp in experiences:
            s = exp.get("structured") or {}
            with st.expander(exp.get("title") or "경험"):
                if s.get("my_role"):
                    st.write("**내 역할**", s.get("my_role"))
                if s.get("problem"):
                    st.write("**문제**", s.get("problem"))
                if s.get("initial_judgment"):
                    st.write("**판단**", s.get("initial_judgment"))
                if s.get("initial_action"):
                    st.write("**행동**", s.get("initial_action"))
                if s.get("result"):
                    st.write("**결과**", s.get("result"))
                if s.get("missing_questions"):
                    st.caption("보완하면 좋은 정보")
                    _bullets(s.get("missing_questions"), 5)

# =========================================================
# Archive: details only, out of the main flow
# =========================================================
with archive_tab:
    project = require_project()
    st.markdown("## 보관함")
    st.caption("최종 자소서, 분석 근거, 검색자료, AI 지시 이력은 여기에서만 확인합니다.")

    a1, a2, a3 = st.tabs(["자소서 저장본", "분석 근거", "AI 지시"])
    with a1:
        questions = list_questions(USER_ID, project["id"])
        drafts = list_drafts(USER_ID, project["id"])
        if not drafts:
            st.info("저장된 자소서가 없습니다.")
        else:
            qmap = {str(q["id"]): q for q in questions}
            for d in drafts:
                q = qmap.get(str(d.get("question_id"))) or {}
                label = f"{d.get('draft_type')} · {(q.get('question_text') or '')[:45]} · {(d.get('created_at') or '')[:16]}"
                with st.expander(label):
                    if d.get("title"):
                        st.markdown(f"**[{d['title']}]**")
                    st.write(d.get("content") or "")

    with a2:
        usage = get_monthly_research_usage(USER_ID)
        m1, m2, m3 = st.columns(3)
        m1.metric("이번 달 웹검색", f"{usage.get('searches', 0)}회")
        m2.metric("예상 Tavily credits", usage.get("credits", 0))
        m3.metric("캐시 재사용", f"{usage.get('cache_hits', 0)}회")

        bundle = get_analysis(USER_ID, project["id"]) or {}
        with st.expander("통합 지원기업 분석 원본"):
            st.json(bundle.get("application") or {})

        sources = list_sources(USER_ID, project["id"])
        st.markdown(f"### 저장된 웹·채용 근거 {len(sources)}개")
        for s in sources:
            title = s.get("title") or s.get("source_type") or "자료"
            with st.expander(title):
                st.caption(f"{s.get('source_type')} · {s.get('trust_level')}")
                if s.get("url"):
                    st.write(s.get("url"))
                st.write((s.get("content") or "")[:5000])
                if st.button("이 자료 삭제", key=f"del_source_{s['id']}"):
                    delete_source(USER_ID, project["id"], s["id"])
                    rerun()

        with st.expander("근거 직접 추가"):
            source_type = st.text_input("자료 유형", value="추가 자료")
            source_title = st.text_input("제목")
            source_url = st.text_input("URL")
            source_text = st.text_area("내용", height=150)
            if st.button("근거 저장", use_container_width=True):
                content = source_text.strip()
                if source_url.strip() and not content:
                    try:
                        content = fetch_url_text(source_url.strip())
                    except Exception as e:
                        st.error(f"URL 본문을 읽지 못했습니다: {e}")
                if content:
                    add_source(USER_ID, project["id"], source_type, source_title or source_type, content, source_url, "supported")
                    rerun()

    with a3:
        instructions = list_instructions(USER_ID, project["id"], active_only=True)
        if not instructions:
            st.info("활성화된 AI 지시가 없습니다.")
        for ins in instructions:
            with st.container(border=True):
                st.caption(ins.get("scope") or "global")
                st.write(ins.get("instruction") or "")
                if st.button("이 지시 사용 중지", key=f"deact_{ins['id']}"):
                    deactivate_instruction(USER_ID, project["id"], ins["id"])
                    rerun()
