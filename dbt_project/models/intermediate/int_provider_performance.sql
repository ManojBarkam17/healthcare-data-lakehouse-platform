-- int_provider_performance.sql
-- Per-provider performance metrics for network analysis.

with claims as (
    select * from {{ ref('int_claims_enriched') }}
),

provider_metrics as (
    select
        provider_id,
        provider_full_name,
        provider_specialty,
        provider_facility,
        provider_state,

        -- Volume
        count(distinct claim_id) as total_claims,
        count(distinct member_id) as unique_patients,
        count(claim_line_id) as total_lines,

        -- Financial
        sum(line_charge_amount) as total_charged,
        sum(paid_amount) as total_paid,
        avg(line_charge_amount) as avg_charge_per_line,
        avg(paid_amount) as avg_paid_per_line,

        -- Denial analysis
        count(distinct case when claim_status = 'denied' then claim_id end) as denied_claims,
        round(
            count(distinct case when claim_status = 'denied' then claim_id end) * 100.0
            / nullif(count(distinct claim_id), 0), 2
        ) as denial_rate_pct,

        -- Top denial reason
        mode(denial_reason) as most_common_denial_reason,

        -- Efficiency
        avg(payment_ratio) as avg_payment_ratio,
        min(service_date) as first_service_date,
        max(service_date) as last_service_date

    from claims
    group by 1, 2, 3, 4, 5
)

select * from provider_metrics
