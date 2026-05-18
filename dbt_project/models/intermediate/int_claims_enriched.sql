-- int_claims_enriched.sql
-- Claims joined with dimensional context for downstream analytics.
-- This is the single "wide" claims table that all marts query from.

with claims as (
    select * from {{ ref('stg_claims') }}
),

members as (
    select * from {{ ref('stg_members') }}
),

providers as (
    select * from {{ ref('stg_providers') }}
),

payers as (
    select * from {{ ref('stg_payers') }}
),

diagnoses as (
    select * from {{ ref('stg_diagnoses') }}
),

procedures as (
    select * from {{ ref('stg_procedures') }}
),

enriched as (
    select
        c.claim_id,
        c.claim_line_id,
        c.claim_type,
        c.claim_status,
        c.denial_reason,
        c.service_date,
        c.submission_date,
        c.days_to_submit,
        c.line_charge_amount,
        c.allowed_amount,
        c.paid_amount,
        c.payment_ratio,
        c.units,
        c.service_year_month,

        -- Member context
        c.member_id,
        m.gender as member_gender,
        m.state as member_state,
        m.plan_type as member_plan_type,
        m.date_of_birth as member_dob,

        -- Provider context
        c.provider_id,
        p.provider_full_name,
        p.specialty as provider_specialty,
        p.facility_name as provider_facility,
        p.state as provider_state,

        -- Payer context
        c.payer_id,
        py.payer_name,
        py.payer_type,

        -- Diagnosis context
        c.diagnosis_code,
        d.diagnosis_description,
        d.icd10_chapter,

        -- Procedure context
        c.procedure_code,
        pr.procedure_description

    from claims c
    left join members m on c.member_id = m.member_id
    left join providers p on c.provider_id = p.provider_id
    left join payers py on c.payer_id = py.payer_id
    left join diagnoses d on c.diagnosis_code = d.diagnosis_code
    left join procedures pr on c.procedure_code = pr.procedure_code
)

select * from enriched
