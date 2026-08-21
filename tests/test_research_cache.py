from modules.recruiting_search import _cache_key


def test_same_company_cache_key_is_stable():
    a = _cache_key("company", "한국전력거래소", extra="18")
    b = _cache_key("company", "  한국전력거래소  ", extra="18")
    assert a == b


def test_job_cache_key_changes_by_position():
    a = _cache_key("job", "회사A", "재무", "")
    b = _cache_key("job", "회사A", "인사", "")
    assert a != b
