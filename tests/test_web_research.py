from modules.recruiting_search import _research_to_results


def test_research_to_results_keeps_synthesis_and_citations():
    research = {
        "text": "회사 공식 홈페이지와 공시를 확인한 리서치 메모",
        "sources": [
            {
                "title": "example.com",
                "url": "https://example.com/a",
                "content": "근거 문장",
                "snippet": "근거 문장",
                "trust_level": "supported",
            }
        ],
    }
    rows = _research_to_results(research, "테스트 기업 리서치", "자동 기업 리서치")
    assert len(rows) == 2
    assert rows[0]["is_synthesis"] is True
    assert rows[1]["url"] == "https://example.com/a"
