from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


AI_TONE_PATTERNS = [
    "라고 생각합니다",
    "이를 통해",
    "나아가",
    "깊이 공감",
    "큰 매력을 느꼈",
    "열정을 가지고",
    "끊임없이 성장",
    "혁신적인",
    "탁월한",
    "차별화된 역량",
    "시너지를 창출",
    "역량을 발휘",
    "기여하는 인재",
    "성장하는 인재",
    "귀사의 발전에 기여",
]


def normalize_fact(text: str) -> str:
    text = re.sub(r"\s+", "", (text or "").lower())
    text = re.sub(r"[^0-9a-z가-힣]", "", text)
    return text


def local_repetition_report(text: str, used_facts: Iterable[str] | None = None) -> dict:
    text = text or ""
    used_facts = list(used_facts or [])

    tone_hits = {
        pattern: text.count(pattern)
        for pattern in AI_TONE_PATTERNS
        if text.count(pattern) > 0
    }

    endings = re.findall(r"([가-힣A-Za-z0-9]+(?:했습니다|였습니다|합니다|됩니다|있습니다|생각합니다))[.!?]?", text)
    ending_counts = Counter(endings)

    semantic_reuse = []
    normalized_text = normalize_fact(text)
    for fact in used_facts:
        nf = normalize_fact(fact)
        if nf and len(nf) >= 5 and nf in normalized_text:
            semantic_reuse.append(fact)

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    starts = [re.sub(r"\s+", " ", p[:35]) for p in paragraphs]

    return {
        "ai_tone_hits": tone_hits,
        "reused_facts": semantic_reuse,
        "paragraph_starts": starts,
        "length": len(text),
        "repeated_endings": {k: v for k, v in ending_counts.items() if v >= 2},
    }
