from __future__ import annotations

import bcrypt

from modules.supabase_client import get_supabase


def _one(data):
    return (data or [None])[0]


def _clean_username(username: str) -> str:
    return (username or "").strip().lower()


# ---------------- Authentication ----------------
def register_user(username: str, password: str, display_name: str = "") -> dict:
    username = _clean_username(username)
    if len(username) < 3:
        raise ValueError("아이디는 3자 이상 입력해주세요.")
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상 입력해주세요.")

    sb = get_supabase()
    exists = sb.table("app_users").select("id").eq("username", username).execute().data
    if exists:
        raise ValueError("이미 사용 중인 아이디입니다.")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    row = {
        "username": username,
        "display_name": (display_name or username).strip(),
        "password_hash": password_hash,
    }
    return _one(sb.table("app_users").insert(row).execute().data)


def authenticate_user(username: str, password: str) -> dict | None:
    username = _clean_username(username)
    rows = get_supabase().table("app_users").select(
        "id,username,display_name,password_hash"
    ).eq("username", username).limit(1).execute().data or []
    if not rows:
        return None
    user = rows[0]
    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8"))
    except Exception:
        ok = False
    if not ok:
        return None
    user.pop("password_hash", None)
    return user


# ---------------- Projects ----------------
def create_project(user_id: str, company: str, position: str, team: str = "", deadline: str = "") -> dict:
    row = {
        "user_id": user_id,
        "company": company.strip(),
        "position": position.strip(),
        "team": team.strip() or None,
        "deadline": deadline or None,
        "status": "준비중",
    }
    return _one(get_supabase().table("application_projects").insert(row).execute().data)


def list_projects(user_id: str) -> list[dict]:
    return get_supabase().table("application_projects").select("*").eq(
        "user_id", user_id
    ).order("updated_at", desc=True).execute().data or []


def get_project(user_id: str, project_id: str) -> dict | None:
    rows = get_supabase().table("application_projects").select("*").eq(
        "user_id", user_id
    ).eq("id", project_id).limit(1).execute().data or []
    return _one(rows)


def update_project(user_id: str, project_id: str, **fields) -> None:
    allowed = {"company", "position", "team", "deadline", "status", "notes"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if fields:
        get_supabase().table("application_projects").update(fields).eq("user_id", user_id).eq("id", project_id).execute()


# ---------------- Candidate profile ----------------
def get_candidate_profile(user_id: str) -> dict:
    rows = get_supabase().table("candidate_profiles").select("*").eq(
        "user_id", user_id
    ).limit(1).execute().data or []
    return _one(rows) or {}


def save_candidate_profile(user_id: str, raw_text: str, structured: dict, style_sample: str = "") -> dict:
    payload = {
        "user_id": user_id,
        "raw_text": raw_text,
        "structured": structured,
        "style_sample": style_sample,
    }
    existing = get_candidate_profile(user_id)
    if existing:
        return _one(get_supabase().table("candidate_profiles").update(payload).eq("user_id", user_id).execute().data)
    return _one(get_supabase().table("candidate_profiles").insert(payload).execute().data)


# ---------------- Experiences ----------------
def add_experience(user_id: str, raw_text: str, structured: dict) -> dict:
    row = {
        "user_id": user_id,
        "title": structured.get("title") or "경험",
        "raw_text": raw_text,
        "structured": structured,
        "fact_status": structured.get("fact_status") or "verified",
    }
    return _one(get_supabase().table("experiences").insert(row).execute().data)


def list_experiences(user_id: str) -> list[dict]:
    return get_supabase().table("experiences").select("*").eq(
        "user_id", user_id
    ).order("created_at", desc=True).execute().data or []


def update_experience(user_id: str, experience_id: str, structured: dict) -> None:
    get_supabase().table("experiences").update({
        "title": structured.get("title") or "경험",
        "structured": structured,
        "fact_status": structured.get("fact_status") or "verified",
    }).eq("user_id", user_id).eq("id", experience_id).execute()


# ---------------- Sources ----------------
def add_source(
    user_id: str,
    project_id: str,
    source_type: str,
    title: str,
    content: str,
    url: str = "",
    trust_level: str = "supported",
) -> dict:
    row = {
        "user_id": user_id,
        "project_id": project_id,
        "source_type": source_type,
        "title": title.strip() or source_type,
        "url": url.strip() or None,
        "content": content,
        "trust_level": trust_level,
    }
    return _one(get_supabase().table("project_sources").insert(row).execute().data)


def list_sources(user_id: str, project_id: str) -> list[dict]:
    return get_supabase().table("project_sources").select("*").eq(
        "user_id", user_id
    ).eq("project_id", project_id).order("created_at").execute().data or []


def delete_source(user_id: str, project_id: str, source_id: str) -> None:
    get_supabase().table("project_sources").delete().eq("user_id", user_id).eq(
        "project_id", project_id
    ).eq("id", source_id).execute()


# ---------------- Analyses: one JSON record, separate sections ----------------
def get_analysis(user_id: str, project_id: str) -> dict:
    rows = get_supabase().table("project_analyses").select("analysis").eq(
        "user_id", user_id
    ).eq("project_id", project_id).limit(1).execute().data or []
    return (rows[0].get("analysis") if rows else {}) or {}


def save_analysis(user_id: str, project_id: str, analysis: dict) -> dict:
    row = {"user_id": user_id, "project_id": project_id, "analysis": analysis}
    existing = get_supabase().table("project_analyses").select("id").eq(
        "user_id", user_id
    ).eq("project_id", project_id).execute().data or []
    if existing:
        return _one(get_supabase().table("project_analyses").update(row).eq("id", existing[0]["id"]).execute().data)
    return _one(get_supabase().table("project_analyses").insert(row).execute().data)


def save_analysis_section(user_id: str, project_id: str, section: str, data: dict) -> dict:
    analysis = get_analysis(user_id, project_id)
    analysis[section] = data
    return save_analysis(user_id, project_id, analysis)


# ---------------- Essay questions ----------------
def add_question(
    user_id: str,
    project_id: str,
    question_text: str,
    char_limit: int = 0,
    user_message: str = "",
    custom_instruction: str = "",
) -> dict:
    row = {
        "user_id": user_id,
        "project_id": project_id,
        "question_text": question_text.strip(),
        "char_limit": int(char_limit or 0),
        "user_message": user_message.strip() or None,
        "custom_instruction": custom_instruction.strip() or None,
        "analysis": {},
    }
    return _one(get_supabase().table("essay_questions").insert(row).execute().data)


def list_questions(user_id: str, project_id: str) -> list[dict]:
    return get_supabase().table("essay_questions").select("*").eq(
        "user_id", user_id
    ).eq("project_id", project_id).order("created_at").execute().data or []


def update_question(
    user_id: str,
    project_id: str,
    question_id: str,
    **fields,
) -> None:
    allowed = {"question_text", "char_limit", "user_message", "custom_instruction", "analysis"}
    payload = {k: v for k, v in fields.items() if k in allowed}
    if payload:
        get_supabase().table("essay_questions").update(payload).eq("user_id", user_id).eq(
            "project_id", project_id
        ).eq("id", question_id).execute()


def delete_question(user_id: str, project_id: str, question_id: str) -> None:
    get_supabase().table("essay_questions").delete().eq("user_id", user_id).eq(
        "project_id", project_id
    ).eq("id", question_id).execute()


# ---------------- Content allocation ----------------
def save_allocation(user_id: str, project_id: str, allocation: dict) -> dict:
    row = {"user_id": user_id, "project_id": project_id, "allocation": allocation}
    existing = get_supabase().table("content_allocations").select("id").eq(
        "user_id", user_id
    ).eq("project_id", project_id).execute().data or []
    if existing:
        return _one(get_supabase().table("content_allocations").update(row).eq("id", existing[0]["id"]).execute().data)
    return _one(get_supabase().table("content_allocations").insert(row).execute().data)


def get_allocation(user_id: str, project_id: str) -> dict:
    rows = get_supabase().table("content_allocations").select("allocation").eq(
        "user_id", user_id
    ).eq("project_id", project_id).limit(1).execute().data or []
    return (rows[0].get("allocation") if rows else {}) or {}


# ---------------- Drafts / usage ----------------
def save_draft(
    user_id: str,
    project_id: str,
    question_id: str,
    draft_type: str,
    content: str,
    used_materials: list[str] | None = None,
    review: dict | None = None,
    title: str = "",
) -> dict:
    row = {
        "user_id": user_id,
        "project_id": project_id,
        "question_id": question_id,
        "draft_type": draft_type,
        "content": content,
        "used_materials": used_materials or [],
        "review": review or {},
        "title": title.strip() or None,
    }
    return _one(get_supabase().table("essay_drafts").insert(row).execute().data)


def list_drafts(user_id: str, project_id: str, question_id: str | None = None) -> list[dict]:
    q = get_supabase().table("essay_drafts").select("*").eq("user_id", user_id).eq("project_id", project_id)
    if question_id:
        q = q.eq("question_id", question_id)
    return q.order("created_at", desc=True).execute().data or []


def prior_used_materials(user_id: str, project_id: str, exclude_question_id: str | None = None) -> list[dict]:
    rows = list_drafts(user_id, project_id)
    result = []
    for row in rows:
        if exclude_question_id and str(row.get("question_id")) == str(exclude_question_id):
            continue
        materials = row.get("used_materials") or []
        if materials:
            result.append({
                "question_id": row.get("question_id"),
                "used_materials": materials,
                "draft_type": row.get("draft_type"),
            })
    return result


# ---------------- User prompt instructions ----------------
def add_instruction(
    user_id: str,
    project_id: str,
    scope: str,
    instruction: str,
    question_id: str | None = None,
) -> dict:
    if not (instruction or "").strip():
        raise ValueError("지시사항을 입력해주세요.")
    row = {
        "user_id": user_id,
        "project_id": project_id,
        "scope": scope,
        "question_id": question_id,
        "instruction": instruction.strip(),
        "active": True,
    }
    return _one(get_supabase().table("prompt_instructions").insert(row).execute().data)


def list_instructions(
    user_id: str,
    project_id: str,
    scope: str | None = None,
    question_id: str | None = None,
    active_only: bool = True,
) -> list[dict]:
    q = get_supabase().table("prompt_instructions").select("*").eq("user_id", user_id).eq(
        "project_id", project_id
    )
    if scope:
        q = q.eq("scope", scope)
    if question_id:
        q = q.eq("question_id", question_id)
    if active_only:
        q = q.eq("active", True)
    return q.order("created_at").execute().data or []


def instruction_context(
    user_id: str,
    project_id: str,
    scope: str,
    question_id: str | None = None,
) -> list[dict]:
    """Project-global + current scope + optional question instructions in chronological order."""
    rows = list_instructions(user_id, project_id, active_only=True)
    allowed = {"global", scope}
    result = []
    for row in rows:
        row_scope = row.get("scope")
        row_qid = row.get("question_id")
        if row_scope not in allowed:
            continue
        if row_qid and question_id and str(row_qid) != str(question_id):
            continue
        if row_qid and not question_id:
            continue
        result.append(row)
    return result


def deactivate_instruction(user_id: str, project_id: str, instruction_id: str) -> None:
    get_supabase().table("prompt_instructions").update({"active": False}).eq("user_id", user_id).eq(
        "project_id", project_id
    ).eq("id", instruction_id).execute()
