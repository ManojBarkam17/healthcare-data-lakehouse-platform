-- stg_claims.sql
-- Claim lines enriched with header-level context.
-- Each row is one service line on a claim.

with source as (
    select * from {{ source('gold', 'fact_claims') }}
),

staged as (
    select
        claim_id,
        claim_line_id,
        member_id,
        provider_id,
        payer_id,
        claim_type,
        claim_status,
        denial_reason,
        service_date,
        submission_date,
        procedure_code,
        diagnosis_code,
        line_charge_amount,
        allowed_amount,
        paid_amount,
        units,
        line_number,
        service_year_month,

        -- Derived: days from service to submission
        submission_date - service_date as days_to_submit,

        -- Derived: payment ratio
        case
            when line_charge_amount > 0
            then round(paid_amount / line_charge_amount, 4)
            else 0
        end as payment_ratio

    from source
    where claim_id is not null
)

select * from staged
