-- int_member_claims_summary.sql
-- Per-member claims aggregation used by risk stratification and cost marts.

with claims as (
    select * from {{ ref('int_claims_enriched') }}
),

member_summary as (
    select
        member_id,
        member_gender,
        member_state,
        member_plan_type,

        -- Volume metrics
        count(distinct claim_id) as total_claims,
        count(claim_line_id) as total_claim_lines,

        -- Financial metrics
        sum(line_charge_amount) as total_charged,
        sum(allowed_amount) as total_allowed,
        sum(paid_amount) as total_paid,
        avg(payment_ratio) as avg_payment_ratio,

        -- Denial metrics
        count(distinct case when claim_status = 'denied' then claim_id end) as denied_claims,
        round(
            count(distinct case when claim_status = 'denied' then claim_id end) * 100.0
            / nullif(count(distinct claim_id), 0), 2
        ) as denial_rate_pct,

        -- Utilization
        count(distinct diagnosis_code) as distinct_diagnoses,
        count(distinct provider_id) as distinct_providers,
        min(service_date) as first_service_date,
        max(service_date) as last_service_date

    from claims
    group by 1, 2, 3, 4
)

select * from member_summary
