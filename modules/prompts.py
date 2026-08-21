from __future__ import annotations

import json
from typing import Any


def _j(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


MASTER_FRAMEWORK = """
[공통 프롬프트 프레임]
ROLE → OBJECTIVE → SOURCE/INPUT → SOURCE PRIORITY → KNOWN FACTS → INFERRED DATA → UNKNOWN DATA
→ ANALYSIS TASK → MATCHING LOGIC → CONTENT ALLOCATION → WRITING STRUCTURE → STYLE PROFILE
→ NEGATIVE RULES → FACT GUARDRAIL → QUALITY RUBRIC → REVISION RULE → OUTPUT FORMAT
"""

FACT_RULES = """
[사실성 가드레일]
- 사용자가 직접 제공했거나 저장된 원문/공식 출처에서 확인된 사실만 단정한다.
- 경험, 기간, 자격, 수치, 성과, 회사 정보, 팀 역할을 만들어내지 않는다.
- 팀의 행동/성과를 지원자 개인의 행동/성과로 바꾸지 않는다.
- 확인되지 않은 추론은 inferred로 분리한다. 사용자 확인 전 자소서의 확정 사실처럼 쓰지 않는다.
- 정보가 없으면 unknown 또는 [확인 필요]로 남긴다. 빈칸을 그럴듯한 내용으로 채우지 않는다.
- 자료 간 충돌이 있으면 더 신뢰도 높은 출처를 우선하고 충돌 사실을 표시한다.
"""

SOURCE_RULES = """
[출처 우선순위]
1. 공식 채용공고 / 공식 직무기술서 / 회사 공식 채용페이지 / IR·사업보고서·공시
2. 회사 공식 뉴스룸·직무 인터뷰·조직/제품/서비스 페이지
3. 공공기관·거래소·정부·산업기관 자료
4. 신뢰할 수 있는 언론·채용 플랫폼의 원문 정보
5. 커뮤니티/후기 자료는 보조 근거만 사용
- official / supported / inferred를 반드시 구분한다.
"""

STYLE_RULES = """
[지원자 문체 원칙]
- 사실 전달형 문장을 우선한다.
- '~라고 생각합니다'를 반복하지 않는다. 필요한 경우 '판단했습니다', '확인했습니다', '했습니다'처럼 판단과 행동을 직접 쓴다.
- 첫째/둘째/셋째 같은 기계적인 3연속 병렬 구조를 남발하지 않는다.
- '혁신적인/탁월한/열정적인/차별화된/시너지' 같은 수식어는 실제 행동·근거·수치로 대체한다.
- 모든 경험을 완벽한 성공담으로 포장하지 않는다. 실제 시행착오가 있으면 짧고 정확하게 살린다.
- '이를 통해 ~ 깨달았습니다'를 습관적으로 쓰지 않는다. 이후 행동 변화나 직무에서의 재현 방식으로 연결한다.
- 한 문장에는 한 개의 핵심 생각이나 행동을 둔다.
- 문장 길이와 종결형을 섞어 기계적인 리듬을 줄인다.
- 지원자가 면접에서 실제로 말해도 어색하지 않은 어휘를 사용한다.
- 회사명만 바꾸면 다른 회사에도 그대로 통하는 문장은 구체화하거나 삭제한다.
"""

ACCEPTED_STRUCTURE_RULES = """
[합격 자소서 구조 참고 원칙]
- 합격 자소서는 문구를 복사하지 않고 구조, 정보 배치, 리듬만 참고한다.
- 경험형 문항은 필요할 때 '핵심 주장 → 상황 → 문제 → 나의 역할 → 판단 → 구체 행동 → 장애물/시행착오 → 수정 → 결과 → 직무 연결' 순서를 선택적으로 사용한다.
- 모든 경험에 실패/장애물을 억지로 만들지 않는다. 실제 사실이 있을 때만 사용한다.
- 소제목은 추상적인 미사여구보다 경험의 핵심 사건·판단·변화를 드러내는 문구를 우선한다.
"""

NON_REPEAT_RULES = """
[소재 중복 방지 원칙]
- 자소서를 다 쓴 뒤 중복을 고치는 것이 아니라 작성 전에 전체 문항의 소재를 배분한다.
- 이미 다른 문항의 핵심 근거로 배정된 학력, 전공, 자격증, 프로젝트, 직장, 성과, 경험을 새 핵심 소재처럼 반복하지 않는다.
- 표현만 바뀌어도 의미가 같으면 같은 소재로 판단한다.
- 예: '회계세무 대학원에서'와 '회계세무 대학원 과정을 통해'는 같은 배경정보다.
- 자격증은 필요한 한 문항에서만 직접 제시하고 다른 문항에서는 실제 적용 행동이 있다면 그 행동을 보여준다.
- 같은 경험을 다시 써야 한다면 이전 문항에서 사용하지 않은 다른 사건/역할/판단/행동/성과가 명확해야 한다.
- 각 문항은 지원자에 대한 새로운 정보를 최소 1개 이상 추가해야 한다.
"""

USER_MESSAGE_RULES = """
[사용자가 하고 싶은 말 처리 원칙]
- '내가 하고 싶은 말'은 AI가 적합성 심사 후 버리는 후보 소재가 아니다. 사용자가 이번 문항에서 반드시 전달하고 싶은 의도·방향·생각이다.
- 핵심 의도를 보존한 상태에서 문항 요구, 기업/직무 근거, 지원자 경험을 연결해 설득력 있는 구조로 재구성한다.
- 사용자가 적은 말을 그대로 복사하지 말고 자연스러운 자소서 문장으로 통합한다.
- 근거가 부족하면 내용을 제거하지 말고, 그 말을 더 설득력 있게 만들기 위해 필요한 사실을 구체적으로 질문한다.
- 단, 명백한 사실 충돌이나 허위가 되는 내용은 사용할 수 없으며 어떤 확인이 필요한지 표시한다.
"""

QUESTION_ANALYSIS_RULES = """
[문항 분석 원칙 — 정확하고 냉정하게]
- 지원자에게 유리하게 해석하려 하지 말고 채용담당자가 실제로 무엇을 확인하려는지 분해한다.
- 문항에 쓰인 동사, 대상, 조건, 시간범위, 결과 요구를 정확히 추출한다.
- '협업 경험'과 '업무가 어려운 구성원을 직접 도운 경험'처럼 비슷해 보여도 필수 조건이 다르면 동일하게 취급하지 않는다.
- 문항이 요구하지 않은 역량을 억지로 끼워 넣지 않는다.
- 경험이 조건을 충족하지 못하면 부적합이라고 판단한다.
- 부족한 근거는 추가 질문으로 남긴다. 그럴듯한 대체 경험을 만들어내지 않는다.
- 감점 포인트를 구체적으로 적는다: 질문 일부 미응답, 본인 행동 불명확, 결과 없음, 추상어, 기업/직무 억지 연결 등.
"""


def _instruction_block(instructions: list[dict] | None) -> str:
    if not instructions:
        return "[사용자 추가 지시]\n없음"
    clean = [
        {
            "scope": i.get("scope"),
            "instruction": i.get("instruction"),
            "created_at": i.get("created_at"),
        }
        for i in instructions
        if i.get("instruction")
    ]
    return "[사용자 추가 지시 — 기본 프롬프트보다 우선하되 사실성 가드레일은 위반할 수 없음]\n" + _j(clean)


def candidate_structure_prompt(raw_text: str, instructions: list[dict] | None = None) -> str:
    return f"""
너는 Candidate Parser + Experience Extractor다.
목적은 자소서를 쓰는 것이 아니라 지원자가 실제로 가진 사실과 경험을 재사용 가능한 개인 DB로 구조화하는 것이다.

{MASTER_FRAMEWORK}
{FACT_RULES}
{_instruction_block(instructions)}

[지원자 원문]
{raw_text}

[구조화 원칙]
- 학력/경력/자격/교육/언어/프로젝트/연구를 사실 단위로 추출한다.
- 경험은 Problem → Judgment → Action의 사고 흐름이 보이게 한다.
- 원문에 없는 숫자/성과/직무는 만들지 않는다.
- 불명확한 항목은 inferred 또는 unknown으로 분리한다.
- 자소서 문장을 재작성하지 않는다.

다음 JSON만 반환하라.
{{
  "basic": {{"education":[], "career":[], "certifications":[], "languages":[], "training":[], "research":[]}},
  "experiences": [
    {{
      "title":"", "period":"", "organization":"", "role":"", "situation":"", "goal":"", "problem":"",
      "my_role":"", "initial_judgment":"", "initial_action":"", "obstacle":"", "failed_attempt":"",
      "revised_judgment":"", "revised_action":"", "result":"", "metric":"", "evidence":"",
      "learning":"", "behavior_change":"", "skills":[], "tools":[], "related_competencies":[],
      "related_jobs":[], "fact_status":"verified|inferred|unknown", "missing_questions":[]
    }}
  ],
  "strength_signals":[],
  "fact_gaps":[]
}}
"""


def experience_structure_prompt(raw_text: str, instructions: list[dict] | None = None) -> str:
    return f"""
너는 Evidence Interviewer다. 사용자가 자유롭게 적은 경험을 자소서에서 재사용할 수 있는 사실 DB로 구조화하라.

{FACT_RULES}
{_instruction_block(instructions)}

[사용자 경험 원문]
{raw_text}

[핵심]
- 단순 STAR보다 '문제 → 판단 → 구체 행동'을 선명하게 만든다.
- 사용자가 직접 한 행동과 팀이 한 행동을 구분한다.
- 시행착오가 원문에 없다면 만들지 않는다.
- 결과의 수치나 객관적 근거가 없으면 빈칸으로 둔다.
- missing_questions에는 자소서의 신뢰성과 차별성을 높일 가치가 큰 질문만 최대 5개 제시한다.

다음 JSON만 반환하라.
{{
  "title":"", "period":"", "organization":"", "situation":"", "goal":"", "problem":"", "my_role":"",
  "initial_judgment":"", "initial_action":"", "obstacle":"", "failed_attempt":"", "revised_judgment":"",
  "revised_action":"", "result":"", "metric":"", "evidence":"", "learning":"", "behavior_change":"",
  "skills":[], "tools":[], "related_competencies":[], "related_jobs":[],
  "fact_status":"verified|inferred|unknown", "missing_questions":[]
}}
"""


def company_analysis_prompt(company: str, sources: list[dict], instructions: list[dict] | None = None) -> str:
    compact_sources = [
        {
            "id": s.get("id"), "source_type": s.get("source_type"), "title": s.get("title"),
            "url": s.get("url"), "trust_level": s.get("trust_level"),
            "content": (s.get("content") or "")[:16000],
        }
        for s in sources
    ]
    return f"""
너는 Company Analyst다. 회사 소개 보고서를 만드는 것이 아니라 최종 자소서의 기업 이해 근거를 만든다.

{MASTER_FRAMEWORK}
{SOURCE_RULES}
{FACT_RULES}
{_instruction_block(instructions)}

[회사]
{company}

[수집 자료]
{_j(compact_sources)}

[분석 과제]
- 주요 사업/제품/서비스/수익 또는 역할 구조를 자소서에 필요한 수준으로 요약한다.
- 최근 전략, 투자, 사업변화, 정책/시장변화, 고객/기술 이슈를 확인한다.
- 현재 회사가 해결해야 하는 과제를 근거와 함께 정리한다.
- 단순 회사 칭찬이 아니라 '시장/환경 변화 → 회사 영향 → 왜 해당 인력이 필요한가'를 설명할 재료를 찾는다.
- 출처 없는 내용을 확정하지 않는다.

다음 JSON만 반환하라.
{{
  "business_summary":"",
  "key_businesses":[],
  "products_services":[],
  "recent_changes":[{{"fact":"", "why_it_matters":"", "source_ids":[], "confidence":"official|supported|inferred"}}],
  "current_challenges":[{{"challenge":"", "evidence":"", "source_ids":[], "confidence":"official|supported|inferred"}}],
  "market_competitor_context":[],
  "essay_specific_points":[{{"point":"", "use_case":"지원동기|직무연결|입사후포부|기타", "source_ids":[], "confidence":"official|supported|inferred"}}],
  "do_not_overclaim":[],
  "data_gaps":[]
}}
"""


def job_analysis_prompt(
    company: str,
    position: str,
    team: str,
    sources: list[dict],
    company_analysis: dict,
    instructions: list[dict] | None = None,
) -> str:
    compact_sources = [
        {
            "id": s.get("id"), "source_type": s.get("source_type"), "title": s.get("title"),
            "url": s.get("url"), "trust_level": s.get("trust_level"),
            "content": (s.get("content") or "")[:16000],
        }
        for s in sources
    ]
    return f"""
너는 Job Posting Analyst + Support Team Analyst다. 목표는 지원 직무가 실제로 무엇을 하고 어떤 지원자를 뽑으려는지 냉정하게 해석하는 것이다.

{MASTER_FRAMEWORK}
{SOURCE_RULES}
{FACT_RULES}
{_instruction_block(instructions)}

[지원 대상]
회사: {company}
직무: {position}
지원 조직/팀: {team or '[미입력]'}

[기업 분석]
{_j(company_analysis)}

[채용/직무 자료]
{_j(compact_sources)}

[분석 과제]
- 공고에 명시된 업무, 필수/우대조건, 기술, 행동역량을 먼저 분리한다.
- 반복 표현과 문장 구조를 보고 채용담당자가 특히 중요하게 보는 역량을 추정하되 추정이라고 표시한다.
- 지원팀/조직의 실제 업무, 협업 대상, 사용하는 데이터/도구, 주요 문제를 확인한다.
- '협업' 같은 단어를 그대로 쓰지 말고 실제 행동역량으로 번역한다.
- KPI는 자료에서 확인되지 않으면 inferred로만 제시한다.
- 기업분석의 변화/과제가 이 직무에 어떤 영향을 주는지 연결한다.

다음 JSON만 반환하라.
{{
  "posting_summary":"",
  "core_tasks":[{{"task":"", "source_ids":[], "confidence":"official|supported|inferred"}}],
  "required_qualifications":[],
  "preferred_qualifications":[],
  "technical_skills":[],
  "behavior_competencies":[{{"competency":"", "observable_behavior":"", "why_required":""}}],
  "hidden_hiring_intents":[{{"intent":"", "basis":"", "confidence":"supported|inferred"}}],
  "team": {{"known_work":[], "inferred_work":[], "collaboration_targets":[], "tools_data":[], "key_problems":[]}},
  "likely_kpis":[{{"item":"", "confidence":"official|supported|inferred"}}],
  "competency_weights":[{{"competency":"", "weight":0, "reason":""}}],
  "company_to_job_link":[{{"company_change":"", "job_impact":"", "needed_behavior":"", "essay_use":""}}],
  "candidate_evidence_needed":[],
  "data_gaps":[]
}}
"""


def question_analysis_prompt(
    question: dict,
    company_analysis: dict,
    job_analysis: dict,
    user_message: str = "",
    instructions: list[dict] | None = None,
) -> str:
    return f"""
너는 한국 기업 채용담당자의 관점에서 자소서 문항을 분석하는 Question Analyst다.
자소서는 아직 쓰지 않는다. 문항을 유리하게 해석하거나 흔한 자기소개서 유형으로 뭉개지 말고 정확하고 냉정하게 해체하라.

{QUESTION_ANALYSIS_RULES}
{FACT_RULES}
{USER_MESSAGE_RULES}
{_instruction_block(instructions)}

[문항]
{_j(question)}

[기업 분석]
{_j(company_analysis)}

[채용직무 분석]
{_j(job_analysis)}

[사용자가 이번 문항에서 하고 싶은 말]
{user_message or '[없음]'}

[분석 과제]
- 문항에서 반드시 답해야 하는 요소를 빠짐없이 분해한다.
- 하드 조건과 있으면 좋은 요소를 구분한다.
- 어떤 경험이 '비슷해 보이지만 실제로는 부적합'한지 예시 기준을 만든다.
- 사용자의 하고 싶은 말은 유지해야 할 핵심 의도로 보고 문항 안에 어떻게 설득력 있게 연결할지 설계한다.
- 사용자 메시지의 핵심을 살리기 위해 추가 근거가 필요하면 질문한다.

다음 JSON만 반환하라.
{{
  "question_type":"",
  "one_line_intent":"",
  "recruiter_is_testing":"",
  "must_answer_elements":[],
  "hard_requirements":[],
  "nice_to_have":[],
  "evidence_needed":[],
  "suitable_experience_criteria":[],
  "lookalike_but_wrong":[],
  "recommended_answer_order":[],
  "user_message_core":"",
  "user_message_integration":"",
  "user_message_evidence_questions":[],
  "deduction_risks":[],
  "company_job_connection_needed":"",
  "analysis_confidence":"high|medium|low"
}}
"""


def allocation_prompt(
    questions: list[dict],
    experiences: list[dict],
    company_analysis: dict,
    job_analysis: dict,
    instructions: list[dict] | None = None,
) -> str:
    return f"""
너는 Content Planner + Evidence Allocator다. 자소서를 쓰지 않는다.
전체 문항과 문항별 냉정 분석을 한꺼번에 보고, 필수 조건을 충족하는 경험만 배정한 뒤 중복을 사전에 차단한다.

{QUESTION_ANALYSIS_RULES}
{NON_REPEAT_RULES}
{FACT_RULES}
{USER_MESSAGE_RULES}
{_instruction_block(instructions)}

[기업 분석]
{_j(company_analysis)}

[채용직무 분석]
{_j(job_analysis)}

[지원자 경험 DB]
{_j(experiences)}

[전체 자소서 문항 + 문항분석 + 사용자 메시지]
{_j(questions)}

[Question Requirement Gate]
- 각 문항의 hard_requirements와 경험 사실을 먼저 대조한다.
- 핵심 조건이 충족되지 않으면 score가 높아도 선택하지 않는다.
- status는 pass / partial / gap 중 하나다.
- gap이면 경험을 꾸며 쓰지 말고 필요한 추가 질문을 만든다.
- 사용자의 '하고 싶은 말' 자체가 질문에 답할 수 있는 사실/방향이면 하나의 evidence로 인정하되, 필요한 구체 근거는 별도로 질문한다.

[적합 경험 점수 — Gate 통과 후]
- 문항 적합도 25
- 직무 적합도 25
- 기업 요구역량 20
- 구체성 10
- 성과/근거 10
- 지원자 고유성 10

다음 JSON만 반환하라.
{{
  "allocations": [
    {{
      "question_id":"",
      "requirement_gate": {{"status":"pass|partial|gap", "matched":[], "missing":[], "gap_questions":[]}},
      "candidate_matches":[{{"experience_id":"", "score":0, "eligible":true, "reason":"", "mismatch":[]}}],
      "primary_experience_id":"",
      "secondary_materials":[],
      "user_message_anchor":"",
      "reserved_materials":[],
      "do_not_repeat":[],
      "new_information_goal":"",
      "recommended_structure":[],
      "reason":""
    }}
  ],
  "global_reserved_facts":[],
  "semantic_repeat_blocks":[],
  "warnings":[]
}}
"""


def essay_writer_prompt(
    question: dict,
    question_analysis: dict,
    allocation: dict,
    experience: dict,
    company_analysis: dict,
    job_analysis: dict,
    candidate_profile: dict,
    prior_usage: list[dict],
    user_message: str = "",
    style_sample: str = "",
    instructions: list[dict] | None = None,
) -> str:
    return f"""
너는 한국 기업 지원용 자기소개서 Writer다.
목표는 'AI가 그럴듯하게 쓴 글'이 아니라 지원자의 실제 경험과 사용자가 전달하고 싶은 핵심을 채용 문항에 정확히 맞추는 것이다.

{MASTER_FRAMEWORK}
{FACT_RULES}
{QUESTION_ANALYSIS_RULES}
{USER_MESSAGE_RULES}
{NON_REPEAT_RULES}
{STYLE_RULES}
{ACCEPTED_STRUCTURE_RULES}
{_instruction_block(instructions)}

[문항]
{_j(question)}
[냉정 문항 분석]
{_j(question_analysis)}
[소재 배정 / Requirement Gate]
{_j(allocation)}
[선택 경험]
{_j(experience)}
[기업 분석]
{_j(company_analysis)}
[채용직무 분석]
{_j(job_analysis)}
[지원자 프로필]
{_j(candidate_profile)}
[이전 문항 사용 소재]
{_j(prior_usage)}
[사용자가 반드시 전달하고 싶은 말]
{user_message or '[없음]'}
[지원자 문체 샘플]
{style_sample or '[없음]'}

[작성 규칙]
- requirement_gate가 gap이면 허위로 채우지 않는다. status를 needs_information으로 반환하고 필요한 질문을 제시한다.
- 사용자가 하고 싶은 말의 핵심 의도를 우선 보존한다. 문항에 맞게 경험/기업/직무 근거를 붙여 재구성한다.
- 문항의 모든 must_answer_elements에 실제로 답한다.
- 소제목을 포함한다. 소제목은 경험의 핵심 사건·판단·변화를 드러낸다.
- 글자수 제한이 있으면 제한 안에서 정보 밀도를 높인다.
- Action은 '소통했다/분석했다/노력했다'로 끝내지 말고 무엇을 어떻게 했는지 적는다.
- 기업 정보는 칭찬용으로 나열하지 않고 지원자의 판단/행동/직무 활용과 연결한다.
- 이전 문항에서 이미 사용한 배경/자격/경험을 표현만 바꿔 재소개하지 않는다.
- 미확인 숫자나 효과를 만들지 않는다.

다음 JSON만 반환하라.
{{
  "status":"complete|needs_information",
  "title":"",
  "essay":"",
  "answered_elements":[],
  "used_materials":[],
  "used_verified_facts":[],
  "user_message_reflected":"",
  "needs_confirmation":[],
  "character_count":0
}}
"""


def review_prompt(
    essay: str,
    question: dict,
    question_analysis: dict,
    allocation: dict,
    experience: dict,
    company_analysis: dict,
    job_analysis: dict,
    candidate_profile: dict,
    prior_usage: list[dict],
    user_message: str = "",
    instructions: list[dict] | None = None,
) -> str:
    return f"""
너는 Recruiter Reviewer → Fact Checker → Human Style Editor 순서로 검토한다.
먼저 냉정하게 평가하고, 그 평가에서 지적된 문제만 수정한다. 점수를 올리기 위해 새로운 사실을 만들지 않는다.

{FACT_RULES}
{QUESTION_ANALYSIS_RULES}
{USER_MESSAGE_RULES}
{NON_REPEAT_RULES}
{STYLE_RULES}
{_instruction_block(instructions)}

[문항]
{_j(question)}
[문항 분석]
{_j(question_analysis)}
[소재 배정]
{_j(allocation)}
[원 경험]
{_j(experience)}
[기업 분석]
{_j(company_analysis)}
[채용직무 분석]
{_j(job_analysis)}
[지원자 프로필]
{_j(candidate_profile)}
[이전 사용 소재]
{_j(prior_usage)}
[사용자가 하고 싶은 말]
{user_message or '[없음]'}
[검토할 초안]
{essay}

[평가]
1. 문항의 hard_requirements를 모두 충족했는가
2. 사용자가 전달하고 싶은 핵심이 훼손되지 않았는가
3. 기업/직무 연결이 구체적이고 근거가 있는가
4. 본인 판단과 구체 행동이 보이는가
5. 사실/수치/기간/주체 오류가 없는가
6. 이전 문항의 소재를 의미상 반복하지 않는가
7. Generic 문장과 AI 상투어가 있는가
8. 소제목과 문장 리듬이 자연스러운가

다음 JSON만 반환하라.
{{
  "scores": {{
    "question_fit":0, "requirement_fit":0, "job_fit":0, "company_fit":0,
    "specificity":0, "action_judgment":0, "evidence":0, "uniqueness":0,
    "naturalness":0, "credibility":0, "user_intent_preservation":0
  }},
  "fatal_issues":[],
  "fact_issues":[],
  "missing_question_elements":[],
  "repetition_issues":[],
  "ai_tone_issues":[],
  "generic_issues":[],
  "revision_notes":[],
  "revised_title":"",
  "revised_essay":""
}}
"""
