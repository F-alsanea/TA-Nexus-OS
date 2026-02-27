-- ==========================================
--  TA NEXUS — SUPABASE SCHEMA
--  Run this in: Supabase SQL Editor
-- ==========================================

-- Enable UUID extension
create extension if not exists "pgcrypto";

-- ─────────────────────────────────────────
--  CANDIDATES
-- ─────────────────────────────────────────
create table if not exists candidates (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  email           text,
  phone           text,
  current_title   text,
  current_company text,
  skills          text[]  default '{}',
  cv_text         text,
  source_job_id   text,
  overall_score   numeric(5,2) default 0,
  retention_risk  numeric(5,2) default 0,
  salary_risk     numeric(5,2) default 0,
  cultural_risk   numeric(5,2) default 0,
  domain_color    text default 'green',  -- green | yellow | red
  email_verified  boolean default false,
  updated_at      timestamptz default now(),
  created_at      timestamptz default now()
);

-- Index for fast score sorting
create index if not exists idx_candidates_score on candidates(overall_score desc);

-- ─────────────────────────────────────────
--  SCREENING SESSIONS
-- ─────────────────────────────────────────
create table if not exists screening_sessions (
  id              uuid primary key default gen_random_uuid(),
  candidate_id    uuid references candidates(id) on delete cascade,
  job_id          text,
  questions       jsonb not null default '[]',  -- [{id, text, type, options, ideal_answer}]
  answers         jsonb default '[]',           -- [{question_id, answer_text}]
  status          text default 'pending',       -- pending | in_progress | completed
  screening_url   text,
  submitted_at    timestamptz,
  expires_at      timestamptz default (now() + interval '7 days'),
  created_at      timestamptz default now()
);

create index if not exists idx_sessions_candidate on screening_sessions(candidate_id);
create index if not exists idx_sessions_status    on screening_sessions(status);

-- ─────────────────────────────────────────
--  SCORES
-- ─────────────────────────────────────────
create table if not exists scores (
  id                   uuid primary key default gen_random_uuid(),
  session_id           uuid references screening_sessions(id) on delete cascade,
  candidate_id         uuid references candidates(id) on delete cascade,
  total_score          numeric(5,2) default 0,
  accuracy_score       numeric(5,2) default 0,
  depth_score          numeric(5,2) default 0,
  cultural_score       numeric(5,2) default 0,
  skill_gap            jsonb default '[]',   -- list of missing skills
  risk_flags           jsonb default '{}',   -- {retention, salary, cultural}
  interview_guide_url  text,
  scored_at            timestamptz default now()
);

create index if not exists idx_scores_candidate on scores(candidate_id);
create index if not exists idx_scores_total     on scores(total_score desc);

-- ─────────────────────────────────────────
--  REMINDERS
-- ─────────────────────────────────────────
create table if not exists reminders (
  id              uuid primary key default gen_random_uuid(),
  candidate_id    uuid references candidates(id) on delete cascade,
  follow_up_date  timestamptz not null,
  status          text default 'pending',   -- pending | sent | dismissed
  recruiter_note  text,
  trigger_score   numeric(5,2),
  created_at      timestamptz default now()
);

create index if not exists idx_reminders_status on reminders(status, follow_up_date);

-- ─────────────────────────────────────────
--  MEMORY SNAPSHOTS (Instant Compaction)
-- ─────────────────────────────────────────
create table if not exists memory_snapshots (
  id             uuid primary key default gen_random_uuid(),
  session_key    text unique not null,
  summary        text,
  full_context   jsonb default '{}',
  compressed_at  timestamptz default now()
);

-- ─────────────────────────────────────────
--  ROW LEVEL SECURITY (RLS)
--  Enable after testing — protects data in production
-- ─────────────────────────────────────────
-- alter table candidates        enable row level security;
-- alter table screening_sessions enable row level security;
-- alter table scores             enable row level security;
-- alter table reminders          enable row level security;
-- alter table memory_snapshots   enable row level security;

-- ─────────────────────────────────────────
--  SAMPLE DATA (optional — for testing)
-- ─────────────────────────────────────────
insert into candidates (name, email, current_title, current_company, skills, overall_score, retention_risk, salary_risk, cultural_risk, domain_color, email_verified)
values
  ('أحمد الشهري',   'ahmed@techco.sa',   'مهندس Backend أول',     'شركة تقنية الرياض', array['Python','PostgreSQL','AWS','Docker'],   87.5, 25, 40, 15, 'green',  true),
  ('نورة العتيبي', 'noura@startup.io',  'مديرة منتج',           'ستارت أب جدة',      array['Product','Agile','Figma','Analytics'], 72.0, 60, 75, 30, 'yellow', true),
  ('فهد القحطاني', 'fahad@company.com', 'مطور Full-Stack',       'شركة متوسطة',       array['React','Node.js','MongoDB'],            55.0, 80, 90, 45, 'red',    false),
  ('سارة الدوسري', 'sara@mega.sa',      'محللة بيانات',          'مؤسسة كبرى',        array['Python','R','PowerBI','SQL'],          91.0, 20, 20, 10, 'green',  true)
on conflict (id) do nothing;
