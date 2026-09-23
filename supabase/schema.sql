-- Safe Child production schema (Supabase PostgreSQL, free tier).
--
-- NOTE: Row Level Security is intentionally NOT enabled on these tables.
-- The Supabase anon/service key lives server-side only, inside the Reflex
-- backend. It is never exposed to the browser, so RLS policies would only
-- add friction with no security benefit in this architecture.

create extension if not exists "pgcrypto";

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    identity text unique not null,
    pw_hash text not null,
    created_at timestamptz not null default now()
);

create table if not exists screenings (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references users(id) on delete set null,
    age_group text,
    answers jsonb,
    score numeric,
    band text,
    critical boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists reports (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references users(id) on delete set null,
    case_id text unique not null,
    data jsonb not null,
    status text not null default 'draft',
    created_at timestamptz not null default now()
);

create index if not exists idx_screenings_user_id on screenings(user_id);
create index if not exists idx_reports_user_id on reports(user_id);
create index if not exists idx_reports_case_id on reports(case_id);
