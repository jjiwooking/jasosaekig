-- v0.2.4: shared public web-research cache to minimize Tavily credits
create table if not exists research_cache (
    cache_key text primary key,
    research_type text not null,
    company text not null,
    position text,
    team text,
    query_text text not null,
    results jsonb not null default '[]'::jsonb,
    searched_at timestamptz not null default now(),
    expires_at timestamptz not null,
    use_count integer not null default 0
);

create table if not exists research_usage (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users(id) on delete cascade,
    project_id uuid not null references application_projects(id) on delete cascade,
    research_type text not null,
    cache_key text not null,
    source text not null check (source in ('cache','tavily')),
    credits_estimate integer not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_research_cache_expiry on research_cache(research_type, expires_at);
create index if not exists idx_research_usage_user_month on research_usage(user_id, created_at);

alter table research_cache enable row level security;
alter table research_usage enable row level security;

-- Server-only service key access (also fixes fresh-project privilege errors).
GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO service_role;
NOTIFY pgrst, 'reload schema';
