-- =========================================================
-- QUORUM RESEARCH AGENT - SUPABASE SCHEMA & RLS SETUP
-- Paste this script into your Supabase Dashboard:
-- SQL Editor -> New Query -> Run
-- =========================================================

-- 1. Create research_history table
create table if not exists public.research_history (
    id uuid default gen_random_uuid() primary key,
    user_id uuid references auth.users(id) on delete cascade not null,
    topic text not null,
    status text default 'completed',
    report_markdown text not null,
    sources jsonb default '[]'::jsonb,
    citations_count integer default 0,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. Enable Row-Level Security (RLS) so each user can only see their own research
alter table public.research_history enable row level security;

-- 3. Policy: Allow users to view only their own reports
create policy "Users can view own research"
    on public.research_history
    for select
    using (auth.uid() = user_id);

-- 4. Policy: Allow users to insert their own research reports
create policy "Users can insert own research"
    on public.research_history
    for insert
    with check (auth.uid() = user_id);

-- 5. Policy: Allow users to delete their own reports
create policy "Users can delete own research"
    on public.research_history
    for delete
    using (auth.uid() = user_id);

-- 6. Index for fast querying by user and date
create index if not exists idx_research_history_user_date
    on public.research_history (user_id, created_at desc);
