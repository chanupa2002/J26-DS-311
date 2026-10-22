-- Financial grant-risk persistence for Supabase/PostgreSQL.
-- Safe to run more than once. This migration does not create a database;
-- execute it in the target PostgreSQL/Supabase database.

create extension if not exists pgcrypto;

-- Upgrade support if the earlier unprefixed version was already executed.
do $$
begin
    if to_regclass('public.monitoring_visits') is not null
       and to_regclass('public.evidence_trust_monitoring_visits') is null then
        alter table public.monitoring_visits rename to evidence_trust_monitoring_visits;
    end if;
    if to_regclass('public.financial_runs') is not null
       and to_regclass('public.evidence_trust_financial_runs') is null then
        alter table public.financial_runs rename to evidence_trust_financial_runs;
    end if;
    if to_regclass('public.financial_flags') is not null
       and to_regclass('public.evidence_trust_financial_flags') is null then
        alter table public.financial_flags rename to evidence_trust_financial_flags;
    end if;
end $$;

create table if not exists evidence_trust_monitoring_visits (
    visit_id uuid primary key default gen_random_uuid(),
    -- Kept as text so imports also accept UUID-like source identifiers from CSV.
    source_uuid text not null unique,
    household_id text,
    month_index integer not null,
    visit_date date,
    is_synthetic boolean not null default false,

    -- Grant ledger and lifecycle fields.
    grant_amount_lkr numeric(14, 2),
    grant_spent_lkr numeric(14, 2),
    monthly_expenditure_lkr numeric(14, 2),
    grant_remaining_lkr numeric(14, 2),
    grant_use_status text,
    grant_used_per_plan boolean,

    -- Livelihood/context fields.
    disaster_impact_reported boolean,
    livelihood_difficulty_reported boolean,
    business_running boolean,
    profit boolean,
    borrowed_money boolean,

    -- Financial/model input fields.
    revenue_mid_lkr numeric(14, 2),
    problem_count integer,
    record_keeping_level numeric(10, 4),
    saved_amount_lkr numeric(14, 2),

    created_at timestamptz not null default now(),

    constraint evidence_trust_monitoring_visits_month_index_nonnegative
        check (month_index >= 0),
    constraint evidence_trust_monitoring_visits_amounts_nonnegative
        check (
            (grant_amount_lkr is null or grant_amount_lkr >= 0)
            and
            (grant_spent_lkr is null or grant_spent_lkr >= 0)
            and (monthly_expenditure_lkr is null or monthly_expenditure_lkr >= 0)
            and (grant_remaining_lkr is null or grant_remaining_lkr >= 0)
            and (revenue_mid_lkr is null or revenue_mid_lkr >= 0)
            and (saved_amount_lkr is null or saved_amount_lkr >= 0)
        ),
    constraint evidence_trust_monitoring_visits_problem_count_nonnegative
        check (problem_count is null or problem_count >= 0)
);

create index if not exists idx_evidence_trust_monitoring_visits_household_month
    on evidence_trust_monitoring_visits (household_id, month_index);

create index if not exists idx_evidence_trust_monitoring_visits_source_uuid
    on evidence_trust_monitoring_visits (source_uuid);

create table if not exists evidence_trust_financial_runs (
    run_id uuid primary key default gen_random_uuid(),
    visit_id uuid not null references evidence_trust_monitoring_visits (visit_id) on delete cascade,
    model_name text,
    model_created timestamptz,
    artifact_versions jsonb not null default '{}'::jsonb,
    reliability_level text,
    confidence numeric(10, 6),
    risk numeric(10, 6),
    rule_score numeric(10, 6),
    model_score numeric(10, 6),
    level text,
    data_origin text,
    report_json jsonb,
    report_text text,
    created_at timestamptz not null default now(),

    constraint evidence_trust_financial_runs_confidence_range
        check (confidence is null or confidence between 0 and 1),
    constraint evidence_trust_financial_runs_score_ranges
        check (
            (risk is null or risk between 0 and 1)
            and (rule_score is null or rule_score between 0 and 1)
            and (model_score is null or model_score between 0 and 1)
        )
);

create index if not exists idx_evidence_trust_financial_runs_visit_id
    on evidence_trust_financial_runs (visit_id);

create table if not exists evidence_trust_financial_flags (
    run_id uuid not null references evidence_trust_financial_runs (run_id) on delete cascade,
    block text not null,
    code text not null,
    value smallint,
    severity text,
    reason text,
    measures jsonb not null default '{}'::jsonb,

    constraint evidence_trust_financial_flags_value_binary_or_unknown
        check (value is null or value in (0, 1)),
    primary key (run_id, block, code)
);

create index if not exists idx_evidence_trust_financial_flags_run_id
    on evidence_trust_financial_flags (run_id);
