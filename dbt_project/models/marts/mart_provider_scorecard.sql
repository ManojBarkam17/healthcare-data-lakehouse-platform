-- mart_provider_scorecard.sql
-- Provider performance scorecard with efficiency rankings.
-- Supports network adequacy reviews and value-based contracting.

with provider_metrics as (
    select * from {{ ref('int_provider_performance') }}
),

scored as (
    select
        provider_id,
        provider_full_name,
        provider_specialty,
        provider_facility,
        provider_state,
        total_claims,
        unique_patients,
        total_charged,
        total_paid,
        avg_charge_per_line,
        avg_paid_per_line,
        denial_rate_pct,
        most_common_denial_reason,
        avg_payment_ratio,
        first_service_date,
        last_service_date,

        -- Efficiency rank (lower denial rate = better)
        rank() over (order by denial_rate_pct asc) as denial_rate_rank,

        -- Volume rank (higher volume = more active)
        rank() over (order by total_claims desc) as volume_rank,

        -- Cost efficiency (higher payment ratio = more efficient billing)
        rank() over (order by avg_payment_ratio desc) as efficiency_rank,

        -- Performance tier
        case
            when denial_rate_pct <= 10 and avg_payment_ratio >= 0.7 then 'Top Performer'
            when denial_rate_pct <= 20 and avg_payment_ratio >= 0.5 then 'Meets Expectations'
            when denial_rate_pct <= 30 then 'Needs Improvement'
            else 'Under Review'
        end as performance_tier

    from provider_metrics
)

select * from scored
