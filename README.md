# Career Essay AI v0.2.2

자기소개서 작성이 중심인 Streamlit + Supabase 프로그램입니다.

메인 화면은 의도적으로 세 단계만 크게 보여줍니다.

**기업분석 → 채용직무분석 → 자소서 완성**

이력서, 경험 DB, 채용자료, 분석 원본, 사용자 프롬프트 지시 이력, 자소서 버전은 보조 탭으로 분리해 메인 화면을 단순하게 유지합니다.

## v0.2.2 핵심 변경

### 자동 웹 리서치
- **기업분석 실행**: 회사명만으로 Google Search → 공식 홈페이지/공시/최근 이슈 수집 → 근거 저장 → 기업분석
- **채용직무분석 실행**: 기업명+직무명으로 최신/최근 채용공고·직무기술서·지원조직 자료 검색 → 근거 저장 → 직무분석
- 분석 근거 탭에서 검색 결과와 중간 분석을 별도로 확인 가능
- 별도 Tavily 키 불필요. 기존 `GEMINI_API_KEY`만 사용


### 1) 문항을 적으면 먼저 냉정하게 분석
기업의 실제 자기소개서 문항을 입력하면 바로 글을 쓰지 않습니다.

- 문항 유형
- 채용담당자가 확인하려는 것
- 반드시 답해야 하는 요소
- 하드 조건
- 필요한 증거
- 비슷해 보여도 부적합한 경험
- 감점 위험
- 권장 답변 순서

를 먼저 분석합니다.

### 2) `내가 하고 싶은 말`
문항마다 사용자가 반드시 전달하고 싶은 생각이나 방향을 별도 입력할 수 있습니다.

이 내용은 AI가 마음대로 버리는 후보 소재가 아닙니다. 핵심 의도를 보존하고 기업·직무·경험 근거를 붙여 자소서 안에 자연스럽게 재구성합니다.

근거가 부족한 경우 삭제하지 않고 어떤 사실이 더 필요한지 질문합니다.

### 3) Question Requirement Gate
경험이 문항과 비슷하다는 이유만으로 배정하지 않습니다.

문항의 하드 조건과 경험 사실을 먼저 대조하고:

- `pass` : 필수조건 충족
- `partial` : 일부 보완 필요
- `gap` : 핵심 사실 부족

으로 판단합니다.

`gap`이면 내용을 만들어 쓰지 않고 추가 사실을 요청합니다.

### 4) 전체 문항 소재 선배분
자소서를 쓴 뒤 중복을 찾는 것이 아니라, 전체 문항을 먼저 보고 경험/학력/자격/프로젝트를 배정합니다.

전공이나 자격증을 표현만 바꿔 여러 문항에서 다시 설명하는 의미상 중복도 막도록 프롬프트에 규칙을 넣었습니다.

### 5) 프로그램 안에서 계속 프롬프트 지시
왼쪽 사이드바에 항상 `AI에게 계속 지시하기` 입력창이 있습니다.

적용범위:

- 전체 프로젝트
- 기업분석
- 채용직무분석
- 자소서

예:

- 최근 1년 이슈 중심으로 봐줘
- 이 직무는 데이터분석 역량을 더 중요하게 봐줘
- 대학원 이야기는 이번 문항에서 쓰지 마
- 문장을 더 담백하게 써줘

저장한 지시는 이후 해당 단계 프롬프트에 누적 반영되며 `분석 근거 > AI 지시 이력`에서 확인하거나 중지할 수 있습니다.

## 화면 구성

### 메인 워크플로우
1. 기업분석
2. 채용직무분석
3. 자소서 완성
   - 문항 입력·분석
   - 소재 배분
   - 작성
   - 검토·최종

### 내 정보
- 이력서/경력기술서 구조화
- Candidate Profile
- Experience DB
- 문체 샘플

### 분석 근거
- 자동 웹 검색(선택)
- URL 본문 수집
- 채용공고/직무기술서 직접 붙여넣기
- 저장 출처
- 기업분석/직무분석/문항분석/소재배분 원본
- 사용자 AI 지시 이력

### 저장소
- 문항별 초안
- 최종본
- 소제목
- 검토 결과
- 버전 이력

## 프롬프트 역할 분리

한 개의 거대한 프롬프트가 자소서를 한 번에 쓰지 않습니다.

1. Candidate Parser
2. Experience Extractor / Evidence Interviewer
3. Company Analyst
4. Job Posting + Support Team Analyst
5. Question Analyst
6. Question Requirement Gate
7. Content Planner / Evidence Allocator
8. Essay Writer
9. Recruiter Reviewer
10. Fact Checker
11. Human Style Editor

공통 프레임은 다음 순서입니다.

`ROLE → OBJECTIVE → SOURCE → SOURCE PRIORITY → KNOWN FACTS → INFERRED → UNKNOWN → ANALYSIS → MATCHING → CONTENT ALLOCATION → WRITING STRUCTURE → STYLE → NEGATIVE RULES → FACT GUARDRAIL → RUBRIC → REVISION → OUTPUT`

## 사실성 원칙

- 사용자 또는 출처에 없는 경험 생성 금지
- 미확인 수치 생성 금지
- 팀 성과를 개인 성과로 변경 금지
- 추론은 확정 사실과 분리
- 부족한 정보는 질문
- 합격 자소서 문구 복사 금지
- 회사명만 바꾸면 통하는 Generic 문장 최소화

## 설치

```bash
pip install -r requirements.txt
```

Supabase 프로젝트에서 `supabase_setup.sql`을 실행합니다.

v0.1 DB를 이미 사용 중이어도 이 SQL 안의 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`가 신규 컬럼을 추가합니다.

Streamlit Secrets:

```toml
GEMINI_API_KEY="..."
SUPABASE_URL="https://xxxx.supabase.co"
SUPABASE_SECRET_KEY="sb_secret_..."
```

실행:

```bash
streamlit run streamlit_app.py
```

## 주요 DB

- `app_users`
- `candidate_profiles`
- `experiences`
- `application_projects`
- `project_sources`
- `project_analyses`
- `essay_questions`
  - `user_message`
  - `custom_instruction`
  - `analysis`
- `content_allocations`
- `essay_drafts`
  - `title`
- `prompt_instructions`

## 현재 범위

현재 버전은 프롬프트/워크플로우와 사용자별 영구 저장 구조를 구현한 MVP입니다. 기업분석과 채용직무분석을 실행하면 기존 GEMINI_API_KEY를 이용한 **Gemini Google Search grounding**이 먼저 공개 웹을 검색하고, 검색 근거를 프로젝트 DB에 저장한 뒤 분석합니다. 별도의 Tavily API 키는 필요하지 않습니다. 사용자는 필요할 때만 URL/본문 자료를 추가하면 됩니다. 사람인/잡코리아/원티드 등 로그인·동적 렌더링이 필요한 사이트의 전용 Connector/API 연동은 후속 Recruiting Intelligence 확장 단계입니다.


## Gemini 모델 설정

기본 모델은 `gemini-3.6-flash`입니다. 필요하면 Streamlit Secrets에서 아래처럼 변경할 수 있습니다.

```toml
GEMINI_MODEL="gemini-3.6-flash"
```
