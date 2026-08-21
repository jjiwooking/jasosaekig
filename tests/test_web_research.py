import sys
import types

# Minimal stub so this pure helper test does not require Streamlit installed.
st = types.SimpleNamespace(secrets={})
sys.modules.setdefault("streamlit", st)

from modules.recruiting_search import _normalize


def test_tavily_results_are_normalized():
    rows = _normalize({
        "results": [{
            "title": "ALIO 채용자료",
            "url": "https://www.alio.go.kr/example",
            "content": "채용 근거",
            "raw_content": "상세 채용 근거",
            "score": 0.9,
        }]
    })
    assert len(rows) == 1
    assert rows[0]["url"] == "https://www.alio.go.kr/example"
    assert rows[0]["trust_level"] == "official"
