create extension if not exists pgcrypto;

create table if not exists app_users (
    id uuid primary key default gen_random_uuid(),
    username text unique not null,
    display_name text,
    password_hash text not null,
    created_at timestamptz not null default now()
);

create table if not exists candidate_profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    raw_text text,
    structured jsonb not null default '{}'::jsonb,
    style_sample text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(user_id)
);

create table if not exists experiences (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    title text not null,
    raw_text text,
    structured jsonb not null default '{}'::jsonb,
    fact_status text not null default 'verified',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists application_projects (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    company text not null,
    position text not null,
    team text,
    deadline date,
    status text not null default '준비중',
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists project_sources (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    project_id uuid not null references application_projects(id) on delete cascade,
    source_type text not null,
    title text not null,
    url text,
    content text not null,
    trust_level text not null default 'supported',
    created_at timestamptz not null default now()
);

create table if not exists project_analyses (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    project_id uuid not null references application_projects(id) on delete cascade,
    analysis jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(user_id, project_id)
);

create table if not exists essay_questions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    project_id uuid not null references application_projects(id) on delete cascade,
    question_text text not null,
    char_limit integer not null default 0,
    user_message text,
    custom_instruction text,
    analysis jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- v0.1에서 업그레이드할 때 기존 테이블에 새 컬럼 추가
alter table essay_questions add column if not exists user_message text;
alter table essay_questions add column if not exists custom_instruction text;
alter table essay_questions add column if not exists analysis jsonb not null default '{}'::jsonb;

create table if not exists content_allocations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    project_id uuid not null references application_projects(id) on delete cascade,
    allocation jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(user_id, project_id)
);

create table if not exists essay_drafts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    project_id uuid not null references application_projects(id) on delete cascade,
    question_id uuid not null references essay_questions(id) on delete cascade,
    draft_type text not null default 'draft',
    title text,
    content text not null,
    used_materials jsonb not null default '[]'::jsonb,
    review jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

alter table essay_drafts add column if not exists title text;

create table if not exists prompt_instructions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    project_id uuid not null references application_projects(id) on delete cascade,
    question_id uuid references essay_questions(id) on delete cascade,
    scope text not null default 'global',
    instruction text not null,
    active boolean not null default true,
    created_at timestamptz not null default now()
);

create index if not exists idx_projects_user on application_projects(user_id);
create index if not exists idx_experiences_user on experiences(user_id);
create index if not exists idx_sources_project on project_sources(user_id, project_id);
create index if not exists idx_questions_project on essay_questions(user_id, project_id);
create index if not exists idx_drafts_project on essay_drafts(user_id, project_id);
create index if not exists idx_prompt_instruction_project on prompt_instructions(user_id, project_id, scope);

-- 서버는 Secret/Service key를 사용합니다. anon 직접 접근을 막기 위해 RLS 활성화.
alter table app_users enable row level security;
alter table candidate_profiles enable row level security;
alter table experiences enable row level security;
alter table application_projects enable row level security;
alter table project_sources enable row level security;
alter table project_analyses enable row level security;
alter table essay_questions enable row level security;
alter table content_allocations enable row level security;
alter table essay_drafts enable row level security;
alter table prompt_instructions enable row level security;
