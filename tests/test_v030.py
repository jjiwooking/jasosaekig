import os

from modules.ai_client import _error_code, get_fallback_models
from modules.prompts import QUESTION_STRATEGIES, question_analysis_prompt, recruiter_review_prompt, fact_check_prompt, final_edit_prompt


def test_transient_error_code_parsing():
    assert _error_code(Exception("503 UNAVAILABLE high demand")) == 503
    assert _error_code(Exception("429 RESOURCE_EXHAUSTED")) == 429


def test_default_fallback_models_are_production_models():
    os.environ.pop("GEMINI_FALLBACK_MODELS", None)
    values = get_fallback_models()
    assert "gemini-3.5-flash" in values
    assert "gemini-3.5-flash-lite" in values


def test_question_strategy_catalog_is_comprehensive():
    required = {
        "support_motivation", "job_competency", "problem_solving", "collaboration", "conflict",
        "challenge_achievement", "failure", "growth_values", "strength_weakness", "future_plan",
        "industry_issue", "public_ethics", "freeform", "compound",
    }
    assert required.issubset(set(QUESTION_STRATEGIES))
    prompt = question_analysis_prompt(
        {"question_text": "지원동기와 입사 후 포부를 작성하세요", "char_limit": 700}, {}, {}, "AI 업무개선 경험을 강조", []
    )
    assert "strategy_ids" in prompt
    assert "복합문항" in prompt
    assert "정확하고 냉정" in prompt


def test_review_is_separated_into_three_roles():
    common_q = {"question_text": "문제해결 경험", "char_limit": 700}
    qa = {"strategy_ids": ["problem_solving"]}
    recruiter = recruiter_review_prompt("초안", common_q, qa, {}, {}, {}, "", [])
    fact = fact_check_prompt("초안", common_q, {}, {}, {}, {}, [])
    final = final_edit_prompt("초안", common_q, qa, {}, {}, "", "", [])
    assert "수정문은 만들지 않는다" in recruiter
    assert "사실성만 검사" in fact
    assert "새 사실을 추가하지 말고" in final
