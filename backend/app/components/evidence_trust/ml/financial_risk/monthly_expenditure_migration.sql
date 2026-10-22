-- Run this once in the Supabase SQL editor for an existing database.
alter table public.evidence_trust_monitoring_visits
    add column if not exists grant_amount_lkr numeric(14, 2);

alter table public.evidence_trust_monitoring_visits
    add column if not exists monthly_expenditure_lkr numeric(14, 2);

alter table public.evidence_trust_monitoring_visits
    drop constraint if exists evidence_trust_monitoring_visits_amounts_nonnegative;

alter table public.evidence_trust_monitoring_visits
    add constraint evidence_trust_monitoring_visits_amounts_nonnegative
    check (
        (grant_amount_lkr is null or grant_amount_lkr >= 0)
        and
        (grant_spent_lkr is null or grant_spent_lkr >= 0)
        and (monthly_expenditure_lkr is null or monthly_expenditure_lkr >= 0)
        and (grant_remaining_lkr is null or grant_remaining_lkr >= 0)
        and (revenue_mid_lkr is null or revenue_mid_lkr >= 0)
        and (saved_amount_lkr is null or saved_amount_lkr >= 0)
    );
