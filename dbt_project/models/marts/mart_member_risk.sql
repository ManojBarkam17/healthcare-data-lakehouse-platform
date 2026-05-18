-- mart_member_risk.sql
-- Member risk stratification for care management targeting.
-- Combines claims spend, utilization, and diagnosis complexity
-- into a single risk tier.

with member_summary as (
    select * from {{ ref('int_member_claims_summary') }}
),

risk_scored as (
    select
        member_id,
        member_gender,
        member_state,
        member_plan_type,
        total_claims,
        total_claim_lines,
        total_charged,
        total_paid,
        denial_rate_pct,
        distinct_diagnoses,
        distinct_providers,
        first_service_date,
        last_service_date,

        -- Risk score components (percentile-based)
        -- Higher spend = higher risk
        percent_rank() over (order by total_paid) as spend_percentile,
        -- More diagnoses = higher complexity
        percent_rank() over (order by distinct_diagnoses) as complexity_percentile,
        -- More claims = higher utilization
        percent_rank() over (order by total_claims) as utilization_percentile

    from member_summary
),

tiered as (
    select
        *,
        -- Composite risk score (weighted average)
        round(
            (spend_percentile * 0.4)
            + (complexity_percentile * 0.35)
            + (utilization_percentile * 0.25),
            4
        ) as risk_score,

        -- Risk tier assignment
        case
            when (spend_percentile * 0.4 + complexity_percentile * 0.35 + utilization_percentile * 0.25) >= 0.85
                then 'Very High'
            when (spend_percentile * 0.4 + complexity_percentile * 0.35 + utilization_percentile * 0.25) >= 0.65
                then 'High'
            when (spend_percentile * 0.4 + complexity_percentile * 0.35 + utilization_percentile * 0.25) >= 0.35
                then 'Medium'
            else 'Low'
        end as risk_tier

    from risk_scored
)

select * from tiered
