from __future__ import annotations

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    )
}


def fetch_url_text(url: str, timeout: int = 15) -> dict:
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("http 또는 https URL을 입력해주세요.")

    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise ValueError("HTML 페이지가 아닙니다. 해당 자료는 본문 붙여넣기를 이용해주세요.")

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "canvas", "form"]):
        tag.decompose()

    title = (soup.title.string.strip() if soup.title and soup.title.string else parsed.netloc)
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 지나치게 큰 페이지는 프롬프트 비용과 오류를 줄이기 위해 상한을 둔다.
    if len(text) > 50000:
        text = text[:50000] + "\n...[본문 일부 생략]"

    return {
        "url": url,
        "title": title,
        "text": text.strip(),
        "domain": parsed.netloc,
    }
