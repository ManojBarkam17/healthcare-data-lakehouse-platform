-- mart_claims_summary.sql
-- Monthly claims analytics by payer and claim type.
-- Powers the executive dashboard and financial reporting.

with claims as (
    select * from {{ ref('int_claims_enriched') }}
),

monthly_summary as (
    select
        service_year_month,
        payer_name,
        payer_type,
        claim_type,
        claim_status,

        -- Volume
        count(distinct claim_id) as claim_count,
        count(claim_line_id) as line_count,
        count(distinct member_id) as unique_members,
        count(distinct provider_id) as unique_providers,

        -- Financial
        sum(line_charge_amount) as total_charged,
        sum(allowed_amount) as total_allowed,
        sum(paid_amount) as total_paid,
        sum(line_charge_amount) - sum(paid_amount) as total_write_off,
        avg(payment_ratio) as avg_payment_ratio,

        -- Per-claim averages
        round(sum(line_charge_amount) / nullif(count(distinct claim_id), 0), 2) as avg_charge_per_claim,
        round(sum(paid_amount) / nullif(count(distinct claim_id), 0), 2) as avg_paid_per_claim

    from claims
    group by 1, 2, 3, 4, 5
)

select * from monthly_summary
