from pathlib import Path
from modules.prompts import application_analysis_prompt


def test_integrated_application_prompt_has_three_analysis_layers():
    text = application_analysis_prompt("테스트회사", "사무", "", [], [])
    assert '"company"' in text
    assert '"job"' in text
    assert '"recruiting"' in text
    assert '"application_summary"' in text
    assert "하나의 지원 맥락" in text


def test_no_unverified_default_fallback_models():
    src = (Path(__file__).parents[1] / "modules" / "ai_client.py").read_text(encoding="utf-8")
    assert 'DEFAULT_FALLBACKS = []' in src
