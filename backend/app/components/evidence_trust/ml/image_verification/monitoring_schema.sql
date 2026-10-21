create table if not exists evidence_trust_monitoring (
    id uuid primary key default gen_random_uuid(),
    household_id text not null,
    division text,
    livelihood_category text,
    monitoring_year integer,
    monitoring_month text not null,
    monitoring_month_key text not null,
    image_reference text,
    content_hash text not null,
    phash text,
    dhash text,
    embedding jsonb,
    keypoints jsonb,
    descriptors jsonb,
    image_size jsonb,
    feature_metadata jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_evidence_trust_monitoring_household
    on evidence_trust_monitoring (household_id, monitoring_month_key);
create index if not exists idx_evidence_trust_monitoring_category
    on evidence_trust_monitoring (livelihood_category, monitoring_month_key);
