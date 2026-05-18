-- mart_denial_analysis.sql
-- Denial patterns by reason, payer, provider specialty, and month.
-- Identifies revenue recovery and process improvement opportunities.

with claims as (
    select * from {{ ref('int_claims_enriched') }}
),

denial_detail as (
    select
        service_year_month,
        payer_name,
        payer_type,
        provider_specialty,
        diagnosis_code,
        diagnosis_description,
        claim_status,
        denial_reason,

        count(distinct claim_id) as claim_count,
        sum(line_charge_amount) as total_charged,
        sum(paid_amount) as total_paid,
        sum(line_charge_amount) - sum(paid_amount) as revenue_at_risk

    from claims
    group by 1, 2, 3, 4, 5, 6, 7, 8
),

with_denial_metrics as (
    select
        *,
        -- Denial rate within each group
        round(
            sum(case when claim_status = 'denied' then claim_count else 0 end)
                over (partition by payer_name, service_year_month) * 100.0
            / nullif(
                sum(claim_count) over (partition by payer_name, service_year_month), 0
            ), 2
        ) as payer_monthly_denial_rate

    from denial_detail
)

select * from with_denial_metrics
