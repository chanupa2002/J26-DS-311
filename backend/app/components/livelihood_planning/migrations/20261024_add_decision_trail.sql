alter table public.livelihood_assessments
add column if not exists decision_trail jsonb;
